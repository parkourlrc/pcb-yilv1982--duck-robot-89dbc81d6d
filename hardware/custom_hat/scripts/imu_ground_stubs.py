"""Connect the BMI088 ground pads to the plane with a checked stub.

The 0.5 mm-pitch LGA pads are too small for the pour to reach, and blind vias
collided earlier. This checks both the via site and the whole stub path against
every other net before adding anything.
"""
import math

import pcbnew

BOARD = "hardware/custom_hat/rev_a/custom_hat_rev_a.kicad_pcb"
PAD_NETS = ("2", "4", "6", "10")


def dist_to_seg(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return math.hypot(px - x1, py - y1)
    t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


def main():
    b = pcbnew.LoadBoard(BOARD)
    gnd = b.GetNetsByName()["POWER_GND"]
    obstacles = []
    for tr in b.GetTracks():
        if isinstance(tr, pcbnew.PCB_VIA):
            p = tr.GetPosition()
            obstacles.append(("pt", pcbnew.ToMM(p.x), pcbnew.ToMM(p.y)))
            continue
        s, e = tr.GetStart(), tr.GetEnd()
        obstacles.append(("seg", pcbnew.ToMM(s.x), pcbnew.ToMM(s.y), pcbnew.ToMM(e.x), pcbnew.ToMM(e.y),
                          pcbnew.ToMM(tr.GetWidth())))
    boxes = []
    for fp in b.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNetname() == "POWER_GND":
                continue
            bb = pad.GetBoundingBox()
            boxes.append((pcbnew.ToMM(bb.GetLeft()), pcbnew.ToMM(bb.GetTop()),
                          pcbnew.ToMM(bb.GetRight()), pcbnew.ToMM(bb.GetBottom())))

    def path_clear(x1, y1, x2, y2, need=0.25):
        steps = max(4, int(math.hypot(x2 - x1, y2 - y1) / 0.1))
        for i in range(steps + 1):
            x = x1 + (x2 - x1) * i / steps
            y = y1 + (y2 - y1) * i / steps
            for ob in obstacles:
                if ob[0] == "pt":
                    if math.hypot(x - ob[1], y - ob[2]) < need + 0.3:
                        return False
                else:
                    if dist_to_seg(x, y, ob[1], ob[2], ob[3], ob[4]) < need + ob[5] / 2:
                        return False
            for bx1, by1, bx2, by2 in boxes:
                if bx1 - need < x < bx2 + need and by1 - need < y < by2 + need:
                    return False
        return True

    made = 0
    for fp in b.GetFootprints():
        if fp.GetReference() != "U501":
            continue
        for pad in fp.Pads():
            if pad.GetNumber() not in PAD_NETS or pad.GetNetname() != "POWER_GND":
                continue
            p = pad.GetPosition()
            px, py = pcbnew.ToMM(p.x), pcbnew.ToMM(p.y)
            done = False
            for r in [0.8, 1.0, 1.2, 1.5, 1.8, 2.2, 2.6]:
                for k in range(24):
                    a = 2 * math.pi * k / 24
                    vx, vy = px + r * math.cos(a), py + r * math.sin(a)
                    if not (101.2 < vx < 164 and 101.2 < vy < 129.4):
                        continue
                    if not path_clear(px, py, vx, vy):
                        continue
                    v = pcbnew.PCB_VIA(b)
                    v.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(vx), pcbnew.FromMM(vy)))
                    v.SetDrill(pcbnew.FromMM(0.3))
                    v.SetWidth(pcbnew.FromMM(0.6))
                    v.SetNet(gnd)
                    b.Add(v)
                    t = pcbnew.PCB_TRACK(b)
                    t.SetStart(p)
                    t.SetEnd(v.GetPosition())
                    t.SetWidth(pcbnew.FromMM(0.25))
                    t.SetLayer(pcbnew.F_Cu)
                    t.SetNet(gnd)
                    b.Add(t)
                    made += 1
                    print(f"U501.{pad.GetNumber()} stub to ({vx:.1f}, {vy:.1f})")
                    done = True
                    break
                if done:
                    break
            if not done:
                print(f"U501.{pad.GetNumber()}: no clear path")
    f = pcbnew.ZONE_FILLER(b)
    f.Fill(b.Zones())
    pcbnew.SaveBoard(BOARD, b)
    print("stubs:", made)


if __name__ == "__main__":
    main()
