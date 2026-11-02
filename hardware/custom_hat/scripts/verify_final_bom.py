"""Verify the final eight choices, four land changes and bounded local rerouting."""
import json
from pathlib import Path
import uuid

import pcbnew
import pipeline
from select_final_bom import EVIDENCE, PARTS
from verify_release_metadata import snapshot


def main():
    candidate_path = EVIDENCE / "candidate.json"
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    after = pipeline.managed(Path(candidate["project"]))
    before = pipeline.prepare(pipeline.PRIMARY)
    runs = {}
    for label, project in (("before", before), ("after", after)):
        board_path = project / (pipeline.STEM + ".kicad_pcb")
        output = project.parent / ("bom-filled-" + label + "-" + uuid.uuid4().hex[:8] + ".json")
        commands = []
        pipeline.run_command([pipeline.find_cli(), "pcb", "drc", "--format", "json", "--severity-all", "--schematic-parity",
                              "--refill-zones", "--save-board", "--output", output, board_path], EVIDENCE, "filled-" + label, commands, output)
        report = json.loads(output.read_text(encoding="utf-8"))
        runs[label] = {"project": str(project), "pcb_sha256": pipeline.digest(board_path), "commands": commands,
                       "violations": len(report["violations"]), "unconnected": len(report["unconnected_items"]), "parity": len(report["schematic_parity"])}
    original = snapshot(before / (pipeline.STEM + ".kicad_pcb"))
    repaired = snapshot(after / (pipeline.STEM + ".kicad_pcb"))
    expected_positions = {("L301", "1"): [133529500, 115900000], ("L301", "2"): [142470500, 115900000],
                          ("R309", "1"): [117240000, 120865000], ("R309", "2"): [117240000, 118535000]}
    unexpected = []
    changed_pads = []
    for identifier, pad in original["pads"].items():
        expected = dict(pad)
        key = (pad["reference"], pad["pin"])
        if key in expected_positions:
            expected["position"] = expected_positions[key]
            expected["size"] = [3124000, 3251000] if key[0] == "L301" else [1570000, 1780000]
            expected["shape"] = int(pcbnew.PAD_SHAPE_RECT)
            changed_pads.append(key)
        if expected != repaired["pads"].get(identifier):
            unexpected.append({"key": key, "expected": expected, "actual": repaired["pads"].get(identifier)})
    moves = json.loads((EVIDENCE / "power-footprint-via-moves.json").read_text(encoding="utf-8"))
    route = json.loads((EVIDENCE / "audio-branch-route.json").read_text(encoding="utf-8"))
    allowed = {entry["via"] for entry in moves} | {identifier for entry in moves for identifier in entry["attached_tracks"]}
    changed = {identifier for identifier, track in original["tracks"].items() if repaired["tracks"].get(identifier) != track}
    added = set(repaired["tracks"])-set(original["tracks"])
    lost = {identifier: sorted(set(group)-set(repaired["connections"].get(identifier, [])))
            for identifier, group in original["connections"].items() if not set(group).issubset(repaired["connections"].get(identifier, []))}
    board = pcbnew.LoadBoard(str(after / (pipeline.STEM + ".kicad_pcb")))
    fields = {reference: board.FindFootprintByReference(reference).GetFieldText("MPN") for reference in PARTS}
    result = {"runs": runs, "unexpected_pad_geometry": unexpected, "changed_pad_keys": changed_pads,
              "pad_keys_unchanged": set(original["pads"]) == set(repaired["pads"]), "pad_nets_unchanged": original["nets"] == repaired["nets"],
              "changed_original_tracks": sorted(changed), "allowed_changed_tracks": sorted(allowed),
              "added_tracks": sorted(added), "expected_added_tracks": route["added_tracks"], "lost_connections": lost, "selected_mpns": fields,
              "project_settings_unchanged": pipeline.digest(after/(pipeline.STEM+".kicad_pro")) == pipeline.digest(pipeline.PRIMARY/(pipeline.STEM+".kicad_pro")),
              "rules_unchanged": pipeline.digest(after/(pipeline.STEM+".kicad_dru")) == pipeline.digest(pipeline.PRIMARY/(pipeline.STEM+".kicad_dru")),
              "production_ready": False}
    result["accepted"] = all((not unexpected, len(changed_pads)==4, result["pad_keys_unchanged"], result["pad_nets_unchanged"],
                               changed == allowed, added == set(route["added_tracks"]), not lost,
                               all(fields[reference] == part[0] for reference, part in PARTS.items()),
                               result["project_settings_unchanged"], result["rules_unchanged"],
                               all(runs["after"][key] == 0 for key in ("violations","unconnected","parity"))))
    pipeline.write_json(EVIDENCE / "geometry-connectivity-check.json", result)
    if not result["accepted"]:
        raise RuntimeError("BOM geometry or connectivity verification failed")
    reports, summary = pipeline.check(after)
    candidate["summary"] = str(reports/"summary.json")
    pipeline.write_json(candidate_path, candidate)
    print(json.dumps({"accepted": result["accepted"], "changed_pads": changed_pads, "lost_connections": len(lost), "status": summary["status"]}))


if __name__ == "__main__":
    main()
