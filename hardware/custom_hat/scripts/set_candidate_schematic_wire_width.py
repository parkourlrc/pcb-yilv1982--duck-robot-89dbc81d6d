"""Restore original colors and set the missing display wire width from KiCad's template."""
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
    current_record = EVIDENCE / "presentation-change.json"
    old_record = json.loads(current_record.read_text(encoding="utf-8"))
    if old_record.get("actual_setting"):
        raise RuntimeError("Default wire width already corrected")
    old_record["rejected_reason"] = "Color-only trial changed label text but wire SVG paths still used stroke:none. The initial cause attribution was not established."
    pipeline.write_json(EVIDENCE / "rejected-color-only-presentation.json", old_record)
    shutil.copy2(path, EVIDENCE / "rejected-color-only-project.json")
    primary = pipeline.PRIMARY / path.name
    original = json.loads(primary.read_text(encoding="utf-8"))
    corrected = copy.deepcopy(original)
    template_path = pipeline.find_cli().parent.parent / "share/kicad/template/RaspberryPi-uHAT/RaspberryPi-uHAT.kicad_pro"
    template = json.loads(template_path.read_text(encoding="utf-8"))
    width = template["schematic"]["drawing"]["default_wire_thickness"]
    if width != 6.0:
        raise RuntimeError("Review changed KiCad template wire width")
    corrected["schematic"].setdefault("drawing", {})["default_wire_thickness"] = width
    if electrical_project_settings(original) != electrical_project_settings(corrected):
        raise RuntimeError("Non-presentation project changes")
    pipeline.write_json(path, corrected)
    manifest_path = work.parent / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["approved_project_settings_sha256"] = pipeline.digest(path)
    manifest["project_settings_review"] = {"scope": "Only schematic.drawing.default_wire_thickness; original net colors and all electrical/manufacturing data retained",
                                           "before_sha256": pipeline.digest(primary), "after_sha256": pipeline.digest(path),
                                           "value": width, "template": str(template_path), "template_sha256": pipeline.digest(template_path)}
    pipeline.write_json(manifest_path, manifest)
    record = {"actual_setting": "schematic.drawing.default_wire_thickness", "before": None, "after": width,
              "template": str(template_path), "template_sha256": pipeline.digest(template_path),
              "original_colors_restored": True, "electrical_settings_equal": True,
              "moved_note": old_record["moved_note"], "before_project_sha256": pipeline.digest(primary),
              "approved_project_sha256": pipeline.digest(path), "color_only_trial_rejected": True}
    pipeline.write_json(current_record, record)
    reports, summary = pipeline.check(work)
    candidate["summary"] = str(reports / "summary.json")
    pipeline.write_json(candidate_path, candidate)
    print(json.dumps({"status": summary["status"], "drc": summary["drc"], "wire_width_template_value": width}))


if __name__ == "__main__":
    main()
