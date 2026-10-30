"""EXPERIMENTAL, NOT USED IN THE PIPELINE.

Ran once on the 44-part board and produced 211 violations (duplicate stubs per
pad, vias too close together). Kept only as a record of the attempt.

DRC-driven repair: give every unconnected pad a via and a short stub.

Auto-routing leaves a handful of pads (mostly bottom-side power pads) without a
connection. Instead of guessing, this reads the DRC report, then for each
unconnected pad searches for a spot that is clear of other copper and drops a
via plus a short track there.
"""
import math
import re
import sys
from pathlib import Path

import pcbnew

BOARD = Path("hardware/custom_hat/rev_a/custom_hat_rev_a.kicad_pcb")
REPORT = Path("hardware/custom_hat/rev_a/drc.rpt")

PAD_RE = re.compile(
    r"@\(([\d.]+) mm, ([\d.]+) mm\): Pad (\S+) \[([^\]]+)\] of (\S+) on (\S+)"
)


def parse_pads():
    text = REPORT.read_text(encoding="utf-8", errors="replace")
    blocks = text.split("[unconnected_items]")
    pads = []
    for block in blocks[1:]:
        for m in PAD_RE.finditer(block):
            x, y, num, net, ref, layer = m.groups()
            pads.append((float(x), float(y), num, net, ref, layer))
    return pads


def clear_of(b, x, y, netname, need=0.45):
    for tr in b.GetTracks():
        if tr.GetNetname() == netname:
            continue
        if isinstance(tr, pcbnew.PCB_VIA):
            p = tr.GetPosition()
            if math.hypot(x - pcbnew.ToMM(p.x), y - pcbnew.ToMM(p.y)) < need + 0.3:
                return False
            continue
        s, e = tr.GetStart(), tr.GetEnd()
        x1, y1, x2, y2 = pcbnew.ToMM(s.x), pcbnew.ToMM(s.y), pcbnew.ToMM(e.x), pcbnew.ToMM(e.y)
        dx, dy = x2 - x1, y2 - y1
        if dx == 0 and dy == 0:
            d = math.hypot(x - x1, y - y1)
        else:
            t = max(0, min(1, ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy)))
            d = math.hypot(x - (x1 + t * dx), y - (y1 + t * dy))
        if d < need + pcbnew.ToMM(tr.GetWidth()) / 2:
            return False
    for fp in b.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNetname() == netname:
                continue
            bb = pad.GetBoundingBox()
            if (pcbnew.ToMM(bb.GetLeft()) - need < x < pcbnew.ToMM(bb.GetRight()) + need and
                    pcbnew.ToMM(bb.GetTop()) - need < y < pcbnew.ToMM(bb.GetBottom()) + need):
                return False
    return True


def main():
    pads = parse_pads()
    if not pads:
        print("no unconnected pads found")
        return
    b = pcbnew.LoadBoard(str(BOARD))
    nets = b.GetNetsByName()
    done = 0
    for x, y, num, net, ref, layer in pads:
        if net not in nets:
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
        spot = None
        for r in [0.5 * k for k in range(2, 9)]:
            for k in range(12):
                a = 2 * math.pi * k / 12
                vx, vy = x + r * math.cos(a), y + r * math.sin(a)
                if not (101 < vx < 164 and 101 < vy < 129):
                    continue
                if clear_of(b, vx, vy, net):
                    spot = (vx, vy)
                    break
            if spot:
                break
        if spot is None:
            print(f"no spot for {ref}.{num} [{net}]")
            continue
        v = pcbnew.PCB_VIA(b)
        v.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(spot[0]), pcbnew.FromMM(spot[1])))
        v.SetDrill(pcbnew.FromMM(0.3))
        v.SetWidth(pcbnew.FromMM(0.6))
        v.SetNet(nets[net])
        b.Add(v)
        t = pcbnew.PCB_TRACK(b)
        t.SetStart(target.GetPosition())
        t.SetEnd(v.GetPosition())
        t.SetWidth(pcbnew.FromMM(0.25))
        t.SetLayer(target.GetLayer())
        t.SetNet(nets[net])
        b.Add(t)
        done += 1
        print(f"{ref}.{num} [{net}] -> via at {spot[0]:.1f},{spot[1]:.1f}")
    f = pcbnew.ZONE_FILLER(b)
    f.Fill(b.Zones())
    pcbnew.SaveBoard(str(BOARD), b)
    print("stubs added:", done)


if __name__ == "__main__":
    main()
