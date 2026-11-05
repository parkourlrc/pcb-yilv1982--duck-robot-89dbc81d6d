"""Check panel tab cut proximity for the explicit SMT-before-THT depanel sequence."""
import csv
from datetime import datetime
import json
import math
from pathlib import Path

import pcbnew
import pipeline

EVIDENCE = pipeline.BASE.parents[1] / "docs/references/扩展板邮票孔与电源修复"


def box_gap_to_cut(box, cut):
    left, top, right, bottom = box
    xpos, ypos, half_width = cut
    return math.hypot(max(left-(xpos+half_width), xpos-half_width-right, 0), max(top-ypos, ypos-bottom, 0))


def main():
    checkpoint = pipeline.current_checkpoint()
    contract = json.loads((EVIDENCE / "panel-candidate.json").read_text(encoding="utf-8"))
    panel_path = Path(contract["panel"])
    verification = json.loads((EVIDENCE / "panel-verification.json").read_text(encoding="utf-8"))
    if contract["source_pcb_sha256"] != checkpoint["pcb_sha256"] or pipeline.digest(panel_path) != verification["panel_sha256"]:
        raise RuntimeError("Panel does not match current review")
    package = pipeline.BASE.parents[1] / checkpoint["review_binding"]["production_package"]
    with (package / "assembly-plan.csv").open(encoding="utf-8-sig", newline="") as stream:
        plan = {row["Reference"]: row for row in csv.DictReader(stream) if not row["Assembly"].startswith("DNP")}
    board = pcbnew.LoadBoard(str(panel_path))
    bodies = []
    for footprint in board.GetFootprints():
        reference = footprint.GetReference()
        original_reference = reference.removeprefix("B2_")
        if original_reference not in plan:
            continue
        layer = pcbnew.F_Fab if footprint.GetLayer() == pcbnew.F_Cu else pcbnew.B_Fab
        shapes = [shape.GetBoundingBox() for shape in footprint.GraphicalItems()
                  if shape.Type() == pcbnew.PCB_SHAPE_T and shape.GetLayer() == layer]
        if not shapes:
            raise RuntimeError("Missing fitted fabrication outline: " + reference)
        box = [min(shape.GetLeft() for shape in shapes), min(shape.GetTop() for shape in shapes),
               max(shape.GetRight() for shape in shapes), max(shape.GetBottom() for shape in shapes)]
        bodies.append({"reference": reference, "assembly": plan[original_reference]["Assembly"],
                       "side": board.GetLayerName(footprint.GetLayer()), "bbox_mm": [value/1e6 for value in box]})
    if len(bodies) != 116:
        raise RuntimeError("Unexpected fitted body inventory")
    groups = json.loads((EVIDENCE / "edge-copper-reference-check.json").read_text(encoding="utf-8"))["centered_hole_groups"]
    checks = []
    for group in groups:
        center = (min(group["xs_mm"])+max(group["xs_mm"]))/2
        cut = [center, group["y_mm"], 2.8]
        distances = [{**row, "cut_to_fab_gap_mm": box_gap_to_cut(row["bbox_mm"], cut)} for row in bodies]
        smt = sorted([row for row in distances if row["assembly"].startswith("SMT")], key=lambda row: row["cut_to_fab_gap_mm"])
        tht = sorted([row for row in distances if row["assembly"].startswith("THT")], key=lambda row: row["cut_to_fab_gap_mm"])
        checks.append({"cut_center_mm": cut[:2], "cut_span_x_mm": [center-2.8, center+2.8],
                       "nearest_smt": smt[0], "nearest_later_tht": tht[0],
                       "smt_within_3mm": [row["reference"] for row in smt if row["cut_to_fab_gap_mm"] < 3]})
    result = {"date": datetime.now().date().isoformat(), "pcb_sha256": checkpoint["pcb_sha256"],
              "panel_sha256": pipeline.digest(panel_path), "panel_project_sha256": pipeline.digest(panel_path.with_suffix(".kicad_pro")),
              "checks": checks, "minimum_smt_cut_to_fab_gap_mm": min(row["nearest_smt"]["cut_to_fab_gap_mm"] for row in checks),
              "minimum_tht_cut_to_fab_gap_mm": min(row["nearest_later_tht"]["cut_to_fab_gap_mm"] for row in checks),
              "assembly_sequence": ["B-side SMT reflow", "F-side SMT reflow", "Supported tab cutting and burr inspection", "Manual point soldering of all THT parts"],
              "hand_breaking_allowed": False, "tht_installed_during_depaneling": False,
              "three_mm_local_cut_screen_pass": all(not row["smt_within_3mm"] for row in checks),
              "limits": ["Cut-line to nominal fabrication bounding boxes only; not cutter diameter, clamp geometry, strain or shock validation",
                         "Three mm screen applies only to these tab-cut corridors, not every routed void boundary",
                         "The factory must select a supported cutting method and fixture compatible with populated boards",
                         "This sequence is a design choice; no actual depaneling, damage or solder quality test has occurred"],
              "manufacturing_released": False, "hardware_tested": False}
    if len(checks) != 8 or not result["three_mm_local_cut_screen_pass"]:
        raise RuntimeError("Tab-cut geometry screen failed")
    pipeline.write_json(EVIDENCE / "depanel-process-check.json", result)
    print(json.dumps({key: value for key, value in result.items() if key != "checks"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
