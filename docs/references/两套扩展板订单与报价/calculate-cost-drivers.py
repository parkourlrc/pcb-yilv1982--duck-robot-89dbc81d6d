import json
import re
from decimal import Decimal
from pathlib import Path


base = Path(__file__).resolve().parent
status = json.loads((base / "order-comparison-status.json").read_text(encoding="utf-8"))
result = {
    "date": "2026-11-04",
    "basis": "2026-11-04 saved visible Y7/Y8 draft quotations; not final invoices",
    "boards": {},
}

for board, filename in (
    ("custom", "custom-y7-smt-auto-match-cells.json"),
    ("kissqy", "kissqy-y8-smt-auto-match-cells.json"),
):
    groups = {}
    unpriced = []
    for row in json.loads((base / filename).read_text(encoding="utf-8")):
        if len(row) != 10 or "替换" not in row[9]:
            continue
        code_match = re.search(r"\bC\d+\b", row[5])
        refs = re.findall(r"\b[A-Z]+\d+\b", row[1] + " " + row[2])
        need_match = re.search(r"使用：\s*(\d+)", row[7])
        price_match = re.search(r"单价：￥\s*([0-9.]+)", row[7])
        if not code_match or not need_match or not price_match:
            unpriced.append({"refs": refs, "reason": "no displayed purchase price", "stock_text": row[7]})
            continue
        code = code_match[0]
        quantity = int(need_match[1])
        unit = Decimal(price_match[1])
        if code in groups:
            if quantity != groups[code]["purchase_quantity"] or unit != groups[code]["unit"]:
                raise ValueError(f"Conflicting displayed group quantities/prices for {code}")
            groups[code]["refs"].extend(refs)
        else:
            groups[code] = {"code": code, "refs": refs, "purchase_quantity": quantity, "unit": unit}
    total = sum((group["unit"] * group["purchase_quantity"] for group in groups.values()), Decimal(0))
    rows = []
    for group in groups.values():
        rows.append({
            "code": group["code"],
            "refs": group["refs"],
            "purchase_quantity": group["purchase_quantity"],
            "unit_cny": float(group["unit"]),
            "batch_cny": float(group["unit"] * group["purchase_quantity"]),
        })
    quoted = status["custom"]["smt"]["parts_cny"] if board == "custom" else status["kissqy"]["smt_parts_cny"]
    result["boards"][board] = {
        "priced_code_groups": len(groups),
        "deduplicated_parts_sum_cny": float(total),
        "website_parts_cny": quoted,
        "rounded_sum_matches_website": round(total, 2) == Decimal(str(quoted)),
        "unpriced_rows": unpriced,
        "groups": sorted(rows, key=lambda group: group["batch_cny"], reverse=True),
    }

delta = Decimal("1915.71")
result["difference"] = {
    name: {"cny": float(amount), "share_percent": float(amount / delta * 100)}
    for name, amount in (("pcb", Decimal("772.38")), ("parts", Decimal("1092.73")), ("assembly", Decimal("50.60")))
}
result["custom_pcb_fee_exposure"] = {
    "small_hole_and_associated_options_cny": 344.15,
    "resin_fill_copper_cap_cny": 101.46,
    "inner_copper_cny": 100.49,
    "enig_including_large_gold_area_cny": 101.70,
    "sum_cny": 647.80,
    "is_guaranteed_removable_cost": False,
}
result["conditional_capacitor_scenario"] = {
    "refs": ["C303", "C304", "C305", "C306", "C323"],
    "old_mpn": "C1210C226K3RACTU",
    "candidate_mpn": "GRM32ER71E226KE15L",
    "old_displayed_unit_cny": 15.52,
    "candidate_catalogue_unit_cny": 1.92,
    "assumed_same_purchase_quantity": 29,
    "old_batch_cny": 450.08,
    "candidate_batch_cny": 55.68,
    "conditional_difference_cny": 394.40,
    "limits": "same-day catalogue tier, unchanged wastage/minimum quantity assumed; electrical adoption and new order quotation required",
}
(base / "cost-driver-calculations.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"totals": {board: {key: value for key, value in data.items() if key != "groups"} for board, data in result["boards"].items()}, "difference": result["difference"], "top_custom": result["boards"]["custom"]["groups"][:8]}, ensure_ascii=False, indent=2))
