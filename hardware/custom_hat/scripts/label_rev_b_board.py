import json
from pathlib import Path

import pcbnew


project=Path(__file__).resolve().parents[1]/"rev_b"
path=project/"custom_hat_rev_b.kicad_pcb"
board=pcbnew.LoadBoard(str(path))
labels=[("MIC-L",140,128.4,0,pcbnew.F_SilkS),("MIC-R",147,128.4,0,pcbnew.F_SilkS),("SPK",154,128.4,0,pcbnew.F_SilkS),("I2C",117.5,125.6,0,pcbnew.F_SilkS),("DXL1",107.8,111.5,90,pcbnew.F_SilkS),("DXL2",114.8,111.5,90,pcbnew.F_SilkS),("B0",109.5,128.2,0,pcbnew.F_SilkS),("HAT-B0",132,124.5,0,pcbnew.B_SilkS),("1",107,104.59,0,pcbnew.B_SilkS),("BAT+",105,116.4,0,pcbnew.F_SilkS)]
created=[]
existing={drawing.GetText() for drawing in board.GetDrawings() if drawing.Type()==pcbnew.PCB_TEXT_T}
for label,xpos,ypos,angle,layer in labels:
    if label in existing:
        drawing=next(item for item in board.GetDrawings() if item.Type()==pcbnew.PCB_TEXT_T and item.GetText()==label)
        drawing.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(xpos),pcbnew.FromMM(ypos)))
        continue
    text=pcbnew.PCB_TEXT(board)
    text.SetText(label)
    text.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(xpos),pcbnew.FromMM(ypos)))
    text.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(1),pcbnew.FromMM(1)))
    text.SetTextThickness(pcbnew.FromMM(0.15))
    text.SetTextAngle(pcbnew.EDA_ANGLE(angle,pcbnew.DEGREES_T))
    text.SetLayer(layer)
    text.SetMirrored(layer==pcbnew.B_SilkS)
    board.Add(text)
    created.append(label)
title=board.GetTitleBlock()
title.SetTitle("Custom HAT Rev B.0")
title.SetRevision("B.0 CANDIDATE")
title.SetDate("2026-11-04")
pcbnew.SaveBoard(str(path),board)
print(json.dumps({"labels":created,"native_DRC_required":True}))
