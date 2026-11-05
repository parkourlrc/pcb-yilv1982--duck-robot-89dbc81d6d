"""Find ground thermal-via sites using all current copper and pad shapes."""
import json
import math
import argparse
from pathlib import Path

import pcbnew
import pipeline
from repair_u501 import geometry
from plan_i2s_sdo import distance_segment


EVIDENCE = pipeline.BASE.parents[1] / "docs/references/扩展板电路仿真工具/buck-thermal-20261031"
BASELINE = "335aea311c179be20bfd9f6531bdad8687ba58be211df88c81e49cd5f35471ca"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path)
    arguments = parser.parse_args()
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    project = pipeline.managed(arguments.project) if arguments.project else pipeline.PRIMARY
    board_path = project / (pipeline.STEM + ".kicad_pcb")
    if not arguments.project and pipeline.digest(board_path) != BASELINE:
        raise RuntimeError("Baseline changed")
    board = pcbnew.LoadBoard(str(board_path))
    thermal_pad = next(pad for pad in board.FindFootprintByReference("U301").Pads() if pad.GetNumber() == "9")
    pad_shapes = []
    holes = []
    for footprint in board.GetFootprints():
        for pad in footprint.Pads():
            if pad.GetDrillSize().x:
                holes.append((tuple(pcbnew.ToMM(value) for value in pad.GetPosition()), pcbnew.ToMM(max(pad.GetDrillSize().x, pad.GetDrillSize().y))/2))
            for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
                if pad.IsOnLayer(layer) and pad.m_Uuid.AsString() != thermal_pad.m_Uuid.AsString():
                    pad_shapes.append((footprint.GetReference(), pad.GetNumber(), pad.GetNetname(), pad.GetEffectiveShape(layer)))
    items = geometry(board)
    for item in items:
        if item["kind"] == "via":
            holes.append((item["position"], item["drill"]/2))
    bounds = thermal_pad.GetBoundingBox()
    left, top, right, bottom = [pcbnew.ToMM(value) for value in (bounds.GetLeft(), bounds.GetTop(), bounds.GetRight(), bounds.GetBottom())]
    valid = []
    rejected = {}
    for column in range(math.floor((right-left-0.65)/0.025)+1):
        for row in range(math.floor((bottom-top-0.65)/0.025)+1):
            point = (round(left+0.325+column*0.025, 6), round(top+0.325+row*0.025, 6))
            center = pcbnew.VECTOR2I(*(pcbnew.FromMM(value) for value in point))
            circle = pcbnew.SHAPE_CIRCLE(center, pcbnew.FromMM(0.275))
            reason = next((reference+"."+number for reference, number, net, shape in pad_shapes
                           if shape.Collide(circle, pcbnew.FromMM(0.05 if net=="POWER_GND" else 0.205))), None)
            if reason is None:
                for item in items:
                    if item.get("net") == "POWER_GND":
                        continue
                    if item["kind"] == "track":
                        gap = distance_segment(*point, item["start"], item["end"])-0.275-item["width"]/2
                    elif item["kind"] == "via":
                        gap = math.dist(point, item["position"])-0.275-item["width"]/2
                    else:
                        continue
                    if gap < 0.205:
                        reason = item.get("net", "")+" on "+item.get("layer", "")
                        break
            if reason is None and any(math.dist(point, position)<0.15+radius+0.255 for position, radius in holes):
                reason = "drill clearance"
            if reason is not None:
                rejected[reason] = rejected.get(reason, 0)+1
            else:
                valid.append(point)
    valid.sort(key=lambda point: math.dist(point, (126, 114)))
    selected = []
    for point in valid:
        if all(math.dist(point, other)>=0.8 for other in selected):
            selected.append(point)
    result = {"source_pcb_sha256": pipeline.digest(board_path), "project": str(project), "diameter_mm": 0.55, "drill_mm": 0.3, "clearance_mm": 0.205,
              "same_net_other_pad_gap_mm": 0.05, "minimum_center_spacing_mm": 0.8, "valid_grid_sites": valid,
              "greedy_selected_sites": selected, "rejected_site_reasons": rejected,
              "limitations": "Bounded 0.025mm site search, not proof of maximum possible count; only DRC/refill and connectivity checks can accept a candidate"}
    pipeline.write_json(EVIDENCE / ("thermal-via-plan-after-cap-move.json" if arguments.project else "thermal-via-plan.json"), result)
    print(json.dumps({key:value for key,value in result.items() if key!="valid_grid_sites"}))


if __name__ == "__main__":
    main()
