import hashlib
import json
import re
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path


base = Path(__file__).resolve().parent
checkout = Path(sys.argv[1]).resolve()
reports = []
for source in sorted(checkout.rglob("*.epro2")):
    documents = {}
    current = None
    with zipfile.ZipFile(source) as archive:
        for member in archive.namelist():
            if not member.endswith(".epru"):
                continue
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
                elif current is not None:
                    identity = header.get("id", str(line_number))
                    if not body or body == "|":
                        documents[current]["records"].pop(identity, None)
                    else:
                        documents[current]["records"][identity] = {"type": header["type"], "data": json.loads(body), "line": line_number}
    project_documents = []
    for key, document in documents.items():
        if key[0] not in {"PCB", "SCH", "SCH_PAGE"}:
            continue
        attributes = defaultdict(dict)
        for record in document["records"].values():
            if record["type"] == "ATTR":
                data = record["data"]
                attributes[data["parentId"]][data["key"]] = data["value"]
        components = []
        for identity, record in document["records"].items():
            if record["type"] != "COMPONENT":
                continue
            instance = attributes[identity]
            inherited = documents.get(("DEVICE", instance.get("Device")), {}).get("records", {}).get("META", {}).get("data", {}).get("attributes", {})
            resolved = dict(inherited)
            resolved.update(record["data"].get("attrs", {}))
            resolved.update(instance)
            components.append({"id": identity, "reference": resolved.get("Designator"), "mpn": resolved.get("Manufacturer Part"), "manufacturer": resolved.get("Manufacturer"), "supplier_part": resolved.get("Supplier Part"), "name": resolved.get("Name"), "value": resolved.get("Value"), "layer": record["data"].get("layerId"), "source_line": record["line"]})
        sensor_matches = [component for component in components if re.search(r"BMI\d|LSM\d|ICM[-_]?\d|MPU[-_]?\d|IIM[-_]?\d|gyroscope|陀螺", json.dumps(component, ensure_ascii=False), re.I)]
        project_documents.append({"doc_type": key[0], "uuid": key[1], "metadata": document["metadata"], "component_count": len(components), "ic_components": [component for component in components if str(component["reference"]).startswith("U")], "sensor_matches": sensor_matches, "components": components})
    reports.append({"source_root": checkout.as_posix(), "path": source.relative_to(checkout).as_posix(), "sha256": hashlib.sha256(source.read_bytes()).hexdigest(), "document_types": dict(Counter(key[0] for key in documents)), "project_documents": project_documents})

output_name = sys.argv[2] if len(sys.argv) > 2 else "epro-projects-audit.json"
(base / output_name).write_text(json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps([{ "path": report["path"], "sha256": report["sha256"], "documents": [{key: document[key] for key in ("doc_type", "uuid", "component_count", "ic_components", "sensor_matches")} for document in report["project_documents"]]} for report in reports], ensure_ascii=False, indent=2))
