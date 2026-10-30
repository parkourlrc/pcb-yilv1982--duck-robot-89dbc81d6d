"""Stitch decoupling capacitors to the inner planes, before routing.

The fine-pitch IC pads cannot host a via (see research note 52), but their
decoupling capacitors sit in open space. Connecting each capacitor's rail pad to
a via gives the net a path to the plane; the autorouter then only has to run the
short IC-pin-to-cap track.

Run on the freshly built, unrouted board so the via search still has room.
"""
import math
import re
import subprocess
from pathlib import Path

import pcbnew

BASE = Path("hardware/custom_hat/rev_a")
BOARD = BASE / "custom_hat_rev_a.kicad_pcb"
KICAD_CLI = r"C:/Users/yilv/AppData/Local/Programs/KiCad/10.0/bin/kicad-cli.exe"
REPORT = BASE / "stitch-check.rpt"

# capacitor -> rail pad number that faces the IC supply
CAP_RAILS = {
    "C311": "1", "C312": "1", "C313": "1", "C315": "1",
    "C319": "1", "C320": "1", "C305": "1", "C306": "1",
    "C308": "1", "C323": "1", "C309": "2",
}

VIA_DRILL, VIA_SIZE = 0.3, 0.6
TRACK_W = 0.25
CLEAR = 0.18


def seg_dist(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return math.hypot(px - x1, py - y1)
    t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


def main():
    b = pcbnew.LoadBoard(str(BOARD))
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
            holes.append((pcbnew.ToMM(p.x), pcbnew.ToMM(p.y), VIA_DRILL / 2))
            continue
        s, e = tr.GetStart(), tr.GetEnd()
        tracks.append((pcbnew.ToMM(s.x), pcbnew.ToMM(s.y), pcbnew.ToMM(e.x), pcbnew.ToMM(e.y),
                       pcbnew.ToMM(tr.GetWidth()) / 2, tr.GetNetname()))

    def ok(x, y, net):
        r = VIA_SIZE / 2
        if not (100.5 + r < x < 164.5 - r and 100.5 + r < y < 129.5 - r):  # absolute coords
            return False
        for x1, y1, x2, y2, n in pads:
            if n == net:
                continue
            if x1 - CLEAR - r < x < x2 + CLEAR + r and y1 - CLEAR - r < y < y2 + CLEAR + r:
                return False
        for hx, hy, hr in holes:
            if math.hypot(x - hx, y - hy) < hr + r + 0.2:
                return False
        for x1, y1, x2, y2, hw, n in tracks:
            if n == net:
                continue
            if seg_dist(x, y, x1, y1, x2, y2) < hw + r + CLEAR:
                return False
        return True

    made = 0
    for fp in b.GetFootprints():
        ref = fp.GetReference()
        if ref not in CAP_RAILS:
            continue
        pnum = CAP_RAILS[ref]
        pad = None
        for p in fp.Pads():
            if p.GetNumber() == pnum:
                pad = p
        if pad is None or not pad.GetNetname():
            continue
        net = pad.GetNetname()
        p = pad.GetPosition()
        px, py = pcbnew.ToMM(p.x), pcbnew.ToMM(p.y)
        got = None
        for r in (0.55, 0.7, 0.85, 1.0, 1.2):
            for k in range(16):
                a = 2 * math.pi * k / 16
                vx, vy = round(px + r * math.cos(a), 2), round(py + r * math.sin(a), 2)
                if ok(vx, vy, net):
                    got = (vx, vy)
                    break
            if got:
                break
        if not got:
            print(f"no spot for {ref}.{pnum} [{net}]")
            continue
        v = pcbnew.PCB_VIA(b)
        v.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(got[0]), pcbnew.FromMM(got[1])))
        v.SetDrill(pcbnew.FromMM(VIA_DRILL))
        v.SetWidth(pcbnew.FromMM(VIA_SIZE))
        v.SetNet(pad.GetNet())
        b.Add(v)
        t = pcbnew.PCB_TRACK(b)
        t.SetStart(p)
        t.SetEnd(v.GetPosition())
        t.SetWidth(pcbnew.FromMM(TRACK_W))
        t.SetLayer(pad.GetLayer())
        t.SetNet(pad.GetNet())
        b.Add(t)
        pads.append((got[0] - 0.3, got[1] - 0.3, got[0] + 0.3, got[1] + 0.3, net))
        holes.append((got[0], got[1], VIA_DRILL / 2))
        made += 1
        print(f"{ref}.{pnum} [{net}] -> via {got[0]},{got[1]}")

    f = pcbnew.ZONE_FILLER(b)
    f.Fill(b.Zones())
    b.Save(str(BOARD))
    print(f"cap stitches: {made}")


if __name__ == "__main__":
    main()
