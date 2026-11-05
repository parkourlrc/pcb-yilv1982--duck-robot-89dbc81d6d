"""Reroute the existing In1 LRCK branch beneath native F.Cu ground copper."""
import json
import math
import uuid

import pcbnew

import pipeline
import plan_i2s_sdo as planner
from add_i2c_pullups import obstacles, vector
from fit_ldo_candidate import remove_objects


EVIDENCE = pipeline.BASE.parents[1] / "docs/references/扩展板电路仿真工具/lrck-ground-reference-20261031"
BASELINE = "fda50c8019c3ab68c7c54228fc09fb36dd028e35b43afe26a7dc0f6c090b0771"
START, END = (149.4, 113.85), (151.5, 104.59)


def main():
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    if (EVIDENCE / "candidate.json").exists():
        raise FileExistsError("Inspect existing candidate before retry")
    if pipeline.digest(pipeline.PRIMARY / (pipeline.STEM + ".kicad_pcb")) != BASELINE:
        raise RuntimeError("Primary baseline changed")
    work = pipeline.prepare(pipeline.PRIMARY)
    candidate = {"project": str(work), "baseline": BASELINE, "promoted": False}
    pipeline.write_json(EVIDENCE / "candidate.json", candidate)
    path = work / (pipeline.STEM + ".kicad_pcb")
    board = pcbnew.LoadBoard(str(path))
    removed = [item.m_Uuid.AsString() for item in board.GetTracks() if item.Type() != pcbnew.PCB_VIA_T
               and item.GetNetname() == "I2S_LRCK" and item.GetLayer() == pcbnew.In1_Cu]
    if len(removed) != 4:
        raise RuntimeError("LRCK source branch changed")
    remove_objects(path, removed)
    report = work.parent / ("reference-fill-" + uuid.uuid4().hex[:8] + ".json")
    pipeline.run_command([pipeline.find_cli(), "pcb", "drc", "--format", "json", "--severity-all", "--refill-zones", "--save-board", "--output", report, path],
                         EVIDENCE, "unrouted-refill", [], report)
    board = pcbnew.LoadBoard(str(path))
    ground = next(zone.GetFilledPolysList(pcbnew.F_Cu) for zone in board.Zones()
                  if zone.IsOnLayer(pcbnew.F_Cu) and zone.GetNetname() == "POWER_GND")
    planner.EVIDENCE = EVIDENCE
    planner.LAYERS = ["In1.Cu"]
    planner.STEP, planner.WIDTH = 0.025, 0.15
    planner.XMIN, planner.YMIN, planner.XMAX, planner.YMAX = 142, 103, 158, 119
    planner.COLS = round((planner.XMAX - planner.XMIN) / planner.STEP) + 1
    planner.ROWS = round((planner.YMAX - planner.YMIN) / planner.STEP) + 1
    planner.SIZE = planner.COLS * planner.ROWS
    normal = planner.occupancy
    mask = bytearray(planner.SIZE)
    for index in range(planner.SIZE):
        point = planner.coordinates(index)[:2]
        exception = math.dist(point, START) <= 0.6 or math.dist(point, END) <= 1.15
        if not exception and not ground.Contains(vector(point)):
            mask[index] = 1
    def occupancy(*args, **kwargs):
        grid = normal(*args, **kwargs)
        for index, blocked in enumerate(mask):
            if blocked:
                grid[index] = 1
        return grid
    planner.occupancy = occupancy
    print("Searching In1 LRCK route beneath F.Cu ground", flush=True)
    try:
        route = planner.solve(obstacles(board), "I2S_LRCK", START, END, [0], 0)
    except RuntimeError as error:
        candidate["status"] = "rejected_unrouted_not_for_use"
        pipeline.write_json(EVIDENCE / "candidate.json", candidate)
        pipeline.write_json(EVIDENCE / "route-failure.json", {"error": str(error), "removed_tracks": removed,
                            "primary_unchanged": pipeline.digest(pipeline.PRIMARY / path.name) == BASELINE})
        raise
    added = []
    for start, end in zip(route["points"], route["points"][1:]):
        if start[:2] == end[:2]:
            continue
        track = pcbnew.PCB_TRACK(board)
        track.SetStart(vector(start[:2]))
        track.SetEnd(vector(end[:2]))
        track.SetLayer(pcbnew.In1_Cu)
        track.SetWidth(pcbnew.FromMM(0.15))
        track.SetNetCode(board.FindNet("I2S_LRCK").GetNetCode())
        board.Add(track)
        added.append(track.m_Uuid.AsString())
    pcbnew.SaveBoard(str(path), board)
    pipeline.write_json(EVIDENCE / "route-contract.json", {"removed_tracks": removed, "added_tracks": added,
                        "points": route["points"], "width_mm": 0.15, "layer": "In1.Cu", "reference_layer": "F.Cu", "reference_net": "POWER_GND",
                        "endpoint_exceptions_mm": {"via": 0.6, "header": 1.15}, "reference_scope": "centerline only; no impedance or EMI claim"})
    reports, summary = pipeline.check(work)
    candidate["summary"] = str(reports / "summary.json")
    pipeline.write_json(EVIDENCE / "candidate.json", candidate)
    print(json.dumps({"drc": summary["drc"], "status": summary["status"], "segments": len(added)}))


if __name__ == "__main__":
    main()
