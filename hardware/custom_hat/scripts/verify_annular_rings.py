"""Verify enlarged rings, original connectivity and explicit changed-object bounds."""
import json
from pathlib import Path
import uuid

import pcbnew
import pipeline
from improve_via_annular_rings import EVIDENCE
from verify_release_metadata import snapshot


def main():
    candidate_path = EVIDENCE / "candidate.json"
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    work = pipeline.managed(Path(candidate["project"]))
    rules_path = work / (pipeline.STEM + ".kicad_dru")
    rules = rules_path.read_text(encoding="utf-8")
    rule_name = "Manufacturing through-via annular ring"
    if rule_name not in rules:
        rules = "\n".join(row for row in rules.splitlines() if not row.startswith("# prototype fabrication:") and not row.startswith("# 3V3 plane from"))
        rules += '\n(rule "Manufacturing through-via annular ring"\n  (condition "A.Type == \'Via\' && A.Via_Type == \'Through\'")\n  (constraint annular_width (min 0.125mm))\n)\n'
        rules_path.write_text(rules, encoding="utf-8")
    project_file = pipeline.STEM + ".kicad_pro"
    if pipeline.digest(work / project_file) != pipeline.digest(pipeline.PRIMARY / project_file):
        raise RuntimeError("Project settings differ from primary")
    before = pipeline.prepare(pipeline.PRIMARY)
    runs = {}
    for label, project in (("before", before), ("after", work)):
        board_path = project / (pipeline.STEM + ".kicad_pcb")
        output = project.parent / ("ring-filled-" + label + "-" + uuid.uuid4().hex[:8] + ".json")
        commands = []
        pipeline.run_command([pipeline.find_cli(), "pcb", "drc", "--format", "json", "--severity-all", "--schematic-parity",
                              "--refill-zones", "--save-board", "--output", output, board_path], EVIDENCE, "filled-" + label, commands, output)
        report = json.loads(output.read_text(encoding="utf-8"))
        runs[label] = {"project": str(project), "pcb_sha256": pipeline.digest(board_path), "commands": commands,
                       "violations": len(report["violations"]), "unconnected": len(report["unconnected_items"]), "parity": len(report["schematic_parity"])}
    original = snapshot(before / (pipeline.STEM + ".kicad_pcb"))
    repaired = snapshot(work / (pipeline.STEM + ".kicad_pcb"))
    changes = json.loads((EVIDENCE / "changes.json").read_text(encoding="utf-8"))
    shifts = json.loads((EVIDENCE / "shifts.json").read_text(encoding="utf-8"))
    detour = json.loads((EVIDENCE / "mclk-detour.json").read_text(encoding="utf-8"))
    stitch = json.loads((EVIDENCE / "ground-stitch.json").read_text(encoding="utf-8"))
    allowed = {item["uuid"] for item in changes} | {identifier for shift in shifts for identifier in shift["attached_tracks"]} | {detour["changed_track"]}
    changed = {identifier for identifier, track in original["tracks"].items() if repaired["tracks"].get(identifier) != track}
    added = set(repaired["tracks"]) - set(original["tracks"])
    expected_added = set(detour["added_tracks"]) | {stitch["uuid"]}
    lost = {identifier: sorted(set(group) - set(repaired["connections"].get(identifier, [])))
            for identifier, group in original["connections"].items() if not set(group).issubset(repaired["connections"].get(identifier, []))}
    board = pcbnew.LoadBoard(str(work / (pipeline.STEM + ".kicad_pcb")))
    vias = [item for item in board.GetTracks() if item.Type() == pcbnew.PCB_VIA_T]
    through_rings = [pcbnew.ToMM(via.GetFrontWidth()-via.GetDrill())/2 for via in vias if via.GetViaType() == pcbnew.VIATYPE_THROUGH]
    ground_via = next(via for via in vias if via.m_Uuid.AsString() == stitch["uuid"])
    gaps = []
    for footprint in board.GetFootprints():
        for pad in footprint.Pads():
            bounds = pad.GetBoundingBox()
            point = ground_via.GetPosition()
            distance = (max(bounds.GetLeft()-point.x, 0, point.x-bounds.GetRight())**2
                        + max(bounds.GetTop()-point.y, 0, point.y-bounds.GetBottom())**2)**0.5
            mask_layers = [layer for layer in (pcbnew.F_Mask, pcbnew.B_Mask) if pad.IsOnLayer(layer)]
            if mask_layers:
                expansion = max(pad.GetSolderMaskExpansion(layer) for layer in mask_layers)
                gaps.append((pcbnew.ToMM(distance-ground_via.GetFrontWidth()/2-expansion), footprint.GetReference(), pad.GetNumber()))
    result = {"runs": runs, "pad_geometry_unchanged": original["pads"] == repaired["pads"], "pad_nets_unchanged": original["nets"] == repaired["nets"],
              "changed_original_tracks": sorted(changed), "allowed_changed_tracks": sorted(allowed), "added_tracks": sorted(added),
              "expected_added_tracks": sorted(expected_added), "lost_connections": lost,
              "through_via_count": len(through_rings), "minimum_through_via_annular_mm": min(through_rings),
              "ground_stitch_mask_bbox_gap_mm": min(gaps), "project_settings_unchanged": pipeline.digest(work/project_file) == pipeline.digest(pipeline.PRIMARY/project_file),
              "production_ready": False}
    result["accepted"] = all((result["pad_geometry_unchanged"], result["pad_nets_unchanged"], changed == allowed, added == expected_added,
                               not lost, min(through_rings) >= 0.125, min(gaps)[0] > 0.05, result["project_settings_unchanged"],
                               all(runs["after"][key] == 0 for key in ("violations", "unconnected", "parity"))))
    pipeline.write_json(EVIDENCE / "geometry-connectivity-check.json", result)
    if not result["accepted"]:
        raise RuntimeError("Ring repair verification failed")
    reports, summary = pipeline.check(work)
    candidate["summary"] = str(reports / "summary.json")
    pipeline.write_json(candidate_path, candidate)
    print(json.dumps({key: value for key, value in result.items() if key not in {"runs", "changed_original_tracks", "allowed_changed_tracks", "added_tracks", "expected_added_tracks"}}))


if __name__ == "__main__":
    main()
