"""Fill only missing netclass wire display properties from the bundled KiCad template."""
import copy
import json
from pathlib import Path
import shutil

import pipeline
from fix_amp_schematic_presentation import EVIDENCE, electrical_project_settings


def main():
    candidate_path = EVIDENCE / "candidate.json"
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    work = pipeline.managed(Path(candidate["project"]))
    path = work / (pipeline.STEM + ".kicad_pro")
    record_path = EVIDENCE / "presentation-change.json"
    previous = json.loads(record_path.read_text(encoding="utf-8"))
    if previous.get("actual_setting") != "schematic.drawing.default_wire_thickness":
        raise RuntimeError("Review prior presentation experiment before continuing")
    previous["rejected_reason"] = "Global drawing wire thickness alone did not fix the exported stroke:none wire group."
    pipeline.write_json(EVIDENCE / "rejected-global-wire-width-presentation.json", previous)
    shutil.copy2(path, EVIDENCE / "rejected-global-wire-width-project.json")
    primary = pipeline.PRIMARY / path.name
    original = json.loads(primary.read_text(encoding="utf-8"))
    corrected = copy.deepcopy(original)
    template_path = pipeline.find_cli().parent.parent / "share/kicad/template/RaspberryPi-uHAT/RaspberryPi-uHAT.kicad_pro"
    template = json.loads(template_path.read_text(encoding="utf-8"))
    defaults = {entry["name"]: entry for entry in template["net_settings"]["classes"]}
    changes = []
    for netclass in corrected["net_settings"]["classes"]:
        for key in ("wire_width", "line_style"):
            if key in netclass:
                raise RuntimeError("Preserve an existing user display property")
            value = defaults[netclass["name"]][key]
            netclass[key] = value
            changes.append({"class": netclass["name"], "key": key, "before": None, "after": value})
    if electrical_project_settings(original) != electrical_project_settings(corrected):
        raise RuntimeError("Non-presentation project changes")
    pipeline.write_json(path, corrected)
    approved = pipeline.digest(path)
    manifest_path = work.parent / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["approved_project_settings_sha256"] = approved
    manifest["project_settings_review"] = {"scope": "Only netclass wire_width and line_style display defaults; original colors,global drawing andall electrical/manufacturing settings retained",
                                           "before_sha256": pipeline.digest(primary), "after_sha256": approved, "changes": changes,
                                           "template": str(template_path), "template_sha256": pipeline.digest(template_path)}
    pipeline.write_json(manifest_path, manifest)
    pipeline.write_json(record_path, {"actual_setting": "net_settings.classes wire_width/line_style", "changes": changes,
                        "template": str(template_path), "template_sha256": pipeline.digest(template_path),
                        "original_colors_and_global_drawing_restored": True, "electrical_settings_equal": True,
                        "moved_note": previous["moved_note"], "before_project_sha256": pipeline.digest(primary), "approved_project_sha256": approved,
                        "prior_trials_rejected": ["color_only", "global_wire_thickness"]})
    reports, summary = pipeline.check(work)
    candidate["summary"] = str(reports / "summary.json")
    pipeline.write_json(candidate_path, candidate)
    print(json.dumps({"status": summary["status"], "drc": summary["drc"], "display_changes": changes}))


if __name__ == "__main__":
    main()
