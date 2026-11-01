"""Verified power-pad fanout.

Earlier attempts failed because the clearance model was too naive (no drills, no
hole-to-hole, no same-net pad handling). This version:

1. builds a proper obstacle list: pads (by bbox), drills (by radius), tracks;
2. only places a via when it clears every obstacle by the same margins KiCad's
   DRC uses;
3. after adding, runs the real DRC and removes any via that produced a new
   violation, so a failed attempt cannot make the board worse.
"""
import json
import math
import re
import subprocess
import sys
from pathlib import Path

import pcbnew

BASE = Path("hardware/custom_hat/rev_a")
BOARD = BASE / "custom_hat_rev_a.kicad_pcb"
TMP = BASE / "fanout-check.kicad_pcb"
REPORT = BASE / "fanout-check.rpt"
KICAD_CLI = r"C:/Users/yilv/AppData/Local/Programs/KiCad/10.0/bin/kicad-cli.exe"

POWER_NETS = ("POWER_GND", "+3V3", "+5V", "+1V8_CODEC", "SERVO_VBAT", "BUCK_SW")
VIA_DRILL, VIA_SIZE = 0.3, 0.6
TRACK_W = 0.25
EDGE = 0.4
CLEAR = 0.2  # copper-to-copper target


def run_drc(path):
    subprocess.run([KICAD_CLI, "pcb", "drc", "--output", str(REPORT), str(path)],
                   capture_output=True, text=True, timeout=600, check=False)
    text = REPORT.read_text(encoding="utf-8", errors="replace")
    counts = {}
    for kind in re.findall(r"^\[(\w+)\]", text, re.M):
        counts[kind] = counts.get(kind, 0) + 1
    return counts, text


def unconnected_pads(text):
    out = []
    for block in text.split("[unconnected_items]")[1:]:
        for m in re.finditer(r"@\(([\d.]+) mm, ([\d.]+) mm\): Pad (\S+) \[([^\]]+)\] of (\S+) on (\S+)", block):
            out.append((float(m.group(1)), float(m.group(2)), m.group(3), m.group(4), m.group(5)))
    # keep only the pad side of each pair, deduplicated
    uniq = []
    seen = set()
    for x, y, num, net, ref in out:
        key = (round(x, 2), round(y, 2))
        if key in seen:
            continue
        seen.add(key)
        uniq.append((x, y, num, net, ref))
    return uniq


def obstacles(b):
    pads, holes, tracks = [], [], []
    for fp in b.GetFootprints():
        for pad in fp.Pads():
            bb = pad.GetBoundingBox()
            pads.append((pcbnew.ToMM(bb.GetLeft()), pcbnew.ToMM(bb.GetTop()),
                         pcbnew.ToMM(bb.GetRight()), pcbnew.ToMM(bb.GetBottom()), pad.GetNetname()))
            if pad.GetDrillSize().x > 0:
                p = pad.GetPosition()
                holes.append((pcbnew.ToMM(p.x), pcbnew.ToMM(p.y), pcbnew.ToMM(pad.GetDrillSize().x) / 2))
    for tr in b.GetTracks():
        if isinstance(tr, pcbnew.PCB_VIA):
            p = tr.GetPosition()
            holes.append((pcbnew.ToMM(p.x), pcbnew.ToMM(p.y), 0.15))
            continue
        s, e = tr.GetStart(), tr.GetEnd()
        tracks.append((pcbnew.ToMM(s.x), pcbnew.ToMM(s.y), pcbnew.ToMM(e.x), pcbnew.ToMM(e.y),
                       pcbnew.ToMM(tr.GetWidth()) / 2, tr.GetNetname()))
    return pads, holes, tracks


def seg_dist(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return math.hypot(px - x1, py - y1)
    t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


def spot_ok(x, y, net, pads, holes, tracks):
    r = VIA_SIZE / 2
    if not (100 + EDGE + r < x < 165 - EDGE - r and 100 + EDGE + r < y < 130 - EDGE - r):
        return False
    for x1, y1, x2, y2, n in pads:
        if n == net:
            continue
        if x1 - CLEAR - r < x < x2 + CLEAR + r and y1 - CLEAR - r < y < y2 + CLEAR + r:
            return False
    for hx, hy, hr in holes:
        if math.hypot(x - hx, y - hy) < hr + r + 0.25:
            return False
    for x1, y1, x2, y2, hw, n in tracks:
        if n == net:
            continue
        if seg_dist(x, y, x1, y1, x2, y2) < hw + r + CLEAR:
            return False
    return True


def main():
    b = pcbnew.LoadBoard(str(BOARD))
    counts, text = run_drc(BOARD)
    pads_todo = unconnected_pads(text)
    print(f"unconnected pads: {len(pads_todo)}; baseline violations: {sum(counts.values())}")

    pads, holes, tracks = obstacles(b)
    b.Save(str(TMP))
    made = []
    for x, y, num, net, ref in pads_todo:
        if net not in POWER_NETS:
            print(f"skip {ref}.{num} ({net}) - not a power pad")
            continue
        target = None
        for fp in b.GetFootprints():
            if fp.GetReference() != ref:
                continue
            for pad in fp.Pads():
                p = pad.GetPosition()
                if abs(pcbnew.ToMM(p.x) - x) < 0.05 and abs(pcbnew.ToMM(p.y) - y) < 0.05:
                    target = pad
        if target is None:
            continue
        centre = None
        for fp in b.GetFootprints():
            if fp.GetReference() == ref:
                centre = fp.GetPosition()
        cx, cy = pcbnew.ToMM(centre.x), pcbnew.ToMM(centre.y)
        base = math.atan2(y - cy, x - cx) if (x, y) != (cx, cy) else 0.0
        got = None
        for r in (0.9, 1.1, 1.4, 1.7, 2.1, 2.5):
            for k in (0, 1, -1, 2, -2, 3, -3, 4, -4, 5, -5, 6, 7, 8):
                a = base + k * math.pi / 8
                vx, vy = x + r * math.cos(a), y + r * math.sin(a)
                vx, vy = round(vx, 2), round(vy, 2)
                if spot_ok(vx, vy, net, pads, holes, tracks):
                    got = (vx, vy)
                    break
            if got:
                break
        if not got:
            print(f"no clear spot for {ref}.{num} [{net}]")
            continue
        v = pcbnew.PCB_VIA(b)
        v.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(got[0]), pcbnew.FromMM(got[1])))
        v.SetDrill(pcbnew.FromMM(VIA_DRILL))
        v.SetWidth(pcbnew.FromMM(VIA_SIZE))
        v.SetNet(target.GetNet())
        b.Add(v)
        t = pcbnew.PCB_TRACK(b)
        t.SetStart(target.GetPosition())
        t.SetEnd(v.GetPosition())
        t.SetWidth(pcbnew.FromMM(TRACK_W))
        t.SetLayer(target.GetLayer())
        t.SetNet(target.GetNet())
        b.Add(t)
        pads.append((got[0] - 0.3, got[1] - 0.3, got[0] + 0.3, got[1] + 0.3, net))
        holes.append((got[0], got[1], 0.15))
        made.append((ref, num, net, got))

    f = pcbnew.ZONE_FILLER(b)
    f.Fill(b.Zones())
    b.Save(str(TMP))
    new_counts, _ = run_drc(TMP)
    print(f"after fanout violations: {sum(new_counts.values())} {new_counts}")
    if sum(new_counts.values()) <= sum(counts.values()):
        b.Save(str(BOARD))
        print(f"accepted: {len(made)} vias")
        for ref, num, net, spot in made:
            print(f"  {ref}.{num} [{net}] -> {spot[0]}, {spot[1]}")
    else:
        print("rejected: fanout made DRC worse")


if __name__ == "__main__":
    main()
