"""Verify the main 5V feed while keeping pad topology and feedback copper intact."""
import json
from pathlib import Path
import uuid

import pcbnew

import pipeline
from inspect_five_volt_paths import EVIDENCE
from verify_buck_control import protection
from verify_release_metadata import snapshot


def main():
    candidate_path = EVIDENCE / "candidate.json"
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    after = pipeline.managed(Path(candidate["project"]))
    before = pipeline.prepare(pipeline.PRIMARY)
    contract = json.loads((EVIDENCE / "header-route-contract.json").read_text(encoding="utf-8"))
    runs = {}
    for label, project in (("before", before), ("after", after)):
        path = project / (pipeline.STEM + ".kicad_pcb")
        output = project.parent / ("five-volt-" + label + "-" + uuid.uuid4().hex[:8] + ".json")
        commands = []
        pipeline.run_command([pipeline.find_cli(), "pcb", "drc", "--format", "json", "--severity-all", "--schematic-parity", "--refill-zones", "--save-board", "--output", output, path],
                             EVIDENCE, "filled-" + label, commands, output)
        data = json.loads(output.read_text(encoding="utf-8"))
        runs[label] = {"project": str(project), "pcb_sha256": pipeline.digest(path), "commands": commands,
                       "violations": len(data["violations"]), "unconnected": len(data["unconnected_items"]), "parity": len(data["schematic_parity"])}
    original = snapshot(before / (pipeline.STEM + ".kicad_pcb"))
    repaired = snapshot(after / (pipeline.STEM + ".kicad_pcb"))
    changes = {entry["id"]: entry for entry in contract["changes"]}
    removed = set(original["tracks"]) - set(repaired["tracks"])
    added = set(repaired["tracks"]) - set(original["tracks"])
    unexpected = []
    modified = []
    for identifier, old in original["tracks"].items():
        if identifier in removed:
            continue
        expected = dict(old)
        if identifier in changes:
            planned = changes[identifier]["after"]
            if planned is None:
                raise RuntimeError("A removed trunk segment unexpectedly remains")
            expected["start"] = [round(value * 1e6) for value in planned["start"]]
            expected["end"] = [round(value * 1e6) for value in planned["end"]]
            expected["width"] = round(planned["width_mm"] * 1e6)
        actual = repaired["tracks"][identifier]
        if actual != old:
            modified.append(identifier)
        valid = all(expected[key] == actual[key] for key in expected if key not in {"start", "end"})
        valid = valid and all(abs(expected[key][axis] - actual[key][axis]) <= 2 for key in ("start", "end") for axis in (0, 1))
        if not valid:
            unexpected.append({"id": identifier, "expected": expected, "actual": actual})
    lost = {identifier: sorted(set(group) - set(repaired["connections"].get(identifier, []))) for identifier, group in original["connections"].items()
            if not set(group).issubset(repaired["connections"].get(identifier, []))}
    old_board = pcbnew.LoadBoard(str(before / (pipeline.STEM + ".kicad_pcb")))
    board = pcbnew.LoadBoard(str(after / (pipeline.STEM + ".kicad_pcb")))
    new_objects_valid = all(item.Type() != pcbnew.PCB_VIA_T and item.GetLayer() == pcbnew.In1_Cu and item.GetNetname() == "+5V" and item.GetWidth() == 1200000
                            for item in board.GetTracks() if item.m_Uuid.AsString() in added)
    front_original = {item.m_Uuid.AsString(): original["tracks"][item.m_Uuid.AsString()] for item in old_board.GetTracks() if item.GetNetname() == "+5V" and item.IsOnLayer(pcbnew.F_Cu)}
    front_new = {item.m_Uuid.AsString(): repaired["tracks"][item.m_Uuid.AsString()] for item in board.GetTracks() if item.GetNetname() == "+5V" and item.IsOnLayer(pcbnew.F_Cu)}
    result = {"runs": runs, "all_pad_geometry_preserved": original["pads"] == repaired["pads"], "all_pad_nets_preserved": original["nets"] == repaired["nets"],
              "lost_pad_connections": lost, "unexpected_track_changes": unexpected, "modified_original_tracks": modified,
              "removed_tracks": sorted(removed), "added_tracks": sorted(added), "new_trunk_objects_valid": new_objects_valid,
              "all_front_5v_copper_including_sense_preserved": front_original == front_new,
              "capacitor_leaf_restored_unchanged": original["tracks"][contract["restored_unchanged_leaf"]] == repaired["tracks"][contract["restored_unchanged_leaf"]],
              "via_process_preserved": protection(old_board) == protection(board),
              "unchanged_other_design_files": all(pipeline.digest(after / name) == digest for name, digest in pipeline.fingerprints(before).items() if name != pipeline.STEM + ".kicad_pcb"),
              "production_ready": False, "hardware_measured": False}
    result["accepted"] = all((result["all_pad_geometry_preserved"], result["all_pad_nets_preserved"], not lost, not unexpected,
                              set(modified) == set(changes) - removed, removed == set(contract["removed_tracks"]), added == set(contract["added_tracks"]),
                              new_objects_valid, result["all_front_5v_copper_including_sense_preserved"], result["capacitor_leaf_restored_unchanged"],
                              result["via_process_preserved"], result["unchanged_other_design_files"],
                              all(runs["after"][key] == 0 for key in ("violations", "unconnected", "parity"))))
    pipeline.write_json(EVIDENCE / "geometry-connectivity-check.json", result)
    print(json.dumps({key: value for key, value in result.items() if key != "runs"}))
    if not result["accepted"]:
        raise RuntimeError("5V header verification failed")
    reports, summary = pipeline.check(after)
    candidate["summary"] = str(reports / "summary.json")
    pipeline.write_json(candidate_path, candidate)


if __name__ == "__main__":
    main()
