import csv
import json
import re
from collections import defaultdict
from pathlib import Path


base = Path(__file__).resolve().parent
repository = base.parents[2]
raw = json.loads((base / "current-reference-raw-audit.json").read_text(encoding="utf-8"))
upstream = json.loads((base / "upstream-amp-bom.json").read_text(encoding="utf-8"))["projects"][0]["parts"]
raw_by_ref = {item["attributes"]["Designator"]: item for item in raw["components"]}
kissqy = []
for part in upstream:
    device = raw_by_ref[part["ref"]]["resolved_device_attributes"]
    mpn = device.get("Manufacturer Part") or part["mpn"]
    code = device.get("Supplier Part") or part["supplier_part"]
    kissqy.append({"ref": part["ref"], "mpn": mpn, "code": code, "footprint": device.get("Supplier Footprint") or part["footprint"], "source": "current_epro_device_metadata", "published_bom_mpn": part["mpn"], "published_bom_code": part["supplier_part"]})

match_rows = json.loads((repository / "docs/references/自主扩展板下单记录/exact-mpn-match-rows.json").read_text(encoding="utf-8"))["rows"]
mpn_codes = {row[3].splitlines()[-1]: re.search(r"C\d+", row[5]).group(0) for row in match_rows}
mpn_codes.update({"SSW-120-01-G-D": "C6302732", "TSW-108-07-G-S": "C3335496", "B3B-EH-A(LF)(SN)": "C160259", "TSW-103-07-G-S": "C3335811", "TSW-102-07-G-S": "C7402729"})
original = []
with (repository / "hardware/custom_hat/order-submission/20261103-five-hats/bom-fitted.csv").open(encoding="utf-8-sig", newline="") as stream:
    for group in csv.DictReader(stream):
        for reference in group["Reference"].split(","):
            original.append({"ref": reference, "mpn": group["MPN"], "code": mpn_codes[group["MPN"]], "footprint": group["Footprint"]})
substitutions = json.loads((repository / "docs/references/自主扩展板下单记录/substitution-candidates.json").read_text(encoding="utf-8"))["proposed_substitutions"]
changes = {reference: (item["candidate"], item["c_number"]) for item in substitutions for reference in item["refs"]}
changes.update({"U301": ("AP64351SP-13", "C3192339"), "U803": ("PAM8302AASCR", "C113367"), "R303": ("C0805C223K5RACTU", "C452753")})
proposed = []
for part in original:
    new_part = dict(part)
    if part["ref"] in changes:
        new_part["mpn"], new_part["code"] = changes[part["ref"]]
    if part["ref"] == "R303":
        new_part.update(ref="C331", footprint="Capacitor_SMD:C_0805_2012Metric")
    if part["ref"] == "U803":
        new_part["footprint"] = "proposed_Diodes_MSOP8_PAM8302A"
    if part["ref"] in {"C308", "C309", "C328"}:
        new_part["rejected_draft_code"] = new_part["code"]
        new_part["code"] = None
    proposed.append(new_part)

queries = {}
for board_name, parts in (("kissqy_amp20261015", kissqy), ("custom_a2_proposal", proposed)):
    for part in parts:
        if not part["code"]:
            continue
        queries.setdefault(part["code"], {"code": part["code"], "mpn": part["mpn"], "boards": []})
        if board_name not in queries[part["code"]]["boards"]:
            queries[part["code"]]["boards"].append(board_name)
document = {"date": "2026-11-04", "batch_units": 5, "kissqy_source_commit": "411878f89d38783ea87a5b21b54270632dbba7d7", "kissqy_source_sha256": raw['sha256'], "kissqy": kissqy, "custom_a1": original, "custom_a2_proposed_not_implemented": proposed, "queries": list(queries.values())}
(base / "comparison-boms.json").write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
(base / "price-query-list.json").write_text(json.dumps(list(queries.values()), ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"kissqy_components": len(kissqy), "kissqy_unique_mpn": len({part['mpn'] for part in kissqy}), "custom_components": len(proposed), "known_code_queries": len(queries), "source_bom_differences": [part for part in kissqy if part['mpn'] != part['published_bom_mpn']]}, ensure_ascii=False))
