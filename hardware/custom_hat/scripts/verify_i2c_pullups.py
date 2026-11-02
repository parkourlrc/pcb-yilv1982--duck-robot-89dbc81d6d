"""Check additive I2C repair against saved, freshly filled copper."""
import json
from pathlib import Path
import shutil

import pipeline
from add_i2c_pullups import EVIDENCE
from verify_release_metadata import snapshot


def main():
    candidate = json.loads((EVIDENCE / "candidate.json").read_text(encoding="utf-8"))
    after = pipeline.managed(Path(candidate["project"]))
    before = pipeline.prepare(pipeline.PRIMARY)
    outcomes = {}
    for label, project in (("before", before), ("after", after)):
        board_path = project / (pipeline.STEM + ".kicad_pcb")
        report_path = project.parent / ("i2c-filled-" + label + ".json")
        commands = []
        pipeline.run_command([pipeline.find_cli(), "pcb", "drc", "--format", "json", "--severity-all", "--schematic-parity", "--refill-zones", "--save-board", "--output", report_path, board_path],
                             EVIDENCE, "filled-" + label, commands, report_path)
        report = json.loads(report_path.read_text(encoding="utf-8"))
        outcomes[label] = {"project": str(project), "pcb_sha256": pipeline.digest(board_path), "commands": commands,
                           "violations": len(report["violations"]), "unconnected": len(report["unconnected_items"]), "parity": len(report["schematic_parity"])}
    original = snapshot(before / (pipeline.STEM + ".kicad_pcb"))
    repaired = snapshot(after / (pipeline.STEM + ".kicad_pcb"))
    lost = {identifier: sorted(set(group) - set(repaired["connections"].get(identifier, [])))
            for identifier, group in original["connections"].items() if not set(group).issubset(repaired["connections"].get(identifier, []))}
    changed_pads = [identifier for identifier, pad in original["pads"].items() if repaired["pads"].get(identifier) != pad]
    changed_tracks = [identifier for identifier, track in original["tracks"].items() if repaired["tracks"].get(identifier) != track]
    changed_nets = [identifier for identifier, net in original["nets"].items() if repaired["nets"].get(identifier) != net]
    new_pads = {identifier: pad for identifier, pad in repaired["pads"].items() if identifier not in original["pads"]}
    target_checks = {}
    for identifier, pad in new_pads.items():
        name = pad["reference"] + "." + pad["pin"]
        net = repaired["nets"][identifier]
        expected = "+3V3" if pad["pin"] == "1" else ("I2C5_SCL" if pad["reference"] == "R501" else "I2C5_SDA")
        original_targets = {other for other, old_net in original["nets"].items() if old_net == expected}
        target_checks[name] = {"net": net, "expected_net": expected, "all_existing_same_net_pads_connected": original_targets.issubset(repaired["connections"].get(identifier, []))}
    u701 = next(identifier for identifier, pad in repaired["pads"].items() if pad["reference"] == "U701" and pad["pin"] == "7")
    r308 = next(identifier for identifier, pad in repaired["pads"].items() if pad["reference"] == "R308" and pad["pin"] == "2")
    result = {"runs": outcomes, "changed_original_pad_geometry": changed_pads, "changed_original_tracks": changed_tracks,
              "changed_original_nets": changed_nets, "lost_connections": lost, "new_pads": new_pads, "target_checks": target_checks,
              "u701_7_to_r308_2": r308 in repaired["connections"].get(u701, []), "production_ready": False}
    result["accepted"] = not any((changed_pads, changed_tracks, changed_nets, lost)) and len(new_pads) == 4
    result["accepted"] = result["accepted"] and set(target_checks) == {"R501.1", "R501.2", "R502.1", "R502.2"}
    result["accepted"] = result["accepted"] and all(check["net"] == check["expected_net"] and check["all_existing_same_net_pads_connected"] for check in target_checks.values())
    result["accepted"] = result["accepted"] and all(outcomes["after"][key] == 0 for key in ("violations", "unconnected", "parity")) and result["u701_7_to_r308_2"]
    pipeline.write_json(EVIDENCE / "geometry-connectivity-check.json", result)
    if not result["accepted"]:
        raise RuntimeError("Additive connectivity verification failed")
    reports, summary = pipeline.check(after)
    candidate["summary"] = str(reports / "summary.json")
    pipeline.write_json(EVIDENCE / "candidate.json", candidate)
    shutil.copy2(reports / "summary.json", EVIDENCE / "candidate-summary.json")
    print(json.dumps({"accepted": result["accepted"], "summary": str(reports / "summary.json"), "status": summary["status"], "drc": summary["drc"], "target_checks": target_checks}))


if __name__ == "__main__":
    main()
