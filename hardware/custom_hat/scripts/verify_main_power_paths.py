"""Verify all original connections and the bounded set of widened power conductors."""
import json
from pathlib import Path
import uuid

import pcbnew

import pipeline
from verify_buck_control import protection
from verify_release_metadata import snapshot
from widen_main_power_paths import EVIDENCE


def main():
    candidate_path = EVIDENCE / "candidate.json"
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    after = pipeline.managed(Path(candidate["project"]))
    before = pipeline.prepare(pipeline.PRIMARY)
    contract = json.loads((EVIDENCE / "power-route-contract.json").read_text(encoding="utf-8"))
    runs = {}
    for label, project in (("before", before), ("after", after)):
        path = project / (pipeline.STEM + ".kicad_pcb")
        report = project.parent / ("power-filled-" + label + "-" + uuid.uuid4().hex[:8] + ".json")
        commands = []
        pipeline.run_command([pipeline.find_cli(), "pcb", "drc", "--format", "json", "--severity-all", "--schematic-parity", "--refill-zones", "--save-board", "--output", report, path],
                             EVIDENCE, "filled-" + label, commands, report)
        data = json.loads(report.read_text(encoding="utf-8"))
        runs[label] = {"project": str(project), "pcb_sha256": pipeline.digest(path), "commands": commands,
                       "violations": len(data["violations"]), "unconnected": len(data["unconnected_items"]), "parity": len(data["schematic_parity"])}
    original = snapshot(before / (pipeline.STEM + ".kicad_pcb"))
    repaired = snapshot(after / (pipeline.STEM + ".kicad_pcb"))
    changes = {entry["id"]: entry for entry in contract["changes"]}
    removed = set(original["tracks"]) - set(repaired["tracks"])
    added = set(repaired["tracks"]) - set(original["tracks"])
    unexpected = []
    actual_changes = []
    for identifier, item in original["tracks"].items():
        if identifier in removed:
            continue
        expected = dict(item)
        if identifier in changes:
            planned = changes[identifier]["after"]
            if planned is None:
                raise RuntimeError("Expected removed trace still exists")
            expected["start"] = [round(value * 1e6) for value in planned["start"]]
            expected["end"] = [round(value * 1e6) for value in planned["end"]]
            expected["width"] = round(planned["width_mm"] * 1e6)
        actual = repaired["tracks"][identifier]
        if actual != item:
            actual_changes.append(identifier)
        valid = all(expected[key] == actual[key] for key in expected if key not in {"start", "end"})
        valid = valid and all(abs(expected[key][axis] - actual[key][axis]) <= 2 for key in ("start", "end") for axis in (0, 1))
        if not valid:
            unexpected.append({"id": identifier, "expected": expected, "actual": actual})
    lost = {identifier: sorted(set(group) - set(repaired["connections"].get(identifier, []))) for identifier, group in original["connections"].items()
            if not set(group).issubset(repaired["connections"].get(identifier, []))}
    old_board = pcbnew.LoadBoard(str(before / (pipeline.STEM + ".kicad_pcb")))
    board = pcbnew.LoadBoard(str(after / (pipeline.STEM + ".kicad_pcb")))
    new_tracks = [item for item in board.GetTracks() if item.m_Uuid.AsString() in added]
    new_tracks_valid = all(item.Type() != pcbnew.PCB_VIA_T and item.GetLayer() == pcbnew.In1_Cu and item.GetNetname() == "SERVO_VBAT" and item.GetWidth() == 1200000 for item in new_tracks)
    original_branch_ids = {entry["id"] for entry in contract["changes"] if entry["net"] == "SERVO_VBAT"} - removed
    full_servo_widths = sorted({item.GetWidth() for item in board.GetTracks() if item.Type() != pcbnew.PCB_VIA_T and item.GetNetname() == "SERVO_VBAT"})
    result = {"runs": runs, "all_pad_geometry_preserved": original["pads"] == repaired["pads"], "all_pad_nets_preserved": original["nets"] == repaired["nets"],
              "lost_pad_connections": lost, "unexpected_track_changes": unexpected, "modified_original_tracks": actual_changes,
              "removed_tracks": sorted(removed), "added_tracks": sorted(added), "new_tracks_valid": new_tracks_valid,
              "servo_track_widths_nm": full_servo_widths, "all_servo_objects_accounted_for": original_branch_ids | added == {item.m_Uuid.AsString() for item in board.GetTracks() if item.GetNetname() == "SERVO_VBAT"},
              "via_process_preserved": protection(old_board) == protection(board),
              "unchanged_other_design_files": all(pipeline.digest(after / name) == digest for name, digest in pipeline.fingerprints(before).items() if name != pipeline.STEM + ".kicad_pcb"),
              "production_ready": False, "current_rating_validated": False}
    result["accepted"] = all((result["all_pad_geometry_preserved"], result["all_pad_nets_preserved"], not lost, not unexpected,
                              set(actual_changes) == set(changes) - removed, removed == set(contract["removed_tracks"]), added == set(contract["added_tracks"]),
                              new_tracks_valid, full_servo_widths == [1200000], result["all_servo_objects_accounted_for"], result["via_process_preserved"],
                              result["unchanged_other_design_files"], all(runs["after"][key] == 0 for key in ("violations", "unconnected", "parity"))))
    pipeline.write_json(EVIDENCE / "geometry-connectivity-check.json", result)
    print(json.dumps({key: value for key, value in result.items() if key != "runs"}))
    if not result["accepted"]:
        raise RuntimeError("Power path verification failed")
    reports, summary = pipeline.check(after)
    candidate["summary"] = str(reports / "summary.json")
    pipeline.write_json(candidate_path, candidate)


if __name__ == "__main__":
    main()
