"""Bind read-only audits to a source-verified native checkpoint, not a filename or timestamp."""
import argparse
import json
from pathlib import Path

import pipeline


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    arguments = parser.parse_args()
    root = pipeline.BASE.parents[1]
    evidence, output = arguments.evidence.resolve(), arguments.output.resolve()
    checkpoint_path, summary_path = evidence / "checkpoint.json", evidence / "post-promotion-summary.json"
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    package = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    hashes = pipeline.fingerprints(pipeline.PRIMARY)
    if checkpoint["design_hashes"] != hashes or summary["source_hashes"] != hashes or package["design_hashes"] != hashes:
        raise RuntimeError("Source, native checks and exported package do not share one identity")
    if summary["status"] != "checks_clean_not_manufacturing_release" or not summary["custom_rules_loading"]["custom_rules_loaded"]:
        raise RuntimeError("Native checks or custom rules did not pass")
    if summary["custom_rules_loading"].get("rules_sha256") != hashes[pipeline.STEM + ".kicad_dru"]:
        raise RuntimeError("Custom-rule proof refers to different rules")
    if any(pipeline.digest(output / name) != expected for name, expected in package["outputs"].items()):
        raise RuntimeError("A fabrication output changed since export")
    binding_path = pipeline.BASE / "current-review.json"
    if binding_path.exists():
        previous = json.loads(binding_path.read_text(encoding="utf-8"))
        pipeline.write_json(evidence / "previous-current-review.json", previous)
    record = {"revision": arguments.revision, "pcb_sha256": checkpoint["pcb_sha256"],
              "checkpoint": checkpoint_path.relative_to(root).as_posix(), "checkpoint_sha256": pipeline.digest(checkpoint_path),
              "native_summary": summary_path.relative_to(root).as_posix(), "native_summary_sha256": pipeline.digest(summary_path),
              "production_package": output.relative_to(root).as_posix(), "production_ready": False, "hardware_tested": False,
              "purpose": "Identity binding for current read-only checks; no manufacturing or real-hardware release"}
    pipeline.write_json(binding_path, record)
    pipeline.current_checkpoint()
    print(json.dumps(record))


if __name__ == "__main__":
    main()
