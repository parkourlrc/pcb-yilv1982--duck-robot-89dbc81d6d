import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
import sys
import zipfile


base = Path(__file__).resolve().parent
repository = base.parents[2]
source = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else repository / "docs/schematics/kissqy-hat-reva-reference/ProPrj_HAT_REVA_SCH_2026-10-15.epro2"
documents = {}
current = None
with zipfile.ZipFile(source) as archive:
    epru_name = next(name for name in archive.namelist() if name.endswith(".epru"))
    for number, line in enumerate(archive.read(epru_name).decode("utf-8").splitlines(), 1):
        if "||" not in line:
            continue
        header_text, body = line.split("||", 1)
        header = json.loads(header_text)
        body = body[:-1] if body.endswith("|") else body
        if header["type"] == "DOCHEAD":
            metadata = json.loads(body)
            current = (metadata["docType"], metadata["uuid"])
            documents.setdefault(current, {"metadata": metadata, "records": {}})
        elif current is not None:
            identity = header.get("id", str(number))
            if not body or body == "|":
                documents[current]["records"].pop(identity, None)
            else:
                documents[current]["records"][identity] = {"type": header["type"], "data": json.loads(body), "source_line": number}

pcb = documents[("PCB", "9d00f144890fd6bb")]
attributes = defaultdict(dict)
for record in pcb["records"].values():
    if record["type"] == "ATTR":
        data = record["data"]
        attributes[data["parentId"]][data["key"]] = data["value"]
components = []
for identity, record in pcb["records"].items():
    if record["type"] != "COMPONENT":
        continue
    data = record["data"]
    device = documents.get(("DEVICE", attributes[identity].get("Device")), {}).get("records", {}).get("META", {}).get("data", {}).get("attributes", {})
    resolved = dict(device)
    resolved.update(data.get("attrs", {}))
    components.append({"id": identity, "data": data, "attributes": attributes[identity], "resolved_device_attributes": resolved, "source_line": record["source_line"]})
pad_nets = {}
for identity, record in pcb["records"].items():
    if record["type"] == "PAD_NET":
        key = json.loads(identity)
        pad_nets[(key[1], key[3])] = (key[2], record["data"]["padNet"], record["source_line"])
pads = []
for item in components:
    component = item["data"]
    reference = item["attributes"]["Designator"]
    angle = math.radians(component["angle"])
    footprint = item["attributes"]["Footprint"]
    for identity, record in documents[("FOOTPRINT", footprint)]["records"].items():
        if record["type"] != "PAD":
            continue
        pad = record["data"]
        number, net, source_line = pad_nets.get((item["id"], identity), (pad["num"], "", None))
        pads.append({"ref": reference, "pin": number, "net": net, "x": component["x"] + pad["centerX"] * math.cos(angle) - pad["centerY"] * math.sin(angle), "y": component["y"] + pad["centerX"] * math.sin(angle) + pad["centerY"] * math.cos(angle), "layer": component["layerId"], "shape": pad["defaultPad"], "source_line": source_line, "footprint": footprint})
board = {"pads": pads, "lines": [record["data"] for record in pcb["records"].values() if record["type"] == "LINE"]}
selected = {"C8", "C9", "C15", "C21", "C22", "J4", "U1", "U2", "U3", "U9", "U10", "Q2", "Y1", "MK1", "J13", "J14"}
result = {
    "source": source.relative_to(repository).as_posix(), "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    "pcb_record_types": dict(Counter(record["type"] for record in pcb["records"].values())),
    "component_count": len(components), "component_layers": dict(Counter(item["data"]["layerId"] for item in components)),
    "components": components,
    "selected_pad_nets": [pad for pad in board["pads"] if pad["ref"] in selected],
    "geometry_examples": [record for record in pcb["records"].values() if record["type"] in {"VIA", "LAYER", "LAYER_STACK", "BOARD", "POLY", "REGION", "ARC"}][:15],
    "track_layers": dict(Counter(item["layerId"] for item in board["lines"])),
    "track_widths_mil": dict(Counter(item.get("width") for item in board["lines"])),
    "via_records": [record for record in pcb["records"].values() if record["type"] == "VIA"],
    "layer_records": [record for record in pcb["records"].values() if record["type"] == "LAYER"],
    "outline_records": [record for record in pcb["records"].values() if record["type"] == "POLY"],
    "unresolved_devices": [{"document_key": key, "document": document} for key, document in documents.items() if key[1] in {"f53b74fa0b05f68e", "77fa94bfd10718b4", "d055c87f1ea2c7a5", "216dbda6538c2d85"}],
    "selected_footprint_pads": {item["attributes"]["Designator"]: [record["data"] for record in documents[("FOOTPRINT", item["attributes"]["Footprint"])]["records"].values() if record["type"] == "PAD"] for item in components if item["attributes"].get("Designator") in {"J4", "J1", "J13", "U2"}},
}
(base / (sys.argv[2] if len(sys.argv) > 2 else "reference-raw-audit.json")).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"component_count": result["component_count"], "component_layers": result["component_layers"], "record_types": result["pcb_record_types"], "selected_components": [{"ref": item["attributes"].get("Designator"), "attrs": item["attributes"], "body": item["data"]} for item in components if item["attributes"].get("Designator") in {"C8", "C9", "C15", "J4"}]}, ensure_ascii=False, indent=2))
