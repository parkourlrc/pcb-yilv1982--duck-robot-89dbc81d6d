"""Identify specific movable traces preventing a standard ground stitch."""
import json
import math

import pcbnew

import pipeline
from add_i2c_pullups import vector
from stitch_i2s_reference_pocket import EVIDENCE, BASELINE


def main():
    path = pipeline.PRIMARY / (pipeline.STEM + ".kicad_pcb")
    if pipeline.digest(path) != BASELINE:
        raise RuntimeError("Stitch investigation baseline changed")
    board = pcbnew.LoadBoard(str(path))
    layers = (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu)
    fixed = []
    moving = []
    for footprint in board.GetFootprints():
        for pad in footprint.Pads():
            for layer in layers:
                if pad.IsOnLayer(layer):
                    fixed.append((pad.GetEffectiveShape(layer), 0.38 if pad.GetNetname() == "POWER_GND" else 0.505))
    for item in board.GetTracks():
        for layer in layers:
            if not item.IsOnLayer(layer):
                continue
            if item.Type() == pcbnew.PCB_VIA_T:
                fixed.append((item.GetEffectiveShape(layer), 0.505))
            elif item.GetNetname() != "POWER_GND":
                moving.append((item, item.GetEffectiveShape(layer)))
    front = next(zone.GetFilledPolysList(pcbnew.F_Cu) for zone in board.Zones() if zone.IsOnLayer(pcbnew.F_Cu) and zone.GetNetname() == "POWER_GND")
    inner = next(zone.GetFilledPolysList(pcbnew.In1_Cu) for zone in board.Zones() if zone.IsOnLayer(pcbnew.In1_Cu) and zone.GetNetname() == "POWER_GND")
    choices = []
    for xpos_index in range(3000, 3061):
        for ypos_index in range(2140, 2201):
            point_mm = (xpos_index / 20, ypos_index / 20)
            point = vector(point_mm)
            if front.Contains(point) or not inner.Contains(point) or any(shape.Collide(point, pcbnew.FromMM(clearance)) for shape, clearance in fixed):
                continue
            blockers = [item for item, shape in moving if shape.Collide(point, pcbnew.FromMM(0.505))]
            if len(blockers) > 4 or any(item.GetNetname() in {"+5V", "BUCK_SW", "VBATT_2S_IN", "SERVO_VBAT"} for item in blockers):
                continue
            choices.append({"position_mm": point_mm, "blocker_count": len(blockers), "distinct_nets": sorted({item.GetNetname() for item in blockers}),
                            "distance_to_target": math.dist(point_mm, (151.2, 108.7)),
                            "blockers": [{"id": item.m_Uuid.AsString(), "net": item.GetNetname(), "layer": item.GetLayerName(),
                                          "start": [pcbnew.ToMM(value) for value in item.GetStart()], "end": [pcbnew.ToMM(value) for value in item.GetEnd()],
                                          "width_mm": pcbnew.ToMM(item.GetWidth())} for item in blockers]})
    choices.sort(key=lambda entry: (len(entry["distinct_nets"]), entry["blocker_count"], entry["distance_to_target"]))
    pipeline.write_json(EVIDENCE / "movable-obstacles.json", {"source_sha256": BASELINE, "diameter_mm": 0.6, "drill_mm": 0.3, "choices": choices})
    print(json.dumps({"candidate_count": len(choices), "best": choices[:4]}))


if __name__ == "__main__":
    main()
