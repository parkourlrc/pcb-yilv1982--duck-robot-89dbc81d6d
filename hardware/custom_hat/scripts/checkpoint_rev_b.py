import argparse
from collections import Counter
import csv
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pcbnew


parser=argparse.ArgumentParser()
parser.add_argument("candidate",type=Path)
parser.add_argument("--current",action="store_true")
arguments=parser.parse_args()
base=Path(__file__).resolve().parents[1]
project=base/"rev_b"
evidence=base.parents[1]/"docs/references/扩展板乙版降本"
candidate=arguments.candidate.resolve()
stem="custom_hat_rev_b"
cli=Path(sys.executable).parent/"kicad-cli.exe"
report=json.loads(((project/"review-output/drc.json") if arguments.current else (candidate/"drc-complete-project.json")).read_text(encoding="utf-8"))
if any(report[key] for key in ("violations","unconnected_items","schematic_parity")):
    raise RuntimeError("Candidate is not native-clean")
original=base/"rev_a/custom_hat_rev_a.kicad_pcb"
if hashlib.sha256(original.read_bytes()).hexdigest()!="86654c03b6c1c8f51f7d5a4bef469aceed2ddfc73433b3e50426940c2a23164a":
    raise RuntimeError("A.1 baseline changed")
if not arguments.current:
    shutil.copy2(project/(stem+".kicad_pcb"),evidence/"before-checkpoint-source.kicad_pcb")
    shutil.copy2(candidate/(stem+".kicad_pcb"),project/(stem+".kicad_pcb"))
board=pcbnew.LoadBoard(str(project/(stem+".kicad_pcb")))
missing_masks=[footprint.GetReference()+"."+pad.GetNumber() for footprint in board.GetFootprints() for pad in footprint.Pads() if pad.GetAttribute()==pcbnew.PAD_ATTRIB_PTH and (not pad.IsOnLayer(pcbnew.F_Mask) or not pad.IsOnLayer(pcbnew.B_Mask))]
if missing_masks:
    raise RuntimeError("THT solder mask opening missing: "+str(missing_masks))
parts=json.loads((project/"design-components.json").read_text(encoding="utf-8"))
parts_by_ref={part["ref"]:part for part in parts}
for footprint in board.GetFootprints():
    reference=footprint.GetReference()
    if reference in parts_by_ref:
        parts_by_ref[reference]["position"]=[*pcbnew.ToMM(footprint.GetPosition()),footprint.GetOrientationDegrees()]
output=project/"review-output"
output.mkdir(exist_ok=True)
(output/"gerbers").mkdir(exist_ok=True)
fitted=[part for part in parts if part["code"]]
groups={}
for part in fitted:
    key=(part["mpn"],part["code"],part["footprint"],part["manufacturer"])
    groups.setdefault(key,[]).append(part)
with (output/"bom-grouped.csv").open("w",encoding="utf-8-sig",newline="") as stream:
    writer=csv.writer(stream)
    writer.writerow(["Designator","Quantity","MPN","LCSC Part #","Footprint","Manufacturer","Function"])
    for key,rows in groups.items():
        writer.writerow([",".join(row["ref"] for row in rows),len(rows),*key,"; ".join(sorted(set(row["sheet"] for row in rows)))])
with (output/"cpl-all-fitted.csv").open("w",encoding="utf-8-sig",newline="") as stream:
    writer=csv.writer(stream)
    writer.writerow(["Designator","Mid X","Mid Y","Layer","Rotation","Assembly"])
    for part in fitted:
        footprint=board.FindFootprintByReference(part["ref"])
        writer.writerow([part["ref"],f"{pcbnew.ToMM(footprint.GetPosition().x):.6f}mm",f"{-pcbnew.ToMM(footprint.GetPosition().y):.6f}mm","Bottom" if footprint.GetLayer()==pcbnew.B_Cu else "Top",footprint.GetOrientationDegrees(),"THT" if footprint.GetAttributes()&pcbnew.FP_THROUGH_HOLE else "SMT"])
commands=[]
for name,command in (
    ("erc",["sch","erc","--format","json","--exit-code-violations","-o",str(output/"erc.json"),str(project/(stem+".kicad_sch"))]),
    ("drc",["pcb","drc","--format","json","--schematic-parity","--exit-code-violations","-o",str(output/"drc.json"),str(project/(stem+".kicad_pcb"))]),
    ("schematic_pdf",["sch","export","pdf","-o",str(output/"schematic.pdf"),str(project/(stem+".kicad_sch"))]),
    ("gerbers",["pcb","export","gerbers","--no-x2","--no-netlist","--disable-aperture-macros","--layers","F.Cu,B.Cu,F.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts","-o",str(output/"gerbers")+"/",str(project/(stem+".kicad_pcb"))]),
    ("drill",["pcb","export","drill","--format","excellon","--drill-origin","absolute","--excellon-units","mm","--excellon-separate-th","-o",str(output/"gerbers")+"/",str(project/(stem+".kicad_pcb"))]),
):
    result=subprocess.run([str(cli),*command],capture_output=True,text=True,encoding="utf-8",errors="replace")
    commands.append({"name":name,"command":command,"returncode":result.returncode,"stdout":result.stdout,"stderr":result.stderr})
    (output/"commands.json").write_text(json.dumps(commands,ensure_ascii=False,indent=2),encoding="utf-8")
    result.check_returncode()
old_board=pcbnew.LoadBoard(str(original))
def header_coordinates(item):
    return {pad.GetNumber():tuple(pad.GetPosition()) for pad in item.FindFootprintByReference("J101").Pads()}
vias=[track for track in board.GetTracks() if track.Type()==pcbnew.PCB_VIA_T]
vip=[]
for footprint in board.GetFootprints():
    for pad in footprint.Pads():
        if pad.GetAttribute()==pcbnew.PAD_ATTRIB_SMD and pad.IsOnLayer(pcbnew.F_Cu):
            vip.extend({"ref":footprint.GetReference(),"pad":pad.GetNumber(),"via":via.m_Uuid.AsString()} for via in vias if via.GetEffectiveHoleShape().Collide(pad.GetEffectiveShape(pcbnew.F_Cu),pcbnew.FromMM(0.05)))
record={"date":datetime.now().astimezone().isoformat(),"status":"native_clean_development_checkpoint_not_for_order","production_ready":False,"cost_target_met":False,"pcb_sha256":hashlib.sha256((project/(stem+".kicad_pcb")).read_bytes()).hexdigest(),"fitted_count":len(fitted),"bom_groups":len(groups),"copper_layers":board.GetCopperLayerCount(),"smt_sides":dict(Counter(part["side"] for part in fitted if not board.FindFootprintByReference(part["ref"]).GetAttributes()&pcbnew.FP_THROUGH_HOLE)),"header_coordinates_match_A1":header_coordinates(board)==header_coordinates(old_board),"via_drills_mm":sorted(set(pcbnew.ToMM(via.GetDrill()) for via in vias)),"via_in_exposed_smd_pad":vip,"files":{path.name:hashlib.sha256(path.read_bytes()).hexdigest() for path in project.iterdir() if path.suffix in {".kicad_sch",".kicad_pcb",".kicad_pro",".kicad_dru",".kicad_sym"}},"remaining":["Exact BOM/footprint/datasheet qualification","Thermal/effective-capacitance and power-path acceptance","Factory admission and complete 5-board quotation","Final fabrication export and review"]}
(output/"manifest.json").write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding="utf-8")
(project/"checkpoint.json").write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps({key:value for key,value in record.items() if key!="files"},ensure_ascii=False))
