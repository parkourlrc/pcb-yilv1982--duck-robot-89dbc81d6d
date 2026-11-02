"""Test small supply-via offsets to retain the LDO ground plane neck."""
import json
from pathlib import Path
import shutil
import uuid

import pcbnew
import pipeline
from improve_via_annular_rings import EVIDENCE


def main():
    candidate_path = EVIDENCE / "candidate.json"
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    work = pipeline.managed(Path(candidate["project"]))
    board_path = work / (pipeline.STEM + ".kicad_pcb")
    baseline = work.parent / ("before-ground-neck-" + uuid.uuid4().hex[:8] + ".kicad_pcb")
    shutil.copy2(board_path, baseline)
    trials = []
    for identifier in ("c6c9e478-bbdc-4453-bd32-c353d46e8c29", "eb735ea3-6278-4224-b374-b13370420d94"):
        for delta in ((0.05, 0), (0.1, 0), (-0.05, 0), (0, -0.05), (0, 0.05), (0.05, -0.05), (0.05, 0.05)):
            shutil.copy2(baseline, board_path)
            board = pcbnew.LoadBoard(str(board_path))
            via = next(item for item in board.GetTracks() if item.m_Uuid.AsString() == identifier)
            old = list(via.GetPosition())
            new = pcbnew.VECTOR2I(old[0]+pcbnew.FromMM(delta[0]), old[1]+pcbnew.FromMM(delta[1]))
            attached = []
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
                    attached.append(track.m_Uuid.AsString())
            via.SetPosition(new)
            pcbnew.SaveBoard(str(board_path), board)
            report_path = work.parent / ("ground-neck-" + uuid.uuid4().hex[:8] + ".json")
            commands = []
            pipeline.run_command([pipeline.find_cli(), "pcb", "drc", "--format", "json", "--severity-all", "--refill-zones", "--output", report_path, board_path],
                                 EVIDENCE, "ground-neck-" + str(len(trials)), commands, report_path)
            report = json.loads(report_path.read_text(encoding="utf-8"))
            trial = {"via": identifier, "delta_mm": delta, "attached_tracks": attached, "report": str(report_path), "commands": commands,
                     "violations": len(report["violations"]), "unconnected": len(report["unconnected_items"])}
            trials.append(trial)
            if not trial["violations"] and not trial["unconnected"]:
                reports, summary = pipeline.check(work)
                candidate["summary"] = str(reports / "summary.json")
                pipeline.write_json(candidate_path, candidate)
                pipeline.write_json(EVIDENCE / "ground-neck-trials.json", {"accepted": trial, "trials": trials})
                print(json.dumps({"accepted": trial, "status": summary["status"]}))
                return
    shutil.copy2(baseline, board_path)
    pipeline.write_json(EVIDENCE / "ground-neck-trials.json", {"accepted": None, "trials": trials})
    raise RuntimeError("No local offset restored the ground neck; baseline candidate retained")


if __name__ == "__main__":
    main()
