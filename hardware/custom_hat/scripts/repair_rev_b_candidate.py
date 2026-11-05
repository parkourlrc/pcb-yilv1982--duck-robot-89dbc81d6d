import argparse
import json
from pathlib import Path
import shutil

import pcbnew

from add_i2c_pullups import obstacles, vector
import plan_i2s_sdo as planner


parser = argparse.ArgumentParser()
parser.add_argument("directory", type=Path)
arguments = parser.parse_args()
directory = arguments.directory.resolve()
path = directory/"custom_hat_rev_b.kicad_pcb"
shutil.copy2(path,directory/"before-local-repair.kicad_pcb")
board = pcbnew.LoadBoard(str(path))
report = json.loads((directory/"drc-complete-project.json").read_text(encoding="utf-8"))
for track in board.GetTracks():
    if track.Type()!=pcbnew.PCB_VIA_T:
        if track.GetWidth()<pcbnew.FromMM(0.15):
            track.SetWidth(pcbnew.FromMM(0.15))
        for method in ("Start","End"):
            point=getattr(track,"Get"+method)()
            if point.y<pcbnew.FromMM(100.46):
                point.y=pcbnew.FromMM(100.46)
                getattr(track,"Set"+method)(point)
planner.EVIDENCE=directory
planner.LAYERS=["F.Cu","B.Cu"]
planner.STEP=0.025
planner.WIDTH=0.15
planner.VIA_AVOID_RADIUS=0.3
planner.VIA_PENALTY=120.0
planner.XMIN,planner.YMIN,planner.XMAX,planner.YMAX=131.0,100.6,164.4,129.4
planner.COLS=round((planner.XMAX-planner.XMIN)/planner.STEP)+1
planner.ROWS=round((planner.YMAX-planner.YMIN)/planner.STEP)+1
planner.SIZE=planner.COLS*planner.ROWS
items={item.m_Uuid.AsString():item for item in board.GetTracks()}
items.update({pad.m_Uuid.AsString():pad for footprint in board.GetFootprints() for pad in footprint.Pads()})
plans=[]
for violation in report["unconnected_items"]:
    start_item,end_item=[items[item["uuid"]] for item in violation["items"]]
    net=start_item.GetNetname()
    start=tuple(pcbnew.ToMM(value) for value in start_item.GetPosition())
    end=tuple(pcbnew.ToMM(value) for value in end_item.GetPosition())
    start_layers=[index for index,layer in enumerate((pcbnew.F_Cu,pcbnew.B_Cu)) if start_item.IsOnLayer(layer)]
    end_layers=[index for index,layer in enumerate((pcbnew.F_Cu,pcbnew.B_Cu)) if end_item.IsOnLayer(layer)]
    seed=next((item for item in board.GetTracks() if item.Type()==pcbnew.PCB_VIA_T and item.GetNetname()==net and pcbnew.ToMM(item.GetPosition().y)<112 and pcbnew.ToMM(item.GetPosition().x)<140),None)
    if seed is not None:
        start=tuple(pcbnew.ToMM(value) for value in seed.GetPosition())
        start_layers=[0,1]
        other=next((item for item in board.GetTracks() if item.Type()==pcbnew.PCB_VIA_T and item.GetNetname()==net and item.m_Uuid.AsString()!=seed.m_Uuid.AsString()),None)
        if other is not None:
            end=tuple(pcbnew.ToMM(value) for value in other.GetPosition())
            end_layers=[0,1]
    print("Routing "+net,flush=True)
    plan=planner.solve(obstacles(board),net,start,end,end_layers,start_layers)
    plan["via_diameter"]=0.6
    for first,last in zip(plan["points"],plan["points"][1:]):
        if first[2]!=last[2]:
            track=pcbnew.PCB_VIA(board)
            track.SetPosition(vector(first[:2]))
            track.SetWidth(pcbnew.FromMM(0.6))
            track.SetDrill(pcbnew.FromMM(0.3))
            track.SetViaType(pcbnew.VIATYPE_THROUGH)
            track.SetLayerPair(pcbnew.F_Cu,pcbnew.B_Cu)
        else:
            track=pcbnew.PCB_TRACK(board)
            track.SetStart(vector(first[:2]))
            track.SetEnd(vector(last[:2]))
            track.SetLayer(pcbnew.F_Cu if first[2]==0 else pcbnew.B_Cu)
            track.SetWidth(pcbnew.FromMM(0.15))
        track.SetNetCode(board.FindNet(net).GetNetCode())
        board.Add(track)
    plans.append(plan)
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
pcbnew.SaveBoard(str(path),board)
(directory/"local-repair.json").write_text(json.dumps(plans,indent=2),encoding="utf-8")
print(json.dumps({"routes":len(plans),"status":"native_DRC_required"}))
