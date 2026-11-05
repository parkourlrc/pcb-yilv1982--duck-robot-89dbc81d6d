"""Prepare single-unit order files for five HATs without changing the reviewed PCB."""
from collections import Counter
import csv
import json
from pathlib import Path
import shutil
import subprocess
import zipfile

import pcbnew
import pipeline
from export_dnp_stencil import LAYERS, paste_flashes
from export_jlc_rs274x import drawing_commands, GERBER_SUFFIXES
from audit_stencil_apertures import aperture_geometry

ROOT = pipeline.BASE.parents[1]
EVIDENCE = ROOT / "docs/references/自主扩展板下单记录"
OUTPUT = pipeline.BASE / "order-submission/20261103-five-hats"


def rows(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def main():
    checkpoint = pipeline.current_checkpoint()
    source = ROOT / checkpoint["review_binding"]["production_package"]
    review = ROOT / "docs/references/扩展板邮票孔与电源修复"
    panel_bundle = json.loads((review / "pcba-review-bundle.json").read_text(encoding="utf-8"))
    panel = (ROOT / panel_bundle["archive"]).with_suffix("")
    output = OUTPUT
    output.mkdir(parents=True, exist_ok=False)
    fabrication = output / "fabrication"
    fabrication.mkdir()
    work = pipeline.prepare(pipeline.PRIMARY)
    path = work / (pipeline.STEM + ".kicad_pcb")
    board = pcbnew.LoadBoard(str(path))
    bmi = []
    dnp = []
    for footprint in board.GetFootprints():
        for pad in footprint.Pads():
            if footprint.GetReference() == "U501" and pad.GetNumber() and pad.IsOnLayer(pcbnew.F_Paste):
                pad.SetLocalSolderPasteMarginRatio(-.05)
                bmi.append((pad.GetPosition().x, -pad.GetPosition().y))
            if footprint.GetReference() == "C307":
                layers = pad.GetLayerSet()
                if layers.Contains(pcbnew.F_Paste):
                    layers.RemoveLayer(pcbnew.F_Paste)
                    pad.SetLayerSet(layers)
                    dnp.append(pad.GetNumber())
    if len(bmi) != 16 or len(dnp) != 2:
        raise RuntimeError("Unexpected paste-pad inventory")
    pcbnew.SaveBoard(str(path), board)
    command = [pipeline.find_cli(), "pcb", "export", "gerbers", "--no-x2", "--no-netlist", "--layers", LAYERS, "--output", str(fabrication), str(path)]
    completed = subprocess.run(command, capture_output=True, encoding="utf-8", errors="replace", timeout=180)
    (EVIDENCE / "unit-gerber-export.log").write_text(completed.stdout+completed.stderr, encoding="utf-8")
    completed.check_returncode()
    comparisons = []
    for original in source.iterdir():
        if original.suffix not in GERBER_SUFFIXES or original.suffix in {".gtp", ".gbp"}:
            continue
        candidate = fabrication / original.name
        equal = drawing_commands(original) == drawing_commands(candidate)
        comparisons.append({"file": original.name, "drawing_commands_equal": equal})
        if not equal:
            raise RuntimeError("Unit copper/mask/silk/outline changed: " + original.name)
    if len(comparisons) != 9:
        raise RuntimeError("Missing non-paste comparison")
    for side, suffix in [("F", "gtp"), ("B", "gbp")]:
        actual, _ = paste_flashes(fabrication / (pipeline.STEM+"-"+side+"_Paste."+suffix))
        doubled, _ = paste_flashes(panel / ("hat_a1_smt_2up-"+side+"_Paste."+suffix))
        expected = Counter({key: count for key, count in doubled.items() if -130000000 <= key[2] <= -100000000})
        normalize = lambda values: Counter({(key[1], key[2], key[3]): count for key, count in values.items()})
        if normalize(actual) != normalize(expected):
            raise RuntimeError("Single-unit paste differs from reviewed r18 first unit")
    for suffix in ["PTH.drl", "NPTH.drl"]:
        shutil.copy2(source / (pipeline.STEM+"-"+suffix), fabrication / (pipeline.STEM+"-"+suffix))
    for name in ["via-process-requirements.csv", "bom-smt.csv", "bom-fitted.csv", "positions-smt.csv", "positions.csv", "assembly-plan.csv", "assembly-front.svg", "assembly-back.svg"]:
        shutil.copy2(source / name, output / name)
    with (output / "jlc-bom-smt.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["Comment","Designator","Footprint","MPN","Manufacturer","Quantity"])
        writer.writeheader()
        for row in rows(source / "bom-smt.csv"):
            writer.writerow({"Comment":row["Value"],"Designator":row["Reference"],"Footprint":row["Footprint"],"MPN":row["MPN"],"Manufacturer":row["Manufacturer"],"Quantity":row["Qty"]})
    with (output / "jlc-cpl-smt.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["Designator","Mid X","Mid Y","Layer","Rotation"])
        writer.writeheader()
        for row in rows(source / "positions-smt.csv"):
            writer.writerow({"Designator":row["Ref"],"Mid X":row["PosX"],"Mid Y":row["PosY"],"Layer":"Top" if row["Side"]=="top" else "Bottom","Rotation":row["Rot"]})
    shutil.copy2(EVIDENCE / "ORDER-NOTES.txt", output / "ORDER-NOTES.txt")
    plot_files = [path for path in fabrication.iterdir() if path.suffix in GERBER_SUFFIXES | {".drl"}]
    if len(plot_files) != 13:
        raise RuntimeError("Unexpected manufacturing file count")
    archive = output / "HAT-A1-86654c03-single-unit-PCB.zip"
    with zipfile.ZipFile(archive,"x",compression=zipfile.ZIP_DEFLATED) as bundle:
        for path in sorted(plot_files):
            bundle.write(path,path.name)
        bundle.write(output/"ORDER-NOTES.txt","ORDER-NOTES.txt")
        bundle.write(output/"via-process-requirements.csv","via-process-requirements.csv")
    for job in fabrication.glob("*.gbrjob"):
        job.rename(work.parent / "unit-job-not-for-order.gbrjob")
    manifest={"source_pcb_sha256":checkpoint["pcb_sha256"],"source_internal_package":str(source.relative_to(ROOT)),
              "outputs":{path.name:pipeline.digest(path) for path in fabrication.iterdir() if path.is_file()}}
    pipeline.write_json(fabrication/"manifest.json",manifest)
    report={"date":"2026-11-03","pcb_sha256":checkpoint["pcb_sha256"],"requested_finished_units":5,
            "units_per_uploaded_design":1,"single_unit_outline_mm":[65,30],"nonpaste_geometry_matches_review":comparisons,
            "paste_matches_reviewed_r18_first_unit":True,"bmi_apertures":16,"paste_flashes":201,"smt_components_per_unit":52,
            "tht_components_per_unit":6,"source_unchanged":pipeline.fingerprints(pipeline.PRIMARY)==checkpoint["design_hashes"],
            "factory_panelization_required":True,"factory_panelization_accepted":False,"order_created":False,"paid":False,
            "archive":str(archive.relative_to(ROOT)),"archive_sha256":pipeline.digest(archive),
            "files":{str(path.relative_to(output)):pipeline.digest(path) for path in output.rglob("*") if path.is_file()},
            "limits":["Factory must return actual production/panel artwork; old r18 is a reference, not the submitted panel",
                      "Single-unit BOM/CPL quantities are per finished HAT, total intended SMT count260 for five units",
                      "THT hand soldering scope and price require order clarification; no extra THT fee automatically approved"]}
    if not report["source_unchanged"]:
        raise RuntimeError("Primary changed")
    pipeline.write_json(EVIDENCE/"unit-order-package.json",report)
    print(json.dumps({key:value for key,value in report.items() if key not in {"files","nonpaste_geometry_matches_review"}},ensure_ascii=False))


if __name__ == "__main__":
    main()
