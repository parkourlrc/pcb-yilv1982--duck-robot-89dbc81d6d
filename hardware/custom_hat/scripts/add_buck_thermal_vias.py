"""Add planned ground thermal vias and explicit filled/capped fabrication requirements."""
import json
from pathlib import Path

import pcbnew
import pipeline
from generate_rev_a import parse
from add_i2c_pullups import vector
from plan_buck_thermal_vias import EVIDENCE


def main():
    candidate_path=EVIDENCE/"candidate.json"
    candidate=json.loads(candidate_path.read_text(encoding="utf-8"))
    work=pipeline.managed(Path(candidate["project"]))
    board_path=work/(pipeline.STEM+".kicad_pcb")
    plan=json.loads((EVIDENCE/"thermal-via-plan-after-cap-move.json").read_text(encoding="utf-8"))
    if pipeline.digest(board_path)!=plan["source_pcb_sha256"] or len(plan["greedy_selected_sites"])!=5:
        raise RuntimeError("Thermal candidate no longer matches the inspected site plan")
    board=pcbnew.LoadBoard(str(board_path))
    new_vias=[]
    for point in plan["greedy_selected_sites"]:
        via=pcbnew.PCB_VIA(board)
        via.SetPosition(vector(point))
        via.SetWidth(pcbnew.FromMM(plan["diameter_mm"]))
        via.SetDrill(pcbnew.FromMM(plan["drill_mm"]))
        via.SetViaType(pcbnew.VIATYPE_THROUGH)
        via.SetLayerPair(pcbnew.F_Cu,pcbnew.B_Cu)
        via.SetNetCode(board.FindNet("POWER_GND").GetNetCode())
        via.SetFillingMode(pcbnew.FILLING_MODE_FILLED)
        via.SetCappingMode(pcbnew.CAPPING_MODE_CAPPED)
        board.Add(via)
        new_vias.append({"uuid":via.m_Uuid.AsString(),"position":point,"diameter_mm":plan["diameter_mm"],
                         "drill_mm":plan["drill_mm"],"net":"POWER_GND","process":"filled and copper-capped thermal through-via; fabrication requirement, not as-built evidence"})
    microvias=[via for via in board.GetTracks() if via.Type()==pcbnew.PCB_VIA_T and via.GetViaType()==pcbnew.VIATYPE_MICROVIA]
    if len(microvias)!=1:
        raise RuntimeError("Expected one existing codec microvia")
    microvia=microvias[0]
    microvia.SetFillingMode(pcbnew.FILLING_MODE_FILLED)
    microvia.SetCappingMode(pcbnew.CAPPING_MODE_CAPPED)
    pcbnew.SaveBoard(str(board_path),board)
    for filename in ("power.kicad_sch","audio.kicad_sch"):
        path=work/filename
        original=path.read_text(encoding="utf-8")
        cleaned="\n".join(row.rstrip() for row in original.splitlines())+"\n"
        if parse(original)!=parse(cleaned):
            raise RuntimeError("Whitespace normalization changed source")
        path.write_text(cleaned,encoding="utf-8")
    pipeline.write_json(EVIDENCE/"thermal-vias-added.json",{"new_vias":new_vias,"existing_microvia":microvia.m_Uuid.AsString(),
        "microvia_process":"filled and copper-capped B.Cu-In2.Cu blind microvia; stackup and supplier acceptance still pending",
        "manufactured":False,"paste_opening_changed":False})
    reports,summary=pipeline.check(work)
    candidate["summary"]=str(reports/"summary.json")
    pipeline.write_json(candidate_path,candidate)
    print(json.dumps({"new_thermal_vias":len(new_vias),"drc":summary["drc"],"erc":summary["erc"],"status":summary["status"]}))


if __name__=="__main__":
    main()
