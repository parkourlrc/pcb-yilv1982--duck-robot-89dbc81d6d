"""Keep 1.2mm power copper while avoiding connector ground pads and the board edge."""
import json
from pathlib import Path

import pcbnew

import pipeline
import plan_i2s_sdo as planner
from add_i2c_pullups import obstacles, vector
from fit_ldo_candidate import remove_objects
from widen_main_power_paths import EVIDENCE


def main():
    candidate_path = EVIDENCE / "candidate.json"
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    work = pipeline.managed(Path(candidate["project"]))
    path = work / (pipeline.STEM + ".kicad_pcb")
    contract_path = EVIDENCE / "power-route-contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    if "added_tracks" in contract or candidate["promoted"]:
        raise RuntimeError("Candidate already fitted/promoted")
    previous = {**candidate, "contract": contract}
    pipeline.write_json(EVIDENCE / "rejected-straight-widening.json", previous)
    removed = "bb1bedbb-ebc8-4fd4-85eb-f92f522f78fe"
    remove_objects(path, [removed])
    board = pcbnew.LoadBoard(str(path))
    placements = {
        "e5918c70-6d7e-4edb-9a52-11cff917fdc1": ((108.35, 118.47), (110.89, 118.47)),
        "faf36f72-6ccd-49ed-88fd-064571a7e986": ((110.89, 118.47), (110.89, 127.32)),
        "9096a290-f2f0-49eb-85d9-fa6b1c9c1197": ((110.89, 127.32), (112.645, 129.075)),
        "b4abce8d-34f5-4500-9d72-f1f97b33218f": ((112.645, 129.075), (142.115, 129.075)),
    }
    for track in board.GetTracks():
        identifier = track.m_Uuid.AsString()
        if identifier in placements:
            start, end = placements[identifier]
            track.SetStart(vector(start))
            track.SetEnd(vector(end))
    planner.EVIDENCE = EVIDENCE
    planner.LAYERS = ["In1.Cu"]
    planner.STEP, planner.WIDTH = 0.025, 1.2
    planner.XMIN, planner.YMIN, planner.XMAX, planner.YMAX = 139, 118, 155, 129.075
    planner.COLS = round((planner.XMAX - planner.XMIN) / planner.STEP) + 1
    planner.ROWS = round((planner.YMAX - planner.YMIN) / planner.STEP) + 1
    planner.SIZE = planner.COLS * planner.ROWS
    plan = planner.solve(obstacles(board), "SERVO_VBAT", (142.115, 129.075), (151.49, 119.7), [0], 0)
    layer = pcbnew.In1_Cu
    shapes = [pad.GetEffectiveShape(layer) for footprint in board.GetFootprints() for pad in footprint.Pads()
              if pad.IsOnLayer(layer) and pad.GetNetname() != "SERVO_VBAT"]
    shapes.extend(item.GetEffectiveShape(layer) for item in board.GetTracks() if item.IsOnLayer(layer) and item.GetNetname() != "SERVO_VBAT")
    points = plan["points"]
    probe = pcbnew.PCB_TRACK(board)
    probe.SetLayer(layer)
    probe.SetWidth(pcbnew.FromMM(1.2))
    simplified = [points[0]]
    cursor = 0
    while cursor < len(points) - 1:
        chosen = cursor + 1
        for endpoint in range(len(points) - 1, cursor, -1):
            probe.SetStart(vector(points[cursor][:2]))
            probe.SetEnd(vector(points[endpoint][:2]))
            if not any(shape.Collide(probe.GetEffectiveShape(layer), pcbnew.FromMM(0.205)) for shape in shapes):
                chosen = endpoint
                break
        simplified.append(points[chosen])
        cursor = chosen
    added = []
    for start, end in zip(simplified, simplified[1:]):
        track = pcbnew.PCB_TRACK(board)
        track.SetStart(vector(start[:2]))
        track.SetEnd(vector(end[:2]))
        track.SetWidth(pcbnew.FromMM(1.2))
        track.SetLayer(layer)
        track.SetNetCode(board.FindNet("SERVO_VBAT").GetNetCode())
        board.Add(track)
        added.append(track.m_Uuid.AsString())
    pcbnew.SaveBoard(str(path), board)
    lookup = {item.m_Uuid.AsString(): item for item in board.GetTracks()}
    for entry in contract["changes"]:
        if entry["id"] == removed:
            entry["after"] = None
            continue
        track = lookup[entry["id"]]
        entry["after"] = {"start": [pcbnew.ToMM(value) for value in track.GetStart()], "end": [pcbnew.ToMM(value) for value in track.GetEnd()], "width_mm": pcbnew.ToMM(track.GetWidth())}
    contract["removed_tracks"] = [removed]
    contract["added_tracks"] = added
    contract["right_servo_route"] = simplified
    contract["minimum_copper_edge_clearance_mm"] = 0.3
    contract["bottom_center_y_mm"] = 129.075
    pipeline.write_json(contract_path, contract)
    reports, summary = pipeline.check(work)
    candidate["summary"] = str(reports / "summary.json")
    pipeline.write_json(candidate_path, candidate)
    print(json.dumps({"drc": summary["drc"], "status": summary["status"], "right_branch_segments": len(added)}))


if __name__ == "__main__":
    main()
