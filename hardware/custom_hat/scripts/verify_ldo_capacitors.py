"""Verify the explicit LDO net change and preserve every other original connection."""
import json
import math
from pathlib import Path
import uuid

import pcbnew

import pipeline
from improve_ldo_capacitors import EVIDENCE, CAP_FIELDS, RES_FIELDS
from verify_buck_control import protection
from verify_release_metadata import snapshot


def main():
    candidate_path = EVIDENCE / "candidate.json"
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    after = pipeline.managed(Path(candidate["project"]))
    before = pipeline.prepare(pipeline.PRIMARY)
    contract = json.loads((EVIDENCE / "change-contract.json").read_text(encoding="utf-8"))
    runs = {}
    for label, project in (("before", before), ("after", after)):
        board_path = project / (pipeline.STEM + ".kicad_pcb")
        report_path = project.parent / ("ldo-filled-" + label + "-" + uuid.uuid4().hex[:8] + ".json")
        commands = []
        pipeline.run_command([pipeline.find_cli(), "pcb", "drc", "--format", "json", "--severity-all", "--schematic-parity",
                              "--refill-zones", "--save-board", "--output", report_path, board_path], EVIDENCE, "filled-" + label, commands, report_path)
        report = json.loads(report_path.read_text(encoding="utf-8"))
        runs[label] = {"project": str(project), "pcb_sha256": pipeline.digest(board_path), "commands": commands,
                       "violations": len(report["violations"]), "unconnected": len(report["unconnected_items"]), "parity": len(report["schematic_parity"])}
    original = snapshot(before / (pipeline.STEM + ".kicad_pcb"))
    repaired = snapshot(after / (pipeline.STEM + ".kicad_pcb"))
    old_ids = {(pad["reference"], pad["pin"]): identifier for identifier, pad in original["pads"].items()}
    new_ids = {(pad["reference"], pad["pin"]): identifier for identifier, pad in repaired["pads"].items()}
    return_id = old_ids[("C309", "2")]
    new_return = new_ids[("R703", "1")]
    new_ground = new_ids[("R703", "2")]
    changed_pads = []
    allowed_pads = {old_ids[("C309", "1")], return_id}
    for identifier, pad in original["pads"].items():
        expected = dict(pad)
        if identifier in allowed_pads:
            center = contract["capacitor_position"]
            expected["position"] = [round((center[0] + (0.95 if pad["pin"] == "1" else -0.95)) * 1e6), round(center[1] * 1e6)]
            expected["orientation"] = 180.0
        actual = repaired["pads"].get(identifier)
        valid = actual is not None and all(expected[key] == actual[key] for key in expected if key not in {"position", "orientation"})
        valid = valid and abs((expected["orientation"] - actual["orientation"] + 180) % 360 - 180) < 1e-6
        valid = valid and all(abs(expected["position"][index] - actual["position"][index]) <= 2 for index in (0, 1))
        if not valid:
            changed_pads.append({"id": identifier, "expected": expected, "actual": actual})
    lost = {}
    for identifier, group in original["connections"].items():
        if identifier == return_id:
            continue
        missing = set(group) - {return_id} - set(repaired["connections"].get(identifier, []))
        if missing:
            lost[identifier] = sorted(missing)
    net_changes = {identifier: [net, repaired["nets"].get(identifier)] for identifier, net in original["nets"].items()
                   if repaired["nets"].get(identifier) != net}
    removed = set(original["tracks"]) - set(repaired["tracks"])
    added = set(repaired["tracks"]) - set(original["tracks"])
    changed_tracks = [identifier for identifier, track in original["tracks"].items() if identifier in repaired["tracks"] and track != repaired["tracks"][identifier]]
    old_board = pcbnew.LoadBoard(str(before / (pipeline.STEM + ".kicad_pcb")))
    board = pcbnew.LoadBoard(str(after / (pipeline.STEM + ".kicad_pcb")))
    fields = {}
    for reference, expected in (("C308", CAP_FIELDS), ("C309", CAP_FIELDS), ("R703", RES_FIELDS)):
        footprint = board.FindFootprintByReference(reference)
        fields[reference] = {key: {"expected": value, "actual": footprint.GetValue() if key == "Value" else footprint.GetFieldText(key)}
                             for key, value in expected.items()}
    geometry = {"runs": runs, "unexpected_original_pad_changes": changed_pads, "lost_connections_except_c309_return": lost,
                "original_pad_net_changes": net_changes, "added_pad_keys": sorted(set(new_ids) - set(old_ids)),
                "footprint_set_change": sorted({fp.GetReference() for fp in board.GetFootprints()} - {fp.GetReference() for fp in old_board.GetFootprints()}),
                "removed_tracks": sorted(removed), "added_tracks": sorted(added), "other_tracks_changed": changed_tracks,
                "return_isolated_to_cap_and_resistor": set(repaired["connections"].get(return_id, [])) == {return_id, new_return},
                "resistor_ground_connected_to_u702": old_ids[("U702", "2")] in repaired["connections"].get(new_ground, []),
                "values": fields, "via_process_unchanged": protection(old_board) == protection(board),
                "native_route_lengths_mm": {route["net"]: sum(math.dist(start, end) for start, end in zip(route["points"], route["points"][1:])) for route in contract["routes"]},
                "same_project_settings": pipeline.digest(before / (pipeline.STEM + ".kicad_pro")) == pipeline.digest(after / (pipeline.STEM + ".kicad_pro")),
                "same_design_rules": pipeline.digest(before / (pipeline.STEM + ".kicad_dru")) == pipeline.digest(after / (pipeline.STEM + ".kicad_dru")),
                "production_ready": False}
    geometry["accepted"] = all((not changed_pads, not lost, net_changes == {return_id: ["POWER_GND", "LDO_CAP_RETURN"]},
                                 geometry["added_pad_keys"] == [("R703", "1"), ("R703", "2")], geometry["footprint_set_change"] == ["R703"],
                                 removed == set(contract["removed_tracks"]), added == {identifier for route in contract["routes"] for identifier in route["added_tracks"]},
                                 not changed_tracks, geometry["return_isolated_to_cap_and_resistor"], geometry["resistor_ground_connected_to_u702"],
                                 all(value["expected"] == value["actual"] for component in fields.values() for value in component.values()),
                                 geometry["via_process_unchanged"], geometry["same_project_settings"], geometry["same_design_rules"],
                                 all(runs["after"][key] == 0 for key in ("violations", "unconnected", "parity"))))
    pipeline.write_json(EVIDENCE / "geometry-connectivity-check.json", geometry)
    print(json.dumps({key: value for key, value in geometry.items() if key not in {"runs", "removed_tracks", "added_tracks", "values"}}))
    if not geometry["accepted"]:
        raise RuntimeError("LDO invariants failed")
    reports, summary = pipeline.check(after)
    candidate["summary"] = str(reports / "summary.json")
    pipeline.write_json(candidate_path, candidate)


if __name__ == "__main__":
    main()
