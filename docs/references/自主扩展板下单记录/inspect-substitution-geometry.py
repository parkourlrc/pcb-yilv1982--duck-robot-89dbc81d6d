import hashlib
import json
from pathlib import Path

import pcbnew


root = Path(__file__).resolve().parents[3]
pcb_path = root / "hardware/custom_hat/rev_a/custom_hat_rev_a.kicad_pcb"
board = pcbnew.LoadBoard(str(pcb_path))
references = {"C301", "R304", "C303", "C305", "C317", "C318", "L301", "R703", "U702", "U803", "U301"}
parts = []
for footprint in board.GetFootprints():
    if footprint.GetReference() not in references:
        continue
    pads = []
    for pad in footprint.Pads():
        position = pad.GetPosition()
        size = pad.GetSize()
        pads.append({
            "number": pad.GetNumber(),
            "net": pad.GetNetname(),
            "position_mm": [pcbnew.ToMM(position.x), pcbnew.ToMM(position.y)],
            "size_mm": [pcbnew.ToMM(size.x), pcbnew.ToMM(size.y)],
            "orientation_degrees": pad.GetOrientationDegrees(),
        })
    parts.append({
        "reference": footprint.GetReference(),
        "footprint": str(footprint.GetFPID().GetLibItemName()),
        "side": board.GetLayerName(footprint.GetLayer()),
        "orientation_degrees": footprint.GetOrientationDegrees(),
        "pads": pads,
    })
result = {"pcb_sha256": hashlib.sha256(pcb_path.read_bytes()).hexdigest(), "board_modified": False, "parts": parts}
target = Path(__file__).with_name("substitution-native-geometry.json")
target.write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps({"pcb_sha256": result["pcb_sha256"], "parts": len(parts), "output": target.name}))
