"""Reroute the widened 5V trunk around the unchanged clock and audio vias."""
import argparse
import json
from pathlib import Path

import pcbnew

import pipeline
import plan_i2s_sdo as planner
from add_i2c_pullups import obstacles, vector
from fit_ldo_candidate import remove_objects
from inspect_five_volt_paths import EVIDENCE


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--retry", action="store_true")
    parser.add_argument("--step", type=float, default=0.025)
    arguments = parser.parse_args()
    candidate_path = EVIDENCE / "candidate.json"
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    work = pipeline.managed(Path(candidate["project"]))
    path = work / (pipeline.STEM + ".kicad_pcb")
    contract_path = EVIDENCE / "header-route-contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    if "added_tracks" in contract or candidate["promoted"]:
        raise RuntimeError("5V candidate already fitted/promoted")
    if not arguments.retry:
        pipeline.write_json(EVIDENCE / "rejected-straight-widening.json", {"candidate": candidate, "contract": contract})
    leaf = "e4560e24-275d-4f0b-bb60-1fa9686504d6"
    removed = [entry["id"] for entry in contract["changes"] if entry["layer"] == "In1.Cu" and entry["id"] != leaf]
    if len(removed) != 7:
        raise RuntimeError("Expected seven trunk segments")
    if not arguments.retry:
        remove_objects(path, removed)
    else:
        retry_board = pcbnew.LoadBoard(str(path))
        existing = {item.m_Uuid.AsString() for item in retry_board.GetTracks()}
        if set(removed) & existing:
            raise RuntimeError("Retry source is not the saved unrouted candidate")
    board = pcbnew.LoadBoard(str(path))
    next(item for item in board.GetTracks() if item.m_Uuid.AsString() == leaf).SetWidth(pcbnew.FromMM(0.6))
    contract["changes"] = [entry for entry in contract["changes"] if entry["id"] != leaf]
    for entry in contract["changes"]:
        if entry["id"] in removed:
            entry["after"] = None
    planner.EVIDENCE = EVIDENCE
    planner.LAYERS = ["In1.Cu"]
    planner.STEP, planner.WIDTH = arguments.step, 1.2
    planner.XMIN, planner.YMIN, planner.XMAX, planner.YMAX = 120, 105.5, 147, 116.5
    planner.COLS = round((planner.XMAX - planner.XMIN) / planner.STEP) + 1
    planner.ROWS = round((planner.YMAX - planner.YMIN) / planner.STEP) + 1
    planner.SIZE = planner.COLS * planner.ROWS
    plans = []
    added = []
    for route_index, (start, end) in enumerate((((145.8126, 115.015), (133.605, 112.1717)), ((133.605, 112.1717), (122.1278, 106.838)))):
        try:
            plan = planner.solve(obstacles(board), "+5V", start, end, [0], 0)
        except RuntimeError as error:
            pipeline.write_json(EVIDENCE / (f"fit-failure-{planner.STEP}-{route_index}.json"), {"start": start, "end": end, "step_mm": planner.STEP, "error": str(error)})
            raise
        layer = pcbnew.In1_Cu
        shapes = [pad.GetEffectiveShape(layer) for footprint in board.GetFootprints() for pad in footprint.Pads()
                  if pad.IsOnLayer(layer) and pad.GetNetname() != "+5V"]
        shapes.extend(item.GetEffectiveShape(layer) for item in board.GetTracks() if item.IsOnLayer(layer) and item.GetNetname() != "+5V")
        probe = pcbnew.PCB_TRACK(board)
        probe.SetWidth(pcbnew.FromMM(1.2))
        probe.SetLayer(layer)
        points = plan["points"]
        compact = [points[0]]
        cursor = 0
        while cursor < len(points) - 1:
            chosen = cursor + 1
            for endpoint in range(len(points) - 1, cursor, -1):
                probe.SetStart(vector(points[cursor][:2]))
                probe.SetEnd(vector(points[endpoint][:2]))
                if not any(shape.Collide(probe.GetEffectiveShape(layer), pcbnew.FromMM(0.205)) for shape in shapes):
                    chosen = endpoint
                    break
            compact.append(points[chosen])
            cursor = chosen
        route_ids = []
        for first_point, last_point in zip(compact, compact[1:]):
            track = pcbnew.PCB_TRACK(board)
            track.SetStart(vector(first_point[:2]))
            track.SetEnd(vector(last_point[:2]))
            track.SetLayer(layer)
            track.SetWidth(pcbnew.FromMM(1.2))
            track.SetNetCode(board.FindNet("+5V").GetNetCode())
            board.Add(track)
            route_ids.append(track.m_Uuid.AsString())
        plans.append({"points": compact, "added_tracks": route_ids, "width_mm": 1.2, "layer": "In1.Cu"})
        added.extend(route_ids)
    pcbnew.SaveBoard(str(path), board)
    contract["removed_tracks"] = removed
    contract["added_tracks"] = added
    contract["trunk_routes"] = plans
    contract["restored_unchanged_leaf"] = leaf
    pipeline.write_json(contract_path, contract)
    reports, summary = pipeline.check(work)
    candidate["summary"] = str(reports / "summary.json")
    pipeline.write_json(candidate_path, candidate)
    print(json.dumps({"drc": summary["drc"], "status": summary["status"], "new_trunk_segments": len(added)}))


if __name__ == "__main__":
    main()
