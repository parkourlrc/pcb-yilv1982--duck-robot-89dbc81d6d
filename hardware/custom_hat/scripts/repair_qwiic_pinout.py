"""Correct the SH4 expansion header to Qwiic pin order in an isolated A.1 candidate."""
import argparse
import json
from pathlib import Path
import shutil

import pcbnew

import pipeline
from add_i2c_pullups import vector
from finish_ttl_local_bypass import route_layer
from generate_rev_a import Sheet, children, dump, first, parse, q
from repair_release_metadata import properties, replace_children


EVIDENCE = pipeline.BASE.parents[1] / "docs/references/扩展板电路仿真工具/qwiic-pinout-20261031"
BASELINE = "6fe440f3cfcd9a30550299258cba5bf9355d888b0c166f62919a21adfc5de82a"
OLD_NETS = {"1": "+3V3", "2": "POWER_GND", "3": "I2C5_SCL", "4": "I2C5_SDA"}
NEW_NETS = {"1": "POWER_GND", "2": "+3V3", "3": "I2C5_SDA", "4": "I2C5_SCL"}
REMOVE = {"1a3ffc2e-36ec-4664-928d-88ddaaae0d50", "8c9a1a3f-9a12-45e4-a255-1d0084e309ef",
          "ae577238-ecc5-45fc-84aa-831ced16ed54", "ca60cb97-1170-4a86-b7ff-f5e58d1a4dfd", "e720df20-19e7-415a-bcba-6ff81996ffc3"}
VIA = "4b32cdf4-4c9f-4063-9192-5ed88caa54f3"


def update_schematic(project):
    path = project / "imu_tof.kicad_sch"
    original = path.read_text(encoding="utf-8")
    tree = parse(original)
    instance = next(row for row in children(tree, "symbol") if properties(row).get("Reference") == "J502")
    origin = first(instance, "at")
    if float(origin[3]) != 0 or first(instance, "mirror"):
        raise RuntimeError("Review the header symbol transform before modifying labels")
    library = next(row for row in children(first(tree, "lib_symbols"), "symbol") if row[1] == first(instance, "lib_id")[1])
    labels = []
    for unit in children(library, "symbol"):
        for pin in children(unit, "pin"):
            number = str(first(pin, "number")[1])
            position = first(pin, "at")
            point = (round(float(origin[1]) + float(position[1]), 4), round(float(origin[2]) - float(position[2]), 4))
            wires = [wire for wire in children(tree, "wire") if point in [tuple(float(value) for value in item[1:]) for item in first(wire, "pts")[1:]]]
            if len(wires) != 1:
                raise RuntimeError("Expected one branch wire at J502 pin " + number)
            endpoint = next(tuple(float(value) for value in item[1:]) for item in first(wires[0], "pts")[1:] if tuple(float(value) for value in item[1:]) != point)
            matched = [label for label in children(tree, "global_label") if tuple(float(value) for value in first(label, "at")[1:3]) == endpoint]
            if len(matched) != 1 or matched[0][1] != OLD_NETS[number]:
                raise RuntimeError("Unexpected existing J502 label")
            labels.append({"pin": number, "old": matched[0][1], "new": NEW_NETS[number], "uuid": first(matched[0], "uuid")[1]})
            matched[0][1] = q(NEW_NETS[number])
    sheet = Sheet("imu_tof", "Qwiic connector correction")
    sheet.counter = 7000
    sheet.text("Rev A.1 J502: pin1=GND, pin2=3V3, pin3=SDA, pin4=SCL (Qwiic/STEMMA QT order). Earlier Rev A differs.", 35.56, 163.83)
    tree.extend(node for node in sheet.tree if isinstance(node, list) and node[0] == "text")
    path.write_text("\n".join(line.rstrip() for line in dump(tree).splitlines()) + "\n", encoding="utf-8")
    contract_path = project / "net-contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    for row in contract["pins"]:
        if row["reference"] == "J502":
            number = str(row["pin"])
            if row["net"] != OLD_NETS[number]:
                raise RuntimeError("Unexpected J502 net contract")
            row["net"] = NEW_NETS[number]
    contract["j502_interface"] = {"revision": "A.1", "pins": NEW_NETS, "voltage": "3.3V",
                                  "pin_order": "Qwiic/STEMMA QT manufacturer pin numbering", "previous_rev_a_pins": OLD_NETS,
                                  "hardware_tested": False, "module_compatibility_not_universal": True}
    pipeline.write_json(contract_path, contract)
    for schematic in project.glob("*.kicad_sch"):
        def revision(node):
            entry = first(node, "rev")
            if entry:
                entry[1] = q("A.1 design under review")
            else:
                node.append(["rev", q("A.1 design under review")])
            return True
        text = replace_children(schematic.read_text(encoding="utf-8"), "title_block", revision)
        schematic.write_text("\n".join(line.rstrip() for line in text.splitlines()) + "\n", encoding="utf-8")
    return labels


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repair-schematic", action="store_true")
    parser.add_argument("--tidy-labels", action="store_true")
    arguments = parser.parse_args()
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    candidate_path = EVIDENCE / "candidate.json"
    if arguments.tidy_labels:
        candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
        work = pipeline.managed(Path(candidate["project"]))
        source_manifest = json.loads((work.parent / "manifest.json").read_text(encoding="utf-8"))
        if candidate.get("promoted") or pipeline.fingerprints(pipeline.PRIMARY) != source_manifest["source_hashes"]:
            raise RuntimeError("Label tidy requires the unchanged source and unpromoted candidate")
        path = work / "imu_tof.kicad_sch"
        archive = EVIDENCE / "before-label-tidy-imu_tof.kicad_sch"
        if archive.exists():
            raise FileExistsError(archive)
        shutil.copy2(path, archive)
        moves = []
        def tidy(node):
            if properties(node).get("Reference") != "J502":
                return False
            origin = first(node, "at")
            for field in children(node, "property"):
                if field[1] in {"Reference", "Value"}:
                    location = first(field, "at")
                    previous = list(location)
                    location[1:3] = [float(origin[1]) + 12.7, float(origin[2]) - (2.54 if field[1] == "Reference" else 0)]
                    moves.append({"field": str(field[1]), "before": previous, "after": list(location)})
            return True
        updated = replace_children(path.read_text(encoding="utf-8"), "symbol", tidy)
        path.write_text("\n".join(line.rstrip() for line in updated.splitlines()) + "\n", encoding="utf-8")
        pipeline.write_json(EVIDENCE / "schematic-label-tidy.json", moves)
        reports, summary = pipeline.check(work)
        candidate["summary"] = str(reports / "summary.json")
        pipeline.write_json(candidate_path, candidate)
        print(summary["status"])
        return
    if arguments.repair_schematic:
        candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
        work = pipeline.managed(Path(candidate["project"]))
        source_manifest = json.loads((work.parent / "manifest.json").read_text(encoding="utf-8"))
        if candidate.get("promoted") or pipeline.fingerprints(pipeline.PRIMARY) != source_manifest["source_hashes"]:
            raise RuntimeError("Schematic repair requires the unchanged source and unpromoted candidate")
        archive = EVIDENCE / "rejected-unquoted-schematic"
        archive.mkdir(exist_ok=False)
        for path in pipeline.PRIMARY.glob("*.kicad_sch"):
            shutil.copy2(work / path.name, archive / path.name)
            shutil.copy2(path, work / path.name)
        shutil.copy2(work / "net-contract.json", archive / "net-contract.json")
        shutil.copy2(pipeline.PRIMARY / "net-contract.json", work / "net-contract.json")
        update_schematic(work)
        reports, summary = pipeline.check(work)
        candidate["summary"] = str(reports / "summary.json")
        pipeline.write_json(candidate_path, candidate)
        print(json.dumps({"status": summary["status"], "drc": summary["drc"], "erc": summary["erc"]}))
        return
    if candidate_path.exists():
        raise FileExistsError("Inspect the existing Qwiic candidate")
    source = pipeline.PRIMARY / (pipeline.STEM + ".kicad_pcb")
    if pipeline.digest(source) != BASELINE:
        raise RuntimeError("Main PCB changed")
    work = pipeline.prepare(pipeline.PRIMARY)
    candidate = {"project": str(work), "baseline": BASELINE, "promoted": False, "revision": "A.1"}
    pipeline.write_json(candidate_path, candidate)
    label_changes = update_schematic(work)
    board_path = work / source.name
    board = pcbnew.LoadBoard(str(board_path))
    footprint = board.FindFootprintByReference("J502")
    pad_changes = []
    pads = {pad.GetNumber(): pad for pad in footprint.Pads() if pad.GetNumber() != "MP"}
    for number, pad in pads.items():
        if pad.GetNetname() != OLD_NETS[number]:
            raise RuntimeError("Unexpected old PCB pin order")
        pad_changes.append({"pin": number, "uuid": pad.m_Uuid.AsString(), "old": pad.GetNetname(), "new": NEW_NETS[number]})
        pad.SetNet(board.FindNet(NEW_NETS[number]))
    matched = {item.m_Uuid.AsString(): item for item in board.GetTracks() if item.m_Uuid.AsString() in REMOVE}
    if set(matched) != REMOVE or any(item.GetLayer() != pcbnew.B_Cu for item in matched.values()):
        raise RuntimeError("Reviewed header branch identifiers changed")
    for item in matched.values():
        board.Remove(item)
    via = next(item for item in board.GetTracks() if item.m_Uuid.AsString() == VIA)
    old_position = tuple(pcbnew.ToMM(value) for value in via.GetPosition())
    if via.GetNetname() != "+3V3" or old_position != (158.92, 112.0):
        raise RuntimeError("Unexpected power escape via")
    via.SetPosition(vector((158.92, 112.1)))
    markers = [item for item in board.GetDrawings() if hasattr(item, "GetText") and item.GetText() == "DUCK HAT Rev A"]
    if len(markers) != 1:
        raise RuntimeError("Expected one board revision marker")
    markers[0].SetText("DUCK HAT A.1")
    title = board.GetTitleBlock()
    title.SetRevision("A.1")
    routes = []
    for pin, net, width, endpoint in (("2", "+3V3", .2, (158.92, 112.1)), ("4", "I2C5_SCL", .25, (160.2654, 109.5713)),
                                      ("3", "I2C5_SDA", .1874, (163.0869, 111.8039))):
        start = tuple(pcbnew.ToMM(value) for value in pads[pin].GetPosition())
        route = route_layer(board, net, "B.Cu", width, start, endpoint, EVIDENCE, search_margin=3, protect_i2s_reference=True)
        routes.append(route)
        pipeline.write_json(EVIDENCE / "selected-routes.json", routes)
    pcbnew.SaveBoard(str(board_path), board)
    pipeline.write_json(EVIDENCE / "change-contract.json", {"label_changes": label_changes, "pad_changes": pad_changes,
        "removed_tracks": sorted(REMOVE), "moved_via": {"uuid": VIA, "before": old_position, "after": [158.92, 112.1]},
        "routes": routes, "new_vias": [], "revision_marker": {"uuid": markers[0].m_Uuid.AsString(), "before": "DUCK HAT Rev A", "after": "DUCK HAT A.1"},
        "revision": "A.1", "manufacturer_pin_numbers": NEW_NETS, "hardware_tested": False})
    reports, summary = pipeline.check(work)
    candidate["summary"] = str(reports / "summary.json")
    pipeline.write_json(candidate_path, candidate)
    print(json.dumps({"routes": [row["length_mm"] for row in routes], "status": summary["status"], "drc": summary["drc"], "erc": summary["erc"]}))


if __name__ == "__main__":
    main()
