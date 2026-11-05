import hashlib
import json
from pathlib import Path
import shutil

import pcbnew


base=Path(__file__).resolve().parents[1]
project=base/"rev_b"
evidence=base.parents[1]/"docs/references/扩展板乙版降本"
path=project/"custom_hat_rev_b.kicad_pcb"
board=pcbnew.LoadBoard(str(path))
footprint=board.FindFootprintByReference("D301")
pads={pad.GetNumber():pad for pad in footprint.Pads()}
if pads["1"].GetNetname()!="POWER_GND" or footprint.GetOrientationDegrees()!=0:
    raise RuntimeError("Expected the recorded TVS polarity candidate")
original={pad.GetNetname():tuple(pad.GetPosition()) for pad in pads.values()}
shutil.copy2(path,evidence/"before-tvs-polarity-fix.kicad_pcb")
footprint.SetOrientationDegrees(180)
pads["1"].SetNet(board.FindNet("VBATT_2S_IN"))
pads["2"].SetNet(board.FindNet("POWER_GND"))
footprint.SetField("Datasheet","https://www.vishay.com/docs/88392/smbj.pdf")
footprint.GetField("Datasheet").SetVisible(False)
corrected={pad.GetNetname():tuple(pad.GetPosition()) for pad in pads.values()}
if corrected!=original:
    raise RuntimeError("Net copper locations unexpectedly changed")
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
pcbnew.SaveBoard(str(path),board)
result={"date":"2026-11-04","before":{"1":"POWER_GND","2":"VBATT_2S_IN","angle":0,"symbol":"Device:D_TVS"},"after":{"1":"VBATT_2S_IN cathode","2":"POWER_GND anode","angle":180,"symbol":"Device:D_Zener"},"copper_net_locations_preserved":True,"pcb_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"native_check_required":True}
(evidence/"tvs-polarity-fix.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
print(json.dumps(result))
