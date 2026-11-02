"""Verify a two-via relocation with unchanged pads and retained connections."""
import json
import uuid
from pathlib import Path

import pcbnew
import pipeline
from repair_cap_vias import EVIDENCE, TARGETS
from verify_release_metadata import snapshot


def main():
    candidate = json.loads((EVIDENCE / "candidate.json").read_text(encoding="utf-8"))
    after = pipeline.managed(Path(candidate["project"]))
    before = pipeline.prepare(pipeline.PRIMARY)
    outcomes = {}
    run_id = uuid.uuid4().hex[:8]
    for label, project in (("before", before), ("after", after)):
        board_path = project / (pipeline.STEM + ".kicad_pcb")
        report_path = project.parent / ("cap-vias-filled-" + label + "-" + run_id + ".json")
        commands = []
        pipeline.run_command([pipeline.find_cli(), "pcb", "drc", "--format", "json", "--severity-all", "--schematic-parity", "--refill-zones", "--save-board", "--output", report_path, board_path],
                             EVIDENCE, "filled-" + label + "-" + run_id, commands, report_path)
        report = json.loads(report_path.read_text(encoding="utf-8"))
        outcomes[label] = {"project": str(project), "pcb_sha256": pipeline.digest(board_path), "commands": commands,
                           "violations": len(report["violations"]), "unconnected": len(report["unconnected_items"]), "parity": len(report["schematic_parity"])}
    original = snapshot(before / (pipeline.STEM + ".kicad_pcb"))
    repaired = snapshot(after / (pipeline.STEM + ".kicad_pcb"))
    lost = {identifier: sorted(set(group) - set(repaired["connections"].get(identifier, [])))
            for identifier, group in original["connections"].items() if not set(group).issubset(repaired["connections"].get(identifier, []))}
    changed = {identifier for identifier, track in original["tracks"].items() if repaired["tracks"].get(identifier) != track}
    allowed = {identifier for target in TARGETS for identifier in (target[2], target[5])}
    board = pcbnew.LoadBoard(str(after / (pipeline.STEM + ".kicad_pcb")))
    mask_clearances = {}
    for reference, number, identifier, _, _, _ in TARGETS:
        via = next(item for item in board.GetTracks() if item.m_Uuid.AsString() == identifier)
        nearest = []
        mask_gaps = []
        for footprint in board.GetFootprints():
            for pad in footprint.Pads():
                if not (pad.IsOnLayer(pcbnew.F_Mask) or pad.IsOnLayer(pcbnew.B_Mask)):
                    continue
                bounds = pad.GetBoundingBox()
                xpos, ypos = via.GetPosition()
                delta_x = max(bounds.GetLeft() - xpos, 0, xpos - bounds.GetRight())
                delta_y = max(bounds.GetTop() - ypos, 0, ypos - bounds.GetBottom())
                distance = (delta_x ** 2 + delta_y ** 2) ** 0.5
                edge_gap = pcbnew.ToMM(distance - via.GetFrontWidth() / 2)
                nearest.append((edge_gap, footprint.GetReference(), pad.GetNumber()))
                expansion = max(pad.GetSolderMaskExpansion(layer) for layer in (pcbnew.F_Mask, pcbnew.B_Mask) if pad.IsOnLayer(layer))
                mask_gaps.append((edge_gap - pcbnew.ToMM(expansion), footprint.GetReference(), pad.GetNumber(), pcbnew.ToMM(expansion)))
        mask_clearances[reference] = {"nearest_pad_copper_bbox_gap_mm": min(nearest), "nearest_mask_bbox_gap_mm": min(mask_gaps)}
    result = {"runs": outcomes, "pad_geometry_unchanged": original["pads"] == repaired["pads"],
              "pad_nets_unchanged": original["nets"] == repaired["nets"], "changed_original_tracks": sorted(changed),
              "allowed_changes": sorted(allowed), "lost_connections": lost, "via_to_pad_clearances": mask_clearances, "production_ready": False}
    result["accepted"] = result["pad_geometry_unchanged"] and result["pad_nets_unchanged"] and changed == allowed and not lost
    result["accepted"] = result["accepted"] and all(value["nearest_mask_bbox_gap_mm"][0] > 0.05 for value in mask_clearances.values())
    result["accepted"] = result["accepted"] and all(outcomes["after"][key] == 0 for key in ("violations", "unconnected", "parity"))
    pipeline.write_json(EVIDENCE / "geometry-connectivity-check.json", result)
    if not result["accepted"]:
        raise RuntimeError("Capacitor-via verification failed")
    reports, summary = pipeline.check(after)
    candidate["summary"] = str(reports / "summary.json")
    pipeline.write_json(EVIDENCE / "candidate.json", candidate)
    print(json.dumps({"accepted": result["accepted"], "status": summary["status"], "clearances": mask_clearances}))


if __name__ == "__main__":
    main()
