"""Withhold auto-generated stackup metadata when the PCB has no explicit stackup."""
import argparse
import json
from pathlib import Path
import shutil

import pipeline
from generate_rev_a import first, parse


def quarantine_default_job(board, output, evidence):
    tree = parse(board.read_text(encoding="utf-8"))
    explicit = first(first(tree, "setup") or [], "stackup") is not None
    job = output / (board.stem + "-job.gbrjob")
    record_path = evidence / "gerber-job-policy.json"
    record = {"pcb_sha256": pipeline.digest(board), "explicit_stackup_in_pcb": explicit,
              "generated_name": job.name, "fabricator_approved": False}
    if not job.exists():
        if record_path.exists():
            existing = json.loads(record_path.read_text(encoding="utf-8"))
            if existing["pcb_sha256"] != record["pcb_sha256"]:
                raise RuntimeError("Old job-policy record belongs to another PCB")
            return existing
        record["status"] = "no_job_generated"
    else:
        data = json.loads(job.read_text(encoding="utf-8-sig"))
        record.update(job_sha256=pipeline.digest(job), generated_stackup=data.get("MaterialStackup"), generated_general_specs=data.get("GeneralSpecs"))
        if explicit:
            record["status"] = "declared_stackup_not_fabrication_release"
        else:
            archive = evidence / "unconfirmed-gerber-job.json"
            if archive.exists() and pipeline.digest(archive) != record["job_sha256"]:
                raise RuntimeError("Preserve the existing raw-job archive before another export")
            if not archive.exists():
                shutil.copy2(job, archive)
            if pipeline.digest(archive) != record["job_sha256"]:
                raise RuntimeError("Raw job archive mismatch")
            job.unlink()
            record.update(status="withheld_default_stackup", archive_file=archive.name,
                          reason="No explicit PCB stackup. KiCad synthesized layer thicknesses; these are not accepted manufacturing parameters.")
    pipeline.write_json(record_path, record)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    output, evidence = arguments.output.resolve(), arguments.evidence.resolve()
    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    board = pipeline.PRIMARY / (pipeline.STEM + ".kicad_pcb")
    if manifest["design_hashes"][board.name] != pipeline.digest(board):
        raise RuntimeError("Exported design differs from the current PCB")
    job = output / (pipeline.STEM + "-job.gbrjob")
    if job.exists() and manifest["outputs"].get(job.name) != pipeline.digest(job):
        raise RuntimeError("Generated job changed since export")
    policy = quarantine_default_job(board, output, evidence)
    if policy["status"] == "withheld_default_stackup":
        manifest["outputs"].pop(job.name, None)
    manifest["job_file_policy"] = policy
    pipeline.write_json(manifest_path, manifest)
    print(json.dumps({"status": policy["status"], "pcb_sha256": policy["pcb_sha256"], "archive": policy.get("archive_file")}))


if __name__ == "__main__":
    main()
