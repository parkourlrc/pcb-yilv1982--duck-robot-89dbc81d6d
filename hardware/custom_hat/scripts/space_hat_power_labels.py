"""Separate the two input labels after checking the initial native preview."""
import json

import pcbnew

import pipeline
from add_i2c_pullups import vector
from analyze_buck_compensation import EVIDENCE as PARENT


EVIDENCE = PARENT / "label-spacing"


def main():
    EVIDENCE.mkdir(exist_ok=True)
    path = EVIDENCE / "candidate.json"
    if path.exists():
        raise RuntimeError("Inspect the existing label-spacing candidate")
    primary = pipeline.PRIMARY / (pipeline.STEM + ".kicad_pcb")
    baseline = pipeline.digest(primary)
    if baseline != "3cc3c240e0c526bd8286a13fb063411ba13139addc787d4c7a1c16f805e38dcd":
        raise RuntimeError("Unexpected input-label baseline")
    work = pipeline.prepare(pipeline.PRIMARY)
    board_path = work / primary.name
    board = pcbnew.LoadBoard(str(board_path))
    positions = {"2S+": (126.65, 124.6), "GND": (123.05, 124.6)}
    changed = []
    for item in board.GetDrawings():
        if item.Type() == pcbnew.PCB_TEXT_T and item.GetText() in positions:
            changed.append({"uuid": item.m_Uuid.AsString(), "text": item.GetText(), "old_mm": [pcbnew.ToMM(value) for value in item.GetPosition()], "new_mm": positions[item.GetText()]})
            item.SetPosition(vector(positions[item.GetText()]))
    if len(changed) != 2:
        raise RuntimeError("Unexpected input label set")
    pcbnew.SaveBoard(str(board_path), board)
    reports, summary = pipeline.check(work)
    pipeline.write_json(path, {"project": str(work), "baseline": baseline, "summary": str(reports / "summary.json"), "promoted": False})
    pipeline.write_json(EVIDENCE / "change-contract.json", {"text_positions": changed, "reason": "Initial visible labels read as one word in the native preview", "copper_changes_allowed": False})
    print(json.dumps({"status": summary["status"], "drc": summary["drc"]}))


if __name__ == "__main__":
    main()
