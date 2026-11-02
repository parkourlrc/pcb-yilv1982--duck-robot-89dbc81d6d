"""Restore only the accidentally reset candidate settings from its exact source."""
import json
from pathlib import Path
import shutil

import pipeline
from improve_via_annular_rings import EVIDENCE


def main():
    candidate_path = EVIDENCE / "candidate.json"
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    work = pipeline.managed(Path(candidate["project"]))
    manifest = json.loads((work.parent / "manifest.json").read_text(encoding="utf-8"))
    if manifest["source_hashes"] != pipeline.fingerprints(pipeline.PRIMARY):
        raise RuntimeError("Source has changed; cannot restore settings")
    filename = pipeline.STEM + ".kicad_pro"
    target = work / filename
    before = pipeline.digest(target)
    shutil.copy2(target, EVIDENCE / "rejected-default-project-settings.json")
    shutil.copy2(pipeline.PRIMARY / filename, target)
    pipeline.write_json(EVIDENCE / "settings-restoration.json", {
        "candidate_before_sha256": before, "restored_sha256": pipeline.digest(target),
        "source_manifest_sha256": manifest["source_hashes"][filename],
        "reason": "A standalone PCB trial was loaded without its paired project; SaveBoard reset candidate rules. The rejected 233-error report is not a design delta."
    })
    reports, summary = pipeline.check(work)
    candidate["summary"] = str(reports / "summary.json")
    pipeline.write_json(candidate_path, candidate)
    print(json.dumps({"drc": summary["drc"], "status": summary["status"]}))


if __name__ == "__main__":
    main()
