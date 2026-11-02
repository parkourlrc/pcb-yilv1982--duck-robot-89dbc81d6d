"""Repair evidenced part metadata in a complete, isolated KiCad workspace."""
import argparse
import copy
import json
from pathlib import Path
import re
import subprocess

import pipeline
from generate_rev_a import children, dump, first, parse, prop, q


PARTS = {
    "U301": ("AP64350SP-13", "Diodes Incorporated", "https://www.diodes.com/assets/Datasheets/AP64350.pdf"),
    "U501": ("BMI088", "Bosch Sensortec", "https://www.bosch-sensortec.com/media/boschsensortec/downloads/datasheets/bst-bmi088-ds001.pdf"),
    "U701": ("TLV320AIC3104IRHBR", "Texas Instruments", "https://www.ti.com/lit/ds/symlink/tlv320aic3104.pdf"),
    "U702": ("LP38691DT-1.8/NOPB", "Texas Instruments", "https://www.ti.com/lit/ds/symlink/lp38691.pdf"),
    "U801": ("SN74LVC1G126DBVR", "Texas Instruments", "https://www.ti.com/lit/ds/symlink/sn74lvc1g126.pdf"),
    "U802": ("SN74LVC1G125DBVT", "Texas Instruments", "https://www.ti.com/lit/ds/symlink/sn74lvc1g125.pdf"),
    "U803": ("PAM8302AADCR", "Diodes Incorporated", "https://www.diodes.com/assets/Datasheets/PAM8302A.pdf"),
}


def child_spans(text, keyword=None):
    depth = 0
    quoted = False
    escaped = False
    start = None
    for offset, char in enumerate(text):
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char == "(":
            if depth == 1:
                start = offset
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 1 and start is not None:
                block = text[start:offset + 1]
                if keyword is None or re.match(r"\(" + re.escape(keyword) + r"(?:\s|\))", block):
                    yield start, offset + 1, block
    if depth or quoted:
        raise ValueError("Unbalanced source document")


def properties(node):
    return {str(entry[1]): str(entry[2]) for entry in children(node, "property") if len(entry) > 2}


def set_property(node, key, value, board=False):
    existing = next((entry for entry in children(node, "property") if entry[1] == key), None)
    if existing is not None:
        existing[2] = q(value)
        return
    if board:
        side = "B" if first(node, "layer")[1] == "B.Cu" else "F"
        entry = ["property", q(key), q(value), ["at", "0", "0"], ["layer", q(side + ".Fab")], ["hide", "yes"], ["effects", ["font", ["size", "1", "1"]]]]
    else:
        at = first(node, "at") or ["at", "0", "0"]
        entry = prop(key, value, at[1], at[2], hidden=True)
    node.append(entry)


def set_flag(node, key, value):
    entry = first(node, key)
    if entry is None:
        node.append([key, value])
    else:
        entry[1] = value


def replace_children(text, keyword, transform):
    for start, end, block in reversed(list(child_spans(text, keyword))):
        node = parse(block)
        if transform(node):
            text = text[:start] + dump(node, 1) + text[end:]
    return text


def repair(project):
    project = pipeline.managed(project)
    schematics = {}
    local_ldo = None
    changed = []
    for path in sorted(project.glob("*.kicad_sch")):
        original = path.read_text(encoding="utf-8")
        text = original
        if path.name == "power.kicad_sch":
            text = text.replace("Regulator_Linear:LP38693DT-1.8", "duck:LP38691DT-1.8")
            text = text.replace("LP38693DT-1.8", "LP38691DT-1.8")
            text = text.replace("symlink/lp38693.pdf", "symlink/lp38691.pdf")
            library = first(parse(text), "lib_symbols")
            local_ldo = copy.deepcopy(next(node for node in children(library, "symbol") if node[1] == "duck:LP38691DT-1.8"))
            local_ldo[1] = q("LP38691DT-1.8")
            set_property(local_ldo, "Footprint", "Package_TO_SOT_SMD:TO-252-3_TabPin2")
            set_property(local_ldo, "Description", "TI LP38691 fixed 1.8V LDO, TO-252 NDP: 1 OUT, 2/TAB GND, 3 IN; no EN")
            set_property(local_ldo, "MPN", PARTS["U702"][0])
            set_property(local_ldo, "Manufacturer", PARTS["U702"][1])
            for start, end, block in child_spans(text, "lib_symbols"):
                old_block = next(block_entry for _, _, block_entry in child_spans(block, "symbol") if parse(block_entry)[1] == "duck:LP38691DT-1.8")
                cached = copy.deepcopy(local_ldo)
                cached[1] = q("duck:LP38691DT-1.8")
                updated = block.replace(old_block, dump(cached, 2), 1)
                text = text[:start] + updated + text[end:]
                break

        def update_symbol(node):
            if first(node, "lib_id") is None:
                return False
            fields = properties(node)
            reference = fields.get("Reference", "")
            updated = False
            if reference in PARTS:
                mpn, manufacturer, datasheet = PARTS[reference]
                for key, value in {"MPN": mpn, "Manufacturer": manufacturer, "Datasheet": datasheet, "BOM Comments": "Design-selected MPN; manufacturer document reviewed; procurement and stock not yet released"}.items():
                    set_property(node, key, value)
                if reference == "U702":
                    set_property(node, "Value", "LP38691DT-1.8")
                updated = True
            if reference.startswith("FLG"):
                set_flag(node, "in_bom", "no")
                set_flag(node, "on_board", "no")
                updated = True
            if reference in {"TP801", "TP802", "TP803"}:
                set_flag(node, "in_bom", "no")
                updated = True
            schematics[reference] = properties(node)
            return updated

        text = replace_children(text, "symbol", update_symbol)
        if text != original:
            parse(text)
            path.write_text(text, encoding="utf-8")
            changed.append(path.name)
    if local_ldo is None:
        raise ValueError("Missing LDO cache")
    symbol_file = project / "duck.kicad_sym"
    library = symbol_file.read_text(encoding="utf-8")
    if any(node[1] == "LP38691DT-1.8" for node in children(parse(library), "symbol")):
        raise ValueError("Local LDO symbol already exists; review baseline")
    insertion = library.rfind(")")
    symbol_file.write_text(library[:insertion] + dump(local_ldo, 1) + "\n" + library[insertion:], encoding="utf-8")
    changed.append(symbol_file.name)

    netlist_path = project.parent / "metadata-netlist.xml"
    subprocess.run([str(pipeline.find_cli()), "sch", "export", "netlist", "--format", "kicadxml", "--output", str(netlist_path), str(project / (pipeline.STEM + ".kicad_sch"))], check=True)
    import xml.etree.ElementTree as xml
    netlist = xml.parse(netlist_path).getroot()
    net_names = {(entry.get("ref"), entry.get("pin")): net.get("name") for net in netlist.findall("nets/net") for entry in net.findall("node")}
    pcb_path = project / (pipeline.STEM + ".kicad_pcb")
    pcb_text = pcb_path.read_text(encoding="utf-8")
    pad_net_changes = []

    def update_footprint(node):
        fields = properties(node)
        reference = fields["Reference"]
        source_fields = schematics.get(reference)
        if source_fields:
            node[1] = q(source_fields["Footprint"])
            for key in ("Value", "Datasheet", "MPN", "Manufacturer", "BOM Comments"):
                if key in source_fields:
                    set_property(node, key, source_fields[key], board=True)
            for pad in children(node, "pad"):
                expected = net_names.get((reference, str(pad[1])))
                if expected and expected.startswith("unconnected-") and first(pad, "net") is None:
                    pad.append(["net", q(expected)])
                    pad_net_changes.append([reference, str(pad[1]), expected])
        attributes = first(node, "attr")
        if attributes is None:
            attributes = ["attr"]
            node.append(attributes)
        if reference.startswith("H") or reference.startswith("FID"):
            for flag in ("board_only", "exclude_from_bom", "exclude_from_pos_files"):
                if flag not in attributes:
                    attributes.append(flag)
        if reference.startswith("FID"):
            side = "B" if first(node, "layer")[1] == "B.Cu" else "F"
            node[1] = q("Fiducial:Fiducial_1mm_Mask2mm")
            set_property(node, "Value", "Fiducial_1mm_Mask2mm", board=True)
            for key in ("Reference", "Value"):
                field = next(entry for entry in children(node, "property") if entry[1] == key)
                first(field, "layer")[1] = q(side + ".Fab")
                effect = first(field, "effects")
                if side == "B" and first(effect, "justify") is None:
                    effect.append(["justify", "mirror"])
            for pad in children(node, "pad"):
                first(pad, "layers")[1:] = [q(side + ".Cu"), q(side + ".Mask")]
                pad.extend([["property", "pad_prop_fiducial_glob"], ["solder_mask_margin", "0.5"], ["clearance", "0.6"]])
            node.append(["fp_circle", ["center", "0", "0"], ["end", "1.25", "0"], ["stroke", ["width", "0.05"], ["type", "solid"]], ["fill", "no"], ["layer", q(side + ".CrtYd")]])
        return True

    pcb_text = replace_children(pcb_text, "footprint", update_footprint)
    parse(pcb_text)
    pcb_path.write_text(pcb_text, encoding="utf-8")
    changed.append(pcb_path.name)
    contract_path = project / "net-contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    for entry in contract["pins"]:
        if entry["reference"] == "U702":
            entry["lib_id"] = "duck:LP38691DT-1.8"
    pipeline.write_json(contract_path, contract)
    changed.append(contract_path.name)
    record = {"work": str(project), "changed_files": changed, "nc_nets_assigned": pad_net_changes, "selected_parts": PARTS, "production_ready": False}
    pipeline.write_json(project.parent / "metadata-changes.json", record)
    print(json.dumps({"work": str(project), "files": changed, "nc_nets": len(pad_net_changes), "mpns": len(PARTS)}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, type=Path)
    arguments = parser.parse_args()
    repair(arguments.project)


if __name__ == "__main__":
    main()
