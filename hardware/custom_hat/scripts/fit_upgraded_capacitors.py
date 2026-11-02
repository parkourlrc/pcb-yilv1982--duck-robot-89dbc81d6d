"""Fit the larger output capacitors around the existing power traces and vias."""
import json
from pathlib import Path

import pcbnew
import pipeline
from add_i2c_pullups import vector
from upgrade_buck_capacitors import EVIDENCE, POSITIONS, MPN


def main():
    candidate_path=EVIDENCE/"candidate.json"
    candidate=json.loads(candidate_path.read_text(encoding="utf-8"))
    work=pipeline.managed(Path(candidate["project"]))
    board_path=work/(pipeline.STEM+".kicad_pcb")
    board=pcbnew.LoadBoard(str(board_path))
    moved=[]
    for reference in ("C305","C306"):
        footprint=board.FindFootprintByReference(reference)
        if footprint.GetFieldText("MPN")!=MPN:
            raise RuntimeError("Unexpected output capacitor")
        previous=[pcbnew.ToMM(value) for value in footprint.GetPosition()]
        footprint.SetPosition(vector(POSITIONS[reference]))
        moved.append({"reference":reference,"previous_trial_position":previous,"position":POSITIONS[reference]})
    pcbnew.SaveBoard(str(board_path),board)
    contract=json.loads((EVIDENCE/"change-contract.json").read_text(encoding="utf-8"))
    contract["positions"]=POSITIONS
    contract["placement_adjustments"]=moved
    pipeline.write_json(EVIDENCE/"change-contract.json",contract)
    reports,summary=pipeline.check(work)
    candidate["summary"]=str(reports/"summary.json")
    pipeline.write_json(candidate_path,candidate)
    print(json.dumps({"drc":summary["drc"],"status":summary["status"]}))


if __name__=="__main__":
    main()
