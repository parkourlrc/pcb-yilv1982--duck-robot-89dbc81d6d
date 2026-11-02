"""Verify intended header changes, preserve other connections and compare I2S reference samples."""
import csv
import json
from pathlib import Path
import subprocess
import sys
import uuid

import pcbnew

import pipeline
from add_i2c_pullups import vector
from repair_qwiic_pinout import EVIDENCE, BASELINE, NEW_NETS, REMOVE, VIA
from verify_release_metadata import snapshot
from verify_buck_control import protection


def footprint_geometry(board):
    return {footprint.GetReference(): {"position": list(footprint.GetPosition()), "angle": footprint.GetOrientationDegrees(),
            "layer": footprint.GetLayer(), "attributes": footprint.GetAttributes(), "pads": [pad.m_Uuid.AsString() for pad in footprint.Pads()]}
            for footprint in board.GetFootprints()}


def main():
    candidate_path = EVIDENCE / "candidate.json"
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    if candidate.get("promoted") or pipeline.digest(pipeline.PRIMARY / (pipeline.STEM + ".kicad_pcb")) != BASELINE:
        raise RuntimeError("Candidate verification requires the original unpromoted baseline")
    work = pipeline.managed(Path(candidate["project"]))
    before = pipeline.prepare(pipeline.PRIMARY)
    contract = json.loads((EVIDENCE / "change-contract.json").read_text(encoding="utf-8"))
    runs = {}
    for label, project in (("before", before), ("after", work)):
        board_path = project / (pipeline.STEM + ".kicad_pcb")
        report_path = project.parent / ("qwiic-filled-" + label + "-" + uuid.uuid4().hex[:8] + ".json")
        commands = []
        pipeline.run_command([pipeline.find_cli(), "pcb", "drc", "--format", "json", "--severity-all", "--schematic-parity",
                              "--refill-zones", "--save-board", "--output", report_path, board_path], EVIDENCE, "filled-" + label, commands, report_path)
        report = json.loads(report_path.read_text(encoding="utf-8"))
        runs[label] = {"project": str(project), "pcb_sha256": pipeline.digest(board_path), "commands": commands,
                       "violations": len(report["violations"]), "unconnected": len(report["unconnected_items"]), "parity": len(report["schematic_parity"])}
    old_path, new_path = before / (pipeline.STEM + ".kicad_pcb"), work / (pipeline.STEM + ".kicad_pcb")
    original, repaired = snapshot(old_path), snapshot(new_path)
    old_board, new_board = pcbnew.LoadBoard(str(old_path)), pcbnew.LoadBoard(str(new_path))
    changed_pads = {row["uuid"] for row in contract["pad_changes"]}
    expected_nets = dict(original["nets"])
    for row in contract["pad_changes"]:
        expected_nets[row["uuid"]] = row["new"]
    lost = {identifier: sorted((set(group) - changed_pads) - set(repaired["connections"].get(identifier, [])))
            for identifier, group in original["connections"].items() if identifier not in changed_pads
            and not (set(group) - changed_pads).issubset(repaired["connections"].get(identifier, []))}
    expected_tracks = {identifier: dict(row) for identifier, row in original["tracks"].items() if identifier not in REMOVE}
    expected_tracks[VIA]["start"] = list(vector((158.92, 112.1)))
    expected_tracks[VIA]["end"] = list(vector((158.92, 112.1)))
    unexpected = {identifier: repaired["tracks"].get(identifier) for identifier, row in expected_tracks.items() if repaired["tracks"].get(identifier) != row}
    added = set(repaired["tracks"]) - set(original["tracks"])
    expected_added = {identifier for route in contract["routes"] for identifier in route["added_tracks"]}
    pads = {(footprint.GetReference(), pad.GetNumber()): pad for footprint in new_board.GetFootprints() for pad in footprint.Pads()}
    anchors = {"1": [("J101", "6")], "2": [("J101", "1"), ("U701", "7"), ("U501", "3")],
               "3": [("J101", "31"), ("U701", "9"), ("U501", "9")], "4": [("J101", "29"), ("U701", "8"), ("U501", "8")]}
    pin_checks = {}
    for number, target_net in NEW_NETS.items():
        pad = pads[("J502", number)]
        group = set(repaired["connections"][pad.m_Uuid.AsString()])
        pin_checks[number] = {"net": pad.GetNetname(), "expected": target_net,
                             "anchors_connected": all(pads[anchor].m_Uuid.AsString() in group for anchor in anchors[number])}
    samples, coverage = {}, {}
    for label, project in (("before", before), ("after", work)):
        prefix = "qwiic-" + label
        completed = subprocess.run([sys.executable, "-X", "utf8", Path(__file__).with_name("inspect_i2s_reference_planes.py"),
                                    "--project", project, "--prefix", prefix, "--evidence", EVIDENCE], capture_output=True, encoding="utf-8", errors="replace")
        (EVIDENCE / (prefix + "-reference.log")).write_text(completed.stdout + completed.stderr, encoding="utf-8")
        completed.check_returncode()
        with (EVIDENCE / (prefix + "-plane-samples.csv")).open(encoding="utf-8", newline="") as stream:
            samples[label] = {(row["segment"], row["x_mm"], row["y_mm"]): row for row in csv.DictReader(stream)}
        reference = json.loads((EVIDENCE / (prefix + "-reference-check.json")).read_text(encoding="utf-8"))
        coverage[label] = {(row["net"], row["source_layer"], row["reference_copper"]): row for row in reference["coverage"]}
    lost_samples = []
    for key, row in samples["before"].items():
        for plane in ("F.Cu:POWER_GND", "In1.Cu:POWER_GND", "In2.Cu:+3V3", "B.Cu:POWER_GND"):
            if plane.split(":")[0] != row["source_layer"] and row[plane] == "True" and samples["after"].get(key, {}).get(plane) != "True":
                lost_samples.append({"segment": key[0], "net": row["net"], "point_mm": key[1:], "plane": plane, "represented_mm": row["represented_mm"]})
    delta = {"lost_samples": lost_samples, "same_sample_keys": samples["before"].keys() == samples["after"].keys(),
             "coverage": [{"net": key[0], "source_layer": key[1], "reference": key[2],
                           "before_pct": row["centerline_coverage_pct"], "after_pct": coverage["after"][key]["centerline_coverage_pct"],
                           "covered_delta_mm": coverage["after"][key]["covered_mm"] - row["covered_mm"]} for key, row in coverage["before"].items()]}
    delta["accepted"] = not lost_samples and delta["same_sample_keys"]
    pipeline.write_json(EVIDENCE / "reference-coverage-delta.json", delta)
    result = {"runs": runs, "all_original_pad_geometry_unchanged": original["pads"] == repaired["pads"],
              "all_footprint_positions_and_orientations_unchanged": footprint_geometry(old_board) == footprint_geometry(new_board),
              "only_expected_j502_net_changes": repaired["nets"] == expected_nets, "lost_non_j502_connections": lost,
              "removed_objects_match_contract": set(original["tracks"]) - set(repaired["tracks"]) == REMOVE,
              "unexpected_original_copper_changes": unexpected, "added_objects_match_contract": added == expected_added,
              "j502_pin_checks": pin_checks, "i2s_reference_samples_preserved": delta["accepted"],
              "existing_fill_cap_requirements_unchanged": protection(old_board) == protection(new_board),
              "rules_unchanged": pipeline.digest(before / (pipeline.STEM + ".kicad_dru")) == pipeline.digest(work / (pipeline.STEM + ".kicad_dru")),
              "project_settings_unchanged": pipeline.digest(before / (pipeline.STEM + ".kicad_pro")) == pipeline.digest(work / (pipeline.STEM + ".kicad_pro")),
              "revision": new_board.GetTitleBlock().GetRevision(), "marker_present": any(hasattr(item, "GetText") and item.GetText() == "DUCK HAT A.1" for item in new_board.GetDrawings()),
              "hardware_tested": False, "production_ready": False}
    result["accepted"] = all((result["all_original_pad_geometry_unchanged"], result["all_footprint_positions_and_orientations_unchanged"],
        result["only_expected_j502_net_changes"], not lost, result["removed_objects_match_contract"], not unexpected, added == expected_added,
        all(row["net"] == row["expected"] and row["anchors_connected"] for row in pin_checks.values()), delta["accepted"],
        result["existing_fill_cap_requirements_unchanged"], result["rules_unchanged"], result["project_settings_unchanged"],
        result["revision"] == "A.1", result["marker_present"], all(not runs["after"][key] for key in ("violations", "unconnected", "parity"))))
    pipeline.write_json(EVIDENCE / "geometry-connectivity-check.json", result)
    print(json.dumps({key: value for key, value in result.items() if key != "runs"}))
    if not result["accepted"]:
        raise RuntimeError("Qwiic candidate failed verification")
    reports, summary = pipeline.check(work)
    candidate["summary"] = str(reports / "summary.json")
    pipeline.write_json(candidate_path, candidate)


if __name__ == "__main__":
    main()
