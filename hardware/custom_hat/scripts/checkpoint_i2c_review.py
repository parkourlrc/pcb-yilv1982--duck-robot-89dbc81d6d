"""Export and review one immutable I2C checkpoint with kicad-happy."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pipeline
from generate_rev_a import children, first, parse
from repair_release_metadata import properties
from quarantine_default_gerber_job import quarantine_default_job
from export_assembly_plan import write_assembly_plan
from export_dnp_stencil import export_dnp_stencil


EVIDENCE = pipeline.BASE.parents[1] / "docs/references/扩展板电路仿真工具/i2c-pullups-20261031"
OUTPUT = pipeline.PRIMARY / "production-20261031-i2c-review"
HAPPY = Path.home() / "AppData/Local/Temp/kicad-happy-review-20261030-new/skills"
PREVIOUS = EVIDENCE.parent / "metadata-repair-20261030"
REUSE_LIFECYCLE = False


def execute(name, command):
    result = subprocess.run(list(map(str, command)), capture_output=True, encoding="utf-8", errors="replace", timeout=600)
    (EVIDENCE / (name + ".log")).write_text(result.stdout + result.stderr, encoding="utf-8")
    record = {"name": name, "command": list(map(str, command)), "returncode": result.returncode}
    pipeline.write_json(EVIDENCE / (name + "-command.json"), record)
    print(f"{name}: exit {result.returncode}", flush=True)
    if result.returncode:
        raise RuntimeError(f"{name} failed; inspect its saved log")
    return record


def export_checkpoint():
    cleanup = {}
    for name in ("audio", "imu_tof", "power", "servo_ttl"):
        path = pipeline.PRIMARY / (name + ".kicad_sch")
        text = path.read_text(encoding="utf-8")
        clean = "\n".join(line.rstrip() for line in text.splitlines()) + "\n"
        if parse(text) != parse(clean):
            raise RuntimeError("Whitespace normalization changed schematic syntax")
        cleanup[name] = {"before": pipeline.digest(path), "syntax_equal": True}
        if clean != text:
            path.write_text(clean, encoding="utf-8")
        cleanup[name]["after"] = pipeline.digest(path)
    rule_path = pipeline.PRIMARY / (pipeline.STEM + ".kicad_dru")
    rule_text = rule_path.read_text(encoding="utf-8")
    clean_rules = "\n".join(line.rstrip() for line in rule_text.splitlines()) + "\n"
    if parse("(rules\n" + rule_text + "\n)") != parse("(rules\n" + clean_rules + "\n)"):
        raise RuntimeError("Rule whitespace normalization changed semantics")
    cleanup["custom_rules"] = {"before": pipeline.digest(rule_path), "syntax_equal": True}
    if clean_rules != rule_text:
        rule_path.write_text(clean_rules, encoding="utf-8")
    cleanup["custom_rules"]["after"] = pipeline.digest(rule_path)
    pipeline.write_json(EVIDENCE / "format-normalization.json", cleanup)
    workspace = pipeline.prepare(pipeline.PRIMARY)
    reports, summary = pipeline.check(workspace)
    if summary["status"] != "checks_clean_not_manufacturing_release":
        raise RuntimeError("Post-promotion checks failed")
    export_source_hashes = pipeline.fingerprints(pipeline.PRIMARY)
    if export_source_hashes != summary["source_hashes"]:
        raise RuntimeError("Primary changed after checks and before fabrication export")
    shutil.copy2(reports / "summary.json", EVIDENCE / "post-promotion-summary.json")
    OUTPUT.mkdir(exist_ok=False)
    cli = pipeline.find_cli()
    board = pipeline.PRIMARY / (pipeline.STEM + ".kicad_pcb")
    execute("export-gerbers", [cli, "pcb", "export", "gerbers", "--output", str(OUTPUT) + os.sep, "--layers", "F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts", board])
    stencil_policy = export_dnp_stencil(board, OUTPUT, EVIDENCE)
    job_policy = quarantine_default_job(board, OUTPUT, EVIDENCE)
    execute("export-drill", [cli, "pcb", "export", "drill", "--output", str(OUTPUT) + os.sep, "--format", "excellon", "--drill-origin", "absolute", "--excellon-units", "mm", "--excellon-separate-th", board])
    execute("export-positions", [cli, "pcb", "export", "pos", "--output", OUTPUT / "positions.csv", "--format", "csv", "--units", "mm", "--side", "both", "--exclude-dnp", board])
    groups = {}
    for path in sorted(pipeline.PRIMARY.glob("*.kicad_sch")):
        for symbol in children(parse(path.read_text(encoding="utf-8")), "symbol"):
            fields = properties(symbol)
            reference = fields.get("Reference", "")
            if not fields.get("Footprint") or reference.startswith("TP") or first(symbol, "on_board") == ["on_board", "no"]:
                continue
            dnp = first(symbol, "dnp") == ["dnp", "yes"]
            key = (fields.get("Value"), fields.get("Footprint"), fields.get("MPN", ""), fields.get("Manufacturer", ""), dnp)
            groups.setdefault(key, []).append(reference)
    with (OUTPUT / "bom-tracking.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["Reference", "Qty", "Value", "Footprint", "MPN", "Manufacturer", "DNP"])
        for key, references in sorted(groups.items(), key=lambda item: sorted(item[1])[0]):
            writer.writerow([",".join(sorted(references)), len(references), *key])
    fitted = sum(len(references) for key, references in groups.items() if not key[-1])
    selected = sum(len(references) for key, references in groups.items() if key[2] and not key[-1])
    assembly_policy = write_assembly_plan(pipeline.PRIMARY, OUTPUT)
    pipeline.write_json(EVIDENCE / "assembly-export.json", assembly_policy)
    if pipeline.fingerprints(pipeline.PRIMARY) != export_source_hashes:
        raise RuntimeError("Design changed during fabrication export; package is not a checkpoint")
    pipeline.write_json(EVIDENCE / "checkpoint.json", {"pcb_sha256": pipeline.digest(board), "design_hashes": pipeline.fingerprints(pipeline.PRIMARY),
        "counts": {"fitted": fitted, "mpn_selected": selected, "mpn_missing": fitted - selected, "fitted_groups": sum(not key[-1] for key in groups), "selected_groups": sum(bool(key[2]) and not key[-1] for key in groups)},
        "geometry": summary["netlist_check"], "summary": str(reports / "summary.json"), "production_ready": False})
    pipeline.write_json(OUTPUT / "manifest.json", {"design_hashes": export_source_hashes, "outputs": {path.name: pipeline.digest(path) for path in OUTPUT.iterdir() if path.is_file()}, "job_file_policy": job_policy, "assembly_policy": assembly_policy, "stencil_policy": stencil_policy, "production_ready": False})
    execute("export-assembly-views", [sys.executable, "-X", "utf8", Path(__file__).with_name("render_assembly_views.py"), "--output", OUTPUT, "--evidence", EVIDENCE])
    execute("export-via-process", [sys.executable, "-X", "utf8", Path(__file__).with_name("export_buck_fabrication_requirements.py"), "--output", OUTPUT, "--evidence", EVIDENCE])


def review():
    os.environ["NGSPICE_PATH"] = str(Path.home() / "AppData/Local/duck-robot-tools/ngspice-47/Spice64/bin/ngspice_con.exe")
    os.environ["PYTHONUTF8"] = "1"
    python = [sys.executable, "-X", "utf8"]
    def command(skill, script, *args):
        return [*python, HAPPY / skill / "scripts" / script, *args]
    def batch(jobs):
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(execute, name, args) for name, args in jobs]
            for future in futures:
                future.result()
    schematic, board = EVIDENCE / "schematic.json", EVIDENCE / "pcb.json"
    batch([
        ("happy-schematic", command("kicad", "analyze_schematic.py", pipeline.PRIMARY / (pipeline.STEM + ".kicad_sch"), "--output", schematic)),
        ("happy-pcb", command("kicad", "analyze_pcb.py", pipeline.PRIMARY / (pipeline.STEM + ".kicad_pcb"), "--full", "--output", board)),
        ("happy-gerbers", command("kicad", "analyze_gerbers.py", OUTPUT, "--output", EVIDENCE / "gerbers.json")),
    ])
    batch([
        ("happy-cross", command("kicad", "cross_analysis.py", "--schematic", schematic, "--pcb", board, "--output", EVIDENCE / "cross.json")),
        ("happy-emc", command("emc", "analyze_emc.py", "--schematic", schematic, "--pcb", board, "--output", EVIDENCE / "emc.json")),
        ("happy-thermal", command("kicad", "analyze_thermal.py", "--schematic", schematic, "--pcb", board, "--output", EVIDENCE / "thermal.json")),
    ])
    final_jobs = [
        ("happy-spice", command("spice", "simulate_subcircuits.py", schematic, "--output", EVIDENCE / "spice.json", "--workdir", EVIDENCE / "spice-work")),
        ("happy-delta", command("kicad", "diff_analysis.py", PREVIOUS / "schematic.json", schematic, "--output", EVIDENCE / "schematic-delta.json")),
    ]
    if REUSE_LIFECYCLE:
        previous_schematic = json.loads((PREVIOUS / "schematic.json").read_text(encoding="utf-8"))
        current_schematic = json.loads(schematic.read_text(encoding="utf-8"))
        def identities(document):
            return sorted((part["reference"], part["mpn"], bool(part.get("dnp"))) for part in document["components"] if part.get("mpn"))
        if identities(previous_schematic) != identities(current_schematic):
            raise RuntimeError("Lifecycle reuse requires unchanged component/MPN/DNP identities")
        previous_lifecycle = PREVIOUS / "lifecycle.json"
        shutil.copy2(previous_lifecycle, EVIDENCE / "lifecycle.json")
        pipeline.write_json(EVIDENCE / "lifecycle-reuse.json", {"reused_from": str(previous_lifecycle),
                            "source_sha256": pipeline.digest(previous_lifecycle), "same_part_identities": True,
                            "network_requeried": False, "limit": "Preserve the earlier audit date and capability limits; no fresh lifecycle or stock claim"})
        print("happy-lifecycle: reused with identical MPN/DNP identities; no fresh query", flush=True)
    else:
        final_jobs.append(("happy-lifecycle", command("kicad", "lifecycle_audit.py", schematic, "--only", "lcsc", "--output", EVIDENCE / "lifecycle.json")))
    batch(final_jobs)
    checkpoint = json.loads((EVIDENCE / "checkpoint.json").read_text(encoding="utf-8"))
    if checkpoint["design_hashes"] != pipeline.fingerprints(pipeline.PRIMARY):
        raise RuntimeError("Design changed during analysis")


def main():
    global EVIDENCE, OUTPUT, PREVIOUS, REUSE_LIFECYCLE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("export", "review"))
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--previous-review", type=Path)
    parser.add_argument("--reuse-lifecycle", action="store_true")
    arguments = parser.parse_args()
    EVIDENCE = arguments.evidence.resolve() if arguments.evidence else EVIDENCE
    OUTPUT = arguments.output.resolve() if arguments.output else OUTPUT
    PREVIOUS = arguments.previous_review.resolve() if arguments.previous_review else PREVIOUS
    REUSE_LIFECYCLE = arguments.reuse_lifecycle
    export_checkpoint() if arguments.action == "export" else review()


if __name__ == "__main__":
    main()
