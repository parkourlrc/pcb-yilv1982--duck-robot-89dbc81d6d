"""Verify one audio detour and one ground stitch without changing signal endpoints."""
import json
from pathlib import Path
import uuid

import pcbnew

import pipeline
from stitch_i2s_reference_pocket import EVIDENCE, coverage
from verify_buck_control import protection
from verify_release_metadata import snapshot


def ground_map(board, label, new_via):
    paths = []
    for zone in board.Zones():
        if not zone.IsOnLayer(pcbnew.F_Cu) or zone.GetNetname() != "POWER_GND":
            continue
        shape = zone.GetFilledPolysList(pcbnew.F_Cu)
        for index in range(shape.OutlineCount()):
            outline = shape.Outline(index)
            points = [(pcbnew.ToMM(outline.CPoint(point).x), pcbnew.ToMM(outline.CPoint(point).y)) for point in range(outline.PointCount())]
            paths.append("M " + " L ".join(f"{xpos},{ypos}" for xpos, ypos in points) + " Z")
    body = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="147 103 8 14" width="320" height="560">',
            '<rect x="147" y="103" width="8" height="14" fill="white"/>',
            '<path d="' + " ".join(paths) + '" fill="#b7d9c2" fill-rule="evenodd"/>']
    for item in board.GetTracks():
        if item.Type() != pcbnew.PCB_VIA_T and item.GetNetname() == "I2S_LRCK" and item.GetLayer() == pcbnew.In1_Cu:
            start, end = item.GetStart(), item.GetEnd()
            body.append(f'<path d="M{pcbnew.ToMM(start.x)},{pcbnew.ToMM(start.y)} L{pcbnew.ToMM(end.x)},{pcbnew.ToMM(end.y)}" fill="none" stroke="#7143ac" stroke-width="0.13"/>')
        if item.Type() == pcbnew.PCB_VIA_T and item.m_Uuid.AsString() == new_via:
            point = item.GetPosition()
            body.append(f'<circle cx="{pcbnew.ToMM(point.x)}" cy="{pcbnew.ToMM(point.y)}" r="0.30" fill="#145c38"/>')
            body.append(f'<circle cx="{pcbnew.ToMM(point.x)}" cy="{pcbnew.ToMM(point.y)}" r="0.15" fill="white"/>')
    body.append("</svg>")
    (EVIDENCE / ("ground-map-" + label + ".svg")).write_text("\n".join(body), encoding="utf-8")


def main():
    candidate_path = EVIDENCE / "candidate.json"
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    after = pipeline.managed(Path(candidate["project"]))
    before = pipeline.prepare(pipeline.PRIMARY)
    contract = json.loads((EVIDENCE / "stitch-contract.json").read_text(encoding="utf-8"))
    runs = {}
    for label, project in (("before", before), ("after", after)):
        path = project / (pipeline.STEM + ".kicad_pcb")
        output = project.parent / ("reference-stitch-" + label + "-" + uuid.uuid4().hex[:8] + ".json")
        commands = []
        pipeline.run_command([pipeline.find_cli(), "pcb", "drc", "--format", "json", "--severity-all", "--schematic-parity", "--refill-zones", "--save-board", "--output", output, path],
                             EVIDENCE, "native-" + label, commands, output)
        report = json.loads(output.read_text(encoding="utf-8"))
        runs[label] = {"project": str(project), "pcb_sha256": pipeline.digest(path), "commands": commands,
                       "violations": len(report["violations"]), "unconnected": len(report["unconnected_items"]), "parity": len(report["schematic_parity"])}
    original = snapshot(before / (pipeline.STEM + ".kicad_pcb"))
    repaired = snapshot(after / (pipeline.STEM + ".kicad_pcb"))
    lost = {identifier: sorted(set(group) - set(repaired["connections"].get(identifier, []))) for identifier, group in original["connections"].items()
            if not set(group).issubset(repaired["connections"].get(identifier, []))}
    removed = set(original["tracks"]) - set(repaired["tracks"])
    added = set(repaired["tracks"]) - set(original["tracks"])
    changed = [identifier for identifier, track in original["tracks"].items() if identifier in repaired["tracks"] and repaired["tracks"][identifier] != track]
    old_board = pcbnew.LoadBoard(str(before / (pipeline.STEM + ".kicad_pcb")))
    board = pcbnew.LoadBoard(str(after / (pipeline.STEM + ".kicad_pcb")))
    new_via = next(item for item in board.GetTracks() if item.m_Uuid.AsString() == contract["new_via"])
    contacts = {board.GetLayerName(layer): any(zone.GetFilledPolysList(layer).Contains(new_via.GetPosition()) for zone in board.Zones()
                                             if zone.IsOnLayer(layer) and zone.GetNetname() == "POWER_GND")
                for layer in (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.B_Cu)}
    new_objects_valid = all(item["net"] == "AUDIO_HP_L" and item["width"] == 250000 and item["drill"] == 0
                            for identifier, item in repaired["tracks"].items() if identifier in added and identifier != contract["new_via"])
    new_via_valid = new_via.GetNetname() == "POWER_GND" and new_via.GetViaType() == pcbnew.VIATYPE_THROUGH and new_via.GetFrontWidth() == 600000 and new_via.GetDrill() == 300000
    ground_map(old_board, "before", contract["new_via"])
    ground_map(board, "after", contract["new_via"])
    result = {"runs": runs, "all_original_pad_geometry_equal": original["pads"] == repaired["pads"], "all_pad_nets_equal": original["nets"] == repaired["nets"],
              "lost_pad_connections": lost, "removed_tracks": sorted(removed), "added_tracks": sorted(added), "changed_other_tracks": changed,
              "new_audio_objects_valid": new_objects_valid, "new_via_geometry_valid": new_via_valid, "new_via_ground_plane_contacts": contacts,
              "process_requirements_unchanged": protection(old_board) == protection(board), "coverage_before": coverage(old_board), "coverage_after": coverage(board),
              "unchanged_other_design_files": all(pipeline.digest(after / name) == digest for name, digest in pipeline.fingerprints(before).items() if name != pipeline.STEM + ".kicad_pcb"),
              "production_ready": False}
    result["accepted"] = all((result["all_original_pad_geometry_equal"], result["all_pad_nets_equal"], not lost,
                              removed == set(contract["removed_tracks"]), added == set(contract["added_tracks"]), not changed,
                              new_objects_valid, new_via_valid, all(contacts.values()), result["process_requirements_unchanged"],
                              result["coverage_after"]["ground_covered_mm"] > result["coverage_before"]["ground_covered_mm"] + 1.3,
                              result["unchanged_other_design_files"], all(runs["after"][key] == 0 for key in ("violations", "unconnected", "parity"))))
    pipeline.write_json(EVIDENCE / "geometry-connectivity-check.json", result)
    print(json.dumps({key: value for key, value in result.items() if key not in {"runs", "removed_tracks", "added_tracks"}}))
    if not result["accepted"]:
        raise RuntimeError("Reference-stitch verification failed")
    reports, summary = pipeline.check(after)
    candidate["summary"] = str(reports / "summary.json")
    pipeline.write_json(candidate_path, candidate)


if __name__ == "__main__":
    main()
