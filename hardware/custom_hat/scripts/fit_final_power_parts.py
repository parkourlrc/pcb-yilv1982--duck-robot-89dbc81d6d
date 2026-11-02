"""Relocate three via conflicts with the selected inductor and fix jumper silk."""
import json
import math
from pathlib import Path

import pcbnew
import pipeline
from generate_rev_a import first
from repair_release_metadata import properties, replace_children
from repair_u501 import geometry
from plan_i2s_sdo import distance_segment
from select_header_connectors import line
from select_final_bom import EVIDENCE


TARGETS = [
    "2eeb5c7c-acae-4fab-9d1c-a7297c6c0d5d",
    "5ca45513-027c-490b-9874-9aaaf94f6fe5",
    "e2205697-9fa5-483f-b2f6-58643a86132d",
]


def main():
    candidate_path = EVIDENCE / "candidate.json"
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    work = pipeline.managed(Path(candidate["project"]))
    board_path = work / (pipeline.STEM + ".kicad_pcb")
    def silk(node):
        if properties(node).get("Reference") != "R309":
            return False
        node[:] = [entry for entry in node if not (isinstance(entry, list) and entry and entry[0] == "fp_line"
                  and first(entry, "layer")[1] in {"B.SilkS", "B.Silkscreen"})]
        node.extend([line((-0.15, -1.05), (0.15, -1.05), "B.SilkS", 0.12), line((-0.15, 1.05), (0.15, 1.05), "B.SilkS", 0.12)])
        return True
    board_path.write_text(replace_children(board_path.read_text(encoding="utf-8"), "footprint", silk), encoding="utf-8")
    board = pcbnew.LoadBoard(str(board_path))
    shapes = [(pad.GetNetname(), pad.GetEffectiveShape(layer)) for footprint in board.GetFootprints() for pad in footprint.Pads()
              for layer in (pcbnew.F_Cu, pcbnew.B_Cu) if pad.IsOnLayer(layer)]
    changes = []
    for identifier in TARGETS:
        via = next(item for item in board.GetTracks() if item.m_Uuid.AsString() == identifier)
        old = list(via.GetPosition())
        start = tuple(pcbnew.ToMM(value) for value in old)
        radius = pcbnew.ToMM(via.GetFrontWidth()) / 2
        items = geometry(board)
        options = [(round(start[0]+column*0.05, 6), round(start[1]+row*0.05, 6)) for column in range(-60,61) for row in range(-60,61)]
        options.sort(key=lambda point: math.dist(point, start))
        selected = None
        for point in options:
            center = pcbnew.VECTOR2I(*(pcbnew.FromMM(value) for value in point))
            circle = pcbnew.SHAPE_CIRCLE(center, pcbnew.FromMM(radius))
            if any(shape.Collide(circle, pcbnew.FromMM(0.1 if net == via.GetNetname() else 0.205)) for net, shape in shapes):
                continue
            conflict = False
            for item in items:
                if item.get("uuid") == identifier or item.get("net") == via.GetNetname():
                    continue
                if item["kind"] == "track":
                    gap = distance_segment(*point, item["start"], item["end"]) - radius - item["width"]/2
                elif item["kind"] == "via":
                    gap = math.dist(point, item["position"]) - radius - item["width"]/2
                else:
                    continue
                if gap < 0.205:
                    conflict = True
                    break
            if not conflict:
                selected = center
                break
        if selected is None:
            pipeline.write_json(EVIDENCE / "via-placement-failure.json", {"via": identifier, "previous_moves": changes})
            raise RuntimeError("No local via placement")
        attached = []
        for track in board.GetTracks():
            if track.Type() == pcbnew.PCB_VIA_T or track.GetNetCode() != via.GetNetCode():
                continue
            moved = False
            if list(track.GetStart()) == old:
                track.SetStart(selected)
                moved = True
            if list(track.GetEnd()) == old:
                track.SetEnd(selected)
                moved = True
            if moved:
                attached.append(track.m_Uuid.AsString())
        via.SetPosition(selected)
        changes.append({"via": identifier, "net": via.GetNetname(), "from": start,
                        "to": [pcbnew.ToMM(value) for value in selected], "attached_tracks": attached})
    pcbnew.SaveBoard(str(board_path), board)
    footprint = board.FindFootprintByReference("R309")
    footprint.Flip(footprint.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
    footprint.SetPosition(pcbnew.VECTOR2I(0,0))
    footprint.SetOrientationDegrees(0)
    pcbnew.FootprintSave(str(work / "duck.pretty"), footprint)
    pipeline.write_json(EVIDENCE / "power-footprint-via-moves.json", changes)
    reports, result = pipeline.check(work)
    candidate["summary"] = str(reports / "summary.json")
    pipeline.write_json(candidate_path, candidate)
    print(json.dumps({"moves": changes, "drc": result["drc"], "status": result["status"]}))


if __name__ == "__main__":
    main()
