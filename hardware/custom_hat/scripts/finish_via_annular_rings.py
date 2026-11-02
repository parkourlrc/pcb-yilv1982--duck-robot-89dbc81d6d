"""Resolve ring-enlargement clearances by bounded local via/stub shifts."""
import json
import math
from pathlib import Path

import pcbnew
import pipeline
from repair_u501 import geometry
from plan_i2s_sdo import distance_segment
from improve_via_annular_rings import EVIDENCE


def clearance_ok(items, point, target, pad_shapes):
    radius = target["new_diameter"] / 2
    circle = pcbnew.SHAPE_CIRCLE(pcbnew.VECTOR2I(*(pcbnew.FromMM(value) for value in point)), pcbnew.FromMM(radius))
    for net, shape in pad_shapes:
        if net != target["net"] and shape.Collide(circle, pcbnew.FromMM(0.205)):
            return False
    minimum = 100.0
    for item in items:
        if item.get("uuid") == target["uuid"] or item.get("net") == target["net"]:
            continue
        if item["kind"] == "pad":
            continue
        elif item["kind"] == "track":
            distance = distance_segment(*point, item["start"], item["end"]) - radius - item["width"]/2
        elif item["kind"] == "via":
            distance = math.dist(point, item["position"]) - radius - item["width"]/2
        else:
            continue
        minimum = min(minimum, distance)
        if distance < 0.205:
            return False
    return True


def main():
    candidate_path = EVIDENCE / "candidate.json"
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    work = pipeline.managed(Path(candidate["project"]))
    board_path = work / (pipeline.STEM + ".kicad_pcb")
    changes = json.loads((EVIDENCE / "changes.json").read_text(encoding="utf-8"))
    changed_by_id = {item["uuid"]: item for item in changes}
    report = json.loads((Path(candidate["summary"]).parent / "drc.json").read_text(encoding="utf-8"))
    targets = {item["uuid"] for finding in report["violations"] for item in finding["items"] if item["uuid"] in changed_by_id}
    board = pcbnew.LoadBoard(str(board_path))
    detour_id = "08449adc-2e96-48f0-96a3-d8a848d5e8d9"
    detour = next(item for item in board.GetTracks() if item.m_Uuid.AsString() == detour_id)
    detour_start = [pcbnew.ToMM(value) for value in detour.GetStart()]
    detour_end = [pcbnew.ToMM(value) for value in detour.GetEnd()]
    if math.dist(detour_start, (147.839999, 113.21)) > 0.00001 or math.dist(detour_end, (140.79, 106.16)) > 0.00001:
        raise RuntimeError("MCLK detour baseline changed")
    points = [detour_start, (147.79, 113.21), (146.79, 112.21), (146.79, 112.16), detour_end]
    added = []
    for index, (start, end) in enumerate(zip(points, points[1:])):
        item = detour if index == 0 else pcbnew.PCB_TRACK(board)
        item.SetStart(pcbnew.VECTOR2I(*(pcbnew.FromMM(value) for value in start)))
        item.SetEnd(pcbnew.VECTOR2I(*(pcbnew.FromMM(value) for value in end)))
        item.SetWidth(pcbnew.FromMM(0.25))
        item.SetLayer(pcbnew.In1_Cu)
        item.SetNetCode(detour.GetNetCode())
        if index:
            board.Add(item)
            added.append(item.m_Uuid.AsString())
    pipeline.write_json(EVIDENCE / "mclk-detour.json", {"changed_track": detour_id, "added_tracks": added, "points": points, "width_mm": 0.25})
    pad_shapes = [(pad.GetNetname(), pad.GetEffectiveShape(layer)) for footprint in board.GetFootprints()
                  for pad in footprint.Pads() for layer in (pcbnew.F_Cu, pcbnew.B_Cu) if pad.IsOnLayer(layer)]
    by_id = {item.m_Uuid.AsString(): item for item in board.GetTracks()}
    shifts = []
    for identifier in sorted(targets):
        target = changed_by_id[identifier]
        via = by_id[identifier]
        old = list(via.GetPosition())
        original = [pcbnew.ToMM(value) for value in old]
        candidates = [(round(original[0] + column*0.025, 6), round(original[1] + row*0.025, 6))
                      for row in range(-24, 25) for column in range(-24, 25)]
        candidates.sort(key=lambda point: math.dist(point, original))
        items = geometry(board)
        position = next((point for point in candidates if clearance_ok(items, point, target, pad_shapes)), None)
        if position is None:
            pipeline.write_json(EVIDENCE / "shift-failure.json", {"via": target, "previous_shifts": shifts})
            raise RuntimeError("No conservative local position")
        new = pcbnew.VECTOR2I(*(pcbnew.FromMM(value) for value in position))
        moved_tracks = []
        for track in board.GetTracks():
            if track.Type() == pcbnew.PCB_VIA_T or track.GetNetCode() != via.GetNetCode():
                continue
            changed = False
            if list(track.GetStart()) == old:
                track.SetStart(new)
                changed = True
            if list(track.GetEnd()) == old:
                track.SetEnd(new)
                changed = True
            if changed:
                moved_tracks.append(track.m_Uuid.AsString())
        via.SetPosition(new)
        shifts.append({"via": identifier, "net": target["net"], "from": original, "to": position, "attached_tracks": moved_tracks})
    pcbnew.SaveBoard(str(board_path), board)
    pipeline.write_json(EVIDENCE / "shifts.json", shifts)
    reports, summary = pipeline.check(work)
    candidate["summary"] = str(reports / "summary.json")
    pipeline.write_json(candidate_path, candidate)
    print(json.dumps({"shifted_vias": len(shifts), "drc": summary["drc"], "status": summary["status"]}))


if __name__ == "__main__":
    main()
