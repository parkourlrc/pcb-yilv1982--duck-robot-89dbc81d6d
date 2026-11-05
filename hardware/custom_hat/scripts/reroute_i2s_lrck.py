"""Move only the LRCK inner-layer path to F.Cu over native In1 ground copper."""
import argparse
import json
import math
from pathlib import Path
import uuid

import pcbnew

import pipeline
import plan_i2s_sdo as planner
from add_i2c_pullups import obstacles, vector
from fit_ldo_candidate import remove_objects


EVIDENCE = pipeline.BASE.parents[1] / "docs/references/扩展板电路仿真工具/i2s-reference-20261031"
BASELINE = "fda50c8019c3ab68c7c54228fc09fb36dd028e35b43afe26a7dc0f6c090b0771"
START, END = (149.4, 113.85), (151.5, 104.59)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--layer", choices=("F.Cu", "In2.Cu"), default="F.Cu")
    parser.add_argument("--continue-candidate", action="store_true")
    arguments = parser.parse_args()
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    candidate_path = EVIDENCE / "candidate.json"
    if candidate_path.exists() and not arguments.continue_candidate:
        raise FileExistsError("Inspect existing LRCK candidate before retry")
    if pipeline.digest(pipeline.PRIMARY / (pipeline.STEM + ".kicad_pcb")) != BASELINE:
        raise RuntimeError("Source baseline changed")
    if arguments.continue_candidate:
        candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
        work = pipeline.managed(Path(candidate["project"]))
        if candidate["promoted"] or (EVIDENCE / "route-contract.json").exists():
            raise RuntimeError("Only an unrouted rejected candidate can be continued")
        if candidate.get("status") == "rejected_unrouted_not_for_use":
            raise RuntimeError("This candidate is retired; start coupled routing from primary")
    else:
        work = pipeline.prepare(pipeline.PRIMARY)
        candidate = {"project": str(work), "baseline": BASELINE, "promoted": False}
        pipeline.write_json(candidate_path, candidate)
    path = work / (pipeline.STEM + ".kicad_pcb")
    board = pcbnew.LoadBoard(str(pipeline.PRIMARY / path.name))
    removed = [track.m_Uuid.AsString() for track in board.GetTracks()
               if track.Type() != pcbnew.PCB_VIA_T and track.GetNetname() == "I2S_LRCK" and track.GetLayer() == pcbnew.In1_Cu]
    if len(removed) != 4:
        raise RuntimeError("Expected four original In1 LRCK segments")
    if not arguments.continue_candidate:
        remove_objects(path, removed)
    report = work.parent / ("lrck-unrouted-fill-" + uuid.uuid4().hex[:8] + ".json")
    pipeline.run_command([pipeline.find_cli(), "pcb", "drc", "--format", "json", "--severity-all", "--refill-zones", "--save-board", "--output", report, path],
                         EVIDENCE, "unrouted-refill", [], report)
    board = pcbnew.LoadBoard(str(path))
    plane = next(zone.GetFilledPolysList(pcbnew.In1_Cu) for zone in board.Zones()
                 if zone.GetNetname() == "POWER_GND" and zone.IsOnLayer(pcbnew.In1_Cu))
    planner.EVIDENCE = EVIDENCE
    planner.LAYERS = [arguments.layer]
    planner.STEP = 0.025
    planner.WIDTH = 0.15
    planner.XMIN, planner.YMIN, planner.XMAX, planner.YMAX = 145, 103, 158, 117
    planner.COLS = round((planner.XMAX - planner.XMIN) / planner.STEP) + 1
    planner.ROWS = round((planner.YMAX - planner.YMIN) / planner.STEP) + 1
    planner.SIZE = planner.COLS * planner.ROWS
    normal_occupancy = planner.occupancy
    ground_mask = bytearray(planner.SIZE)
    endpoint_exception_mm = 1.15
    for index in range(planner.SIZE):
        point = planner.coordinates(index)[:2]
        endpoint = min(math.dist(point, START), math.dist(point, END)) <= endpoint_exception_mm
        if not endpoint and not plane.Contains(vector(point)):
            ground_mask[index] = 1
    def reference_occupancy(*args, **kwargs):
        grid = normal_occupancy(*args, **kwargs)
        for index, masked in enumerate(ground_mask):
            if masked:
                grid[index] = 1
        return grid
    planner.occupancy = reference_occupancy
    print("Routing LRCK on " + arguments.layer + " with native In1 ground occupancy constraint", flush=True)
    try:
        route = planner.solve(obstacles(board), "I2S_LRCK", START, END, [0], 0)
    except RuntimeError as error:
        pipeline.write_json(EVIDENCE / ("route-failure-" + arguments.layer + ".json"), {"removed_segments": removed, "error": str(error),
                            "region": [planner.XMIN, planner.YMIN, planner.XMAX, planner.YMAX], "endpoint_exception_mm": endpoint_exception_mm,
                            "primary_unchanged": pipeline.digest(pipeline.PRIMARY / path.name) == BASELINE})
        raise
    added = []
    for start, end in zip(route["points"], route["points"][1:]):
        if start[:2] == end[:2]:
            continue
        track = pcbnew.PCB_TRACK(board)
        track.SetStart(vector(start[:2]))
        track.SetEnd(vector(end[:2]))
        track.SetLayer(pcbnew.F_Cu if arguments.layer == "F.Cu" else pcbnew.In2_Cu)
        track.SetWidth(pcbnew.FromMM(0.15))
        track.SetNetCode(board.FindNet("I2S_LRCK").GetNetCode())
        board.Add(track)
        added.append(track.m_Uuid.AsString())
    pcbnew.SaveBoard(str(path), board)
    pipeline.write_json(EVIDENCE / "route-contract.json", {"removed_tracks": removed, "added_tracks": added,
                        "points": route["points"], "width_mm": 0.15, "layer": arguments.layer, "endpoint_exception_mm": endpoint_exception_mm,
                        "reference_layer": "In1.Cu", "reference_net": "POWER_GND", "new_vias": 0})
    reports, summary = pipeline.check(work)
    candidate["summary"] = str(reports / "summary.json")
    pipeline.write_json(candidate_path, candidate)
    print(json.dumps({"drc": summary["drc"], "status": summary["status"], "added_segments": len(added)}))


if __name__ == "__main__":
    main()
