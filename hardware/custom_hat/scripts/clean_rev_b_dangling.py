import argparse
import json
from pathlib import Path
import shutil

import pcbnew

from fit_ldo_candidate import remove_objects


parser=argparse.ArgumentParser()
parser.add_argument("directory",type=Path)
arguments=parser.parse_args()
directory=arguments.directory.resolve()
path=directory/"custom_hat_rev_b.kicad_pcb"
report=json.loads((directory/"drc-complete-project.json").read_text(encoding="utf-8"))
identifiers={item["uuid"] for violation in report["violations"] if violation["type"] in {"via_dangling","track_dangling"} for item in violation["items"]}
shutil.copy2(path,directory/"before-dangling-cleanup.kicad_pcb")
remove_objects(path,identifiers)
board=pcbnew.LoadBoard(str(path))
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
pcbnew.SaveBoard(str(path),board)
(directory/"dangling-cleanup.json").write_text(json.dumps({"removed":sorted(identifiers),"needs_DRC":True},indent=2),encoding="utf-8")
print(json.dumps({"removed_items":len(identifiers)}))
