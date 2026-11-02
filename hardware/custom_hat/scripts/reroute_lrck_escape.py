"""Try a new LRCK escape via with F.Cu routing referenced to In1 ground."""
import json
import math
from pathlib import Path
import uuid

import pcbnew

import pipeline
import plan_i2s_sdo as planner
from add_i2c_pullups import obstacles, vector
from fit_ldo_candidate import remove_objects
from reroute_i2s_lrck import EVIDENCE, BASELINE


def main():
    candidate_path = EVIDENCE / "candidate.json"
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    if candidate.get("status") == "rejected_unrouted_not_for_use":
        raise RuntimeError("This candidate is retired; start coupled routing from primary")
    work = pipeline.managed(Path(candidate["project"]))
    path = work / (pipeline.STEM + ".kicad_pcb")
    if (EVIDENCE / "route-contract.json").exists() or pipeline.digest(pipeline.PRIMARY / path.name) != BASELINE:
        raise RuntimeError("Source/candidate changed before escape attempt")
    source_board = pcbnew.LoadBoard(str(pipeline.PRIMARY / path.name))
    original_lrck = [item.m_Uuid.AsString() for item in source_board.GetTracks() if item.GetNetname() == "I2S_LRCK"]
    board = pcbnew.LoadBoard(str(path))
    residual = [item.m_Uuid.AsString() for item in board.GetTracks() if item.GetNetname() == "I2S_LRCK"]
    if len(residual) != 3:
        raise RuntimeError("Expected unchanged B fanout and one original via")
    remove_objects(path, residual)
    report = work.parent / ("lrck-escape-refill-" + uuid.uuid4().hex[:8] + ".json")
    pipeline.run_command([pipeline.find_cli(), "pcb", "drc", "--format", "json", "--severity-all", "--refill-zones", "--save-board", "--output", report, path],
                         EVIDENCE, "escape-unrouted-refill", [], report)
    board = pcbnew.LoadBoard(str(path))
    ground = next(zone.GetFilledPolysList(pcbnew.In1_Cu) for zone in board.Zones()
                  if zone.GetNetname() == "POWER_GND" and zone.IsOnLayer(pcbnew.In1_Cu))
    planner.EVIDENCE = EVIDENCE
    planner.LAYERS = ["F.Cu", "B.Cu"]
    planner.STEP, planner.WIDTH, planner.VIA_AVOID_RADIUS = 0.025, 0.15, 0.275
    planner.XMIN, planner.YMIN, planner.XMAX, planner.YMAX = 144, 103, 162, 121
    planner.COLS = round((planner.XMAX - planner.XMIN) / planner.STEP) + 1
    planner.ROWS = round((planner.YMAX - planner.YMIN) / planner.STEP) + 1
    planner.SIZE = planner.COLS * planner.ROWS
    original_occupancy = planner.occupancy
    source, target = (150.3625, 114.1), (151.5, 104.59)
    mask = bytearray(planner.SIZE)
    for index in range(planner.SIZE):
        point = planner.coordinates(index)[:2]
        if math.dist(point, target) > 1.15 and not ground.Contains(vector(point)):
            mask[index] = 1
    def occupancy(items, radius, layers, net, forbid_terminal=False):
        grid = original_occupancy(items, radius, layers, net, forbid_terminal)
        if layers == ["F.Cu"]:
            for index, blocked in enumerate(mask):
                if blocked:
                    grid[index] = 1
        return grid
    planner.occupancy = occupancy
    print("Searching a new LRCK escape with standard 0.55/0.30mm vias", flush=True)
    try:
        route = planner.solve(obstacles(board), "I2S_LRCK", source, target, [0], 1)
    except RuntimeError as error:
        pipeline.write_json(EVIDENCE / "escape-failure.json", {"error": str(error), "removed_tracks": original_lrck,
                            "primary_unchanged": pipeline.digest(pipeline.PRIMARY / path.name) == BASELINE})
        raise
    added = []
    vias = []
    for start, end in zip(route["points"], route["points"][1:]):
        if start[2] != end[2]:
            if start[:2] != end[:2]:
                raise RuntimeError("Invalid via transition")
            via = pcbnew.PCB_VIA(board)
            via.SetPosition(vector(start[:2]))
            via.SetWidth(pcbnew.FromMM(0.55))
            via.SetDrill(pcbnew.FromMM(0.3))
            via.SetViaType(pcbnew.VIATYPE_THROUGH)
            via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
            via.SetNetCode(board.FindNet("I2S_LRCK").GetNetCode())
            board.Add(via)
            added.append(via.m_Uuid.AsString())
            vias.append(start[:2])
        elif start[:2] != end[:2]:
            track = pcbnew.PCB_TRACK(board)
            track.SetStart(vector(start[:2]))
            track.SetEnd(vector(end[:2]))
            track.SetLayer(pcbnew.F_Cu if start[2] == 0 else pcbnew.B_Cu)
            track.SetWidth(pcbnew.FromMM(0.15))
            track.SetNetCode(board.FindNet("I2S_LRCK").GetNetCode())
            board.Add(track)
            added.append(track.m_Uuid.AsString())
    pcbnew.SaveBoard(str(path), board)
    pipeline.write_json(EVIDENCE / "route-contract.json", {"removed_tracks": original_lrck, "added_tracks": added,
                        "points": route["points"], "width_mm": 0.15, "layers": ["F.Cu", "B.Cu"],
                        "new_vias": vias, "via_diameter_mm": 0.55, "via_drill_mm": 0.3,
                        "reference_requirement": "F route sampled over native In1 ground except header endpoint within1.15mm; post-fill check still required"})
    reports, summary = pipeline.check(work)
    candidate["summary"] = str(reports / "summary.json")
    pipeline.write_json(candidate_path, candidate)
    print(json.dumps({"drc": summary["drc"], "status": summary["status"], "new_vias": vias, "new_objects": len(added)}))


if __name__ == "__main__":
    main()
