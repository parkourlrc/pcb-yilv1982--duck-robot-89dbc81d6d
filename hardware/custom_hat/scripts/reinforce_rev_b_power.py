import argparse
import json
from pathlib import Path
import shutil

import pcbnew


parser=argparse.ArgumentParser()
parser.add_argument("directory",type=Path)
arguments=parser.parse_args()
directory=arguments.directory.resolve()
path=directory/"custom_hat_rev_b.kicad_pcb"
backup=directory/"before-power-reinforcement.kicad_pcb"
if backup.exists():
    raise FileExistsError("Inspect existing power candidate before rerunning")
shutil.copy2(path,backup)
board=pcbnew.LoadBoard(str(path))
changes=[]
for track in board.GetTracks():
    if track.Type()==pcbnew.PCB_VIA_T:
        continue
    start=tuple(pcbnew.ToMM(value) for value in track.GetStart())
    end=tuple(pcbnew.ToMM(value) for value in track.GetEnd())
    width=None
    if track.GetNetname()=="VBATT_2S_IN" and start[1]==end[1]==111.5 and {start[0],end[0]}=={105.5,112.5}:
        width=1.6
    if track.GetNetname()=="BUCK_SW" and start[1]==end[1]==120.0:
        width=0.8 if min(start[0],end[0])<112 else 1.2
    if track.GetNetname()=="VBATT_2S_IN" and track.GetLayer()==pcbnew.F_Cu and min(start[1],end[1])>=120.9:
        width=1.2
    if track.GetNetname()=="+5V_PRE_IDEAL" and track.GetLayer()==pcbnew.F_Cu and min(start[1],end[1])>=120.0:
        width=1.2
    if width:
        changes.append({"uuid":track.m_Uuid.AsString(),"net":track.GetNetname(),"before":pcbnew.ToMM(track.GetWidth()),"after":width})
        track.SetWidth(pcbnew.FromMM(width))
for net,layer,width,points in (
    ("VBATT_2S_IN",pcbnew.B_Cu,1.6,[(105.5,111.5),(112.5,111.5)]),
    ("POWER_GND",pcbnew.F_Cu,1.6,[(105.5,113.5),(112.5,113.5)]),
):
    for start,end in zip(points,points[1:]):
        track=pcbnew.PCB_TRACK(board)
        track.SetStart(pcbnew.VECTOR2I(*(pcbnew.FromMM(value) for value in start)))
        track.SetEnd(pcbnew.VECTOR2I(*(pcbnew.FromMM(value) for value in end)))
        track.SetWidth(pcbnew.FromMM(width))
        track.SetLayer(layer)
        track.SetNet(board.FindNet(net))
        board.Add(track)
        changes.append({"new":track.m_Uuid.AsString(),"net":net,"width":width,"layer":board.GetLayerName(layer)})
footprint_library=Path("C:/Users/yilv/AppData/Local/Programs/KiCad/10.0/share/kicad/footprints/Fiducial.pretty")
for reference,position in (("FID1",(101.35,108.0)),("FID2",(163.5,108.0)),("FID3",(124.0,128.1))):
    footprint=pcbnew.FootprintLoad(str(footprint_library),"Fiducial_1mm_Mask2mm")
    footprint.SetFPID(pcbnew.LIB_ID("Fiducial","Fiducial_1mm_Mask2mm"))
    footprint.SetReference(reference)
    footprint.SetAttributes(pcbnew.FP_EXCLUDE_FROM_BOM|pcbnew.FP_EXCLUDE_FROM_POS_FILES|pcbnew.FP_BOARD_ONLY)
    footprint.SetPosition(pcbnew.VECTOR2I(*(pcbnew.FromMM(value) for value in position)))
    footprint.Reference().SetVisible(False)
    footprint.Value().SetVisible(False)
    board.Add(footprint)
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
pcbnew.SaveBoard(str(path),board)
(directory/"power-reinforcement.json").write_text(json.dumps(changes,indent=2),encoding="utf-8")
print(json.dumps({"changes":len(changes),"fiducials":3,"native_check_required":True}))
