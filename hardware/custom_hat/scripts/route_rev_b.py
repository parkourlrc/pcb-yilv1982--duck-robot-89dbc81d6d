import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pcbnew


base=Path(__file__).resolve().parents[1]
project=base/"rev_b"
stem="custom_hat_rev_b"
evidence=base.parents[1]/"docs/references/扩展板乙版降本"
parser=argparse.ArgumentParser()
parser.add_argument("--passes",type=int,default=12)
parser.add_argument("--input",type=Path)
parser.add_argument("--no-fanout", action="store_true")
arguments=parser.parse_args()
run=evidence/("route-"+datetime.now().strftime("%H%M%S"))
run.mkdir()
board_path=arguments.input or project/(stem+".kicad_pcb")
source_hash=hashlib.sha256(board_path.read_bytes()).hexdigest()
shutil.copy2(board_path,run/"before.kicad_pcb")
for source_file in project.iterdir():
    if source_file.is_file() and (source_file.suffix in {".kicad_sch", ".kicad_pro", ".kicad_dru", ".kicad_sym"} or source_file.name in {"fp-lib-table", "sym-lib-table"}):
        shutil.copy2(source_file,run/source_file.name)
shutil.copytree(project/"duck.pretty",run/"duck.pretty")
board=pcbnew.LoadBoard(str(board_path))
dsn=run/(stem+".dsn")
ses=run/(stem+".ses")
if not pcbnew.ExportSpecctraDSN(board,str(dsn)):
    raise RuntimeError("DSN export failed")
tool_root=Path.home()/"AppData/Local/duck-robot-tools"
command=[str(tool_root/"jre25/jdk-25.0.5+8-jre/bin/java.exe"),"-jar",str(tool_root/"freerouting/freerouting-2.5.0.jar"),"-de",str(dsn),"-do",str(ses),"--router.autorouter.max_passes="+str(arguments.passes),"--router.neck_width_um=150","--router.strict_drc=true"]
if arguments.no_fanout:
    command.extend(["--router.fanout.enabled=false","--router.optimizer.enabled=false","--router.copper_to_edge_clearance_um=325"])
record={"source_sha256":source_hash,"command":command,"status":"running","production_ready":False}
(run/"result.json").write_text(json.dumps(record,indent=2),encoding="utf-8")
with (run/"router.log").open("w",encoding="utf-8") as output:
    result=subprocess.run(command,stdout=output,stderr=subprocess.STDOUT,timeout=1200)
record["returncode"]=result.returncode
if result.returncode or not ses.exists():
    record["status"]="router_failed"
    (run/"result.json").write_text(json.dumps(record,indent=2),encoding="utf-8")
    raise RuntimeError("Router did not produce a valid session")
if hashlib.sha256(board_path.read_bytes()).hexdigest()!=source_hash:
    raise RuntimeError("Input board changed during routing")
if not pcbnew.ImportSpecctraSES(board,str(ses)):
    raise RuntimeError("SES import failed")
candidate=run/(stem+".kicad_pcb")
pcbnew.SaveBoard(str(candidate),board)
record.update(status="routed_candidate_needs_check",candidate=str(candidate),tracks=len(board.GetTracks()))
(run/"result.json").write_text(json.dumps(record,indent=2),encoding="utf-8")
print(json.dumps(record,ensure_ascii=False,indent=2))
