import json
from pathlib import Path

import pcbnew

from add_i2c_pullups import obstacles, position, vector
from fit_ldo_candidate import remove_objects
import plan_i2s_sdo as planner


project=Path(__file__).resolve().parents[1]/"rev_b"
path=project/"custom_hat_rev_b.kicad_pcb"
evidence=project.parents[2]/"docs/references/扩展板乙版降本"
board=pcbnew.LoadBoard(str(path))
nets={"MIC_EXT_L","MIC_EXT_R"}
removed=[track.m_Uuid.AsString() for track in board.GetTracks() if track.GetNetname() in nets or track.m_Uuid.AsString()=="2e77acb4-d919-4215-8fcf-a41db5fd0bfc"]
remove_objects(path,removed)
board=pcbnew.LoadBoard(str(path))
planner.EVIDENCE=evidence
planner.LAYERS=["F.Cu","B.Cu"]
planner.STEP=0.05
planner.WIDTH=0.25
planner.VIA_AVOID_RADIUS=0.3
planner.VIA_PENALTY=120
planner.XMIN,planner.YMIN,planner.XMAX,planner.YMAX=133,119,153,129.4
planner.COLS=round((planner.XMAX-planner.XMIN)/planner.STEP)+1
planner.ROWS=round((planner.YMAX-planner.YMIN)/planner.STEP)+1
planner.SIZE=planner.COLS*planner.ROWS
plans=[]
for net,start_ref,start_pin,end_ref,end_pin in (("MIC_EXT_L","J505","2","R721","2"),("MIC_EXT_L","C723","1","R721","2"),("MIC_EXT_R","J507","2","R722","2"),("MIC_EXT_R","C724","1","R722","2")):
    start=next(pad for pad in board.FindFootprintByReference(start_ref).Pads() if pad.GetNumber()==start_pin)
    end=next(pad for pad in board.FindFootprintByReference(end_ref).Pads() if pad.GetNumber()==end_pin)
    if start.GetNetname()!=net or end.GetNetname()!=net:
        raise RuntimeError("Endpoint mismatch")
    plan=planner.solve(obstacles(board),net,position(start),position(end),[0],[0,1] if start_ref.startswith("J") else 0)
    for first,last in zip(plan["points"],plan["points"][1:]):
        if first[2]!=last[2]:
            track=pcbnew.PCB_VIA(board)
            track.SetPosition(vector(first[:2]))
            track.SetWidth(pcbnew.FromMM(0.6))
            track.SetDrill(pcbnew.FromMM(0.3))
            track.SetViaType(pcbnew.VIATYPE_THROUGH)
            track.SetLayerPair(pcbnew.F_Cu,pcbnew.B_Cu)
            track.SetFrontTentingMode(pcbnew.TENTING_MODE_TENTED)
            track.SetBackTentingMode(pcbnew.TENTING_MODE_TENTED)
        else:
            track=pcbnew.PCB_TRACK(board)
            track.SetStart(vector(first[:2]))
            track.SetEnd(vector(last[:2]))
            track.SetWidth(pcbnew.FromMM(0.25))
            track.SetLayer(pcbnew.F_Cu if first[2]==0 else pcbnew.B_Cu)
        track.SetNet(board.FindNet(net))
        board.Add(track)
    plans.append(plan)
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
pcbnew.SaveBoard(str(path),board)
(evidence/"mic-connector-reroute.json").write_text(json.dumps(plans,indent=2),encoding="utf-8")
print(json.dumps({"routes":len(plans),"needs_native_DRC":True}))
