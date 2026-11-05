"""Move only generated passive Reference/Value labels off their vertical pins and wires."""
import argparse
import copy
import json
from pathlib import Path

import pipeline
from generate_rev_a import children, first, parse
from repair_release_metadata import properties, replace_children


EVIDENCE = pipeline.BASE.parents[1] / "docs/references/扩展板电路仿真工具/amp-decoupling-20261031"


def without_label_positions(text):
    tree = copy.deepcopy(parse(text))
    for symbol in children(tree, "symbol"):
        for field in children(symbol, "property"):
            if field[1] in {"Reference", "Value"}:
                location = first(field, "at")
                if location:
                    location[1:3] = [0, 0]
    return tree


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refine", action="store_true")
    arguments = parser.parse_args()
    record_path = EVIDENCE / "passive-label-presentation.json"
    if record_path.exists() and not arguments.refine:
        raise FileExistsError("Passive-label correction already recorded")
    candidate_path = EVIDENCE / "candidate.json"
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    if candidate["promoted"]:
        raise RuntimeError("Use a new workspace after promotion")
    work = pipeline.managed(Path(candidate["project"]))
    if arguments.refine:
        record = json.loads(record_path.read_text(encoding="utf-8"))
        if record.get("label_offset_mm") == 5.08:
            raise RuntimeError("Label spacing already refined")
        entries = {(entry["file"], entry["reference"]): entry for entry in record["changes"]}
        for path in work.glob("*.kicad_sch"):
            original = path.read_text(encoding="utf-8")
            def refine(node):
                entry = entries.get((path.name, properties(node).get("Reference")))
                if not entry:
                    return False
                fields = {str(field[1]): field for field in children(node, "property")}
                for key in ("Reference", "Value"):
                    position = first(fields[key], "at")
                    if any(abs(float(position[axis + 1]) - float(entry["after"][key][axis])) > 1e-6 for axis in (0, 1)):
                        raise RuntimeError("Unexpected label movement before refinement")
                entry["first_after"] = copy.deepcopy(entry["after"])
                for key in ("Reference", "Value"):
                    position = first(fields[key], "at")
                    position[1] = round(float(position[1]) + 1.27, 4)
                    entry["after"][key] = list(position[1:3])
                return True
            updated = replace_children(original, "symbol", refine)
            if without_label_positions(original) != without_label_positions(updated):
                raise RuntimeError("Electrical content changed during refinement")
            if updated != original:
                path.write_text("\n".join(line.rstrip() for line in updated.splitlines()) + "\n", encoding="utf-8")
        record["label_offset_mm"] = 5.08
        record["refinement_reason"] = "Increase text-to-capacitor-plate clearance after rendered review"
        pipeline.write_json(record_path, record)
        print(json.dumps({"labelled_parts": len(entries), "electrical_content_equal": True, "requires_final_pipeline_check": True}))
        return
    changes = []
    for path in work.glob("*.kicad_sch"):
        original = path.read_text(encoding="utf-8")
        def update(node):
            library = first(node, "lib_id")
            location = first(node, "at")
            if not library or library[1] not in {"Device:C", "Device:R", "Device:L"} or not location or float(location[3]) % 360 != 0:
                return False
            xpos, ypos = float(location[1]), float(location[2])
            fields = {str(field[1]): field for field in children(node, "property")}
            if not {"Reference", "Value"}.issubset(fields):
                return False
            old_positions = {key: first(fields[key], "at")[1:3] for key in ("Reference", "Value")}
            expected = {"Reference": [xpos, ypos - 5.08], "Value": [xpos, ypos - 2.54]}
            if not all(abs(float(old_positions[key][axis]) - expected[key][axis]) < 1e-6 for key in expected for axis in (0, 1)):
                return False
            first(fields["Reference"], "at")[1:3] = [round(xpos + 5.08, 4), round(ypos - 1.27, 4)]
            first(fields["Value"], "at")[1:3] = [round(xpos + 5.08, 4), round(ypos + 1.27, 4)]
            changes.append({"file": path.name, "reference": properties(node)["Reference"], "before": old_positions,
                            "after": {key: first(fields[key], "at")[1:3] for key in expected}})
            return True
        updated = replace_children(original, "symbol", update)
        if without_label_positions(original) != without_label_positions(updated):
            raise RuntimeError("Electrical or value content changed during label layout")
        if updated != original:
            path.write_text("\n".join(line.rstrip() for line in updated.splitlines()) + "\n", encoding="utf-8")
    pipeline.write_json(record_path, {"changes": changes, "reference_value_positions_only": True, "all_other_schematic_content_equal": True})
    reports, summary = pipeline.check(work)
    candidate["summary"] = str(reports / "summary.json")
    pipeline.write_json(candidate_path, candidate)
    print(json.dumps({"labelled_parts": len(changes), "drc": summary["drc"], "erc": summary["erc"], "status": summary["status"]}))


if __name__ == "__main__":
    main()
