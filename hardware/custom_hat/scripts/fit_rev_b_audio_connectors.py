import json
from pathlib import Path
import shutil

import pcbnew


base=Path(__file__).resolve().parents[1]
project=base/"rev_b"
path=project/"custom_hat_rev_b.kicad_pcb"
evidence=base.parents[1]/"docs/references/扩展板乙版降本"
shutil.copy2(path,evidence/"before-audio-connector-fit.kicad_pcb")
board=pcbnew.LoadBoard(str(path))
changes=[]
for reference in ("J505","J506","J507"):
    footprint=board.FindFootprintByReference(reference)
    center=footprint.GetPosition()
    if footprint.GetOrientationDegrees()!=0:
        raise RuntimeError("Expected zero-degree connector")
    drawings=[item for item in footprint.GraphicalItems() if item.Type()==pcbnew.PCB_SHAPE_T and item.GetLayer() in {pcbnew.F_Fab,pcbnew.F_CrtYd}]
    for layer,bounds in ((pcbnew.F_Fab,(-2.15,-0.35,2.15,2.85)),(pcbnew.F_CrtYd,(-2.4,-0.6,2.4,3.1))):
        shapes=[item for item in drawings if item.GetLayer()==layer]
        if len(shapes)!=4:
            raise RuntimeError("Unexpected connector body representation")
        left,top,right,bottom=bounds
        for shape,(start,end) in zip(shapes,(((left,top),(right,top)),((right,top),(right,bottom)),((right,bottom),(left,bottom)),((left,bottom),(left,top)))):
            shape.SetStart(pcbnew.VECTOR2I(center.x+pcbnew.FromMM(start[0]),center.y+pcbnew.FromMM(start[1])))
            shape.SetEnd(pcbnew.VECTOR2I(center.x+pcbnew.FromMM(end[0]),center.y+pcbnew.FromMM(end[1])))
    old_pads={pad.GetNumber():pad.GetPosition() for pad in footprint.Pads()}
    footprint.SetPosition(pcbnew.VECTOR2I(center.x,pcbnew.FromMM(126.5)))
    for pad in footprint.Pads():
        old=old_pads[pad.GetNumber()]
        for track in board.GetTracks():
            if track.Type()!=pcbnew.PCB_VIA_T and track.GetNetname()==pad.GetNetname():
                if track.GetStart()==old:
                    track.SetStart(pad.GetPosition())
                if track.GetEnd()==old:
                    track.SetEnd(pad.GetPosition())
    footprint.SetField("Datasheet","https://atta.szlcsc.com/upload/public/pdf/source/20180913/C273009_2E94D2EE16A658F8B593BE6904D224FC.pdf")
    footprint.GetField("Datasheet").SetVisible(False)
    pcbnew.FootprintSave(str(project/"duck.pretty"),footprint)
    changes.append({"ref":reference,"center":pcbnew.ToMM(footprint.GetPosition()),"body_mm":[4.3,3.2],"height_mm":4.7,"finished_hole_mm":0.5,"orientation":"Pin1 left; mating/front lip toward +Y; per CJT top-view rotated180"})
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
pcbnew.SaveBoard(str(path),board)
(evidence/"audio-connectors-fit.json").write_text(json.dumps(changes,indent=2),encoding="utf-8")
print(json.dumps(changes))
