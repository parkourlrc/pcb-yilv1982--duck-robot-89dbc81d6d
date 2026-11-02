"""Audit the complete design BOM, CAD consistency, output bindings and new links."""
import csv
import argparse
import json
from pathlib import Path
import re
import subprocess

import pipeline
from generate_rev_a import children, first, parse
from repair_release_metadata import properties
from export_dnp_stencil import audit_stencil_policy


EVIDENCE = pipeline.BASE.parents[1] / "docs/references/hat-simulation-tools-20261029/final-bom-20261031"
OUTPUT = pipeline.PRIMARY / "production-20261031-bom-review"


def main():
    global EVIDENCE,OUTPUT
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence",type=Path)
    parser.add_argument("--output",type=Path)
    parser.add_argument("--expected-fitted", type=int, default=54)
    arguments=parser.parse_args()
    EVIDENCE=arguments.evidence.resolve() if arguments.evidence else EVIDENCE
    OUTPUT=arguments.output.resolve() if arguments.output else OUTPUT
    checkpoint = json.loads((EVIDENCE / "checkpoint.json").read_text(encoding="utf-8"))
    manifest = json.loads((OUTPUT / "manifest.json").read_text(encoding="utf-8"))
    board = parse((pipeline.PRIMARY / (pipeline.STEM + ".kicad_pcb")).read_text(encoding="utf-8"))
    explicit_stackup = first(first(board, "setup") or [], "stackup") is not None
    job_policy = manifest.get("job_file_policy", {})
    actual_outputs = {path.relative_to(OUTPUT).as_posix() for path in OUTPUT.rglob("*") if path.is_file()}
    unexpected_outputs = sorted(actual_outputs - set(manifest["outputs"]) - {"README.md", "manifest.json"})
    default_jobs = sorted(path.name for path in OUTPUT.glob("*.gbrjob")) if not explicit_stackup else []
    job_policy_valid = job_policy.get("pcb_sha256") == pipeline.digest(pipeline.PRIMARY / (pipeline.STEM + ".kicad_pcb")) and job_policy.get("explicit_stackup_in_pcb") == explicit_stackup
    if not explicit_stackup:
        if job_policy.get("status") == "withheld_default_stackup":
            archive = EVIDENCE / job_policy.get("archive_file", "__missing_job_archive__")
            job_policy_valid = job_policy_valid and archive.is_file()
            job_policy_valid = job_policy_valid and pipeline.digest(archive) == job_policy.get("job_sha256")
        else:
            job_policy_valid = job_policy_valid and job_policy.get("status") == "no_job_generated"
    pcb = {properties(footprint).get("Reference"): {"Footprint": str(footprint[1]), **properties(footprint)}
           for footprint in children(board, "footprint")}
    footprint_nodes = {properties(footprint).get("Reference"): footprint for footprint in children(board, "footprint")}
    fitted = {}
    dnp = {}
    mismatch = []
    for path in pipeline.PRIMARY.glob("*.kicad_sch"):
        for symbol in children(parse(path.read_text(encoding="utf-8")), "symbol"):
            fields = properties(symbol)
            reference = fields.get("Reference", "")
            if not fields.get("Footprint") or reference.startswith("TP") or first(symbol, "on_board") == ["on_board", "no"]:
                continue
            group = dnp if first(symbol, "dnp") == ["dnp", "yes"] else fitted
            group[reference] = fields.get("MPN", "")
            for key in ("Value", "MPN", "Manufacturer", "Footprint", "Datasheet"):
                if not fields.get(key) or fields[key] != pcb.get(reference, {}).get(key):
                    mismatch.append([reference, key, fields.get(key), pcb.get(reference, {}).get(key)])
    with (OUTPUT / "bom-tracking.csv").open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    bom_references = {reference for row in rows if row["DNP"] == "False" for reference in row["Reference"].split(",")}
    with (OUTPUT / "positions.csv").open(encoding="utf-8-sig", newline="") as stream:
        positions = list(csv.DictReader(stream))
    position_refs = [row["Ref"] for row in positions]
    position_mismatches = []
    for row in positions:
        reference = row["Ref"]
        node = footprint_nodes.get(reference)
        if node is None:
            position_mismatches.append([reference, "missing footprint"])
            continue
        location = first(node, "at")
        side = "top" if first(node, "layer")[1] == "F.Cu" else "bottom"
        angle = float(location[3]) if len(location) > 3 else 0
        if not (abs(float(row["PosX"]) - float(location[1])) <= 2e-6 and abs(float(row["PosY"]) + float(location[2])) <= 2e-6
                and abs((float(row["Rot"]) - angle + 180) % 360 - 180) < 1e-6 and row["Side"] == side
                and row["Val"] == pcb[reference]["Value"] and row["Package"] == str(node[1]).split(":")[-1]):
            position_mismatches.append([reference, row, location])
    expected_smt = {reference for reference in fitted if "smd" in (first(footprint_nodes[reference], "attr") or [])}
    with (OUTPUT / "positions-smt.csv").open(encoding="utf-8-sig", newline="") as stream:
        smt_positions = list(csv.DictReader(stream))
    native_position_map = {row["Ref"]: row for row in positions}
    smt_positions_valid = len(smt_positions) == len(expected_smt) and {row["Ref"] for row in smt_positions} == expected_smt
    smt_positions_valid = smt_positions_valid and all(row == native_position_map[row["Ref"]] for row in smt_positions)
    with (OUTPUT / "assembly-plan.csv").open(encoding="utf-8-sig", newline="") as stream:
        assembly = list(csv.DictReader(stream))
    assembly_refs = [row["Reference"] for row in assembly]
    assembly_valid = len(assembly_refs) == len(set(assembly_refs)) and set(assembly_refs) == set(fitted) | set(dnp)
    for row in assembly:
        reference = row["Reference"]
        expected_method = "DNP" if reference in dnp else "SMT" if reference in expected_smt else "THT"
        expected_side = "top" if first(footprint_nodes[reference], "layer")[1] == "F.Cu" else "bottom"
        assembly_valid = assembly_valid and row["Assembly"].startswith(expected_method) and row["Side"] == expected_side
        assembly_valid = assembly_valid and all(row[key] == pcb[reference][key] for key in ("Value", "MPN", "Footprint"))
    filtered_bom_checks = {}
    for name, expected in (("bom-fitted.csv", set(fitted)), ("bom-smt.csv", expected_smt)):
        with (OUTPUT / name).open(encoding="utf-8-sig", newline="") as stream:
            filtered_rows = list(csv.DictReader(stream))
        references = [reference for row in filtered_rows for reference in row["Reference"].split(",")]
        valid = set(references) == expected and len(references) == len(expected)
        valid = valid and all(row["DNP"] == "False" and int(row["Qty"]) == len(row["Reference"].split(",")) for row in filtered_rows)
        valid = valid and all(row[key] == pcb[reference][key] for row in filtered_rows for reference in row["Reference"].split(",") for key in ("Value", "MPN", "Footprint"))
        filtered_bom_checks[name] = valid
    documents = [pipeline.BASE.parents[1] / name for name in (
        "README.md", "PROGRESS.md", "hardware/custom_hat/README.md", "hardware/custom_hat/rev_a/README.md", "docs/photos/README.md",
        "docs/specs/20261028-custom-hat/spec.md", "docs/specs/20261028-custom-hat/recovery-plan.md",
        "docs/references/hat-simulation-tools-20261029/research.md", "docs/references/hat-simulation-tools-20261029/issue-matrix-20261030.md",
        "docs/references/hat-simulation-tools-20261029/mpn-lock-20261030/research.md")] + [EVIDENCE/"research.md", OUTPUT/"README.md"]
    broken = []
    for document in documents:
        for target in re.findall(r"\]\(([^)]+)\)", document.read_text(encoding="utf-8")):
            if not any(token in target for token in (EVIDENCE.name,OUTPUT.name)):
                continue
            if not target.startswith(("https:", "http:")) and not (document.parent/target.split("#")[0]).exists():
                broken.append([str(document), target])
    diff = subprocess.run(["git", "diff", "--check"], cwd=pipeline.BASE.parents[1], capture_output=True, encoding="utf-8", errors="replace")
    stencil = audit_stencil_policy(OUTPUT, EVIDENCE, manifest.get("stencil_policy", {}), dnp,
                                   pipeline.digest(pipeline.PRIMARY / (pipeline.STEM + ".kicad_pcb")))
    result = {"pcb_sha256": pipeline.digest(pipeline.PRIMARY/(pipeline.STEM+".kicad_pcb")),
              "expected_fitted_count": arguments.expected_fitted,
              "fitted_count": len(fitted), "fitted_mpn_count": sum(bool(value) for value in fitted.values()),
              "unique_fitted_mpns": len(set(fitted.values())), "dnp_parts": dnp, "cad_field_mismatches": mismatch,
              "bom_reference_set_matches": bom_references == set(fitted), "bom_fitted_quantity": sum(int(row["Qty"]) for row in rows if row["DNP"]=="False"),
              "native_position_reference_set_matches": set(position_refs) == set(fitted) and len(position_refs) == len(set(position_refs)),
              "native_position_mismatches": position_mismatches, "smt_positions_valid": smt_positions_valid, "smt_position_count": len(smt_positions), "assembly_plan_valid": assembly_valid,
              "filtered_bom_checks": filtered_bom_checks, "stencil_policy": stencil,
              "design_hash_mismatches": [name for name, expected in checkpoint["design_hashes"].items() if pipeline.digest(pipeline.PRIMARY/name)!=expected],
              "output_hash_mismatches": [name for name, expected in manifest["outputs"].items() if pipeline.digest(OUTPUT/name)!=expected],
              "unexpected_output_files": unexpected_outputs, "unreviewed_default_job_files": default_jobs, "job_policy_valid": job_policy_valid,
              "broken_current_links": broken, "git_diff_check_exit": diff.returncode,
              "production_ready": False, "hardware_tested": False, "goal_complete": False, "committed": False}
    pipeline.write_json(EVIDENCE/"final-audit.json", result)
    print(json.dumps(result, ensure_ascii=False))
    if not all((len(fitted)==arguments.expected_fitted, all(fitted.values()), not mismatch, result["bom_reference_set_matches"], result["bom_fitted_quantity"]==arguments.expected_fitted,
                not result["design_hash_mismatches"], not result["output_hash_mismatches"], not unexpected_outputs, not default_jobs,
                job_policy_valid, result["native_position_reference_set_matches"], not position_mismatches, smt_positions_valid, assembly_valid,
                all(filtered_bom_checks.values()), stencil["accepted"], not broken, diff.returncode==0)):
        raise RuntimeError("BOM/artifact audit failed")


if __name__ == "__main__":
    main()
