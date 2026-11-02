"""Verify connector drill-only pad changes and unchanged functional routing."""
import json
from pathlib import Path
import uuid

import pipeline
from select_header_connectors import EVIDENCE, PARTS
from verify_release_metadata import snapshot


def main():
    candidate_path = EVIDENCE / "candidate.json"
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    after = pipeline.managed(Path(candidate["project"]))
    before = pipeline.prepare(pipeline.PRIMARY)
    runs = {}
    for label, project in (("before", before), ("after", after)):
        board_path = project / (pipeline.STEM + ".kicad_pcb")
        report_path = project.parent / ("header-filled-" + label + "-" + uuid.uuid4().hex[:8] + ".json")
        commands = []
        pipeline.run_command([pipeline.find_cli(), "pcb", "drc", "--format", "json", "--severity-all", "--schematic-parity",
                              "--refill-zones", "--save-board", "--output", report_path, board_path],
                             EVIDENCE, "filled-" + label, commands, report_path)
        report = json.loads(report_path.read_text(encoding="utf-8"))
        runs[label] = {"project": str(project), "pcb_sha256": pipeline.digest(board_path), "commands": commands,
                       "violations": len(report["violations"]), "unconnected": len(report["unconnected_items"]), "parity": len(report["schematic_parity"])}
    original = snapshot(before / (pipeline.STEM + ".kicad_pcb"))
    repaired = snapshot(after / (pipeline.STEM + ".kicad_pcb"))
    unexpected = []
    drills = []
    for identifier, pad in original["pads"].items():
        expected = dict(pad)
        if pad["reference"] in PARTS:
            drill = round(PARTS[pad["reference"]]["drill"] * 1000000)
            expected["drill"] = [drill, drill]
            drills.append({"reference": pad["reference"], "pin": pad["pin"], "before": pad["drill"], "after": expected["drill"]})
        if expected != repaired["pads"].get(identifier):
            unexpected.append(identifier)
    lost = {identifier: sorted(set(group) - set(repaired["connections"].get(identifier, [])))
            for identifier, group in original["connections"].items() if not set(group).issubset(repaired["connections"].get(identifier, []))}
    result = {"runs": runs, "unexpected_pad_changes": unexpected, "changed_drills": drills,
              "pad_keys_unchanged": set(original["pads"]) == set(repaired["pads"]),
              "routing_unchanged": original["tracks"] == repaired["tracks"], "nets_unchanged": original["nets"] == repaired["nets"],
              "lost_connections": lost, "production_ready": False}
    result["accepted"] = all((not unexpected, len(drills) == 53, result["pad_keys_unchanged"], result["routing_unchanged"],
                               result["nets_unchanged"], not lost, all(runs["after"][key] == 0 for key in ("violations", "unconnected", "parity"))))
    pipeline.write_json(EVIDENCE / "geometry-connectivity-check.json", result)
    if not result["accepted"]:
        raise RuntimeError("Connector geometry or connectivity check failed")
    reports, summary = pipeline.check(after)
    candidate["summary"] = str(reports / "summary.json")
    pipeline.write_json(candidate_path, candidate)
    print(json.dumps({"accepted": result["accepted"], "drills_changed": len(drills), "status": summary["status"]}))


if __name__ == "__main__":
    main()
