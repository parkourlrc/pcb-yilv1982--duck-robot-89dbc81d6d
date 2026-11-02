"""Audit current artifacts and reproduce rejection of the captured settings reset."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

import pipeline
from improve_via_annular_rings import EVIDENCE


def main():
    checkpoint = json.loads((EVIDENCE / "checkpoint.json").read_text(encoding="utf-8"))
    output = pipeline.PRIMARY / "production-20261031-annular-review"
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    guard_copy = pipeline.prepare(pipeline.PRIMARY)
    shutil.copy2(EVIDENCE / "rejected-default-project-settings.json", guard_copy / (pipeline.STEM + ".kicad_pro"))
    rejected = False
    try:
        pipeline.check(guard_copy)
    except RuntimeError as error:
        rejected = "Project settings changed without a reviewed manifest hash" in str(error)
    summaries = list((guard_copy.parent / "reports").glob("*/summary.json"))
    if len(summaries) != 1:
        raise RuntimeError("Unexpected guard-test output count")
    guard_result = json.loads(summaries[0].read_text(encoding="utf-8"))
    guard = {"rejected_known_default_settings": rejected, "commands_executed": guard_result["commands"], "summary": str(summaries[0]),
             "source_unchanged": checkpoint["design_hashes"] == pipeline.fingerprints(pipeline.PRIMARY)}
    pipeline.write_json(EVIDENCE / "project-settings-guard-test.json", guard)
    documents = [
        pipeline.BASE.parents[1] / name for name in
        ("README.md", "PROGRESS.md", "hardware/custom_hat/README.md", "hardware/custom_hat/rev_a/README.md",
         "docs/photos/README.md", "docs/specs/20261028-custom-hat/spec.md", "docs/specs/20261028-custom-hat/recovery-plan.md",
         "docs/references/hat-simulation-tools-20261029/issue-matrix-20261030.md",
         "docs/references/hat-simulation-tools-20261029/mpn-lock-20261030/research.md")
    ] + [EVIDENCE / "research.md", output / "README.md"]
    broken = []
    for document in documents:
        for target in re.findall(r"\]\(([^)]+)\)", document.read_text(encoding="utf-8")):
            if not any(token in target for token in ("annular-rings-20261031", "connectors-20261031", "production-20261031-annular")):
                continue
            if not target.startswith(("https:", "http:")) and not (document.parent / target.split("#")[0]).exists():
                broken.append([str(document), target])
    diff = subprocess.run(["git", "diff", "--check"], cwd=pipeline.BASE.parents[1], capture_output=True, encoding="utf-8", errors="replace")
    result = {"pcb_sha256": pipeline.digest(pipeline.PRIMARY / (pipeline.STEM + ".kicad_pcb")),
              "design_hash_mismatches": [name for name, expected in checkpoint["design_hashes"].items() if pipeline.digest(pipeline.PRIMARY / name) != expected],
              "output_hash_mismatches": [name for name, expected in manifest["outputs"].items() if pipeline.digest(output / name) != expected],
              "broken_new_links": broken, "project_settings_guard": guard, "git_diff_check_exit": diff.returncode,
              "hardware_tested": False, "production_ready": False, "goal_complete": False, "committed": False}
    pipeline.write_json(EVIDENCE / "final-audit.json", result)
    print(json.dumps(result, ensure_ascii=False))
    if any((result["design_hash_mismatches"], result["output_hash_mismatches"], broken, diff.returncode, not rejected, guard_result["commands"], not guard["source_unchanged"])):
        raise RuntimeError("Final artifact or guard audit failed")


if __name__ == "__main__":
    main()
