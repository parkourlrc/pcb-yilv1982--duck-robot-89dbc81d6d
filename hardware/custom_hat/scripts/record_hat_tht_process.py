"""Record native THT clearances and an explicit local point-soldering process."""
import csv
from datetime import datetime
import json
import math
from pathlib import Path

import pcbnew
import pipeline

EVIDENCE = pipeline.BASE.parents[1] / "docs/references/扩展板邮票孔与电源修复"


def main():
    checkpoint = pipeline.current_checkpoint()
    root = pipeline.BASE.parents[1]
    package = root / checkpoint["review_binding"]["production_package"]
    with (package / "assembly-plan.csv").open(encoding="utf-8-sig", newline="") as stream:
        fitted = {row["Reference"]: row for row in csv.DictReader(stream) if not row["Assembly"].startswith("DNP")}
    board = pcbnew.LoadBoard(str(pipeline.PRIMARY / (pipeline.STEM + ".kicad_pcb")))
    bodies = []
    for footprint in board.GetFootprints():
        reference = footprint.GetReference()
        if reference not in fitted or not fitted[reference]["Assembly"].startswith("SMT"):
            continue
        side = footprint.GetLayer()
        layer = pcbnew.F_Fab if side == pcbnew.F_Cu else pcbnew.B_Fab
        boxes = [item.GetBoundingBox() for item in footprint.GraphicalItems()
                 if item.Type() == pcbnew.PCB_SHAPE_T and item.GetLayer() == layer]
        if not boxes:
            raise RuntimeError("Missing fabrication body: " + reference)
        bodies.append((reference, side, [min(box.GetLeft() for box in boxes), min(box.GetTop() for box in boxes),
                                        max(box.GetRight() for box in boxes), max(box.GetBottom() for box in boxes)]))
    connectors = []
    pin_checks = []
    for footprint in board.GetFootprints():
        reference = footprint.GetReference()
        if reference not in fitted or not fitted[reference]["Assembly"].startswith("THT"):
            continue
        connector_checks = []
        for pad in footprint.Pads():
            if not pad.GetDrillSize().x:
                continue
            xpos, ypos = pad.GetPosition()
            distances = []
            for name, side, box in bodies:
                if side == footprint.GetLayer():
                    continue
                left, top, right, bottom = box
                gap = math.hypot(max(left-xpos, xpos-right, 0), max(top-ypos, ypos-bottom, 0))/1e6 - pad.GetDrillSize().x/2e6
                distances.append((gap, name))
            distance, nearest = min(distances)
            connector_checks.append({"reference": reference, "pin": pad.GetNumber(), "nearest_opposite_smt_fab": nearest,
                                     "hole_edge_to_fab_mm": distance})
        pin_checks.extend(connector_checks)
        nearest = min(connector_checks, key=lambda row: row["hole_edge_to_fab_mm"])
        connectors.append({"reference": reference, "mpn": fitted[reference]["MPN"], "pin_count": len(connector_checks),
                           "component_side": "top" if footprint.GetLayer() == pcbnew.F_Cu else "bottom",
                           "solder_side": "bottom" if footprint.GetLayer() == pcbnew.F_Cu else "top",
                           "closest_pin": nearest["pin"], "nearest_opposite_smt_fab": nearest["nearest_opposite_smt_fab"],
                           "minimum_hole_edge_to_fab_mm": nearest["hole_edge_to_fab_mm"]})
    if len(connectors) != 6 or len(pin_checks) != 59:
        raise RuntimeError("Unexpected THT inventory")
    source = root / "docs/references/归档扩展板嘉立创规则自查/sources/smt-rule-62761.txt"
    if "插件引脚附近5mm内有贴片元器件，无法进行波峰焊" not in source.read_text(encoding="utf-8"):
        raise RuntimeError("Archived process rule unavailable")
    rows = []
    for unit, prefix in [("A1", ""), ("A2", "B2_")]:
        for connector in sorted(connectors, key=lambda row: row["reference"]):
            rows.append({"Unit": unit, "Reference": prefix+connector["reference"], "MPN": connector["mpn"],
                         "PinCount": connector["pin_count"], "ComponentSide": connector["component_side"],
                         "SolderSide": connector["solder_side"], "Process": "双面SMT及支撑切断分板后逐点手工焊接",
                         "BoardWideWaveAllowed": "False", "PinInPasteReflowAllowed": "False",
                         "ClosestPin": connector["closest_pin"], "NearestOppositeSMT": prefix+connector["nearest_opposite_smt_fab"],
                         "NominalHoleToFabGap_mm": format(connector["minimum_hole_edge_to_fab_mm"], ".6f"),
                         "Status": "设计工序选择；烙铁/时长/夹具/焊点质量待实际工艺确认"})
    with (EVIDENCE / "tht-soldering-plan.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    result = {"date": datetime.now().date().isoformat(), "pcb_sha256": checkpoint["pcb_sha256"],
              "panel_sha256": json.loads((EVIDENCE / "panel-verification.json").read_text(encoding="utf-8"))["panel_sha256"],
              "rule": {"source": str(source.relative_to(root)), "sha256": pipeline.digest(source), "section": "62761 second section, THT pin/SMT distance"},
              "connectors": sorted(connectors, key=lambda row: row["reference"]), "pin_checks": pin_checks,
              "all_six_connectors_have_smt_within_5mm": all(row["minimum_hole_edge_to_fab_mm"] < 5 for row in connectors),
              "selected_process": "After both SMT reflows and supported tab cutting, manually solder each THT pin locally; no board-wide wave solder or pin-in-paste reflow",
              "panel_tht_count": len(rows), "panel_tht_pin_count": sum(int(row["PinCount"]) for row in rows),
              "csv_sha256": pipeline.digest(EVIDENCE / "tht-soldering-plan.csv"),
              "limits": ["Nominal hole circle to Fab bounding-box screen, not a soldering-tool clearance measurement",
                         "Manual point soldering is a project process selection, not supplier acceptance or demonstrated solder quality",
                         "Actual tip, temperature/time, fixtures and inspection remain manufacturing-stage work"],
              "primary_unchanged": pipeline.current_checkpoint()["pcb_sha256"] == checkpoint["pcb_sha256"],
              "manufacturing_released": False, "hardware_tested": False}
    pipeline.write_json(EVIDENCE / "tht-soldering-plan.json", result)
    print(json.dumps({key: value for key, value in result.items() if key != "pin_checks"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
