"""Join the LP38691 ground lead directly to its same-net tab on B.Cu."""
import json
from pathlib import Path

import pcbnew
import pipeline
import plan_i2s_sdo as planner
from add_i2c_pullups import obstacles, position, vector
from improve_via_annular_rings import EVIDENCE


def main():
    candidate_path = EVIDENCE / "candidate.json"
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    work = pipeline.managed(Path(candidate["project"]))
    board_path = work / (pipeline.STEM + ".kicad_pcb")
    board = pcbnew.LoadBoard(str(board_path))
    pads = sorted((pad for pad in board.FindFootprintByReference("U702").Pads() if pad.GetNumber() == "2"),
                  key=lambda pad: pad.GetSize().x * pad.GetSize().y)
    planner.EVIDENCE = EVIDENCE
    planner.LAYERS = ["B.Cu"]
    planner.STEP = 0.025
    planner.WIDTH = 0.2
    planner.XMIN, planner.YMIN, planner.XMAX, planner.YMAX = 122, 115, 135, 124
    planner.COLS = round((planner.XMAX-planner.XMIN)/planner.STEP)+1
    planner.ROWS = round((planner.YMAX-planner.YMIN)/planner.STEP)+1
    planner.SIZE = planner.COLS*planner.ROWS
    plan = planner.solve(obstacles(board), "POWER_GND", position(pads[0]), position(pads[1]), [0], 0)
    added = []
    for start, end in zip(plan["points"], plan["points"][1:]):
        if start[:2] == end[:2]:
            continue
        track = pcbnew.PCB_TRACK(board)
        track.SetStart(vector(start[:2]))
        track.SetEnd(vector(end[:2]))
        track.SetWidth(pcbnew.FromMM(planner.WIDTH))
        track.SetLayer(pcbnew.B_Cu)
        track.SetNetCode(pads[0].GetNetCode())
        board.Add(track)
        added.append(track.m_Uuid.AsString())
    plan["added_tracks"] = added
    pcbnew.SaveBoard(str(board_path), board)
    pipeline.write_json(EVIDENCE / "ldo-ground-bridge.json", plan)
    reports, summary = pipeline.check(work)
    candidate["summary"] = str(reports / "summary.json")
    pipeline.write_json(candidate_path, candidate)
    print(json.dumps({"drc": summary["drc"], "status": summary["status"], "added_tracks": len(added)}))


if __name__ == "__main__":
    main()
