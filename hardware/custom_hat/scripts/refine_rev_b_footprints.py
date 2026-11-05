from pathlib import Path
import json
import shutil

import pcbnew


base=Path(__file__).resolve().parents[1]
project=base/"rev_b"
evidence=base.parents[1]/"docs/references/扩展板乙版降本"
path=project/"custom_hat_rev_b.kicad_pcb"
shutil.copy2(path,evidence/"before-footprint-refinement.kicad_pcb")
board=pcbnew.LoadBoard(str(path))
oscillator=board.FindFootprintByReference("Y701")
anchor=oscillator.GetPosition()
if oscillator.GetOrientationDegrees()!=0:
    raise RuntimeError("Unexpected oscillator orientation")
positions={"1":(-0.925,0.725),"2":(0.925,0.725),"3":(0.925,-0.725),"4":(-0.925,-0.725)}
for pad in oscillator.Pads():
    delta_x,delta_y=positions[pad.GetNumber()]
    pad.SetPosition(pcbnew.VECTOR2I(anchor.x+pcbnew.FromMM(delta_x),anchor.y+pcbnew.FromMM(delta_y)))
    pad.SetSize(pcbnew.VECTOR2I(pcbnew.FromMM(0.9),pcbnew.FromMM(0.8)))
oscillator.SetFPID(pcbnew.LIB_ID("duck","YXC_2520_YSO110TR_B"))
oscillator.SetField("Manufacturer","YXC")
oscillator.GetField("Manufacturer").SetVisible(False)
oscillator.SetField("Datasheet","https://atta.szlcsc.com/upload/public/pdf/source/20260116/277ADDA9FE6BD42D3AF503786E6466E2.pdf")
oscillator.GetField("Datasheet").SetVisible(False)
pcbnew.FootprintSave(str(project/"duck.pretty"),oscillator)
for reference in ("J505","J506","J507"):
    footprint=board.FindFootprintByReference(reference)
    for pad in footprint.Pads():
        pad.SetDrillSize(pcbnew.VECTOR2I(pcbnew.FromMM(0.5),pcbnew.FromMM(0.5)))
    pcbnew.FootprintSave(str(project/"duck.pretty"),footprint)
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
pcbnew.SaveBoard(str(path),board)
(evidence/"footprint-refinement.json").write_text(json.dumps({"Y701":"YXC YSO110TR 2520 recommended land 0.9x0.8mm; centers1.85x1.45mm; 1OE2GND3OUT4VDD", "J505_J506_J507":"CJT A1251WV-2P 0.5mm recommended finished hole; 0.3mm square pins; body/courtyard still needs assembly orientation review","native_check_required":True},indent=2),encoding="utf-8")
