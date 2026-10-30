"""Finish the ground connectivity: IMU ground stubs plus one plane-stitch via.

The pour cannot reach the 0.25 mm IMU pads, and the two outer ground pours need
a via to be electrically joined. Both are placed by searching for a point that
is clear of existing tracks and pads, instead of guessing coordinates.
"""
import math

import pcbnew

BOARD = "hardware/custom_hat/rev_a/custom_hat_rev_a.kicad_pcb"


def clear_point(b, x, y, need=0.75):
    """True when (x, y) mm is far enough from every track and pad."""
    for tr in b.GetTracks():
        if isinstance(tr, pcbnew.PCB_VIA):
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
            bb = pad.GetBoundingBox()
            if (pcbnew.ToMM(bb.GetLeft()) - need < x < pcbnew.ToMM(bb.GetRight()) + need and
                    pcbnew.ToMM(bb.GetTop()) - need < y < pcbnew.ToMM(bb.GetBottom()) + need):
                return False
    return True


def find_near(b, x0, y0, rmax=3.0):
    step = 0.25
    r = step
    while r <= rmax:
        for k in range(0, 24):
            a = 2 * math.pi * k / 24
            x, y = x0 + r * math.cos(a), y0 + r * math.sin(a)
            if 101 < x < 164 and 101 < y < 129.5 and clear_point(b, x, y):
                return x, y
        r += step
    return None


def add_via(b, net, x, y):
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
    v.SetDrill(pcbnew.FromMM(0.3))
    v.SetWidth(pcbnew.FromMM(0.6))
    v.SetNet(net)
    b.Add(v)
    return v


def main():
    b = pcbnew.LoadBoard(BOARD)
    gnd = b.GetNetsByName()["POWER_GND"]

    made = 0
    for fp in b.GetFootprints():
        if fp.GetReference() != "U501":
            continue
        for pad in fp.Pads():
            if pad.GetNetname() != "POWER_GND":
                continue
            p = pad.GetPosition()
            px, py = pcbnew.ToMM(p.x), pcbnew.ToMM(p.y)
            spot = find_near(b, px, py + 1.0)
            if spot is None:
                print(f"no clear spot near U501 pad {pad.GetNumber()}")
                continue
            v = add_via(b, gnd, *spot)
            t = pcbnew.PCB_TRACK(b)
            t.SetStart(p)
            t.SetEnd(v.GetPosition())
            t.SetWidth(pcbnew.FromMM(0.3))
            t.SetLayer(pcbnew.F_Cu)
            t.SetNet(gnd)
            b.Add(t)
            made += 1
            print(f"U501 pad {pad.GetNumber()} -> via at {spot[0]:.2f},{spot[1]:.2f}")

    # one more via just to join the two pours
    for probe in [(150.0, 110.0), (120.0, 120.0), (160.0, 120.0)]:
        if clear_point(b, *probe):
            add_via(b, gnd, *probe)
            print(f"plane stitch via at {probe}")
            break

    f = pcbnew.ZONE_FILLER(b)
    f.Fill(b.Zones())
    pcbnew.SaveBoard(BOARD, b)
    print("ground stubs added:", made)


if __name__ == "__main__":
    main()
