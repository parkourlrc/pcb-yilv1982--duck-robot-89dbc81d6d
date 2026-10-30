"""Build the Rev A PCB skeleton: outline, mounting holes, power block, staging.

Status: skeleton, nothing routed and nothing final:
- board outline is the Pi-Zero-class 65 x 30.9 mm used by the reference HAT;
- the four M2.5 holes follow the Pi Zero pattern (3.5 mm from each edge);
- J101 is placed so pad 1 sits at (8.37, 3.5) mm, i.e. a 40-pin header centred
  between the corner holes - this still needs checking against the Radxa Zero
  3W mechanical drawing;
- parts outside the power block are parked in a row above the board (staging),
  because the full HAT placement is not designed yet.

Run with KiCad's bundled Python.
"""
import json
from pathlib import Path

import math

import pcbnew

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / "rev_a"
CONTRACT = OUT / "net-contract.json"
BOARD_FILE = OUT / "custom_hat_rev_a.kicad_pcb"
FPLIB = Path("C:/Users/yilv/AppData/Local/Programs/KiCad/10.0/share/kicad/footprints")
LOCAL_FPLIB = OUT

BOARD_W = 65.0
BOARD_H = 30.0
ORIGIN = (100.0, 100.0)

# Pi Zero class hole pattern, pending Radxa drawing check.
HOLES = [(3.6, 3.6), (61.4, 3.6), (3.6, 26.4), (61.4, 26.4)]

LAYOUT = {
    "J101": (8.32, 4.59, 90),
    "D301": (15.5, 11.5, 0),
    "R305": (15.5, 16.5, 0),
    "C303": (15.5, 20.0, 0),
    "C304": (15.5, 23.0, 0),
    "U301": (26.0, 14.0, 0),
    "L301": (38.0, 15.9, 0),
    "C302": (26.0, 19.0, 0),
    "R303": (26.0, 22.5, 0),
    "C305": (49.0, 14.0, 0),
    "C306": (54.0, 14.0, 0),
    "C307": (59.0, 14.0, 0),
    "R301": (38.0, 24.2, 0),
    "R302": (43.0, 24.2, 0),
    "R304": (48.0, 24.2, 0),
    "C301": (53.0, 24.2, 0),
}

# preferred anchors for auto-placement (board-local mm). The placer searches a
# grid, rejects courtyard overlaps / hole keepouts / board-edge violations and
# picks the candidate closest to the anchor.
ANCHORS = {
    "C319": (44.0, 12.0),
    "C320": (48.0, 12.0),
    "TP802": (24.0, 9.2),
    "J505": (26.0, 26.0),
    "J506": (14.0, 26.0),
    "U803": (19.0, 20.0),
    "R311": (23.0, 16.0),
    "R312": (27.0, 16.0),
    "C321": (31.0, 16.0),
    "C322": (35.0, 16.0),
    "C323": (39.0, 16.0),
    "C325": (43.0, 16.0),
    "C326": (47.0, 16.0),
    "C327": (51.0, 16.0),
    "U801": (34.0, 20.0),
    "U802": (38.0, 20.0),
    "R309": (22.0, 20.0),
    "R310": (42.0, 20.0),
    "J504": (41.0, 6.0),
    "C317": (44.5, 6.0),
    "C318": (47.5, 6.0),
    "TP801": (24.0, 9.2),
    "TP803": (32.0, 9.2),
    "TP804": (36.0, 9.2),
    "U702": (30.0, 20.0),
    "R308": (47.0, 9.5),
    "C310": (50.0, 9.5),
    "C311": (53.0, 9.5),
    "C312": (56.0, 9.5),
    "C313": (59.0, 9.5),
    "C314": (56.0, 20.0),
    "C315": (62.0, 9.5),
    "C316": (60.0, 20.0),
                "C308": (24.0, 20.0),
    "C309": (36.0, 20.0),
    "J301": (15.0, 28.0),
    "J401": (36.0, 28.0),
    "J402": (47.0, 28.0),
    "J403": (60.0, 28.0),
    "J502": (61.0, 9.5),
    "J802": (56.0, 7.6),
    "U501": (57.0, 26.0),
    "U701": (59.0, 19.0),
}
HOLE_KEEPOUT_R = 2.4
EDGE_MARGIN = 0.6


def read_footprints_from_netlist():
    import re

    text = (OUT / "custom_hat_rev_a.net").read_text(encoding="utf-8")
    result = {}
    for block in re.split(r"\(comp\s*\n", text)[1:]:
        ref = re.search(r'\(ref "([^"]+)"\)', block)
        val = re.search(r'\(value "([^"]*)"\)', block)
        fp = re.search(r'\(footprint "([^"]*)"\)', block)
        if ref and fp and fp.group(1):
            result[ref.group(1)] = (fp.group(1), val.group(1) if val else "")
    return result


def add_screen_keepout(board):
    """Draw the 98 x 55.5 screen outline centred on the board as a reference."""
    layer = getattr(pcbnew, "User_Drawings", pcbnew.F_Fab)
    x0 = (BOARD_W - SCREEN_W) / 2.0
    y0 = (BOARD_H - SCREEN_H) / 2.0
    corners = [(x0, y0), (x0 + SCREEN_W, y0), (x0 + SCREEN_W, y0 + SCREEN_H), (x0, y0 + SCREEN_H)]
    for i, (x1, y1) in enumerate(corners):
        x2, y2 = corners[(i + 1) % len(corners)]
        shape = pcbnew.PCB_SHAPE(board)
        shape.SetShape(pcbnew.SHAPE_T_SEGMENT)
        shape.SetLayer(layer)
        shape.SetWidth(pcbnew.FromMM(0.15))
        shape.SetStart(mm(x1, y1))
        shape.SetEnd(mm(x2, y2))
        board.Add(shape)


def add_outline(board):
    corners = [(0, 0), (BOARD_W, 0), (BOARD_W, BOARD_H), (0, BOARD_H)]
    for i, (x1, y1) in enumerate(corners):
        x2, y2 = corners[(i + 1) % len(corners)]
        shape = pcbnew.PCB_SHAPE(board)
        shape.SetShape(pcbnew.SHAPE_T_SEGMENT)
        shape.SetLayer(pcbnew.Edge_Cuts)
        shape.SetWidth(pcbnew.FromMM(0.1))
        shape.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(ORIGIN[0] + x1), pcbnew.FromMM(ORIGIN[1] + y1)))
        shape.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(ORIGIN[0] + x2), pcbnew.FromMM(ORIGIN[1] + y2)))
        board.Add(shape)


def mm(x, y):
    return pcbnew.VECTOR2I(pcbnew.FromMM(ORIGIN[0] + x), pcbnew.FromMM(ORIGIN[1] + y))


def main():
    board = pcbnew.BOARD()
    board.SetFileName(str(BOARD_FILE))
    board.SetCopperLayerCount(int(__import__('os').environ.get('HAT_LAYERS', '4')))  # layer count is a cost decision
    add_outline(board)

    for i, (x, y) in enumerate(HOLES, 1):
        fp = pcbnew.FootprintLoad(str(FPLIB / "MountingHole.pretty"), "MountingHole_2.7mm_M2.5")
        if fp is None:
            raise SystemExit("mounting hole footprint missing")
        fp.SetReference(f"H{i}")
        fp.SetPosition(mm(x, y))
        board.Add(fp)

    net_pins = json.loads(CONTRACT.read_text(encoding="utf-8"))["pins"]
    pin_map = {}
    for pin in net_pins:
        pin_map.setdefault(pin["reference"], {})[str(pin["pin"])] = pin["net"]

    net_cache = {}

    def net_for(name):
        if name is None:
            return None
        if name not in net_cache:
            item = pcbnew.NETINFO_ITEM(board, name)
            board.Add(item)
            net_cache[name] = item
        return net_cache[name]

    parts = read_footprints_from_netlist()
    placed, auto = [], []

    def bbox_of(fp):
        bb = fp.GetCourtyard(pcbnew.F_CrtYd).BBox()
        return (pcbnew.ToMM(bb.GetLeft()) - ORIGIN[0], pcbnew.ToMM(bb.GetTop()) - ORIGIN[1],
                pcbnew.ToMM(bb.GetRight()) - ORIGIN[0], pcbnew.ToMM(bb.GetBottom()) - ORIGIN[1])

    def hits(box, boxes, margin=0.45):
        x1, y1, x2, y2 = box
        for a1, b1, a2, b2 in boxes:
            if x1 < a2 + margin and a1 < x2 + margin and y1 < b2 + margin and b1 < y2 + margin:
                return True
        return False

    def inside(box):
        x1, y1, x2, y2 = box
        return x1 >= EDGE_MARGIN and y1 >= EDGE_MARGIN and x2 <= BOARD_W - EDGE_MARGIN and y2 <= BOARD_H - EDGE_MARGIN

    def hole_hit(box):
        x1, y1, x2, y2 = box
        for hx, hy in HOLES:
            if x1 < hx + HOLE_KEEPOUT_R and hx - HOLE_KEEPOUT_R < x2 and y1 < hy + HOLE_KEEPOUT_R and hy - HOLE_KEEPOUT_R < y2:
                return True
        return False

    occupied = []
    for ref in LAYOUT:
        pass

    for ref, (lib_id, value) in sorted(parts.items()):
        lib, name = lib_id.split(":", 1)
        root = LOCAL_FPLIB if lib == "duck" else FPLIB
        fp = pcbnew.FootprintLoad(str(root / (lib + ".pretty")), name)
        if fp is None:
            raise SystemExit(f"footprint load failed: {lib_id}")
        fp.SetReference(ref)
        fp.SetValue(value)
        if ref[0] in "RCLD":
            # keep silkscreen readable: passives get their reference on the fab
            # layer only, not printed on the board
            fp.Reference().SetVisible(False)
        if ref in LAYOUT:
            x, y, rot = LAYOUT[ref]
            placed.append(ref)
        else:
            x, y, rot = 0.0, 0.0, 0
            auto.append(ref)
        fp.SetPosition(mm(x, y))
        fp.SetOrientationDegrees(rot)
        if ref == "J101":
            # Reference HAT J4 numbers pin 1 on the row away from the board
            # edge (odd pads on the outer SMD tab row), so mirror the pad field
            # about the anchor row: pad1 stays at y, pad2 moves from y+2.54 to y-2.54.
            row = pcbnew.FromMM(ORIGIN[1] + y)
            for pad in fp.Pads():
                q = pad.GetPosition()
                pad.SetPosition(pcbnew.VECTOR2I(q.x, 2 * row - q.y))
            mark = pcbnew.PCB_TEXT(board)
            mark.SetText("1")
            mark.SetLayer(pcbnew.F_SilkS)
            mark.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(1.0), pcbnew.FromMM(1.0)))
            mark.SetPosition(mm(x - 1.6, y))
            board.Add(mark)
        for pad in fp.Pads():
            name_ = pin_map.get(ref, {}).get(pad.GetNumber())
            if name_ is not None:
                pad.SetNet(net_for(name_))
        board.Add(fp)

    # ---- second pass: auto-place, top side first then bottom side ----
    BOTTOM = {"U701", "J502", "U702", "C308", "C309", "R308",
              "C310", "C311", "C312", "C313", "C314", "C315", "C316", "C317", "C318", "J504", "U801", "U802", "R309", "R310", "C319", "C320", "TP802", "U803", "R311", "R312", "C321", "C322", "C323", "C325", "C326", "C327", "J505", "J506"}
    TOP_ONLY = {"J801"}  # through-hole: cannot be flipped to the bottom

    def bbox_of_layered(fp):
        layer = pcbnew.B_CrtYd if fp.GetLayer() == pcbnew.B_Cu else pcbnew.F_CrtYd
        bb = fp.GetCourtyard(layer).BBox()
        if not bb.GetWidth():
            bb = fp.GetBoundingBox(False)
        return (pcbnew.ToMM(bb.GetLeft()) - ORIGIN[0], pcbnew.ToMM(bb.GetTop()) - ORIGIN[1],
                pcbnew.ToMM(bb.GetRight()) - ORIGIN[0], pcbnew.ToMM(bb.GetBottom()) - ORIGIN[1])

    def try_place(ref, fp, occupied, bottom):
        if bottom and fp.GetLayer() != pcbnew.B_Cu:
            fp.Flip(fp.GetPosition(), False)
        if not bottom and fp.GetLayer() != pcbnew.F_Cu:
            fp.Flip(fp.GetPosition(), False)
        best = None
        for rot in (0, 90, 180, 270):
            fp.SetOrientationDegrees(rot)
            fp.SetPosition(mm(0, 0))
            bx1, by1, bx2, by2 = bbox_of_layered(fp)
            for gx in [round(2.0 + 1.27 * i, 2) for i in range(int((BOARD_W - 4.0) / 1.27) + 1)]:
                for gy in [round(7.0 + 1.27 * j, 2) for j in range(int((BOARD_H - 8.0) / 1.27) + 1)]:
                    box = (gx + bx1, gy + by1, gx + bx2, gy + by2)
                    if not inside(box) or hole_hit(box) or hits(box, occupied):
                        continue
                    ax, ay = ANCHORS.get(ref, (BOARD_W / 2, BOARD_H / 2))
                    cx, cy = (box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0
                    d = (cx - ax) ** 2 + (cy - ay) ** 2
                    if best is None or d < best[0]:
                        best = (d, gx, gy, rot, box)
        if best is None:
            return None
        _, gx, gy, rot, box = best
        fp.SetOrientationDegrees(rot)
        fp.SetPosition(mm(gx, gy))
        return box

    top_boxes = [bbox_of_layered(fp) for fp in board.GetFootprints()
                 if fp.GetReference() in LAYOUT]
    # through-hole parts block the bottom side too: their holes go through
    tht_boxes = []
    for fp in board.GetFootprints():
        if any(pad.GetDrillSize().x > 0 for pad in fp.Pads()):
            tht_boxes.append(bbox_of_layered(fp))
    pending = {fp.GetReference(): fp for fp in board.GetFootprints()
               if fp.GetReference() in ANCHORS and fp.GetReference() not in LAYOUT}

    order = ["J301", "J401", "J402", "J403", "J802", "U501", "TP801", "TP803", "TP804", "J502", "U701", "U702", "C308", "C309", "R308", "C310", "C311", "C312", "C313", "C314", "C315", "C316", "C317", "C318", "J504", "U801", "U802", "R309", "R310", "C319", "C320", "TP802", "U803", "R311", "R312", "C321", "C322", "C323", "C325", "C326", "C327", "J505", "J506"]
    placed_auto, bottom_placed, parked = [], [], []
    bottom_boxes = []
    for ref in order:
        fp = pending.get(ref)
        if fp is None:
            continue
        bottom = ref in BOTTOM
        occupied = top_boxes if not bottom else bottom_boxes + tht_boxes
        box = try_place(ref, fp, occupied, bottom)
        if box is None and bottom:
            box = try_place(ref, fp, top_boxes, False)
            bottom = False
        if box is None and not bottom and ref not in TOP_ONLY:
            box = try_place(ref, fp, bottom_boxes, True)
            bottom = True
        if box is None:
            park = len(parked)
            fp.SetPosition(mm(-30.0 - 12.0 * park, -20.0))
            parked.append(ref)
            continue
        if bottom:
            bottom_boxes.append(box)
            bottom_placed.append(ref)
        else:
            top_boxes.append(box)
            placed_auto.append(ref)
            if any(pad.GetDrillSize().x > 0 for pad in fp.Pads()):
                # through-hole copper/vias pass through the board: keep the
                # bottom side clear under this part as well
                tht_boxes.append(box)

    # ---- decoupling ring: put each IC's capacitors in a ring around it ----
    # This is the layout idea the recovery plan asks for: short power loops and
    # gaps between parts that a fanout via can actually use.
    RING = [("C311", "U701"), ("C312", "U701"), ("C313", "U701"), ("C315", "U701"),
            ("R308", "U701"), ("C310", "U701"), ("C319", "U501"), ("C320", "U501")]
    for cap_ref, ic_ref in RING:
        cap = next((fp for fp in board.GetFootprints() if fp.GetReference() == cap_ref), None)
        ic = next((fp for fp in board.GetFootprints() if fp.GetReference() == ic_ref), None)
        if cap is None or ic is None:
            continue
        ip = ic.GetPosition()
        ix, iy = pcbnew.ToMM(ip.x) - ORIGIN[0], pcbnew.ToMM(ip.y) - ORIGIN[1]
        others = [bbox_of_layered(fp) for fp in board.GetFootprints()
                  if fp.GetReference() != cap_ref]
        start_pos = cap.GetPosition()
        start_rot = cap.GetOrientationDegrees()
        placed_at = None
        for radius in (2.6, 3.0, 3.5, 4.0):
            for k in range(32):
                a = 2 * math.pi * k / 32
                x, y = ix + radius * math.cos(a), iy + radius * math.sin(a)
                cap.SetPosition(mm(x, y))
                bb = bbox_of_layered(cap)
                if inside(bb) and not hits(bb, others, 0.25):
                    placed_at = (round(x, 2), round(y, 2))
                    break
            if placed_at:
                break
        if placed_at:
            others.append(bbox_of_layered(cap))
            print(f"ring: {cap_ref} -> {placed_at} around {ic_ref}")
        else:
            cap.SetPosition(start_pos)
            cap.SetOrientationDegrees(start_rot)
            print(f"ring: no slot for {cap_ref}")

    # silkscreen hygiene: mounting holes and test pads need no reference text,
    # and a few references sit on top of connector silk
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        if ref.startswith("H") or ref.startswith("TP") or ref in ("J504", "J506", "U702", "U801", "U802"):
            fp.Reference().SetVisible(False)
        elif ref == "U301":
            fp.Reference().SetPosition(fp.GetPosition() + pcbnew.VECTOR2I(0, pcbnew.FromMM(-5.0)))
        elif ref == "J802":
            fp.Reference().SetPosition(fp.GetPosition() + pcbnew.VECTOR2I(0, pcbnew.FromMM(2.2)))

    # ---- net classes: power nets get a wider track than signals ----
    ns = board.GetDesignSettings().m_NetSettings
    default_nc = ns.GetDefaultNetclass()
    default_nc.SetTrackWidth(pcbnew.FromMM(0.25))
    default_nc.SetClearance(pcbnew.FromMM(0.15))
    power_nc = pcbnew.NETCLASS("Power")
    power_nc.SetTrackWidth(pcbnew.FromMM(0.8))
    power_nc.SetClearance(pcbnew.FromMM(0.2))
    power_nc.SetViaDiameter(pcbnew.FromMM(0.8))
    power_nc.SetViaDrill(pcbnew.FromMM(0.4))
    ns.SetNetclass("Power", power_nc)
    for name in ("+5V", "+3V3", "VBATT_2S_IN", "SERVO_VBAT", "BUCK_SW", "POWER_GND"):
        ns.SetNetclassPatternAssignment(name, "Power")
    print("netclasses: Power 0.8 mm, Default 0.25 mm")

    # ---- copper pours: F/B ground, In1 solid ground, In2 +3V3 plane ----
    gnd = net_cache.get("POWER_GND")
    if gnd is None:
        gnd = net_for("POWER_GND")
    rails = net_cache.get("+3V3")
    if rails is None:
        rails = net_for("+3V3")
    plan = [(pcbnew.F_Cu, gnd), (pcbnew.B_Cu, gnd), (pcbnew.In1_Cu, gnd), (pcbnew.In2_Cu, rails)]
    for layer, net in plan:
        zone = pcbnew.ZONE(board)
        zone.SetLayer(layer)
        zone.SetNet(net)
        zone.SetLocalClearance(pcbnew.FromMM(0.2))
        zone.SetMinThickness(pcbnew.FromMM(0.2))
        zone.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
        zone.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        outline = zone.Outline()
        pts = [(0.4, 0.4), (BOARD_W - 0.4, 0.4), (BOARD_W - 0.4, BOARD_H - 0.4), (0.4, BOARD_H - 0.4)]
        outline.NewOutline()
        for px, py in pts:
            outline.Append(pcbnew.VECTOR2I(pcbnew.FromMM(ORIGIN[0] + px), pcbnew.FromMM(ORIGIN[1] + py)))
        board.Add(zone)
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())

    pcbnew.SaveBoard(str(BOARD_FILE), board)
    print(f"fixed placement ({len(placed)}): {' '.join(placed)}")
    print(f"auto placement top ({len(placed_auto)}): {' '.join(placed_auto)}")
    print(f"auto placement bottom ({len(bottom_placed)}): {' '.join(bottom_placed)}")
    print(f"parked off-board ({len(parked)}): {' '.join(parked)}")
    print(f"board written to {BOARD_FILE}")


if __name__ == "__main__":
    raise SystemExit("Legacy generator disabled: it assigns nets from net-contract and overwrites the main PCB. Use pipeline.py prepare for a verified project copy.")
