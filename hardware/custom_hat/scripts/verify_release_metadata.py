"""Check freshly filled copper and unchanged functional pad/track geometry."""
import argparse
import json
from pathlib import Path
import subprocess

import pcbnew
import pipeline
from verify_u501_connectivity import partitions


def snapshot(path):
    board = pcbnew.LoadBoard(str(path))
    pads = {}
    names = {}
    for footprint in board.GetFootprints():
        if footprint.GetReference().startswith("FID"):
            continue
        for pad in footprint.Pads():
            identifier = pad.m_Uuid.AsString()
            position = pad.GetPosition()
            size = pad.GetSize()
            drill = pad.GetDrillSize()
            pads[identifier] = {
                "reference": footprint.GetReference(), "pin": pad.GetNumber(),
                "position": [position.x, position.y], "size": [size.x, size.y],
                "drill": [drill.x, drill.y], "shape": int(pad.GetShape()),
                "orientation": pad.GetOrientationDegrees(), "layers": pad.GetLayerSet().FmtHex(),
            }
            names[identifier] = pad.GetNetname()
    tracks = {}
    for item in board.GetTracks():
        tracks[item.m_Uuid.AsString()] = {
            "start": list(item.GetStart()), "end": list(item.GetEnd()),
            "width": item.GetFrontWidth() if item.Type() == pcbnew.PCB_VIA_T else item.GetWidth(),
            "layers": item.GetLayerSet().FmtHex(), "net": item.GetNetname(),
            "drill": item.GetDrill() if item.Type() == pcbnew.PCB_VIA_T else 0,
        }
    return {"pads": pads, "nets": names, "tracks": tracks, "connections": partitions(board)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    after = pipeline.managed(arguments.project)
    before = pipeline.prepare(pipeline.PRIMARY)
    outcomes = {}
    for label, project in (("before", before), ("after", after)):
        board_path = project / (pipeline.STEM + ".kicad_pcb")
        report_path = project.parent / ("metadata-filled-" + label + ".json")
        command = [str(pipeline.find_cli()), "pcb", "drc", "--format", "json", "--severity-all", "--schematic-parity", "--refill-zones", "--save-board", "--output", str(report_path), str(board_path)]
        subprocess.run(command, capture_output=True, check=True)
        report = json.loads(report_path.read_text(encoding="utf-8"))
        outcomes[label] = {"project": str(project), "pcb_sha256": pipeline.digest(board_path), "command": command,
                           "violations": len(report["violations"]), "unconnected": len(report["unconnected_items"]), "parity": len(report["schematic_parity"])}
    original = snapshot(before / (pipeline.STEM + ".kicad_pcb"))
    repaired = snapshot(after / (pipeline.STEM + ".kicad_pcb"))
    lost = {identifier: sorted(set(group) - set(repaired["connections"].get(identifier, [])))
            for identifier, group in original["connections"].items()
            if not set(group).issubset(repaired["connections"].get(identifier, []))}
    assigned_net_changes = {identifier: [net, repaired["nets"].get(identifier)] for identifier, net in original["nets"].items()
                            if net and net != repaired["nets"].get(identifier)}
    u701 = next(identifier for identifier, pad in repaired["pads"].items() if pad["reference"] == "U701" and pad["pin"] == "7")
    r308 = next(identifier for identifier, pad in repaired["pads"].items() if pad["reference"] == "R308" and pad["pin"] == "2")
    outcome = {"runs": outcomes, "functional_pad_geometry_unchanged": original["pads"] == repaired["pads"],
               "routing_unchanged": original["tracks"] == repaired["tracks"], "lost_connections": lost,
               "assigned_net_changes": assigned_net_changes,
               "u701_7_to_r308_2": r308 in repaired["connections"].get(u701, []),
               "functional_pad_count": len(original["pads"]), "connected_pad_count_before": len(original["connections"]),
               "production_ready": False}
    outcome["accepted"] = all((outcome["functional_pad_geometry_unchanged"], outcome["routing_unchanged"], not lost,
                               not assigned_net_changes, outcome["u701_7_to_r308_2"], outcomes["after"]["violations"] == 0,
                               outcomes["after"]["unconnected"] == 0, outcomes["after"]["parity"] == 0))
    pipeline.write_json(arguments.output, outcome)
    print(json.dumps({key: value for key, value in outcome.items() if key != "runs"}))
    if not outcome["accepted"]:
        raise SystemExit("Metadata/copper invariants failed")


if __name__ == "__main__":
    main()
