"""Promote an inspected, fully checked metadata workspace with source guards."""
import argparse
import json
from pathlib import Path
import shutil

import pipeline


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    arguments = parser.parse_args()
    work = pipeline.managed(arguments.project)
    evidence = arguments.evidence.resolve()
    source_before = pipeline.fingerprints(pipeline.PRIMARY)
    manifest = json.loads((work.parent / "manifest.json").read_text(encoding="utf-8"))
    summary = json.loads(arguments.summary.read_text(encoding="utf-8"))
    geometry = json.loads((evidence / "geometry-connectivity-check.json").read_text(encoding="utf-8"))
    if source_before != manifest["source_hashes"]:
        raise RuntimeError("Primary design changed; re-review required")
    if pipeline.fingerprints(work) != summary["source_hashes"]:
        raise RuntimeError("Candidate no longer matches its checked fingerprint")
    if summary["status"] != "checks_clean_not_manufacturing_release" or not geometry["accepted"]:
        raise RuntimeError("Checks did not pass")
    rule_loading = summary.get("custom_rules_loading", {})
    if not rule_loading.get("custom_rules_loaded") or rule_loading.get("rules_sha256") != pipeline.digest(work / (pipeline.STEM + ".kicad_dru")):
        raise RuntimeError("Fresh proof of custom-rule loading is required before promotion")
    if pipeline.digest(work / (pipeline.STEM + ".kicad_pcb")) != geometry["runs"]["after"]["pcb_sha256"]:
        raise RuntimeError("Candidate no longer matches filled-geometry check")
    backup = evidence / "before-metadata"
    if backup.exists():
        raise FileExistsError("Promotion snapshot already exists")
    backup.mkdir()
    changed = []
    for path in pipeline.design_files(work):
        name = path.relative_to(work).as_posix()
        if source_before.get(name) == pipeline.digest(path):
            continue
        target = pipeline.PRIMARY / name
        if target.is_file():
            archived = backup / name
            archived.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, archived)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        changed.append(name)
    report_copy = evidence / "accepted-reports"
    shutil.copytree(arguments.summary.parent, report_copy)
    pipeline.write_json(evidence / "promotion.json", {
        "work": str(work), "changed_files": changed, "before_hashes": source_before,
        "after_hashes": pipeline.fingerprints(pipeline.PRIMARY), "summary": str(arguments.summary),
        "production_ready": False, "hardware_tested": False,
    })
    candidate_path = evidence / "candidate.json"
    if candidate_path.exists():
        candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
        candidate["promoted"] = True
        candidate["promoted_pcb_sha256"] = pipeline.digest(pipeline.PRIMARY / (pipeline.STEM + ".kicad_pcb"))
        pipeline.write_json(candidate_path, candidate)
    print(json.dumps({"changed_files": changed, "pcb_sha256": pipeline.digest(pipeline.PRIMARY / (pipeline.STEM + ".kicad_pcb"))}))


if __name__ == "__main__":
    main()
