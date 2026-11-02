"""Move two capacitor vias out of solder pads in a guarded full workspace."""
import json
import math
import argparse
from pathlib import Path

import pcbnew

import pipeline
import plan_i2s_sdo as planner
from add_i2c_pullups import obstacles, position, vector


EVIDENCE = pipeline.BASE.parents[1] / "docs/references/hat-simulation-tools-20261029/cap-vias-20261031"
BASELINE = "a96508311bfc66dbab1b94b54d0391a7552f8f979acbbe26603ca281171336dc"
TARGETS = [
    ("C305", "1", "3df6d50d-2d16-47ac-8a09-662eccba3b17", ["F.Cu", "In1.Cu"], 0.6, "c3a3b7d1-7c38-49aa-9fda-d80991337d25"),
    ("C309", "2", "21b4c24a-3d42-4139-89db-0401a0cc3a8f", ["B.Cu", "F.Cu"], 0.25, "9fcde2d3-38b4-4693-b45c-747cb7f2d805"),
]


def add_path(board, net, layer, width, points, existing=None):
    for index, (start, end) in enumerate(zip(points, points[1:])):
        if start[:2] == end[:2]:
            continue
        track = existing if index == 0 and existing is not None else pcbnew.PCB_TRACK(board)
        track.SetStart(vector(start[:2]))
        track.SetEnd(vector(end[:2]))
        track.SetWidth(pcbnew.FromMM(width))
        track.SetLayer(board.GetLayerID(layer))
        track.SetNetCode(board.FindNet(net).GetNetCode())
        if track is not existing:
            board.Add(track)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--retry", action="store_true")
    arguments = parser.parse_args()
    EVIDENCE.mkdir(exist_ok=True)
    source = pipeline.PRIMARY / (pipeline.STEM + ".kicad_pcb")
    if pipeline.digest(source) != BASELINE:
        raise ValueError("Baseline changed")
    checkpoint = EVIDENCE / "candidate.json"
    if checkpoint.exists() and not arguments.retry:
        raise FileExistsError("Inspect existing attempt before starting another")
    work = pipeline.managed(Path(json.loads(checkpoint.read_text(encoding="utf-8"))["project"])) if arguments.retry else pipeline.prepare(pipeline.PRIMARY)
    pipeline.write_json(checkpoint, {"project": str(work), "baseline": BASELINE, "promoted": False})
    board = pcbnew.LoadBoard(str(source))
    plans = []
    for reference, number, identifier, layers, width, track_id in TARGETS:
        via = next(item for item in board.GetTracks() if item.m_Uuid.AsString() == identifier)
        pad = next(item for item in board.FindFootprintByReference(reference).Pads() if item.GetNumber() == number)
        old = position(via)
        net = via.GetNetname()
        old_track = next(item for item in board.GetTracks() if item.m_Uuid.AsString() == track_id)
        endpoints = [tuple(pcbnew.ToMM(value) for value in point) for point in (old_track.GetStart(), old_track.GetEnd())]
        terminal = max(endpoints, key=lambda point: math.dist(point, old))
        planner.EVIDENCE = EVIDENCE
        planner.STEP = 0.025
        planner.WIDTH = width
        planner.XMIN, planner.YMIN = round(old[0]) - 4, round(old[1]) - 4
        planner.XMAX, planner.YMAX = round(old[0]) + 4, round(old[1]) + 4
        planner.COLS = round((planner.XMAX - planner.XMIN) / planner.STEP) + 1
        planner.ROWS = round((planner.YMAX - planner.YMIN) / planner.STEP) + 1
        planner.SIZE = planner.COLS * planner.ROWS
        items = [item for item in obstacles(board) if item.get("uuid") != identifier]
        radius = pcbnew.ToMM(via.GetFrontWidth()) / 2
        via_grid = planner.occupancy(items, radius + 0.05, ["F.Cu", "B.Cu", "In1.Cu", "In2.Cu"], net, True)
        targets = [planner.coordinates(index)[:2] for index in range(planner.SIZE) if not via_grid[index]]
        targets.sort(key=lambda point: math.dist(point, old))
        attempts = []
        for target in targets[:80]:
            routes = []
            try:
                for layer in layers:
                    planner.LAYERS = [layer]
                    start = position(pad) if layer == pad.GetLayerName() else terminal
                    route = planner.solve(items, net, start, target, [0], 0)
                    routes.append({"layer": layer, **route})
            except RuntimeError as error:
                attempts.append({"target": target, "failed_layer": layer, "reason": str(error)})
                continue
            via.SetPosition(vector(target))
            for route in routes:
                add_path(board, net, route["layer"], width, route["points"], old_track if route["layer"] == old_track.GetLayerName() else None)
            plans.append({"reference": reference, "pin": number, "via": identifier, "changed_track": track_id, "from": old, "to": target, "routes": routes, "failed_attempts": attempts})
            print(f"{reference}: via moved {old} -> {target}", flush=True)
            break
        else:
            pipeline.write_json(EVIDENCE / "search-failure.json", {"reference": reference, "attempts": attempts, "previous_plans": plans})
            raise RuntimeError("No candidate found; primary is unchanged")
    pcbnew.SaveBoard(str(work / source.name), board)
    pipeline.write_json(EVIDENCE / "route-plans.json", plans)
    reports, result = pipeline.check(work)
    pipeline.write_json(checkpoint, {"project": str(work), "baseline": BASELINE, "summary": str(reports / "summary.json"), "promoted": False})
    print(json.dumps({"drc": result["drc"], "erc": result["erc"], "status": result["status"]}))


if __name__ == "__main__":
    main()
