"""Export explicit via protection requirements and a bounded conduction estimate."""
import csv
import argparse
import json
import math
from pathlib import Path

import pcbnew
import pipeline
from plan_buck_thermal_vias import EVIDENCE


OUTPUT=pipeline.PRIMARY/"production-20261031-buck-review"


def main():
    global EVIDENCE,OUTPUT
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence",type=Path)
    parser.add_argument("--output",type=Path)
    arguments=parser.parse_args()
    EVIDENCE=arguments.evidence.resolve() if arguments.evidence else EVIDENCE
    OUTPUT=arguments.output.resolve() if arguments.output else OUTPUT
    board_path=pipeline.PRIMARY/(pipeline.STEM+".kicad_pcb")
    checkpoint=json.loads((EVIDENCE/"checkpoint.json").read_text(encoding="utf-8"))
    if pipeline.digest(board_path)!=checkpoint["pcb_sha256"]:
        raise RuntimeError("Current board differs from the export checkpoint")
    board=pcbnew.LoadBoard(str(board_path))
    processes=[]
    for via in board.GetTracks():
        if via.Type()!=pcbnew.PCB_VIA_T or via.GetFillingMode()!=pcbnew.FILLING_MODE_FILLED:
            continue
        micro=via.GetViaType()==pcbnew.VIATYPE_MICROVIA
        processes.append({
            "UUID":via.m_Uuid.AsString(),"Net":via.GetNetname(),"X_mm":pcbnew.ToMM(via.GetPosition().x),"Y_mm":pcbnew.ToMM(via.GetPosition().y),
            "CAM_X_nominal_mm":pcbnew.ToMM(via.GetPosition().x),"CAM_Y_nominal_mm":-pcbnew.ToMM(via.GetPosition().y),
            "StartLayer":board.GetLayerName(via.TopLayer()),"EndLayer":board.GetLayerName(via.BottomLayer()),
            "Diameter_mm":pcbnew.ToMM(via.GetFrontWidth()),"Drill_mm":pcbnew.ToMM(via.GetDrill()),
            "RequiredProcess":"HDI blind via, filled and copper capped" if micro else "Mechanical through-via, filled and copper capped",
            "Purpose":"Codec VCC via-in-pad" if via.m_Uuid.AsString()=="c6ad78c2-361f-4c03-a650-a32f6c415d72" else "U301 thermal via",
            "CappedInDesign":via.GetCappingMode()==pcbnew.CAPPING_MODE_CAPPED,
            "Status":"Design requirement only; supplier acceptance and as-built verification pending",
        })
    if len(processes)!=6 or not all(item["CappedInDesign"] for item in processes):
        raise RuntimeError("Expected five thermal vias and one codec supply via with protection requirements")
    with (OUTPUT/"via-process-requirements.csv").open("w",encoding="utf-8-sig",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=list(processes[0]))
        writer.writeheader()
        writer.writerows(processes)
    pipeline.write_json(EVIDENCE/"via-process-requirements.json",{"pcb_sha256":checkpoint["pcb_sha256"],"coordinate_system":"X_mm/Y_mm are KiCad board coordinates (Y down); CAM nominal columns use the current absolute mm Excellon/CPL frame (Y negated), before export rounding. B side is not mirrored again.","vias":processes,"manufactured":False})
    calculations=[]
    for vin in (6.6,7.4,8.4):
        for load in (1.0,2.0,3.5):
            duty=4.984/vin
            ripple=4.984*(vin-4.984)/(vin*5.6e-6*500000)
            rms_squared=load*load+ripple*ripple/12
            conduction=rms_squared*(0.075*duty+0.045*(1-duty))
            calculations.append({"vin_v":vin,"load_a":load,"nominal_duty":duty,"nominal_ripple_pp_a":ripple,"typical_25c_conduction_only_w":conduction})
    pipeline.write_json(EVIDENCE/"buck-loss-scenarios.json",{
        "source":"Diodes AP64350 DS41976 Rev5-2 p5: typical25C Rds(on) HS75mOhm/LS45mOhm",
        "assumptions":"Nominal5.6uH,500kHz,4.984V, idealCCM; input6.6-8.4V is an analysis window, not a battery cutoff",
        "limits":"Only a conduction-loss illustration; no guaranteed thermal bound; excludes switching/core/gate losses and temperature-dependent Rds. Datasheet45C/W is a reference-board condition, not measured for this board.",
        "scenarios":calculations,"hardware_tested":False,
    })
    manifest=json.loads((OUTPUT/"manifest.json").read_text(encoding="utf-8"))
    manifest["outputs"]["via-process-requirements.csv"]=pipeline.digest(OUTPUT/"via-process-requirements.csv")
    pipeline.write_json(OUTPUT/"manifest.json",manifest)
    print(json.dumps({"required_filled_capped_vias":len(processes),"conduction_loss_3p5a_w":[item["typical_25c_conduction_only_w"] for item in calculations if item["load_a"]==3.5]}))


if __name__=="__main__":
    main()
