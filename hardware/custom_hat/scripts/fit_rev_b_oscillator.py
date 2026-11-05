from pathlib import Path
import json

import pcbnew


project=Path(__file__).resolve().parents[1]/"rev_b"
path=project/"custom_hat_rev_b.kicad_pcb"
board=pcbnew.LoadBoard(str(path))
footprint=board.FindFootprintByReference("Y701")
original=footprint.GetPosition()
foreign_pads=[pad for other in board.GetFootprints() if other.GetReference()!="Y701" for pad in other.Pads() if pad.IsOnLayer(pcbnew.F_Cu)]
tracks=[track for track in board.GetTracks() if track.IsOnLayer(pcbnew.F_Cu)]
for shape in footprint.GraphicalItems():
    if shape.GetLayer()==pcbnew.F_SilkS:
        shape.SetLayer(pcbnew.F_Fab)
candidates=sorted((delta_x*delta_x+delta_y*delta_y,delta_x,delta_y) for delta_x in range(-40,41) for delta_y in range(-40,41))
for _,delta_x,delta_y in candidates:
    footprint.SetPosition(pcbnew.VECTOR2I(original.x+pcbnew.FromMM(delta_x*0.025),original.y+pcbnew.FromMM(delta_y*0.025)))
    valid=True
    for pad in footprint.Pads():
        shape=pad.GetEffectiveShape(pcbnew.F_Cu)
        for other in foreign_pads+tracks:
            if other.GetNetname()==pad.GetNetname():
                continue
            clearance=0.205 if "POWER_GND" in {other.GetNetname(),pad.GetNetname()} or other.GetNetname() in {"+5V","+5V_PRE_IDEAL","VBATT_2S_IN"} else 0.155
            if shape.Collide(other.GetEffectiveShape(pcbnew.F_Cu),pcbnew.FromMM(clearance)):
                valid=False
                break
        if not valid:
            break
        if pad.GetNetname()!="POWER_GND" and not any(other.GetNetname()==pad.GetNetname() and shape.Collide(other.GetEffectiveShape(pcbnew.F_Cu),0) for other in tracks):
            valid=False
            break
    if valid:
        break
else:
    raise RuntimeError("No connected oscillator placement within 1mm")
pcbnew.FootprintSave(str(project/"duck.pretty"),footprint)
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
pcbnew.SaveBoard(str(path),board)
print(json.dumps({"oscillator_position":pcbnew.ToMM(footprint.GetPosition()),"native_DRC_required":True}))
