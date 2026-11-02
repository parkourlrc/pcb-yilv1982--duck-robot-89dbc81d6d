"""Separate overlapping header and TTL labels without changing the pin contract."""
import json
import argparse
from pathlib import Path

import pipeline
from generate_rev_a import Sheet, children, dump, first, parse, uid
from repair_release_metadata import properties, replace_children


EVIDENCE = pipeline.BASE.parents[1] / "docs/references/hat-simulation-tools-20261029/codec-reset-20261031"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resume-check", action="store_true")
    parser.add_argument("--refine", action="store_true")
    arguments = parser.parse_args()
    pipeline.find_cli()
    candidate_path = EVIDENCE / "candidate.json"
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    if candidate.get("promoted") or ((EVIDENCE / "schematic-display-changes.json").exists() and not arguments.refine):
        raise RuntimeError("Inspect existing schematic display changes")
    project = pipeline.managed(Path(candidate["project"]))
    if arguments.refine:
        path = project / "servo_ttl.kicad_sch"
        tree = parse(path.read_text(encoding="utf-8"))
        for label in children(tree, "global_label"):
            location = first(label, "at")
            point = tuple(float(value) for value in location[1:3])
            if point in ((185.42, 35.56), (234.95, 35.56)):
                location[2] = 38.1
            if label[1] == "DXL_DIR" and point in ((190.5, 41.91), (240.03, 41.91)):
                location[3] = 0
                justification = first(first(label, "effects"), "justify")
                if justification:
                    justification[1:] = ["left"]
        for wire in children(tree, "wire"):
            for point in first(wire, "pts")[1:]:
                if tuple(float(value) for value in point[1:3]) in ((185.42, 35.56), (234.95, 35.56)):
                    point[2] = 38.1
        duplicate = next(node for node in children(tree, "global_label") if first(node, "uuid")[1] == "4d5293d6-e2fd-5805-9b23-f5009191770c")
        tree.remove(duplicate)
        sheet = Sheet("servo_ttl", "Shared DATA net presentation")
        sheet.counter = 6100
        sheet.wire((210.82, 59.69), (217.17, 59.69))
        sheet.tree.append(["junction", ["at", 210.82, 59.69], ["diameter", 0], ["color", 0, 0, 0, 0],
                           ["uuid", str(uid("servo_ttl:shared_data_junction:reset_review"))]])
        tree.extend(node for node in sheet.tree if isinstance(node, list) and node[0] in {"wire", "junction"})
        for symbol in children(tree, "symbol"):
            if properties(symbol).get("Reference") not in {"J401", "J402", "J403"}:
                continue
            position = first(symbol, "at")
            for field in children(symbol, "property"):
                if field[1] in ("Reference", "Value"):
                    first(field, "at")[1:3] = [float(position[1]) + 12.7, float(position[2]) - (2.54 if field[1] == "Reference" else 0)]
        path.write_text("\n".join(line.rstrip() for line in dump(tree).splitlines()) + "\n", encoding="utf-8")
        reports, summary = pipeline.check(project)
        record_path = EVIDENCE / "schematic-display-changes.json"
        record = json.loads(record_path.read_text(encoding="utf-8"))
        record["refinements"] = ["clear the explanatory note", "orient OE labels away from VCC wires", "join the same DATA net with one label and a junction", "move connector fields clear of pins"]
        record["summary"], record["accepted"] = str(reports / "summary.json"), summary["status"] == "checks_clean_not_manufacturing_release"
        pipeline.write_json(record_path, record)
        candidate["summary"] = record["summary"]
        pipeline.write_json(candidate_path, candidate)
        if not record["accepted"]:
            raise RuntimeError("Refined presentation failed checks")
        return
    if arguments.resume_check:
        backups = [EVIDENCE / (name + "-before-display.kicad_sch") for name in ("radxa_40p", "servo_ttl")]
        if not all(path.is_file() for path in backups):
            raise RuntimeError("Display backups are required")
        reports, summary = pipeline.check(project)
        accepted = summary["status"] == "checks_clean_not_manufacturing_release"
        pipeline.write_json(EVIDENCE / "schematic-display-changes.json", {
            "resumed_after_cli_lookup_failure": True, "backups": {path.name: pipeline.digest(path) for path in backups},
            "changes": ["J101 reference/value above the header", "U801/U802 reference/value outside symbols",
                        "stagger +3V3/OE and ground labels", "move one DXL_DATA label down with a right-angle wire extension"],
            "summary": str(reports / "summary.json"), "accepted": accepted})
        candidate["summary"] = str(reports / "summary.json")
        pipeline.write_json(candidate_path, candidate)
        if not accepted:
            raise RuntimeError("Display check failed")
        print(summary["status"])
        return
    changes = {}
    for name, positions in (("radxa_40p", {"J101": ((127, 59.69), (127, 62.23))}),
                            ("servo_ttl", {"U801": ((199.39, 48.26), (199.39, 50.8)),
                                           "U802": ((248.92, 48.26), (248.92, 50.8))})):
        path = project / (name + ".kicad_sch")
        original = path.read_text(encoding="utf-8")
        (EVIDENCE / (name + "-before-display.kicad_sch")).write_text(original, encoding="utf-8")
        def properties_only(node):
            reference = properties(node).get("Reference")
            if reference not in positions:
                return False
            for field in children(node, "property"):
                if field[1] in ("Reference", "Value"):
                    location = positions[reference][field[1] == "Value"]
                    first(field, "at")[1:3] = list(location)
            return True
        updated = replace_children(original, "symbol", properties_only)
        if name == "servo_ttl":
            relocations = {(185.42, 41.91): (185.42, 35.56), (234.95, 41.91): (234.95, 35.56),
                           (234.95, 77.47): (234.95, 73.66), (210.82, 59.69): (210.82, 67.31)}
            moved = []
            def label(node):
                location = first(node, "at")
                point = tuple(float(value) for value in location[1:3])
                if point not in relocations:
                    return False
                location[1:3] = list(relocations[point])
                moved.append({"name": node[1], "from": point, "to": relocations[point]})
                return True
            updated = replace_children(updated, "global_label", label)
            if len(moved) != 4:
                raise RuntimeError("Unexpected number of label positions")
            def wire(node):
                changed = False
                for point in first(node, "pts")[1:]:
                    position = tuple(float(value) for value in point[1:3])
                    if position in relocations and position != (210.82, 59.69):
                        point[1:3] = list(relocations[position])
                        changed = True
                return changed
            updated = replace_children(updated, "wire", wire)
            sheet = Sheet("servo_ttl", "Label presentation repair")
            sheet.counter = 6000
            sheet.wire((210.82, 59.69), (210.82, 67.31))
            closing = updated.rfind(")")
            updated = updated[:closing] + "\n" + "\n".join(dump(node, 1) for node in children(sheet.tree, "wire")) + "\n" + updated[closing:]
            changes["labels"] = moved
        path.write_text("\n".join(line.rstrip() for line in updated.splitlines()) + "\n", encoding="utf-8")
        changes[name] = {"properties": positions, "before_components": len(children(parse(original), "symbol")),
                         "after_components": len(children(parse(updated), "symbol"))}
    reports, summary = pipeline.check(project)
    changes["summary"] = str(reports / "summary.json")
    changes["accepted"] = summary["status"] == "checks_clean_not_manufacturing_release"
    pipeline.write_json(EVIDENCE / "schematic-display-changes.json", changes)
    candidate["summary"] = str(reports / "summary.json")
    pipeline.write_json(candidate_path, candidate)
    if not changes["accepted"]:
        raise RuntimeError("Display edits failed native or unchanged pin-contract checks")
    print(summary["status"])


if __name__ == "__main__":
    main()
