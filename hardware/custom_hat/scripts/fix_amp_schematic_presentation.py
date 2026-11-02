"""Fix overlapping review text and transparent schematic wire colors only."""
import copy
import json
from pathlib import Path

import pipeline
from generate_rev_a import first, parse
from repair_release_metadata import replace_children


EVIDENCE = pipeline.BASE.parents[1] / "docs/references/hat-simulation-tools-20261029/amp-decoupling-20261031"


def project_except_colors(document):
    normalized = copy.deepcopy(document)
    for netclass in normalized["net_settings"]["classes"]:
        netclass.pop("schematic_color", None)
    return normalized


def electrical_project_settings(document):
    normalized = copy.deepcopy(document)
    for netclass in normalized["net_settings"]["classes"]:
        netclass.pop("wire_width", None)
        netclass.pop("line_style", None)
    return normalized


def main():
    record_path = EVIDENCE / "presentation-change.json"
    if record_path.exists():
        raise FileExistsError("Presentation correction already recorded")
    candidate_path = EVIDENCE / "candidate.json"
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    if candidate["promoted"]:
        raise RuntimeError("Use a new full workspace for a promoted design")
    work = pipeline.managed(Path(candidate["project"]))
    project_path = work / (pipeline.STEM + ".kicad_pro")
    before = json.loads(project_path.read_text(encoding="utf-8"))
    after = copy.deepcopy(before)
    changes = []
    for netclass in after["net_settings"]["classes"]:
        if netclass.get("schematic_color") != "rgba(0, 0, 0, 0.000)":
            raise RuntimeError("Review the existing user wire color before replacing it")
        changes.append({"class": netclass["name"], "before": netclass["schematic_color"], "after": "rgba(0, 132, 0, 1.000)"})
        netclass["schematic_color"] = "rgba(0, 132, 0, 1.000)"
    if {entry["class"] for entry in changes} != {"Default", "Power"} or project_except_colors(before) != project_except_colors(after):
        raise RuntimeError("Unexpected project settings delta")
    previous_project_hash = pipeline.digest(project_path)
    pipeline.write_json(project_path, after)
    schematic_path = work / "audio.kicad_sch"
    original = schematic_path.read_text(encoding="utf-8")
    moved = []
    def relocate(node):
        if len(node) < 2 or not str(node[1]).startswith("C323=22uF bulk and C328=2.2uF"):
            return False
        moved.append({"text": str(node[1]), "before": list(first(node, "at")[1:])})
        first(node, "at")[1:3] = [241.3, 148.59]
        moved[-1]["after"] = list(first(node, "at")[1:])
        return True
    updated = replace_children(original, "text", relocate)
    def electrical_schematic(text):
        return [node for node in parse(text) if not (isinstance(node, list) and node and node[0] == "text")]
    if len(moved) != 1 or electrical_schematic(original) != electrical_schematic(updated):
        raise RuntimeError("Non-presentation schematic changes detected")
    schematic_path.write_text("\n".join(line.rstrip() for line in updated.splitlines()) + "\n", encoding="utf-8")
    approved = pipeline.digest(project_path)
    manifest_path = work.parent / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["approved_project_settings_sha256"] = approved
    manifest["project_settings_review"] = {"scope": "Only netclass schematic display colors; all electrical/manufacturing settings identical",
                                           "before_sha256": previous_project_hash, "after_sha256": approved, "changes": changes}
    pipeline.write_json(manifest_path, manifest)
    pipeline.write_json(record_path, {"project_color_changes": changes, "moved_note": moved,
                        "before_project_sha256": previous_project_hash, "approved_project_sha256": approved,
                        "electrical_settings_equal": True, "electrical_schematic_equal": True,
                        "reason": "Native SVG emitted stroke:none for project wires; note overlappedU701. Only presentation corrected."})
    reports, summary = pipeline.check(work)
    candidate["summary"] = str(reports / "summary.json")
    pipeline.write_json(candidate_path, candidate)
    print(json.dumps({"drc": summary["drc"], "erc": summary["erc"], "status": summary["status"], "approved_project_hash": approved}))


if __name__ == "__main__":
    main()
