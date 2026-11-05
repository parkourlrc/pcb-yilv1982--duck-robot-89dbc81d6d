"""Audit final Gerber mask flashes against native pads and nearby copper/holes."""
import csv
from datetime import datetime
import json
from pathlib import Path

import pcbnew
import pipeline
from export_dnp_stencil import paste_flashes

EVIDENCE = pipeline.BASE.parents[1] / "docs/references/扩展板邮票孔与电源修复"


def validate_macros(macros):
    expected = ["4,1,4,$2,$3,$4,$5,$6,$7,$8,$9,$2,$3,0*",
                "1,1,$1+$1,$2,$3*", "1,1,$1+$1,$4,$5*", "1,1,$1+$1,$6,$7*", "1,1,$1+$1,$8,$9*",
                "20,1,$1+$1,$2,$3,$4,$5,0*", "20,1,$1+$1,$4,$5,$6,$7,0*",
                "20,1,$1+$1,$6,$7,$8,$9,0*", "20,1,$1+$1,$8,$9,$2,$3,0*"]
    if len(macros) != 1 or not macros[0].startswith("%AMRoundRect*"):
        raise RuntimeError("Unreviewed mask aperture macro")
    primitives = [line.strip().rstrip("%") for line in macros[0].splitlines()
                  if line.strip() and not line.startswith(("%AM", "0 "))]
    if primitives != expected:
        raise RuntimeError("Mask macro differs from the reviewed rounded-rectangle construction")


def geometry(definition):
    family, parameters = definition.split(",", 1)
    values = [float(value) for value in parameters.split("X")]
    if family == "C" and len(values) == 1:
        return "circle", values[0], values[0], values[0]/2
    if family in {"R", "O"} and len(values) == 2:
        return ("rectangle" if family == "R" else "oval"), values[0], values[1], 0
    if family == "RoundRect" and len(values) == 10 and values[-1] == 0:
        radius = values[0]
        xs, ys = values[1:9:2], values[2:9:2]
        if len(set(xs)) != 2 or len(set(ys)) != 2 or abs(min(xs)+max(xs))+abs(min(ys)+max(ys)) > 1e-8:
            raise RuntimeError("Unreviewed rotated or offset mask macro")
        return "roundrect", max(xs)-min(xs)+2*radius, max(ys)-min(ys)+2*radius, radius
    raise RuntimeError("Unreviewed mask aperture: " + definition)


def shape_from_flash(parent, center, data):
    kind, width, height, radius = data
    pad = pcbnew.PAD(parent)
    pad.SetShape({"circle": pcbnew.PAD_SHAPE_CIRCLE, "rectangle": pcbnew.PAD_SHAPE_RECT,
                  "oval": pcbnew.PAD_SHAPE_OVAL, "roundrect": pcbnew.PAD_SHAPE_ROUNDRECT}[kind])
    pad.SetSize(pcbnew.VECTOR2I(pcbnew.FromMM(width), pcbnew.FromMM(height)))
    pad.SetPosition(pcbnew.VECTOR2I(*center))
    if kind == "roundrect":
        pad.SetRoundRectRadiusRatio(radius/min(width, height))
    return pad


def separation(first, second, maximum):
    if not first.Collide(second, pcbnew.FromMM(maximum)):
        return None
    low, high = 0, pcbnew.FromMM(maximum)
    while low < high:
        middle = (low+high)//2
        if first.Collide(second, middle):
            high = middle
        else:
            low = middle+1
    return pcbnew.ToMM(high)


def main():
    checkpoint = pipeline.current_checkpoint()
    binding = json.loads((EVIDENCE / "pcba-review-bundle.json").read_text(encoding="utf-8"))
    package = (pipeline.BASE.parents[1] / binding["archive"]).with_suffix("")
    panel_path = pipeline.BASE / "panels/a1-smt-2up-20261102-r18/hat_a1_smt_2up.kicad_pcb"
    if pipeline.digest(panel_path) != binding["panel_sha256"] or binding["pcb_sha256"] != checkpoint["pcb_sha256"]:
        raise RuntimeError("Stale panel/package identity")
    board = pcbnew.LoadBoard(str(panel_path))
    parent = pcbnew.FOOTPRINT(board)
    rows, matches, narrow, foreign, holes = [], [], [], [], []
    source_shapes = {pcbnew.PAD_SHAPE_CIRCLE: "circle", pcbnew.PAD_SHAPE_RECT: "rectangle",
                     pcbnew.PAD_SHAPE_OVAL: "oval", pcbnew.PAD_SHAPE_ROUNDRECT: "roundrect"}
    vias = [track for track in board.GetTracks() if track.Type() == pcbnew.PCB_VIA_T]
    for side, mask, filename in [(pcbnew.F_Cu, pcbnew.F_Mask, "hat_a1_smt_2up-F_Mask.gts"),
                                 (pcbnew.B_Cu, pcbnew.B_Mask, "hat_a1_smt_2up-B_Mask.gbs")]:
        if any(not via.IsTented(side) for via in vias):
            raise RuntimeError("Non-tented via requires explicit aperture matching")
        if any(shape.GetLayer() == mask for shape in board.GetDrawings()):
            raise RuntimeError("Board-level mask graphics require additional audit")
        native = {}
        for footprint in board.GetFootprints():
            if any(item.GetLayer() == mask for item in footprint.GraphicalItems()):
                raise RuntimeError("Footprint mask graphics require additional audit")
            for pad in footprint.Pads():
                if not pad.IsOnLayer(mask):
                    continue
                center = (pad.GetPosition().x, -pad.GetPosition().y)
                if center in native:
                    raise RuntimeError("Coincident native mask pads need union matching")
                native[center] = (footprint.GetReference(), pad)
        flashes, macros = paste_flashes(package / filename)
        validate_macros(macros)
        apertures = []
        for key, count in flashes.items():
            _, xpos, cam_y, definition = key
            if count != 1 or (xpos, cam_y) not in native:
                raise RuntimeError("Unexpected or duplicated mask flash")
            reference, pad = native.pop((xpos, cam_y))
            data = geometry(definition)
            kind, width, height, radius = data
            expansion = pcbnew.ToMM(pad.GetSolderMaskExpansion(mask))
            expected_width, expected_height = [pcbnew.ToMM(value)+2*expansion for value in pad.GetSize(side)]
            rotation = pad.GetOrientationDegrees() % 180
            if abs(rotation-90) < 1e-6:
                expected_width, expected_height = expected_height, expected_width
            elif abs(rotation) > 1e-6:
                raise RuntimeError("Non-orthogonal native pad")
            expected_kind = source_shapes[pad.GetShape(side)]
            if kind != expected_kind or abs(width-expected_width)+abs(height-expected_height) > 2e-6:
                raise RuntimeError("Mask/native dimensions differ: " + reference + "." + pad.GetNumber())
            if kind == "roundrect" and abs(radius-pcbnew.ToMM(pad.GetRoundRectCornerRadius(side))-expansion) > 1e-6:
                raise RuntimeError("Mask/native corner radius differs")
            synthetic = shape_from_flash(parent, (xpos, -cam_y), data)
            apertures.append({"reference": reference, "pin": pad.GetNumber(), "net": pad.GetNetname(),
                              "shape_pad": synthetic, "native_pad": pad, "geometry": data})
            matches.append({"side": board.GetLayerName(mask), "reference": reference, "pin": pad.GetNumber(),
                            "position_mm": [xpos/1e6, -cam_y/1e6], "shape": kind,
                            "width_mm": width, "height_mm": height, "radius_mm": radius, "expansion_mm": expansion})
        if native:
            raise RuntimeError("Native mask pads missing from Gerber")
        for index, opening in enumerate(apertures):
            shape = opening["shape_pad"].GetEffectiveShape(pcbnew.F_Cu)
            identifier = opening["reference"] + "." + opening["pin"]
            for second in apertures[index+1:]:
                distance = separation(shape, second["shape_pad"].GetEffectiveShape(pcbnew.F_Cu), .3)
                if distance is not None:
                    narrow.append({"mask_layer": board.GetLayerName(mask), "openings": [identifier, second["reference"]+"."+second["pin"]],
                                   "nominal_gap_mm": distance, "different_nets": opening["net"] != second["net"]})
            for footprint in board.GetFootprints():
                for pad in footprint.Pads():
                    if not pad.IsOnLayer(side) or pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH or pad == opening["native_pad"]:
                        continue
                    if pad.GetNetname() == opening["net"]:
                        continue
                    if shape.Collide(pad.GetEffectiveShape(side), 0):
                        foreign.append({"opening": identifier, "mask_layer": board.GetLayerName(mask),
                                        "copper": footprint.GetReference()+"."+pad.GetNumber(), "net": pad.GetNetname()})
            for track in board.GetTracks():
                if track.IsOnLayer(side) and track.GetNetname() != opening["net"] and shape.Collide(track.GetEffectiveShape(side), 0):
                    foreign.append({"opening": identifier, "mask_layer": board.GetLayerName(mask),
                                    "copper": track.m_Uuid.AsString(), "net": track.GetNetname()})
            for zone in board.Zones():
                if zone.IsOnLayer(side) and zone.GetNetname() != opening["net"] and zone.GetFilledPolysList(side).Collide(shape, 0):
                    foreign.append({"opening": identifier, "mask_layer": board.GetLayerName(mask),
                                    "copper": zone.m_Uuid.AsString(), "net": zone.GetNetname()})
            for via in vias:
                if shape.Collide(via.GetPosition(), via.GetDrillValue()//2):
                    filled = via.GetFillingMode() == pcbnew.FILLING_MODE_FILLED and via.GetCappingMode() == pcbnew.CAPPING_MODE_CAPPED
                    holes.append({"opening": identifier, "mask_layer": board.GetLayerName(mask), "via": via.m_Uuid.AsString(),
                                  "filled_and_capped": filled, "same_net": via.GetNetname() == opening["net"]})
        rows.append({"layer": board.GetLayerName(mask), "matched_apertures": len(apertures), "file_sha256": pipeline.digest(package/filename)})
    violations = [row for row in narrow if row["nominal_gap_mm"] < .1-1e-6]
    unfilled = [row for row in holes if not row["filled_and_capped"]]
    with (package / "via-process-requirements.csv").open(encoding="utf-8-sig", newline="") as stream:
        required_vias = {row["UUID"] for row in csv.DictReader(stream)}
    pofv_matches = {row["via"] for row in holes} == required_vias and len(holes) == 12
    negative_first = shape_from_flash(parent, (0, 0), ("rectangle", 1, 1, 0))
    negative_second = shape_from_flash(parent, (1050000, 0), ("rectangle", 1, 1, 0))
    probe = separation(negative_first.GetEffectiveShape(pcbnew.F_Cu), negative_second.GetEffectiveShape(pcbnew.F_Cu), .3)
    if probe is None or abs(probe-.05) > 1e-6:
        raise RuntimeError("Mask geometry negative control failed")
    result = {"date": datetime.now().date().isoformat(), "pcb_sha256": checkpoint["pcb_sha256"], "panel_sha256": binding["panel_sha256"],
              "archive": binding["archive"], "layers": rows, "total_apertures": len(matches),
              "minimum_distinct_mask_opening_gap_mm": min(row["nominal_gap_mm"] for row in narrow),
              "pairs_within_0p3mm": narrow, "below_0p1mm": violations, "foreign_net_exposures": foreign,
              "mask_openings_over_via_holes": holes, "unfilled_via_holes_exposed": unfilled,
              "exposed_vias_match_all_12_pofv_requirements": pofv_matches,
              "aperture_geometry_matches": matches, "negative_control_gap_mm": probe,
              "nominal_mask_geometry_screen_pass": not violations and not foreign and not unfilled and pofv_matches,
              "source_unchanged": pipeline.current_checkpoint()["pcb_sha256"] == checkpoint["pcb_sha256"],
              "limits": ["No production-film adjustment or actual registration tolerance measured",
                         "Archived domestic green1oz minimum uses pad spacing; this check also measures actual mask opening spacing",
                         "Same-net exposed copper at pad connections is intentional and not treated as foreign-net exposure",
                         "Mask aperture matching covers current primitive families only, rejects unrecognized geometry"],
              "manufacturing_released": False, "hardware_tested": False}
    pipeline.write_json(EVIDENCE / "mask-opening-audit.json", result)
    print(json.dumps({key: value for key, value in result.items() if key not in {"pairs_within_0p3mm", "aperture_geometry_matches", "mask_openings_over_via_holes"}}, ensure_ascii=False))
    if not result["nominal_mask_geometry_screen_pass"]:
        raise RuntimeError("Mask geometry has findings requiring review")


if __name__ == "__main__":
    main()
