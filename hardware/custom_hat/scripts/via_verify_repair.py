"""Add power fanout vias one at a time, letting KiCad's own DRC judge each one.

WHY: hand-written clearance approximations kept admitting vias that DRC then
rejected (see research notes 52-54). Instead of describing the geometry, this
proposes a via, runs the real DRC, and only keeps the change when the unconnected
count actually drops and no new violation category appears.
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pcbnew

BASE = Path("hardware/custom_hat/rev_a")
BOARD = BASE / "custom_hat_rev_a.kicad_pcb"
WORK = BASE / "via-work.kicad_pcb"
REPORT = BASE / "via-work.rpt"
CLI = r"C:/Users/yilv/AppData/Local/Programs/KiCad/10.0/bin/kicad-cli.exe"

POWER_NETS = {"POWER_GND", "+3V3", "+5V", "+1V8_CODEC", "SERVO_VBAT", "BUCK_SW"}
BAD = ("shorting_items", "clearance", "hole_clearance", "solder_mask_bridge", "items_not_allowed")
# dangling stubs are tolerated: they are cleaned up afterwards and do not create shorts
MAX_CANDIDATES = 4


def run_drc(path):
    subprocess.run([CLI, "pcb", "drc", "--refill-zones", "--output", str(REPORT), str(path)],
                   capture_output=True, text=True, timeout=600, check=False)
    text = REPORT.read_text(encoding="utf-8", errors="replace")
    counts = {}
    for kind in re.findall(r"^\[(\w+)\]", text, re.M):
        counts[kind] = counts.get(kind, 0) + 1
    return counts, text


def unconnected_pads(text):
    out, seen = [], set()
    for block in text.split("[unconnected_items]")[1:]:
        for m in re.finditer(r"@\(([\d.]+) mm, ([\d.]+) mm\): Pad (\S+) \[([^\]]+)\] of (\S+)", block):
            key = (m.group(5), m.group(3))
            if key in seen:
                continue
            seen.add(key)
            out.append((m.group(5), m.group(3), m.group(4)))
    return out


def candidates(b, ref, num):
    for fp in b.GetFootprints():
        if fp.GetReference() != ref:
            continue
        centre = fp.GetPosition()
        cx, cy = pcbnew.ToMM(centre.x), pcbnew.ToMM(centre.y)
        for pad in fp.Pads():
            if pad.GetNumber() != num:
                continue
            p = pad.GetPosition()
            px, py = pcbnew.ToMM(p.x), pcbnew.ToMM(p.y)
            import math
            base = math.atan2(py - cy, px - cx) if (px, py) != (cx, cy) else 0.0
            for r in (0.6, 0.8, 1.0, 1.3):
                for k in (0, 1, -1, 2, -2, 3, -3, 4):
                    a = base + k * math.pi / 8
                    yield pad, (round(px + r * math.cos(a), 2), round(py + r * math.sin(a), 2))


def main():
    base_counts, text = run_drc(BOARD)
    base_unconn = base_counts.get("unconnected_items", 0)
    print(f"baseline: {base_counts} total={sum(base_counts.values())}")
    pads = [p for p in unconnected_pads(text) if p[2] in POWER_NETS]
    print(f"power pads to try: {len(pads)}")

    for ref, num, net in pads:
        improved = False
        for pad, (vx, vy) in list(candidates(pcbnew.LoadBoard(str(BOARD)), ref, num))[:MAX_CANDIDATES]:
            b = pcbnew.LoadBoard(str(BOARD))
            target = None
            for fp in b.GetFootprints():
                if fp.GetReference() != ref:
                    continue
                for p in fp.Pads():
                    if p.GetNumber() == num:
                        target = p
            if target is None:
                break
            v = pcbnew.PCB_VIA(b)
            v.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(vx), pcbnew.FromMM(vy)))
            v.SetDrill(pcbnew.FromMM(0.3))
            v.SetWidth(pcbnew.FromMM(0.6))
            v.SetNet(target.GetNet())
            b.Add(v)
            t = pcbnew.PCB_TRACK(b)
            t.SetStart(target.GetPosition())
            t.SetEnd(v.GetPosition())
            t.SetWidth(pcbnew.FromMM(0.25))
            t.SetLayer(target.GetLayer())
            t.SetNet(target.GetNet())
            b.Add(t)
            b.Save(str(WORK))
            counts, _ = run_drc(WORK)
            worse = any(counts.get(k, 0) > base_counts.get(k, 0) for k in BAD)
            better = counts.get("unconnected_items", 0) < base_counts.get("unconnected_items", 0)
            print(f"  {ref}.{num} at {vx},{vy}: unconn {base_counts.get('unconnected_items')}->"
                  f"{counts.get('unconnected_items')} worse={worse}")
            if better and not worse:
                shutil.copyfile(WORK, BOARD)
                base_counts = counts
                improved = True
                break
        if not improved:
            print(f"  no accepted via for {ref}.{num}")

    final_counts, _ = run_drc(BOARD)
    print(f"final: {final_counts} total={sum(final_counts.values())}")


if __name__ == "__main__":
    main()
