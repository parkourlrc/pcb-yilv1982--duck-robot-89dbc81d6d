"""Read the unchanged HAT geometry against the archived domestic JLC via limits."""
from collections import Counter
import argparse
import csv
import json
import math
from pathlib import Path

import pcbnew
import pipeline


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence',type=Path)
    arguments=parser.parse_args()
    checkpoint = pipeline.current_checkpoint()
    root = pipeline.BASE.parents[1]
    evidence = arguments.evidence.resolve() if arguments.evidence else root / "docs/references/归档扩展板嘉立创规则自查"
    board = pcbnew.LoadBoard(str(pipeline.PRIMARY / (pipeline.STEM + ".kicad_pcb")))
    vias, holes, plated_pads = [], [], []
    for track in board.GetTracks():
        if track.Type() != pcbnew.PCB_VIA_T:
            continue
        diameter = pcbnew.ToMM(track.GetFrontWidth())
        drill = pcbnew.ToMM(track.GetDrill())
        layer_diameters={board.GetLayerName(layer):pcbnew.ToMM(track.GetWidth(layer)) for layer in (pcbnew.F_Cu,pcbnew.In1_Cu,pcbnew.In2_Cu,pcbnew.B_Cu)}
        row = {"uuid": track.m_Uuid.AsString(), "net": track.GetNetname(),
               "position_mm": [pcbnew.ToMM(value) for value in track.GetPosition()],
               "drill_mm": drill, "copper_diameter_mm": diameter,
               "per_layer_copper_diameter_mm":layer_diameters,
               "diameter_difference_mm": round(diameter - drill, 9),
               "nominal_annular_width_mm": round((diameter - drill) / 2, 9),
               "through": track.GetViaType() == pcbnew.VIATYPE_THROUGH,
               "meets_published_via_minimum": drill >= .15 - 1e-9 and all(value>=.25-1e-9 and value-drill>=.1-1e-9 for value in layer_diameters.values()),
               "meets_recommended_diameter_difference": all(value-drill>=.15-1e-9 for value in layer_diameters.values())}
        vias.append(row)
        holes.append({"id": row["uuid"], "type": "via", "position_mm": row["position_mm"], "drill_mm": drill})
    for footprint in board.GetFootprints():
        for pad in footprint.Pads():
            drill = pad.GetDrillSize()
            if not drill.x:
                continue
            if drill.x != drill.y:
                raise RuntimeError("Slot needs separate review")
            row = {"id": footprint.GetReference() + "." + pad.GetNumber(),
                   "type": "npth" if pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH else "pth",
                   "position_mm": [pcbnew.ToMM(value) for value in pad.GetPosition()], "drill_mm": pcbnew.ToMM(drill.x)}
            holes.append(row)
            if pad.GetAttribute() != pcbnew.PAD_ATTRIB_NPTH:
                plated_pads.append({**row, "minimum_pad_dimension_mm": pcbnew.ToMM(min(pad.GetSize().x, pad.GetSize().y)),
                                    "nominal_minimum_ring_mm": pcbnew.ToMM(min(pad.GetSize().x, pad.GetSize().y) - drill.x) / 2})
    minima = {}
    for index, first in enumerate(holes):
        for second in holes[index + 1:]:
            pair = ":".join(sorted((first["type"], second["type"])))
            gap = math.dist(first["position_mm"], second["position_mm"]) - (first["drill_mm"] + second["drill_mm"]) / 2
            if pair not in minima or gap < minima[pair]["edge_gap_mm"]:
                minima[pair] = {"items": [first["id"], second["id"]], "edge_gap_mm": gap}
    package = root / checkpoint["review_binding"]["production_package"]
    with (package / "via-process-requirements.csv").open(encoding="utf-8-sig", newline="") as stream:
        process_rows = list(csv.DictReader(stream))
    via_map = {row["uuid"]: row for row in vias}
    process_checks = [{"uuid": row["UUID"], "drill_mm": via_map[row["UUID"]]["drill_mm"],
                       "matches_csv": abs(via_map[row["UUID"]]["drill_mm"] - float(row["Drill_mm"])) < 1e-9,
                       "within_fill_cap_range": .15 - 1e-9 <= via_map[row["UUID"]]["drill_mm"] <= .55 + 1e-9}
                      for row in process_rows]
    bounding = board.GetBoardEdgesBoundingBox()
    edges = [drawing for drawing in board.GetDrawings() if drawing.GetLayer() == pcbnew.Edge_Cuts]
    if len(edges) != 4 or any(edge.GetShape() != pcbnew.SHAPE_T_SEGMENT for edge in edges):
        raise RuntimeError("Non-rectangular outline requires an independent dimensions check")
    endpoints = [point for edge in edges for point in (edge.GetStart(), edge.GetEnd())]
    outline_size = [pcbnew.ToMM(max(point.x for point in endpoints) - min(point.x for point in endpoints)),
                    pcbnew.ToMM(max(point.y for point in endpoints) - min(point.y for point in endpoints))]
    codec = next(footprint for footprint in board.GetFootprints() if footprint.GetReference() == "U701")
    codec_pad = next(pad for pad in codec.Pads() if pad.GetNumber() == "7")
    codec_via = next(row for row in vias if row["uuid"] == "c6ad78c2-361f-4c03-a650-a32f6c415d72")
    codec_pad_width = pcbnew.ToMM(min(codec_pad.GetSize().x, codec_pad.GetSize().y))
    codec_check = {"pad_size_mm": [pcbnew.ToMM(value) for value in codec_pad.GetSize()],
                   "pad_position_mm": [pcbnew.ToMM(value) for value in codec_pad.GetPosition()],
                   "via_position_mm": codec_via["position_mm"], "via_copper_diameter_mm": codec_via["per_layer_copper_diameter_mm"]["B.Cu"],
                   "pad_narrow_dimension_mm": codec_pad_width,
                   "via_copper_wider_than_original_smd_land": codec_via["per_layer_copper_diameter_mm"]["B.Cu"] > codec_pad_width,
                   "mask_expansion_mm": pcbnew.ToMM(codec_pad.GetSolderMaskExpansion(pcbnew.B_Mask)),
                   "status": "Solder-side diameter compared with original pad width; containment and process acceptance require their separate checks"}
    result = {"date": "2026-11-02", "pcb_sha256": checkpoint["pcb_sha256"], "source_binding_valid": True,
              "board_size_mm": outline_size,
              "edge_stroke_bounding_box_mm": [pcbnew.ToMM(bounding.GetWidth()), pcbnew.ToMM(bounding.GetHeight())],
              "board_thickness_mm": pcbnew.ToMM(board.GetDesignSettings().GetBoardThickness()),
              "via_count": len(vias), "hole_counts": dict(Counter(row["type"] for row in holes)), "vias": vias,
              "all_vias_meet_published_minimum": all(row["meets_published_via_minimum"] for row in vias),
              "all_vias_meet_recommended_diameter_difference": all(row["meets_recommended_diameter_difference"] for row in vias),
              "vias_below_recommended_0_2mm_drill": [row for row in vias if row["drill_mm"] < .2 - 1e-9],
              "hole_edge_minima": minima, "plated_pads": plated_pads,
              "minimum_pth_nominal_ring_mm": min(row["nominal_minimum_ring_mm"] for row in plated_pads),
              "fill_cap_requirements": process_checks,
              "u701_7_land_check": codec_check,
              "minimum_track_width_mm": min(pcbnew.ToMM(track.GetWidth()) for track in board.GetTracks() if track.Type() != pcbnew.PCB_VIA_T),
              "scope": "Nominal CAD dimensions; published via diameter rules, not IPC certification or measured finished holes. No mask-bridge, panel or thermal signoff.",
              "source_rules": {"via_minimum_drill_mm": .15, "via_minimum_diameter_mm": .25, "minimum_diameter_difference_mm": .1,
                               "recommended_diameter_difference_mm": .15, "recommended_drill_mm": .2, "fill_cap_drill_range_mm": [.15, .55]},
              "manufacturing_released": False, "hardware_tested": False}
    if pipeline.fingerprints(pipeline.PRIMARY) != checkpoint["design_hashes"]:
        raise RuntimeError("Source changed during read-only audit")
    pipeline.write_json(evidence / "native-dimensions.json", result)
    print(json.dumps({key: value for key, value in result.items() if key not in {"vias", "plated_pads"}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
