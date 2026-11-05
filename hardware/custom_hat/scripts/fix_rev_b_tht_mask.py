import json
from pathlib import Path
import shutil

import pcbnew


project=Path(__file__).resolve().parents[1]/"rev_b"
evidence=project.parents[2]/"docs/references/扩展板乙版降本"
path=project/"custom_hat_rev_b.kicad_pcb"
shutil.copy2(path,evidence/"before-tht-mask-fix.kicad_pcb")
board=pcbnew.LoadBoard(str(path))
changed=[]
for footprint in board.GetFootprints():
    fixed=[]
    for pad in footprint.Pads():
        if pad.GetAttribute()==pcbnew.PAD_ATTRIB_PTH and (not pad.IsOnLayer(pcbnew.F_Mask) or not pad.IsOnLayer(pcbnew.B_Mask)):
            pad.SetLayerSet(pcbnew.PAD.PTHMask())
            fixed.append(pad.GetNumber())
    if fixed:
        if not footprint.GetFPIDAsString().startswith("duck:"):
            raise RuntimeError("Unexpected non-project THT footprint")
        pcbnew.FootprintSave(str(project/"duck.pretty"),footprint)
        changed.append({"ref":footprint.GetReference(),"pads":fixed})
pcbnew.SaveBoard(str(path),board)
reloaded=pcbnew.LoadBoard(str(path))
remaining=[footprint.GetReference()+"."+pad.GetNumber() for footprint in reloaded.GetFootprints() for pad in footprint.Pads() if pad.GetAttribute()==pcbnew.PAD_ATTRIB_PTH and (not pad.IsOnLayer(pcbnew.F_Mask) or not pad.IsOnLayer(pcbnew.B_Mask))]
if remaining:
    raise RuntimeError("Saved PTH mask missing: "+str(remaining))
(evidence/"tht-mask-fix.json").write_text(json.dumps({"changed":changed,"saved_PTH_mask_check_passed":True,"native_DRC_required":True,"retired_quote_package":"quote-8af23ba8"},indent=2),encoding="utf-8")
print(json.dumps({"footprints":len(changed),"pads":sum(len(row["pads"]) for row in changed),"remaining":remaining}))
