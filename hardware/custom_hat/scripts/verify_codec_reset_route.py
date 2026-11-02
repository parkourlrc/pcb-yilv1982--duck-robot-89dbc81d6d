"""Verify the reset GPIO branch, the single intentional NC change and old connectivity."""
import json
import math
import csv
from pathlib import Path
import subprocess
import sys
import uuid

import pcbnew

import pipeline
from connect_codec_hardware_reset import EVIDENCE
from verify_release_metadata import snapshot
from verify_buck_control import protection


def main():
    candidate_path = EVIDENCE / "candidate.json"
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    after = pipeline.managed(Path(candidate["project"]))
    before = pipeline.prepare(pipeline.PRIMARY)
    contract = json.loads((EVIDENCE / "change-contract.json").read_text(encoding="utf-8"))
    header_pin = str(contract.get("header_pin", 36))
    runs = {}
    for label, project in (("before", before), ("after", after)):
        path = project / (pipeline.STEM + ".kicad_pcb")
        report_path = project.parent / ("reset-filled-" + label + "-" + uuid.uuid4().hex[:8] + ".json")
        commands = []
        pipeline.run_command([pipeline.find_cli(), "pcb", "drc", "--format", "json", "--severity-all", "--schematic-parity", "--refill-zones", "--save-board", "--output", report_path, path],
                             EVIDENCE, "filled-" + label, commands, report_path)
        report = json.loads(report_path.read_text(encoding="utf-8"))
        runs[label] = {"project": str(project), "pcb_sha256": pipeline.digest(path), "commands": commands,
                       "violations": len(report["violations"]), "unconnected": len(report["unconnected_items"]), "parity": len(report["schematic_parity"])}
    original = snapshot(before / (pipeline.STEM + ".kicad_pcb"))
    repaired = snapshot(after / (pipeline.STEM + ".kicad_pcb"))
    expected_nets = dict(original["nets"])
    expected_nets[contract["header_pad_uuid"]] = "CODEC_RST"
    lost = {identifier: sorted(set(group) - set(repaired["connections"].get(identifier, []))) for identifier, group in original["connections"].items()
            if not set(group).issubset(repaired["connections"].get(identifier, []))}
    old_copper_changes = {identifier: repaired["tracks"].get(identifier) for identifier, values in original["tracks"].items() if repaired["tracks"].get(identifier) != values}
    added = set(repaired["tracks"]) - set(original["tracks"])
    expected_added = {identifier for route in contract["routes"] for identifier in route["added_tracks"]}
    expected_added.update(via["uuid"] for via in contract["new_vias"])
    board = pcbnew.LoadBoard(str(after / (pipeline.STEM + ".kicad_pcb")))
    old_board = pcbnew.LoadBoard(str(before / (pipeline.STEM + ".kicad_pcb")))
    pads = {(footprint.GetReference(), pad.GetNumber()): pad for footprint in board.GetFootprints() for pad in footprint.Pads()}
    reset_ids = {pads[(reference, number)].m_Uuid.AsString() for reference, number in (("J101", header_pin), ("R308", "1"), ("U701", "31"))}
    actual_group = set(repaired["connections"][contract["header_pad_uuid"]])
    new_via_checks = []
    for entry in contract["new_vias"]:
        via = next(item for item in board.GetTracks() if item.m_Uuid.AsString() == entry["uuid"])
        gaps = []
        for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
            for pad in pads.values():
                if not pad.IsOnLayer(layer):
                    continue
                bounds = pad.GetBoundingBox()
                point = via.GetPosition()
                distance = math.hypot(max(bounds.GetLeft() - point.x, 0, point.x - bounds.GetRight()), max(bounds.GetTop() - point.y, 0, point.y - bounds.GetBottom()))
                mask_layer = pcbnew.F_Mask if layer == pcbnew.F_Cu else pcbnew.B_Mask
                gaps.append(pcbnew.ToMM(distance - via.GetFrontWidth() / 2 - pad.GetSolderMaskExpansion(mask_layer)))
        new_via_checks.append({"uuid": entry["uuid"], "net": via.GetNetname(), "through": via.GetViaType() == pcbnew.VIATYPE_THROUGH,
                               "diameter_mm": pcbnew.ToMM(via.GetFrontWidth()), "drill_mm": pcbnew.ToMM(via.GetDrill()),
                               "minimum_pad_mask_bbox_gap_mm": min(gaps)})
    result = {"runs": runs, "all_original_pad_geometry_unchanged": original["pads"] == repaired["pads"],
              "only_expected_header_net_change": repaired["nets"] == expected_nets, "all_original_copper_unchanged": not old_copper_changes,
              "unexpected_original_copper_changes": old_copper_changes, "added_objects_match_contract": added == expected_added,
              "lost_original_connections": lost, "header_to_codec_and_pullup_connected": reset_ids.issubset(actual_group),
              "header_pin_type": pads[("J101", header_pin)].GetPinType(), "new_via_checks": new_via_checks,
              "existing_fill_cap_requirements_unchanged": protection(board) == protection(old_board),
              "rules_unchanged": pipeline.digest(after / (pipeline.STEM + ".kicad_dru")) == pipeline.digest(before / (pipeline.STEM + ".kicad_dru")),
              "project_settings_unchanged": pipeline.digest(after / (pipeline.STEM + ".kicad_pro")) == pipeline.digest(before / (pipeline.STEM + ".kicad_pro")),
              "hardware_tested": False, "production_ready": False}
    result["accepted"] = all((result["all_original_pad_geometry_unchanged"], result["only_expected_header_net_change"], not old_copper_changes,
        added == expected_added, not lost, result["header_to_codec_and_pullup_connected"], result["header_pin_type"] == "passive",
        result["existing_fill_cap_requirements_unchanged"], result["rules_unchanged"], result["project_settings_unchanged"],
        all(row["through"] and row["net"] == "CODEC_RST" and row["diameter_mm"] == .55 and row["drill_mm"] == .3 and row["minimum_pad_mask_bbox_gap_mm"] >= .1 for row in new_via_checks),
        all(not runs["after"][key] for key in ("violations", "unconnected", "parity"))))
    samples, coverage = {}, {}
    for label, project in (("before", before), ("after", after)):
        prefix = "reset-" + label
        completed = subprocess.run([sys.executable, "-X", "utf8", Path(__file__).with_name("inspect_i2s_reference_planes.py"),
                                    "--project", project, "--prefix", prefix, "--evidence", EVIDENCE],
                                   capture_output=True, text=True, encoding="utf-8", errors="replace")
        (EVIDENCE / (prefix + "-reference.log")).write_text(completed.stdout + completed.stderr, encoding="utf-8")
        completed.check_returncode()
        with (EVIDENCE / (prefix + "-plane-samples.csv")).open(encoding="utf-8", newline="") as stream:
            samples[label] = {(row["segment"], row["x_mm"], row["y_mm"]): row for row in csv.DictReader(stream)}
        reference = json.loads((EVIDENCE / (prefix + "-reference-check.json")).read_text(encoding="utf-8"))
        coverage[label] = {(row["net"], row["source_layer"], row["reference_copper"]): row for row in reference["coverage"]}
    lost_samples = []
    for key, row in samples["before"].items():
        for plane in ("F.Cu:POWER_GND", "In1.Cu:POWER_GND", "In2.Cu:+3V3", "B.Cu:POWER_GND"):
            if plane.split(":")[0] == row["source_layer"]:
                continue
            if row[plane] == "True" and samples["after"].get(key, {}).get(plane) != "True":
                lost_samples.append({"segment": key[0], "net": row["net"], "point_mm": key[1:], "plane": plane,
                                     "represented_mm": float(row["represented_mm"])})
    reference_delta = {"before_pcb_sha256": runs["before"]["pcb_sha256"], "after_pcb_sha256": runs["after"]["pcb_sha256"],
                       "same_sample_keys": samples["before"].keys() == samples["after"].keys(), "lost_samples": lost_samples,
                       "coverage": [{"net": key[0], "source_layer": key[1], "reference_copper": key[2],
                                     "before_pct": value["centerline_coverage_pct"], "after_pct": coverage["after"][key]["centerline_coverage_pct"],
                                     "covered_delta_mm": coverage["after"][key]["covered_mm"] - value["covered_mm"]}
                                    for key, value in coverage["before"].items()],
                       "limit": "Saved filled-zone centerline samples at <=0.025mm; not a return-impedance or EMI test"}
    reference_delta["accepted"] = reference_delta["same_sample_keys"] and not lost_samples
    pipeline.write_json(EVIDENCE / "reference-coverage-delta.json", reference_delta)
    result["i2s_reference_samples_preserved"] = reference_delta["accepted"]
    result["accepted"] = result["accepted"] and reference_delta["accepted"]
    pipeline.write_json(EVIDENCE / "geometry-connectivity-check.json", result)
    print(json.dumps({key: value for key, value in result.items() if key != "runs"}))
    if not result["accepted"]:
        raise RuntimeError("Reset-branch acceptance failed")
    reports, summary = pipeline.check(after)
    candidate["summary"] = str(reports / "summary.json")
    pipeline.write_json(candidate_path, candidate)
    print(summary["status"])


if __name__ == "__main__":
    main()
