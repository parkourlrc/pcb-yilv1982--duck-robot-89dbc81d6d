import hashlib
import json
from collections import defaultdict
from pathlib import Path
import zipfile


repository = Path(__file__).resolve().parents[3]
source = repository / "docs/references/自主扩展板与社区版成本比较/kissqy-HAT-AMP2.0-411878f.epro2"
output = repository / "docs/references/扩展板乙版降本/reference-circuit.json"
documents = {}
current = None
with zipfile.ZipFile(source) as archive:
    member = next(name for name in archive.namelist() if name.endswith(".epru"))
    for line_number, line in enumerate(archive.read(member).decode("utf-8").splitlines(), 1):
        if "||" not in line:
            continue
        header_text, body = line.split("||", 1)
        header = json.loads(header_text)
        body = body[:-1] if body.endswith("|") else body
        if header["type"] == "DOCHEAD":
            metadata = json.loads(body)
            current = (metadata["docType"], metadata["uuid"])
            documents.setdefault(current, {"metadata": metadata, "records": {}})
        elif current:
            identity = header.get("id", str(line_number))
            if not body or body == "|":
                documents[current]["records"].pop(identity, None)
            else:
                documents[current]["records"][identity] = {"type": header["type"], "data": json.loads(body), "line": line_number}
pcb = documents[("PCB", "9d00f144890fd6bb")]
attributes = defaultdict(dict)
pad_nets = defaultdict(dict)
for identity, record in pcb["records"].items():
    if record["type"] == "ATTR":
        data = record["data"]
        attributes[data["parentId"]][data["key"]] = data["value"]
    elif record["type"] == "PAD_NET":
        key = json.loads(identity)
        pad_nets[key[1]][key[3]] = {"pin": key[2], "net": record["data"]["padNet"], "line": record["line"]}
components = []
for identity, record in pcb["records"].items():
    if record["type"] != "COMPONENT":
        continue
    instance = attributes[identity]
    device = documents.get(("DEVICE", instance.get("Device")), {}).get("records", {}).get("META", {}).get("data", {}).get("attributes", {})
    fields = dict(device)
    fields.update(record["data"].get("attrs", {}))
    fields.update(instance)
    footprint = documents[("FOOTPRINT", fields["Footprint"])]
    pins = []
    for pad_id, pad_record in footprint["records"].items():
        if pad_record["type"] != "PAD":
            continue
        pad = pad_record["data"]
        connection = pad_nets[identity].get(pad_id, {"pin": pad.get("num"), "net": "", "line": None})
        pins.append(connection)
    components.append({"ref": fields["Designator"], "mpn": fields.get("Manufacturer Part"), "manufacturer": fields.get("Manufacturer"), "code": fields.get("Supplier Part"), "value": fields.get("Value"), "name": fields.get("Name"), "datasheet": fields.get("Datasheet"), "pins": pins, "instance": record["data"], "footprint_name": footprint["metadata"].get("title"), "source_line": record["line"]})
result = {"source": source.relative_to(repository).as_posix(), "sha256": hashlib.sha256(source.read_bytes()).hexdigest(), "components": components, "use": "reference electrical topology only; Rev B remains independent KiCad design"}
output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
for component in components:
    print(component["ref"], component["mpn"], {str(pin["pin"]): pin["net"] for pin in component["pins"]})
