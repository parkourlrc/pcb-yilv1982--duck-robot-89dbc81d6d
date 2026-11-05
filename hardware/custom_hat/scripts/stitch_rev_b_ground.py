import argparse
import json
import math
from pathlib import Path
import shutil

import pcbnew


parser=argparse.ArgumentParser()
parser.add_argument("directory",type=Path)
parser.add_argument("--targets",nargs="+")
parser.add_argument("--output-stem",default="ground-stitching")
arguments=parser.parse_args()
directory=arguments.directory.resolve()
path=directory/"custom_hat_rev_b.kicad_pcb"
backup=directory/"before-ground-stitching.kicad_pcb"
if not backup.exists():
    shutil.copy2(path,backup)
board=pcbnew.LoadBoard(str(path))
ground=board.FindNet("POWER_GND")
planes={layer:next(zone.GetFilledPolysList(layer) for zone in board.Zones() if zone.GetNetname()=="POWER_GND" and zone.IsOnLayer(layer)) for layer in (pcbnew.F_Cu,pcbnew.B_Cu)}
all_pads=[pad for footprint in board.GetFootprints() for pad in footprint.Pads() if pad.IsOnLayer(pcbnew.F_Cu) or pad.IsOnLayer(pcbnew.B_Cu) or pad.GetDrillSize().x]
foreign=[pad.GetEffectiveShape(pcbnew.F_Cu) for pad in all_pads]
foreign.extend(track.GetEffectiveShape(pcbnew.F_Cu) for track in board.GetTracks() if track.GetNetname()!="POWER_GND")
targets=[]
for reference in (arguments.targets or ("U301","C301","C303","C304","U302","U701","C704","C705","C707","C709","C711","U702","U803","C735","C737","MK701","J502","J401","J402")):
    footprint=board.FindFootprintByReference(reference)
    for pad in footprint.Pads():
        if pad.GetNetname()=="POWER_GND" and pad.GetNumber():
            targets.append((reference+"."+pad.GetNumber(),pad.GetPosition(),2 if reference in {"U301","C301","C303","C304"} else 1))
if not arguments.targets:
    for track in board.GetTracks():
        if track.Type()==pcbnew.PCB_VIA_T and track.GetNetname() in {"AUDIO_MCLK","I2S_BCLK","I2S_LRCK","I2S_SDO","I2S_SDI"}:
            targets.append((track.GetNetname(),track.GetPosition(),1))
added=[]
for reference,anchor,count in targets:
    candidates=sorted((delta_x*delta_x+delta_y*delta_y,delta_x,delta_y) for delta_x in range(-12,13) for delta_y in range(-12,13))
    for _,delta_x,delta_y in candidates:
        point=pcbnew.VECTOR2I(anchor.x+pcbnew.FromMM(delta_x*0.25),anchor.y+pcbnew.FromMM(delta_y*0.25))
        if not(100.8<pcbnew.ToMM(point.x)<164.2 and 100.8<pcbnew.ToMM(point.y)<129.2):
            continue
        if any(not plane.Contains(point) for plane in planes.values()):
            continue
        if any(math.hypot(point.x-existing[0],point.y-existing[1])<pcbnew.FromMM(0.9) for existing in [tuple(track.GetPosition()) for track in board.GetTracks() if track.Type()==pcbnew.PCB_VIA_T]):
            continue
        via=pcbnew.PCB_VIA(board)
        via.SetPosition(point)
        via.SetWidth(pcbnew.FromMM(0.6))
        via.SetDrill(pcbnew.FromMM(0.3))
        via.SetViaType(pcbnew.VIATYPE_THROUGH)
        via.SetLayerPair(pcbnew.F_Cu,pcbnew.B_Cu)
        via.SetNet(ground)
        if any(via.GetEffectiveShape(pcbnew.F_Cu).Collide(shape,pcbnew.FromMM(0.22)) for shape in foreign):
            continue
        board.Add(via)
        added.append({"near":reference,"position":pcbnew.ToMM(point),"diameter":0.6,"drill":0.3})
        count-=1
        if count==0:
            break
for track in board.GetTracks():
    if track.Type()==pcbnew.PCB_VIA_T:
        track.SetFrontTentingMode(pcbnew.TENTING_MODE_TENTED)
        track.SetBackTentingMode(pcbnew.TENTING_MODE_TENTED)
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
pcbnew.SaveBoard(str(path),board)
(directory/(arguments.output_stem+".json")).write_text(json.dumps(added,indent=2),encoding="utf-8")
print(json.dumps({"added_ground_vias":len(added),"native_check_required":True}))
