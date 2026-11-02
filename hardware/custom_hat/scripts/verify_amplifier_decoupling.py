"""Verify local amplifier decoupling, the moved feed via, and all original pad connections."""
import json
import math
from pathlib import Path
import uuid

import pcbnew

import pipeline
from improve_amplifier_decoupling import EVIDENCE, BULK_FIELDS, BYPASS_FIELDS, POWER_VIA
from verify_buck_control import protection
from verify_release_metadata import snapshot
from fix_amp_schematic_presentation import electrical_project_settings


def main():
    candidate_path = EVIDENCE / "candidate.json"
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    after = pipeline.managed(Path(candidate["project"]))
    before = pipeline.prepare(pipeline.PRIMARY)
    contract = json.loads((EVIDENCE / "amp-route-contract.json").read_text(encoding="utf-8"))
    runs = {}
    for label, project in (("before", before), ("after", after)):
        path = project / (pipeline.STEM + ".kicad_pcb")
        report_path = project.parent / ("amp-filled-" + label + "-" + uuid.uuid4().hex[:8] + ".json")
        commands = []
        pipeline.run_command([pipeline.find_cli(), "pcb", "drc", "--format", "json", "--severity-all", "--schematic-parity", "--refill-zones", "--save-board", "--output", report_path, path],
                             EVIDENCE, "filled-" + label, commands, report_path)
        report = json.loads(report_path.read_text(encoding="utf-8"))
        runs[label] = {"project": str(project), "pcb_sha256": pipeline.digest(path), "commands": commands,
                       "violations": len(report["violations"]), "unconnected": len(report["unconnected_items"]), "parity": len(report["schematic_parity"])}
    original = snapshot(before / (pipeline.STEM + ".kicad_pcb"))
    repaired = snapshot(after / (pipeline.STEM + ".kicad_pcb"))
    library = pipeline.find_cli().parent.parent / "share/kicad/footprints/Capacitor_SMD.pretty"
    template = pcbnew.FootprintLoad(str(library), "C_1210_3225Metric")
    front_layers = next(iter(template.Pads())).GetLayerSet().FmtHex()
    unexpected_pads = []
    for identifier, old in original["pads"].items():
        expected = dict(old)
        if old["reference"] == "C323":
            center = contract["bulk_position"]
            expected.update(position=[round(center[0] * 1e6), round((center[1] + (-1.475 if old["pin"] == "1" else 1.475)) * 1e6)],
                            size=[1150000, 2700000], orientation=270.0, layers=front_layers)
        actual = repaired["pads"].get(identifier)
        valid = actual is not None and all(expected[key] == actual[key] for key in expected if key not in {"position", "orientation"})
        valid = valid and abs((expected["orientation"] - actual["orientation"] + 180) % 360 - 180) < 1e-6
        valid = valid and all(abs(expected["position"][axis] - actual["position"][axis]) <= 2 for axis in (0, 1))
        if not valid:
            unexpected_pads.append({"id": identifier, "expected": expected, "actual": actual})
    old_keys = {(pad["reference"], pad["pin"]) for pad in original["pads"].values()}
    new_keys = {(pad["reference"], pad["pin"]) for pad in repaired["pads"].values()}
    old_net_changes = {identifier: [net, repaired["nets"].get(identifier)] for identifier, net in original["nets"].items() if repaired["nets"].get(identifier) != net}
    lost = {identifier: sorted(set(group) - set(repaired["connections"].get(identifier, []))) for identifier, group in original["connections"].items()
            if not set(group).issubset(repaired["connections"].get(identifier, []))}
    removed = set(original["tracks"]) - set(repaired["tracks"])
    added = set(repaired["tracks"]) - set(original["tracks"])
    unexpected_tracks = []
    modified = []
    for identifier, old in original["tracks"].items():
        if identifier in removed:
            continue
        expected = dict(old)
        if identifier == POWER_VIA:
            position = [round(value * 1e6) for value in contract["power_via_after"]]
            expected.update(start=position, end=position)
        actual = repaired["tracks"][identifier]
        if actual != old:
            modified.append(identifier)
        valid = all(expected[key] == actual[key] for key in expected if key not in {"start", "end"})
        valid = valid and all(abs(expected[key][axis] - actual[key][axis]) <= 2 for key in ("start", "end") for axis in (0, 1))
        if not valid:
            unexpected_tracks.append({"id": identifier, "expected": expected, "actual": actual})
    old_board = pcbnew.LoadBoard(str(before / (pipeline.STEM + ".kicad_pcb")))
    board = pcbnew.LoadBoard(str(after / (pipeline.STEM + ".kicad_pcb")))
    values = {}
    for reference, fields in (("C323", BULK_FIELDS), ("C328", BYPASS_FIELDS)):
        footprint = board.FindFootprintByReference(reference)
        values[reference] = {key: {"expected": expected, "actual": footprint.GetValue() if key == "Value" else
                                  str(footprint.GetFPID().GetLibNickname()) + ":" + str(footprint.GetFPID().GetLibItemName()) if key == "Footprint" else footprint.GetFieldText(key)}
                             for key, expected in fields.items()}
    via_lookup = {item.m_Uuid.AsString(): item for item in board.GetTracks() if item.Type() == pcbnew.PCB_VIA_T}
    ground_via = via_lookup[contract["new_ground_via"]]
    ground_contacts = {board.GetLayerName(layer): any(zone.GetFilledPolysList(layer).Contains(ground_via.GetPosition()) for zone in board.Zones()
                                                    if zone.IsOnLayer(layer) and zone.GetNetname() == "POWER_GND")
                       for layer in (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.B_Cu)}
    gaps = {}
    for reference in ("C323", "C328"):
        distances = []
        for pad in board.FindFootprintByReference(reference).Pads():
            bounds = pad.GetBoundingBox()
            for via in via_lookup.values():
                if not via.IsOnLayer(pcbnew.F_Cu):
                    continue
                point = via.GetPosition()
                distance = math.hypot(max(bounds.GetLeft() - point.x, 0, point.x - bounds.GetRight()), max(bounds.GetTop() - point.y, 0, point.y - bounds.GetBottom()))
                distances.append(pcbnew.ToMM(distance - via.GetFrontWidth() / 2 - pad.GetSolderMaskExpansion(pcbnew.F_Mask)))
        gaps[reference] = min(distances)
    route_lengths = [{"net": route["net"], "layer": route["layer"], "planar_length_mm": sum(math.dist(start, end) for start, end in zip(route["points"], route["points"][1:]))}
                     for route in contract["routes"]]
    power_front = next(route for route in contract["routes"] if route["net"] == "+5V" and route["layer"] == "F.Cu")
    power_back = next(row["planar_length_mm"] for row in route_lengths if row["net"] == "+5V" and row["layer"] == "B.Cu")
    footprint_added = sorted({fp.GetReference() for fp in board.GetFootprints()} - {fp.GetReference() for fp in old_board.GetFootprints()})
    result = {"runs": runs, "unexpected_original_pad_changes": unexpected_pads, "new_pad_keys": sorted(new_keys - old_keys), "added_footprints": footprint_added,
              "original_pad_net_changes": old_net_changes, "lost_pad_connections": lost, "removed_objects": sorted(removed), "added_objects": sorted(added),
              "modified_original_objects": modified, "unexpected_original_track_changes": unexpected_tracks,
              "component_fields": values, "cap_mask_bbox_to_via_copper_gap_mm": gaps, "new_ground_via_contacts": ground_contacts,
              "new_ground_via_valid": ground_via.GetNetname() == "POWER_GND" and ground_via.GetViaType() == pcbnew.VIATYPE_THROUGH and ground_via.GetFrontWidth() == 600000 and ground_via.GetDrill() == 300000,
              "protected_vias_preserved": protection(old_board) == protection(board), "routes": route_lengths,
              "vdd_to_bypass_planar_trace_mm": power_back + math.dist(power_front["points"][0], power_front["points"][1]),
              "vdd_to_bulk_planar_trace_mm": power_back + sum(math.dist(start, end) for start, end in zip(power_front["points"], power_front["points"][1:])),
              "local_path_layer_transitions": "One through-via in VDD path and one in ground return; planar lengths exclude barrel length,ESL andparallel plane current paths",
              "project_electrical_settings_preserved": electrical_project_settings(json.loads((before / (pipeline.STEM + ".kicad_pro")).read_text(encoding="utf-8"))) == electrical_project_settings(json.loads((after / (pipeline.STEM + ".kicad_pro")).read_text(encoding="utf-8"))),
              "project_presentation_review": json.loads((EVIDENCE / "presentation-change.json").read_text(encoding="utf-8")) if (EVIDENCE / "presentation-change.json").exists() else None,
              "rules_preserved": pipeline.digest(before / (pipeline.STEM + ".kicad_dru")) == pipeline.digest(after / (pipeline.STEM + ".kicad_dru")),
              "production_ready": False, "hardware_measured": False}
    expected_added = {identifier for route in contract["routes"] for identifier in route["added_tracks"]} | {contract["new_ground_via"]}
    result["accepted"] = all((not unexpected_pads, new_keys - old_keys == {("C328", "1"), ("C328", "2")}, footprint_added == ["C328"],
                              not old_net_changes, not lost, removed == set(contract["removed_objects"]), added == expected_added,
                              modified == [POWER_VIA], not unexpected_tracks, all(item["actual"] == item["expected"] for fields in values.values() for item in fields.values()),
                              all(value > 0.08 for value in gaps.values()), all(ground_contacts.values()), result["new_ground_via_valid"], result["protected_vias_preserved"],
                              result["project_electrical_settings_preserved"], result["rules_preserved"],
                              all(runs["after"][key] == 0 for key in ("violations", "unconnected", "parity"))))
    pipeline.write_json(EVIDENCE / "geometry-connectivity-check.json", result)
    print(json.dumps({key: value for key, value in result.items() if key not in {"runs", "component_fields", "removed_objects", "added_objects"}}))
    if not result["accepted"]:
        raise RuntimeError("Amplifier geometry/connectivity verification failed")
    reports, summary = pipeline.check(after)
    candidate["summary"] = str(reports / "summary.json")
    pipeline.write_json(candidate_path, candidate)


if __name__ == "__main__":
    main()
