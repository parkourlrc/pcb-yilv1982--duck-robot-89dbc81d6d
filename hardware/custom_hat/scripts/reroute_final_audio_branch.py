"""Route the displaced audio branch around its neighbouring amplifier via."""
import json
from pathlib import Path

import pcbnew
import pipeline
import plan_i2s_sdo as planner
from add_i2c_pullups import obstacles, vector
from select_final_bom import EVIDENCE


def main():
    candidate_path = EVIDENCE / "candidate.json"
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    work = pipeline.managed(Path(candidate["project"]))
    board_path = work / (pipeline.STEM + ".kicad_pcb")
    board = pcbnew.LoadBoard(str(board_path))
    identifier = "a28231d7-6f9b-4e2d-9b49-e57ac7a2e97f"
    original = next(track for track in board.GetTracks() if track.m_Uuid.AsString() == identifier)
    start = tuple(pcbnew.ToMM(value) for value in original.GetStart())
    end = tuple(pcbnew.ToMM(value) for value in original.GetEnd())
    planner.EVIDENCE = EVIDENCE
    planner.LAYERS = ["B.Cu"]
    planner.STEP = 0.025
    planner.WIDTH = 0.25
    planner.XMIN, planner.YMIN, planner.XMAX, planner.YMAX = 131.5, 112, 139, 118
    planner.COLS = round((planner.XMAX-planner.XMIN)/planner.STEP)+1
    planner.ROWS = round((planner.YMAX-planner.YMIN)/planner.STEP)+1
    planner.SIZE = planner.COLS*planner.ROWS
    items = [item for item in obstacles(board) if item.get("uuid") != identifier]
    plan = planner.solve(items, "AUDIO_LINE_L", start, end, [0], 0)
    added = []
    for index, (first_point, last_point) in enumerate(zip(plan["points"], plan["points"][1:])):
        track = original if index == 0 else pcbnew.PCB_TRACK(board)
        track.SetStart(vector(first_point[:2]))
        track.SetEnd(vector(last_point[:2]))
        track.SetLayer(pcbnew.B_Cu)
        track.SetWidth(pcbnew.FromMM(0.25))
        track.SetNetCode(original.GetNetCode())
        if index:
            board.Add(track)
            added.append(track.m_Uuid.AsString())
    plan["changed_track"] = identifier
    plan["added_tracks"] = added
    pcbnew.SaveBoard(str(board_path), board)
    pipeline.write_json(EVIDENCE / "audio-branch-route.json", plan)
    reports, result = pipeline.check(work)
    candidate["summary"] = str(reports / "summary.json")
    pipeline.write_json(candidate_path, candidate)
    print(json.dumps({"drc": result["drc"], "status": result["status"], "route_points": len(plan["points"])}))


if __name__ == "__main__":
    main()
