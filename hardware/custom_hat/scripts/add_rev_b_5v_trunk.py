import json
from pathlib import Path
import sys

import pcbnew

from add_i2c_pullups import obstacles, position, vector
import plan_i2s_sdo as planner


directory=Path(sys.argv[1]).resolve()
path=directory/"custom_hat_rev_b.kicad_pcb"
board=pcbnew.LoadBoard(str(path))
planner.EVIDENCE=directory
planner.LAYERS=["F.Cu","B.Cu"]
planner.STEP=0.05
planner.WIDTH=1.0
planner.VIA_AVOID_RADIUS=0.5
planner.VIA_PENALTY=150
planner.XMIN,planner.YMIN,planner.XMAX,planner.YMAX=101.0,101.0,133.0,129.0
planner.COLS=round((planner.XMAX-planner.XMIN)/planner.STEP)+1
planner.ROWS=round((planner.YMAX-planner.YMIN)/planner.STEP)+1
planner.SIZE=planner.COLS*planner.ROWS
start=next(pad for pad in board.FindFootprintByReference("Q301").Pads() if pad.GetNumber()=="3")
end=next(pad for pad in board.FindFootprintByReference("J101").Pads() if pad.GetNumber()=="2")
plan=planner.solve(obstacles(board),"+5V",position(start),position(end),[0,1],0)
plan["via_diameter"]=1.0
plan["via_drill"]=0.3
for first,last in zip(plan["points"],plan["points"][1:]):
    if first[2]!=last[2]:
        track=pcbnew.PCB_VIA(board)
        track.SetPosition(vector(first[:2]))
        track.SetWidth(pcbnew.FromMM(1.0))
        track.SetDrill(pcbnew.FromMM(0.3))
        track.SetViaType(pcbnew.VIATYPE_THROUGH)
        track.SetLayerPair(pcbnew.F_Cu,pcbnew.B_Cu)
        track.SetFrontTentingMode(pcbnew.TENTING_MODE_TENTED)
        track.SetBackTentingMode(pcbnew.TENTING_MODE_TENTED)
    else:
        track=pcbnew.PCB_TRACK(board)
        track.SetStart(vector(first[:2]))
        track.SetEnd(vector(last[:2]))
        track.SetWidth(pcbnew.FromMM(1.0))
        track.SetLayer(pcbnew.F_Cu if first[2]==0 else pcbnew.B_Cu)
    track.SetNet(board.FindNet("+5V"))
    board.Add(track)
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
pcbnew.SaveBoard(str(path),board)
(directory/"5v-trunk.json").write_text(json.dumps(plan,indent=2),encoding="utf-8")
print(json.dumps({"status":"native_check_required","vertices":len(plan["points"])}))
