"""Fan out every SMD power pad to a via, on the unrouted board.

FreeRouting treats ground/3V3 as planes and never adds stitching vias, so those
pads stay unconnected no matter how often the board is routed. Doing the fanout
before routing - on a board with no tracks yet - is the only reliable moment:
there is free space around every pad.

Rules that made earlier attempts fail: duplicate stubs for the same pad, vias
placed on other pads, and a clearance check that ignored pad extents. All three
are handled here.
"""
import math

import pcbnew

BOARD = "hardware/custom_hat/rev_a/custom_hat_rev_a.kicad_pcb"
POWER_NETS = ("POWER_GND", "+3V3", "+5V", "VBATT_2S_IN", "SERVO_VBAT", "+1V8_CODEC", "BUCK_SW")
VIA_DRILL = 0.3
VIA_SIZE = 0.6
TRACK_W = 0.25
CLEAR = 0.42  # via edge to foreign copper


def main():
    b = pcbnew.LoadBoard(BOARD)
    gnd_nets = b.GetNetsByName()

    pads_all = []
    for fp in b.GetFootprints():
        for pad in fp.Pads():
            bb = pad.GetBoundingBox()
            pads_all.append((pcbnew.ToMM(bb.GetLeft()), pcbnew.ToMM(bb.GetTop()),
                             pcbnew.ToMM(bb.GetRight()), pcbnew.ToMM(bb.GetBottom()),
                             pad.GetNetname(), fp.GetReference(), pad.GetNumber(),
                             pad.GetPosition()))

    # rule areas / keepouts: U501 has a documented no-copper area under the sensor
    keepouts = []
    for z in b.Zones():
        if z.GetIsRuleArea():
            keepouts.append(z.GetBoundingBox())
    for fp in b.GetFootprints():
        if fp.GetReference() == "U501":
            bb = fp.GetBoundingBox(False)
            keepouts.append(bb)

    vias = []
    for tr in b.GetTracks():
        if isinstance(tr, pcbnew.PCB_VIA):
            p = tr.GetPosition()
            vias.append((pcbnew.ToMM(p.x), pcbnew.ToMM(p.y)))

    def free(x, y, net):
        if not (101.3 < x < 163.7 and 101.3 < y < 128.7):  # absolute coords
            return False
        for ko in keepouts:
            if (pcbnew.ToMM(ko.GetLeft()) < x < pcbnew.ToMM(ko.GetRight()) and
                    pcbnew.ToMM(ko.GetTop()) < y < pcbnew.ToMM(ko.GetBottom())):
                return False
        for x1, y1, x2, y2, n, _, _, _ in pads_all:
            if n == net:
                continue
            if x1 - CLEAR < x < x2 + CLEAR and y1 - CLEAR < y < y2 + CLEAR:
                return False
        for vx, vy in vias:
            if math.hypot(x - vx, y - vy) < VIA_SIZE + 0.2:
                return False
        return True

    made = 0
    seen = set()
    for fp in b.GetFootprints():
        centre = fp.GetPosition()
        cx, cy = pcbnew.ToMM(centre.x), pcbnew.ToMM(centre.y)
        for pad in fp.Pads():
            net = pad.GetNetname()
            if net not in POWER_NETS:
                continue
            if pad.GetDrillSize().x > 0:
                continue  # through-hole already ties every layer
            key = (fp.GetReference(), pad.GetNumber())
            if key in seen:
                continue
            seen.add(key)
            p = pad.GetPosition()
            px, py = pcbnew.ToMM(p.x), pcbnew.ToMM(p.y)
            # prefer the direction pointing away from the part centre
            base = math.atan2(py - cy, px - cx) if (px, py) != (cx, cy) else 0.0
            got = None
            for r in (0.9, 1.1, 1.3, 1.6, 1.9, 2.3):
                for k in (0, 1, -1, 2, -2, 3, -3, 4, -4, 5, -5, 6):
                    a = base + k * math.pi / 8
                    vx, vy = px + r * math.cos(a), py + r * math.sin(a)
                    if free(vx, vy, net):
                        got = (vx, vy)
                        break
                if got:
                    break
            if not got:
                continue
            v = pcbnew.PCB_VIA(b)
            v.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(got[0]), pcbnew.FromMM(got[1])))
            v.SetDrill(pcbnew.FromMM(VIA_DRILL))
            v.SetWidth(pcbnew.FromMM(VIA_SIZE))
            v.SetNet(pad.GetNet())
            b.Add(v)
            vias.append(got)
            t = pcbnew.PCB_TRACK(b)
            t.SetStart(p)
            t.SetEnd(v.GetPosition())
            t.SetWidth(pcbnew.FromMM(TRACK_W))
            t.SetLayer(pad.GetLayer())
            t.SetNet(pad.GetNet())
            b.Add(t)
            made += 1

    f = pcbnew.ZONE_FILLER(b)
    f.Fill(b.Zones())
    pcbnew.SaveBoard(BOARD, b)
    print(f"power fanout: {made} pads stitched")


if __name__ == "__main__":
    main()
