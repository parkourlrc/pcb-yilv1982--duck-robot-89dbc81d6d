"""Validate the two TTL bypass additions against original geometry and filled copper."""
import json
import math
from pathlib import Path
import uuid

import pcbnew

import pipeline
from add_ttl_local_bypass import EVIDENCE, PARTS, FIELDS
from verify_release_metadata import snapshot
from verify_buck_control import protection


def main():
    candidate_path = EVIDENCE / "candidate.json"
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    after = pipeline.managed(Path(candidate["project"]))
    before = pipeline.prepare(pipeline.PRIMARY)
    contract = json.loads((EVIDENCE / "ttl-route-contract.json").read_text(encoding="utf-8"))
    runs = {}
    for label, project in (("before", before), ("after", after)):
        path = project / (pipeline.STEM + ".kicad_pcb")
        report_path = project.parent / ("ttl-filled-" + label + "-" + uuid.uuid4().hex[:8] + ".json")
        commands = []
        pipeline.run_command([pipeline.find_cli(), "pcb", "drc", "--format", "json", "--severity-all", "--schematic-parity", "--refill-zones", "--save-board", "--output", report_path, path],
                             EVIDENCE, "filled-" + label, commands, report_path)
        report = json.loads(report_path.read_text(encoding="utf-8"))
        runs[label] = {"project": str(project), "pcb_sha256": pipeline.digest(path), "commands": commands,
                       "violations": len(report["violations"]), "unconnected": len(report["unconnected_items"]), "parity": len(report["schematic_parity"])}
    original = snapshot(before / (pipeline.STEM + ".kicad_pcb"))
    repaired = snapshot(after / (pipeline.STEM + ".kicad_pcb"))
    unexpected_pads = {identifier: repaired["pads"].get(identifier) for identifier, old in original["pads"].items() if repaired["pads"].get(identifier) != old}
    unexpected_tracks = {identifier: repaired["tracks"].get(identifier) for identifier, old in original["tracks"].items() if repaired["tracks"].get(identifier) != old}
    net_changes = {identifier: repaired["nets"].get(identifier) for identifier, net in original["nets"].items() if repaired["nets"].get(identifier) != net}
    lost = {identifier: sorted(set(group) - set(repaired["connections"].get(identifier, []))) for identifier, group in original["connections"].items()
            if not set(group).issubset(repaired["connections"].get(identifier, []))}
    new_keys = sorted((pad["reference"], pad["pin"]) for identifier, pad in repaired["pads"].items() if identifier not in original["pads"])
    added = set(repaired["tracks"]) - set(original["tracks"])
    expected_added = {identifier for part in contract["parts"] for route in part["routes"] for identifier in route["added_tracks"]}
    expected_added.update(part["ground_via"]["uuid"] for part in contract["parts"])
    old_board = pcbnew.LoadBoard(str(before / (pipeline.STEM + ".kicad_pcb")))
    board = pcbnew.LoadBoard(str(after / (pipeline.STEM + ".kicad_pcb")))
    tracks = {item.m_Uuid.AsString(): item for item in board.GetTracks()}
    pads = {(fp.GetReference(), pad.GetNumber()): pad for fp in board.GetFootprints() for pad in fp.Pads()}
    local = []
    for part in contract["parts"]:
        reference, device = part["reference"], part["device"]
        footprint = board.FindFootprintByReference(reference)
        via = tracks[part["ground_via"]["uuid"]]
        contacts = {board.GetLayerName(layer): any(zone.GetFilledPolysList(layer).Contains(via.GetPosition()) for zone in board.Zones()
                                                 if zone.IsOnLayer(layer) and zone.GetNetname() == "POWER_GND")
                    for layer in (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.B_Cu)}
        connections = {}
        for cap_pin, device_pin in (("1", "5"), ("2", "3")):
            cap_id, device_id = pads[(reference, cap_pin)].m_Uuid.AsString(), pads[(device, device_pin)].m_Uuid.AsString()
            connections[cap_pin + "_to_" + device_pin] = device_id in repaired["connections"].get(cap_id, [])
        gaps = []
        for pad in footprint.Pads():
            bounds = pad.GetBoundingBox()
            for item in tracks.values():
                if item.Type() != pcbnew.PCB_VIA_T or not item.IsOnLayer(pcbnew.B_Cu):
                    continue
                point = item.GetPosition()
                distance = math.hypot(max(bounds.GetLeft() - point.x, 0, point.x - bounds.GetRight()), max(bounds.GetTop() - point.y, 0, point.y - bounds.GetBottom()))
                gaps.append(pcbnew.ToMM(distance - item.GetFrontWidth() / 2 - pad.GetSolderMaskExpansion(pcbnew.B_Mask)))
        fields_match = all(footprint.GetFieldText(key) == value for key, value in FIELDS.items())
        local.append({"reference": reference, "device": device, "position": [pcbnew.ToMM(value) for value in footprint.GetPosition()],
                      "value": footprint.GetValue(), "layer": board.GetLayerName(footprint.GetLayer()), "fields_match": fields_match,
                      "connections": connections, "ground_via_contacts": contacts, "minimum_mask_to_via_copper_gap_mm": min(gaps),
                      "ground_via_valid": via.GetNetname() == "POWER_GND" and via.GetViaType() == pcbnew.VIATYPE_THROUGH and via.GetFrontWidth() == 600000 and via.GetDrill() == 300000,
                      "routes": [{key: route[key] for key in ("net", "layer", "width_mm", "length_mm")} for route in part["routes"]]})
    old_footprints = {fp.GetReference() for fp in old_board.GetFootprints()}
    new_footprints = {fp.GetReference() for fp in board.GetFootprints()}
    unchanged_files = {suffix: pipeline.digest(before / (pipeline.STEM + suffix)) == pipeline.digest(after / (pipeline.STEM + suffix)) for suffix in (".kicad_pro", ".kicad_dru")}
    result = {"runs": runs, "unexpected_original_pad_changes": unexpected_pads, "unexpected_original_copper_changes": unexpected_tracks,
              "original_pad_net_changes": net_changes, "lost_pad_connections": lost, "new_pad_keys": new_keys,
              "added_footprints": sorted(new_footprints - old_footprints), "removed_footprints": sorted(old_footprints - new_footprints),
              "added_objects_match_contract": added == expected_added, "original_filled_capped_vias_preserved": protection(old_board) == protection(board),
              "project_and_rules_unchanged": unchanged_files, "local_checks": local,
              "counts": {"footprints": len(new_footprints), "segments": sum(item.Type() != pcbnew.PCB_VIA_T for item in tracks.values()),
                         "vias": sum(item.Type() == pcbnew.PCB_VIA_T for item in tracks.values()),
                         "ground_vias": sum(item.Type() == pcbnew.PCB_VIA_T and item.GetNetname() == "POWER_GND" for item in tracks.values())},
              "hardware_tested": False, "production_ready": False}
    result["accepted"] = all((not unexpected_pads, not unexpected_tracks, not net_changes, not lost,
        new_keys == [("C329", "1"), ("C329", "2"), ("C330", "1"), ("C330", "2")],
        new_footprints - old_footprints == set(PARTS), not old_footprints - new_footprints, added == expected_added,
        result["original_filled_capped_vias_preserved"], all(unchanged_files.values()),
        all(not runs["after"][key] for key in ("violations", "unconnected", "parity")),
        all(row["fields_match"] and all(row["connections"].values()) and row["ground_via_valid"] and row["ground_via_contacts"]["In1.Cu"]
            and row["minimum_mask_to_via_copper_gap_mm"] >= .1 and row["value"] == "100nF" and row["layer"] == "B.Cu" for row in local)))
    pipeline.write_json(EVIDENCE / "geometry-connectivity-check.json", result)
    print(json.dumps({key: result[key] for key in ("accepted", "counts", "local_checks", "unexpected_original_pad_changes", "unexpected_original_copper_changes", "lost_pad_connections")}))
    if not result["accepted"]:
        raise SystemExit("TTL local acceptance failed")
    reports, summary = pipeline.check(after)
    candidate["summary"] = str(reports / "summary.json")
    pipeline.write_json(candidate_path, candidate)
    print(json.dumps({"status": summary["status"], "summary": candidate["summary"]}))


if __name__ == "__main__":
    main()
