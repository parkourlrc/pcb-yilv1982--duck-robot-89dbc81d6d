"""Verify final design/output bindings, selected-part fields and local links."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

from generate_rev_a import children, parse
from repair_release_metadata import properties


ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "docs/references/hat-simulation-tools-20261029/bom-passives-20261031"
PRIMARY = ROOT / "hardware/custom_hat/rev_a"
OUTPUT = PRIMARY / "production-20261031-passives-review"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    checkpoint = json.loads((EVIDENCE / "checkpoint.json").read_text(encoding="utf-8"))
    manifest = json.loads((OUTPUT / "manifest.json").read_text(encoding="utf-8"))
    selected = json.loads((EVIDENCE / "selected-parts.json").read_text(encoding="utf-8"))
    board_fields = {properties(footprint).get("Reference"): properties(footprint)
                    for footprint in children(parse((PRIMARY / "custom_hat_rev_a.kicad_pcb").read_text(encoding="utf-8")), "footprint")}
    schematic_fields = {}
    for path in PRIMARY.glob("*.kicad_sch"):
        schematic_fields.update({properties(symbol).get("Reference"): properties(symbol)
                                 for symbol in children(parse(path.read_text(encoding="utf-8")), "symbol")})
    field_mismatches = []
    for reference, part in selected.items():
        for key, expected in part.items():
            if key in {"value", "footprint_contains"} or not expected:
                continue
            for kind, fields in (("schematic", schematic_fields), ("pcb", board_fields)):
                if fields.get(reference, {}).get(key) != expected:
                    field_mismatches.append([kind, reference, key])
    paths = [
        ROOT / "README.md", ROOT / "PROGRESS.md", ROOT / "hardware/custom_hat/README.md", PRIMARY / "README.md",
        ROOT / "docs/specs/20261028-custom-hat/spec.md", ROOT / "docs/specs/20261028-custom-hat/recovery-plan.md",
        EVIDENCE.parent / "issue-matrix-20261030.md", EVIDENCE.parent / "mpn-lock-20261030/research.md",
        EVIDENCE / "research.md", OUTPUT / "README.md", ROOT / "docs/photos/README.md",
    ]
    broken = []
    for path in paths:
        for target in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
            if "bom-passives-20261031" not in target and "production-20261031-passives" not in target:
                continue
            if not target.startswith(("http:", "https:")) and not (path.parent / target.split("#")[0]).exists():
                broken.append([str(path.relative_to(ROOT)), target])
    whitespace = subprocess.run(["git", "diff", "--check"], cwd=ROOT, capture_output=True, encoding="utf-8", errors="replace")
    result = {
        "pcb_sha256": digest(PRIMARY / "custom_hat_rev_a.kicad_pcb"),
        "design_hash_mismatches": [name for name, expected in checkpoint["design_hashes"].items() if digest(PRIMARY / name) != expected],
        "output_hash_mismatches": [name for name, expected in manifest["outputs"].items() if digest(OUTPUT / name) != expected],
        "selected_field_mismatches": field_mismatches, "selected_references_including_dnp": len(selected),
        "broken_current_links": broken, "git_diff_check_exit": whitespace.returncode,
        "hardware_tested": False, "production_ready": False, "goal_complete": False, "committed": False,
    }
    (EVIDENCE / "final-audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    if any(result[key] for key in ("design_hash_mismatches", "output_hash_mismatches", "selected_field_mismatches", "broken_current_links", "git_diff_check_exit")):
        raise SystemExit("Checkpoint audit failed")


if __name__ == "__main__":
    main()
