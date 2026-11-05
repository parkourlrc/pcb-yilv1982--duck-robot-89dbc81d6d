"""Add a fabrication-visible board name and revision in an isolated checked project."""
import json
import argparse
from pathlib import Path

import pcbnew

import pipeline
from add_i2c_pullups import vector


EVIDENCE = pipeline.BASE.parents[1] / "docs/references/扩展板电路仿真工具/board-marking-20261031"
BASELINE = "143a483d578822d332f4576c3eb01c66c11131f45257d675dd95d15c6c0e8985"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--retry-position", action="store_true")
    arguments = parser.parse_args()
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    candidate_path = EVIDENCE / "candidate.json"
    if candidate_path.exists() and not arguments.retry_position:
        raise FileExistsError("Inspect the existing marking candidate")
    if pipeline.digest(pipeline.PRIMARY / (pipeline.STEM + ".kicad_pcb")) != BASELINE:
        raise RuntimeError("Source changed")
    candidate = json.loads(candidate_path.read_text(encoding="utf-8")) if arguments.retry_position else None
    work = pipeline.managed(Path(candidate["project"])) if candidate else pipeline.prepare(pipeline.PRIMARY)
    path = work / (pipeline.STEM + ".kicad_pcb")
    board = pcbnew.LoadBoard(str(path))
    if candidate:
        pipeline.write_json(EVIDENCE / "rejected-fiducial-overlap-candidate.json", candidate)
        old = json.loads((EVIDENCE / "change-contract.json").read_text(encoding="utf-8"))
        text = next(item for item in board.GetDrawings() if item.m_Uuid.AsString() == old["added_text_uuid"])
    else:
        text = pcbnew.PCB_TEXT(board)
        text.SetText("DUCK HAT Rev A")
        board.Add(text)
    text.SetPosition(vector((141, 126.5)))
    text.SetTextSize(vector((.8, .8)))
    text.SetTextThickness(pcbnew.FromMM(.12))
    text.SetLayer(pcbnew.F_SilkS)
    pcbnew.SaveBoard(str(path), board)
    pipeline.write_json(EVIDENCE / "change-contract.json", {"added_text_uuid": text.m_Uuid.AsString(), "text": text.GetText(),
        "layer": "F.Silkscreen", "position_mm": [141, 126.5], "height_mm": .8, "stroke_mm": .12,
        "changed_existing_geometry": False, "revision_meaning": "Design revision A; not a manufacturing approval or tested-board mark"})
    reports, summary = pipeline.check(work)
    pipeline.write_json(candidate_path, {"project": str(work), "baseline": BASELINE, "summary": str(reports / "summary.json"), "promoted": False})
    print(json.dumps({"project": str(work), "status": summary["status"], "drc": summary["drc"]}))


if __name__ == "__main__":
    main()
