import argparse
import json
from pathlib import Path

import pcbnew

from fit_ldo_candidate import remove_objects


parser=argparse.ArgumentParser()
parser.add_argument("directory",type=Path)
arguments=parser.parse_args()
directory=arguments.directory.resolve()
project=Path(__file__).resolve().parents[1]/"rev_b"
path=directory/"custom_hat_rev_b.kicad_pcb"
board=pcbnew.LoadBoard(str(path))
removed=[track.m_Uuid.AsString() for track in board.GetTracks() if track.Type()!=pcbnew.PCB_VIA_T and track.GetNetname()=="VBATT_2S_IN" and track.GetLayer()==pcbnew.B_Cu and pcbnew.ToMM(track.GetWidth())==1.6]
remove_objects(path,removed)
board=pcbnew.LoadBoard(str(path))
for track in board.GetTracks():
    if track.Type()==pcbnew.PCB_VIA_T:
        continue
    if track.GetNetname()=="BUCK_SW" and track.GetWidth()>pcbnew.FromMM(1.0):
        track.SetWidth(pcbnew.FromMM(1.0))
    if track.GetNetname()=="+5V_PRE_IDEAL":
        minimum_y=min(track.GetStart().y,track.GetEnd().y)
        maximum_x=max(track.GetStart().x,track.GetEnd().x)
        width=1.2 if track.GetLayer()==pcbnew.F_Cu and minimum_y>=pcbnew.FromMM(120.0) else 0.6
        if minimum_y>=pcbnew.FromMM(120.0) and maximum_x>pcbnew.FromMM(128):
            width=0.8 if track.GetLayer()==pcbnew.F_Cu else 0.6
        if track.GetLayer()==pcbnew.F_Cu and track.GetStart().y!=track.GetEnd().y and maximum_x<pcbnew.FromMM(123) and minimum_y>=pcbnew.FromMM(120):
            width=0.9
        track.SetWidth(pcbnew.FromMM(width))
fiducials=[footprint for footprint in board.GetFootprints() if footprint.GetReference().startswith("FID")]
shapes=[pad.GetEffectiveShape(pcbnew.F_Cu) for footprint in board.GetFootprints() if not footprint.GetReference().startswith("FID") for pad in footprint.Pads() if pad.IsOnLayer(pcbnew.F_Cu) or pad.GetDrillSize().x]
shapes.extend(track.GetEffectiveShape(pcbnew.F_Cu) for track in board.GetTracks() if track.IsOnLayer(pcbnew.F_Cu))
courtyards=[footprint.GetCourtyard(pcbnew.F_CrtYd) for footprint in board.GetFootprints() if not footprint.GetReference().startswith("FID")]
for footprint in fiducials:
    original=footprint.GetPosition()
    candidates=sorted((delta_x*delta_x+delta_y*delta_y,delta_x,delta_y) for delta_x in range(-20,21) for delta_y in range(-20,21))
    for _,delta_x,delta_y in candidates:
        point=pcbnew.VECTOR2I(original.x+pcbnew.FromMM(delta_x*0.25),original.y+pcbnew.FromMM(delta_y*0.25))
        if not(101.2<pcbnew.ToMM(point.x)<163.8 and 101.2<pcbnew.ToMM(point.y)<128.8):
            continue
        footprint.SetPosition(point)
        pad=next(iter(footprint.Pads()))
        shape=pad.GetEffectiveShape(pcbnew.F_Cu)
        courtyard=footprint.GetCourtyard(pcbnew.F_CrtYd)
        if not any(shape.Collide(other,pcbnew.FromMM(0.65)) for other in shapes) and not any(courtyard.Collide(other,0) for other in courtyards):
            break
    else:
        raise RuntimeError("No clear fiducial position")
    footprint.SetFPID(pcbnew.LIB_ID("duck","Fiducial_1mm_Mask2mm_B"))
    pcbnew.FootprintSave(str(project/"duck.pretty"),footprint)
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
pcbnew.SaveBoard(str(path),board)
print(json.dumps({"removed_duplicate_power_tracks":len(removed),"fiducial_locations":[[footprint.GetReference(),pcbnew.ToMM(footprint.GetPosition())] for footprint in fiducials]}))
