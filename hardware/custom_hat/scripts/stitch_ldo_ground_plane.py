"""Stitch the isolated LDO lead ground outside every solder pad."""
import json
import math
from pathlib import Path

import pcbnew
import pipeline
from improve_via_annular_rings import EVIDENCE
from repair_u501 import geometry
from plan_i2s_sdo import distance_segment


def main():
    candidate_path = EVIDENCE / "candidate.json"
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    work = pipeline.managed(Path(candidate["project"]))
    board_path = work / (pipeline.STEM + ".kicad_pcb")
    board = pcbnew.LoadBoard(str(board_path))
    pads = [pad for footprint in board.GetFootprints() for pad in footprint.Pads()]
    pad_shapes = [(pad.GetNetname(), pad.GetEffectiveShape(layer)) for pad in pads
                  for layer in (pcbnew.F_Cu, pcbnew.B_Cu) if pad.IsOnLayer(layer)]
    ground_lead = min((pad for pad in board.FindFootprintByReference("U702").Pads() if pad.GetNumber() == "2"), key=lambda pad: pad.GetSize().x * pad.GetSize().y)
    ground = next(zone for zone in board.Zones() if zone.GetNetname() == "POWER_GND" and zone.GetLayer() == pcbnew.B_Cu)
    shape = ground.GetFilledPolysList(pcbnew.B_Cu)
    island = next(shape.Outline(index) for index in range(shape.OutlineCount()) if shape.Outline(index).PointInside(ground_lead.GetPosition()))
    items = geometry(board)
    options = []
    for column in range(81):
        for row in range(101):
            point = (round(123.5 + column*0.05, 6), round(116.5 + row*0.05, 6))
            position = pcbnew.VECTOR2I(*(pcbnew.FromMM(value) for value in point))
            if not island.PointInside(position):
                continue
            circle = pcbnew.SHAPE_CIRCLE(position, pcbnew.FromMM(0.3))
            if any(pad_shape.Collide(circle, pcbnew.FromMM(0.10 if net == "POWER_GND" else 0.205)) for net, pad_shape in pad_shapes):
                continue
            blocked = False
            for item in items:
                if item.get("net") == "POWER_GND":
                    continue
                if item["kind"] == "track":
                    gap = distance_segment(*point, item["start"], item["end"]) - 0.3 - item["width"]/2
                elif item["kind"] == "via":
                    gap = math.dist(point, item["position"]) - 0.3 - item["width"]/2
                else:
                    continue
                if gap < 0.205:
                    blocked = True
                    break
            if not blocked:
                options.append(point)
    options.sort(key=lambda point: math.dist(point, (126.17, 119.7)))
    pipeline.write_json(EVIDENCE / "ground-stitch-options.json", options)
    if not options:
        raise RuntimeError("No conservative through-via point in the isolated ground island")
    via = pcbnew.PCB_VIA(board)
    via.SetPosition(pcbnew.VECTOR2I(*(pcbnew.FromMM(value) for value in options[0])))
    via.SetWidth(pcbnew.FromMM(0.6))
    via.SetDrill(pcbnew.FromMM(0.3))
    via.SetViaType(pcbnew.VIATYPE_THROUGH)
    via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    via.SetNetCode(ground_lead.GetNetCode())
    board.Add(via)
    pcbnew.SaveBoard(str(board_path), board)
    pipeline.write_json(EVIDENCE / "ground-stitch.json", {"uuid": via.m_Uuid.AsString(), "position": options[0], "diameter": 0.6, "drill": 0.3})
    reports, summary = pipeline.check(work)
    candidate["summary"] = str(reports / "summary.json")
    pipeline.write_json(candidate_path, candidate)
    print(json.dumps({"via": options[0], "drc": summary["drc"], "status": summary["status"]}))


if __name__ == "__main__":
    main()
