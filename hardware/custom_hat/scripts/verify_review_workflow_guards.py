"""Check stale-source and DNP-stencil rejection on isolated copies of the real outputs."""
import copy
import json
from pathlib import Path
import shutil

import pipeline
from export_dnp_stencil import audit_stencil_policy


def main():
    checkpoint = pipeline.current_checkpoint()
    root = pipeline.BASE.parents[1]
    binding = checkpoint["review_binding"]
    evidence = (root / binding["checkpoint"]).parent
    output = root / binding["production_package"]
    original_primary = pipeline.PRIMARY
    original_hashes = pipeline.fingerprints(original_primary)
    work = pipeline.prepare(original_primary)
    stale_rejected = False
    try:
        pipeline.PRIMARY = work
        pipeline.current_checkpoint()
        schematic = work / (pipeline.STEM + ".kicad_sch")
        schematic.write_bytes(schematic.read_bytes() + b"\n")
        try:
            pipeline.current_checkpoint()
        except RuntimeError:
            stale_rejected = True
    finally:
        pipeline.PRIMARY = original_primary
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    policy = copy.deepcopy(manifest["stencil_policy"])
    audit = json.loads((evidence / "final-audit.json").read_text(encoding="utf-8"))
    dnp = set(audit["dnp_parts"])
    if "C307" not in dnp:
        raise RuntimeError("The real DNP regression case no longer matches this scenario")
    temporary = work.parent / "stencil-negative-case"
    temporary.mkdir()
    for row in policy["comparisons"]:
        shutil.copy2(output / row["file"], temporary / row["file"])
    positive = audit_stencil_policy(temporary, evidence, policy, dnp, checkpoint["pcb_sha256"])
    front = next(row for row in policy["comparisons"] if row["file"].endswith("-F_Paste.gtp"))
    shutil.copy2(evidence / "unfiltered-paste" / front["file"], temporary / front["file"])
    front["final_sha256"] = pipeline.digest(temporary / front["file"])
    policy["accepted"] = True
    negative = audit_stencil_policy(temporary, evidence, policy, dnp, checkpoint["pcb_sha256"])
    result = {"pcb_sha256": checkpoint["pcb_sha256"], "matching_source_copy_accepted": True,
              "stale_byte_fingerprint_rejected": stale_rejected,
              "valid_stencil_copy_accepted": positive["accepted"],
              "unfiltered_dnp_rejected_despite_matching_claimed_hash": not negative["accepted"],
              "primary_unchanged": pipeline.fingerprints(original_primary) == original_hashes,
              "original_package_unchanged": all(pipeline.digest(output / name) == expected for name, expected in manifest["outputs"].items()),
              "isolated_work": str(work), "hardware_tested": False, "manufacturing_released": False}
    result["accepted"] = all(result[key] for key in ("matching_source_copy_accepted", "stale_byte_fingerprint_rejected", "valid_stencil_copy_accepted",
        "unfiltered_dnp_rejected_despite_matching_claimed_hash", "primary_unchanged", "original_package_unchanged"))
    pipeline.write_json(evidence / "workflow-negative-checks.json", result)
    print(json.dumps(result))
    if not result["accepted"]:
        raise RuntimeError("A review identity or stencil guard did not reject the bad copy")


if __name__ == "__main__":
    main()
