"""Resolve three silk placements exposed by the stricter clearance check."""
import json
from pathlib import Path

import pcbnew

import pipeline
from add_i2c_pullups import vector
from enforce_manufacturing_text import EVIDENCE


def main():
    candidate_path = EVIDENCE / "candidate.json"
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    work = pipeline.managed(Path(candidate["project"]))
    contract_path = EVIDENCE / "change-contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    if "additional_silkscreen_adjustments" in contract:
        raise RuntimeError("Silk placements already adjusted")
    board_path = work / (pipeline.STEM + ".kicad_pcb")
    board = pcbnew.LoadBoard(str(board_path))
    changes = []
    for reference, position in (("U803", (147.72, 129.2)), ("J802", (160.12, 123.17))):
        item = board.FindFootprintByReference(reference).Reference()
        changes.append({"uuid": item.m_Uuid.AsString(), "text": reference, "before_mm": [pcbnew.ToMM(value) for value in item.GetPosition()], "after_mm": position})
        item.SetPosition(vector(position))
    outline = next(item for item in board.FindFootprintByReference("C309").GraphicalItems() if item.m_Uuid.AsString() == "9d5e185b-95ea-4a88-8a29-4bc9a25a726d")
    changes.append({"uuid": outline.m_Uuid.AsString(), "reference": "C309", "before_layer": outline.GetLayerName(), "after_layer": "B.Fab"})
    outline.SetLayer(pcbnew.B_Fab)
    pcbnew.SaveBoard(str(board_path), board)
    contract["additional_silkscreen_adjustments"] = changes
    pipeline.write_json(contract_path, contract)
    reports, summary = pipeline.check(work)
    candidate["summary"] = str(reports / "summary.json")
    pipeline.write_json(candidate_path, candidate)
    print(json.dumps({"status": summary["status"], "drc": summary["drc"]}))


if __name__ == "__main__":
    main()
