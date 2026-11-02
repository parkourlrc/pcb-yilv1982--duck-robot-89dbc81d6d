"""Check unchanged routing, explicit text limits and a failing-rule control board."""
import json
from pathlib import Path
import subprocess
import sys

import pcbnew

import pipeline
from add_i2c_pullups import vector
from enforce_manufacturing_text import EVIDENCE, expected_project_settings


def main():
    candidate_path = EVIDENCE / "candidate.json"
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    work = pipeline.managed(Path(candidate["project"]))
    result = subprocess.run([sys.executable, "-X", "utf8", str(Path(__file__).with_name("verify_release_metadata.py")),
                             "--project", str(work), "--output", str(EVIDENCE / "geometry-connectivity-check.json")],
                            capture_output=True, encoding="utf-8", errors="replace", timeout=300)
    (EVIDENCE / "native-geometry.log").write_text(result.stdout + result.stderr, encoding="utf-8")
    if result.returncode:
        raise RuntimeError("Native geometry invariants failed")
    board = pcbnew.LoadBoard(str(work / (pipeline.STEM + ".kicad_pcb")))
    text_items = [item for item in board.GetDrawings() if item.Type() == pcbnew.PCB_TEXT_T]
    for footprint in board.GetFootprints():
        text_items.extend(footprint.GetFields())
        text_items.extend(item for item in footprint.GraphicalItems() if item.Type() == pcbnew.PCB_TEXT_T)
    visible = [{"text": item.GetText(), "layer": item.GetLayerName(), "size_mm": [pcbnew.ToMM(value) for value in item.GetTextSize()],
                "stroke_mm": pcbnew.ToMM(item.GetTextThickness())}
               for item in text_items if item.GetLayer() in (pcbnew.F_SilkS, pcbnew.B_SilkS) and item.IsVisible()]
    original = (pipeline.PRIMARY / (pipeline.STEM + ".kicad_dru")).read_text(encoding="utf-8")
    actual = (work / (pipeline.STEM + ".kicad_dru")).read_text(encoding="utf-8")
    negative = pipeline.prepare(work)
    negative_path = negative / (pipeline.STEM + ".kicad_pcb")
    negative_board = pcbnew.LoadBoard(str(negative_path))
    text = next(item for item in negative_board.GetDrawings() if item.Type() == pcbnew.PCB_TEXT_T and item.GetText() == "DUCK HAT Rev A")
    text.SetTextSize(vector((.8, .8)))
    text.SetTextThickness(pcbnew.FromMM(.12))
    pcbnew.SaveBoard(str(negative_path), negative_board)
    negative_reports, negative_summary = pipeline.check(negative)
    report = json.loads((negative_reports / "drc.json").read_text(encoding="utf-8"))
    types = sorted({item["type"] for item in report["violations"]})
    verification = {"visible_silkscreen_text": visible,
                    "all_printed_text_meets_dimensions": all(min(row["size_mm"]) >= 1 and row["stroke_mm"] >= .15 for row in visible),
                    "custom_rules_unchanged": actual == original,
                    "project_settings_match_allowed_changes": json.loads((work / (pipeline.STEM + ".kicad_pro")).read_text(encoding="utf-8")) == expected_project_settings(json.loads((pipeline.PRIMARY / (pipeline.STEM + ".kicad_pro")).read_text(encoding="utf-8"))),
                    "negative_control": {"project": str(negative), "summary": str(negative_reports / "summary.json"), "status": negative_summary["status"], "violation_types": types},
                    "negative_control_rejected_for_both_limits": {"text_height", "text_thickness"}.issubset(types),
                    "hardware_tested": False, "manufacturing_approved": False}
    verification["accepted"] = all(verification[key] for key in ("all_printed_text_meets_dimensions", "custom_rules_unchanged", "project_settings_match_allowed_changes", "negative_control_rejected_for_both_limits"))
    pipeline.write_json(EVIDENCE / "manufacturing-rules-check.json", verification)
    geometry = json.loads((EVIDENCE / "geometry-connectivity-check.json").read_text(encoding="utf-8"))
    geometry["accepted"] = geometry["accepted"] and verification["accepted"]
    pipeline.write_json(EVIDENCE / "geometry-connectivity-check.json", geometry)
    print(json.dumps(verification))
    if not geometry["accepted"]:
        raise RuntimeError("Manufacturing text verification failed")
    reports, summary = pipeline.check(work)
    candidate["summary"] = str(reports / "summary.json")
    pipeline.write_json(candidate_path, candidate)
    print(summary["status"])


if __name__ == "__main__":
    main()
