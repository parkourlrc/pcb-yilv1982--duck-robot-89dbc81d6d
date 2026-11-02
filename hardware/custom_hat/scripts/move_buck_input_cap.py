"""Place C303 close to VIN and add a local ground return via."""
import json
from pathlib import Path
import shutil
import uuid

import pcbnew
import pipeline
from add_i2c_pullups import vector
from plan_buck_thermal_vias import EVIDENCE


def main():
    candidate_path=EVIDENCE/"candidate.json"
    candidate=json.loads(candidate_path.read_text(encoding="utf-8"))
    work=pipeline.managed(Path(candidate["project"]))
    board_path=work/(pipeline.STEM+".kicad_pcb")
    shutil.copy2(board_path,work.parent/("before-c303-"+uuid.uuid4().hex[:8]+".kicad_pcb"))
    board=pcbnew.LoadBoard(str(board_path))
    capacitor=board.FindFootprintByReference("C303")
    capacitor.SetPosition(vector((126.84,108.8)))
    power=next(pad for pad in capacitor.Pads() if pad.GetNumber()=="1")
    ground=next(pad for pad in capacitor.Pads() if pad.GetNumber()=="2")
    vin=next(pad for pad in board.FindFootprintByReference("U301").Pads() if pad.GetNumber()=="2")
    via=pcbnew.PCB_VIA(board)
    via.SetPosition(vector((129.3,109.7)))
    via.SetWidth(pcbnew.FromMM(0.6))
    via.SetDrill(pcbnew.FromMM(0.3))
    via.SetViaType(pcbnew.VIATYPE_THROUGH)
    via.SetLayerPair(pcbnew.F_Cu,pcbnew.B_Cu)
    via.SetNetCode(ground.GetNetCode())
    board.Add(via)
    tracks=[]
    for pad,end in ((power,vin.GetPosition()),(ground,via.GetPosition())):
        track=pcbnew.PCB_TRACK(board)
        track.SetStart(pad.GetPosition())
        track.SetEnd(end)
        track.SetWidth(pcbnew.FromMM(0.6))
        track.SetLayer(pcbnew.F_Cu)
        track.SetNetCode(pad.GetNetCode())
        board.Add(track)
        tracks.append(track.m_Uuid.AsString())
    pcbnew.SaveBoard(str(board_path),board)
    pipeline.write_json(EVIDENCE/"input-cap-relocation.json",{
        "reference":"C303","from":[115.5,120.0,0],"to":[126.84,108.8,0],
        "added_tracks":tracks,"added_ground_via":via.m_Uuid.AsString(),"ground_via_position":[129.3,109.7],
        "power_pin_distance_before_mm":((125.365-114.025)**2+(111.5025-120.0)**2)**0.5,
        "power_pin_distance_after_mm":111.5025-108.8,"production_ready":False,
    })
    reports,summary=pipeline.check(work)
    candidate["summary"]=str(reports/"summary.json")
    pipeline.write_json(candidate_path,candidate)
    print(json.dumps({"drc":summary["drc"],"status":summary["status"]}))


if __name__=="__main__":
    main()
