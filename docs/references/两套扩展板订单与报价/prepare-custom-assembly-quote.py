import csv
import hashlib
import json
from pathlib import Path


base = Path(__file__).resolve().parent
root = base.parents[2]
source = root / "hardware/custom_hat/order-submission/20261103-five-hats"


def read_csv(name):
    with (source / name).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


rows = read_csv("jlc-bom-exact-mpn.csv")
fitted = read_csv("bom-fitted.csv")
assembly = {row["Reference"]: row for row in read_csv("assembly-plan.csv")}
tht_refs = {ref for ref, row in assembly.items() if row["Assembly"].startswith("THT")}
for row in fitted:
    if row["Reference"] in tht_refs:
        rows.append({"Comment": row["MPN"], "Designator": row["Reference"], "Footprint": "PTH P2.50mm" if row["Reference"] in {"J401", "J402"} else "PTH P2.54mm", "Manufacturer": row["Manufacturer"], "Quantity": row["Qty"], "Value": row["Value"], "MPN": row["MPN"], "KiCadFootprint": row["Footprint"]})
references = {reference for row in rows for reference in row["Designator"].split(",")}
positions = read_csv("positions.csv")
cpl = [{"Designator": row["Ref"], "Mid X": row["PosX"], "Mid Y": row["PosY"], "Layer": row["Side"].capitalize(), "Rotation": row["Rot"]} for row in positions if row["Ref"] in references]
assert len(references) == 58 and len(cpl) == 58 and len(tht_refs) == 6
for name, records in (("custom-bom-all58.csv", rows), ("custom-cpl-all58.csv", cpl)):
    with (base / name).open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
manifest = {"date": "2026-11-04", "purpose": "same-quantity complete fitted-parts assembly quotation", "fitted_per_board": 58, "smt_per_board": 52, "tht_per_board": 6, "tht_refs": sorted(tht_refs), "source_pcb_unchanged": True, "bom": "custom-bom-all58.csv", "cpl": "custom-cpl-all58.csv", "bom_sha256": hashlib.sha256((base / "custom-bom-all58.csv").read_bytes()).hexdigest(), "cpl_sha256": hashlib.sha256((base / "custom-cpl-all58.csv").read_bytes()).hexdigest(), "remarks_added": False, "missing_stock_and_mapping_not_resolved": True}
(base / "custom-assembly-quote-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print(json.dumps(manifest))
