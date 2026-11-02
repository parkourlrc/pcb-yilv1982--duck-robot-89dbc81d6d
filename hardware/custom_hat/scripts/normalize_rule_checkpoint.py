"""Normalize rule whitespace and bind the unchanged manufacturing outputs to a fresh check."""
import json
from pathlib import Path
import shutil

import pipeline
from generate_rev_a import parse


EVIDENCE = pipeline.BASE.parents[1] / "docs/references/hat-simulation-tools-20261029/npth-clearance-20261031"
OUTPUT = pipeline.PRIMARY / "production-20261031-pth-clearance-review"


def main():
    record_path = EVIDENCE / "rule-format-rebind.json"
    if record_path.exists():
        raise RuntimeError("Formatting checkpoint already recorded")
    manifest_path = OUTPUT / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    before = pipeline.fingerprints(pipeline.PRIMARY)
    if before != manifest["design_hashes"]:
        raise RuntimeError("Source no longer matches the pre-format package")
    path = pipeline.PRIMARY / (pipeline.STEM + ".kicad_dru")
    original = path.read_bytes().decode("utf-8")
    clean = "\n".join(line.rstrip() for line in original.splitlines()) + "\n"
    if parse("(rules\n" + original + "\n)") != parse("(rules\n" + clean + "\n)"):
        raise RuntimeError("Rule semantics differ")
    record = {"before_hashes": before, "before_rule_text": original, "syntax_equal": True, "manufacturing_outputs_unchanged": True}
    pipeline.write_json(EVIDENCE / "rule-format-before.json", record)
    path.write_text(clean, encoding="utf-8")
    work = pipeline.prepare(pipeline.PRIMARY)
    reports, summary = pipeline.check(work)
    if summary["status"] != "checks_clean_not_manufacturing_release":
        raise RuntimeError("Formatted rules failed fresh validation")
    after = pipeline.fingerprints(pipeline.PRIMARY)
    changed = [name for name, value in after.items() if before.get(name) != value]
    if changed != [path.name]:
        raise RuntimeError("Unexpected source change during formatting")
    if any(pipeline.digest(OUTPUT / name) != expected for name, expected in manifest["outputs"].items()):
        raise RuntimeError("Manufacturing output changed during formatting")
    checkpoint_path = EVIDENCE / "checkpoint.json"
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    checkpoint["design_hashes"] = after
    checkpoint["summary"] = str(reports / "summary.json")
    manifest["design_hashes"] = after
    pipeline.write_json(checkpoint_path, checkpoint)
    pipeline.write_json(manifest_path, manifest)
    shutil.copy2(reports / "summary.json", EVIDENCE / "post-promotion-summary.json")
    record.update(after_hashes=after, changed_files=changed, summary=str(reports / "summary.json"), custom_rules_loading=summary["custom_rules_loading"])
    pipeline.write_json(record_path, record)
    print(json.dumps({"changed_files": changed, "pcb_sha256": checkpoint["pcb_sha256"], "status": summary["status"]}))


if __name__ == "__main__":
    main()
