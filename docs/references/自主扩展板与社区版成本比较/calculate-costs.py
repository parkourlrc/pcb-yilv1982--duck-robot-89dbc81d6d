import json
from collections import defaultdict
from decimal import Decimal
from pathlib import Path


base = Path(__file__).resolve().parent
boms = json.loads((base / "comparison-boms.json").read_text(encoding="utf-8"))
observations = json.loads((base / "live-prices.json").read_text(encoding="utf-8"))
prices = {record["code"]: record for record in observations}
prices.pop("C377773", None)


def calculate(parts):
    groups = defaultdict(list)
    for part in parts:
        groups[part["mpn"]].append(part)
    rows = []
    total = Decimal(0)
    missing = []
    shortages = []
    for mpn, items in groups.items():
        code = items[0]["code"]
        quantity = len(items) * 5
        record = prices.get(code, {})
        if record.get("mpn") != mpn:
            record = {}
        tiers = [tier for tier in record.get("tiers", []) if tier["quantity"] <= quantity]
        if tiers:
            selected = max(tiers, key=lambda tier: tier["quantity"])
            unit = Decimal(str(selected["unit_cny"]))
            basis = f"catalogue quantity tier {selected['quantity']}+"
        elif record.get("single_reference_price") is not None:
            unit = Decimal(str(record["single_reference_price"]))
            basis = "catalogue single reference price; tier not shown"
        else:
            unit = None
            basis = "no valid exact-MPN quote"
        batch_cost = unit * quantity if unit is not None else None
        if batch_cost is not None:
            total += batch_cost
        else:
            missing.append({"mpn": mpn, "refs": [item["ref"] for item in items], "quantity_5_boards": quantity})
        if record.get("stock") is not None and record["stock"] < quantity:
            shortages.append({"mpn": mpn, "code": code, "stock": record["stock"], "quantity_5_boards": quantity})
        rows.append({"mpn": mpn, "code": code if code != "C377773" else None, "refs": [item["ref"] for item in items], "per_board_qty": len(items), "batch_qty": quantity, "unit_cny": float(unit) if unit is not None else None, "per_board_cny": float(unit * len(items)) if unit is not None else None, "batch_cny": float(batch_cost) if batch_cost is not None else None, "basis": basis, "stock_observed": record.get("stock"), "evidence": record.get("evidence")})
    return {"component_count": len(parts), "unique_mpns": len(groups), "priced_component_count": len(parts) - sum(len(item['refs']) for item in missing), "priced_subtotal_batch_cny": float(total), "priced_subtotal_per_board_cny": float(total / 5), "unpriced": missing, "shortages_without_attrition": shortages, "groups": sorted(rows, key=lambda row: row['per_board_cny'] or 0, reverse=True)}


kissqy = calculate(boms["kissqy"])
custom = calculate(boms["custom_a2_proposed_not_implemented"])
result = {"date": "2026-11-04", "method": "same domestic JLC SMT catalogue; 5 finished boards, net quantities by exact MPN, best displayed tier not exceeding required quantity; excludes attrition, minimum assembly charges, feeders, stencil, PCB, THT labor, shipping and coupons", "kissqy_current_411878f": kissqy, "custom_a2_proposal": custom, "priced_subtotal_per_board_delta_cny": custom["priced_subtotal_per_board_cny"]-kissqy["priced_subtotal_per_board_cny"], "not_manufacturing_quotes": True, "material_mapping_error": {"refs": ["C308", "C309", "C328"], "requested": "C0805C225K5RACTU", "incorrect_code": "C377773", "actual_code_product": "CL21A225KBQNNNE, Samsung X5R", "excluded_wrong_price_cny_each": 0.24}}
def reference_subtotal(board, references):
    return sum((row["unit_cny"] or 0) * sum(reference in references for reference in row["refs"]) for row in board["groups"])


comparisons = [
    ("40P母座", {"J4"}, {"J101"}),
    ("板载IMU芯片", set(), {"U501"}),
    ("Buck芯片+电感", {"U9", "L4"}, {"U301", "L301"}),
    ("1.8V稳压芯片及自主阻尼电阻", {"U3"}, {"U702", "R703"}),
    ("codec", {"U2"}, {"U701"}),
    ("功放芯片", {"U1"}, {"U803"}),
    ("防倒灌控制器+MOS", {"U10", "Q2"}, set()),
    ("板载麦克风+12MHz振荡器", {"MK1", "Y1"}, set()),
]
result["cost_drivers"] = [{"scope": title, "kissqy_per_board_cny": reference_subtotal(kissqy, before), "custom_per_board_cny": reference_subtotal(custom, after), "difference_cny": reference_subtotal(custom, after)-reference_subtotal(kissqy, before)} for title, before, after in comparisons]
result["known_custom_excluding_bmi088_per_board_cny"] = custom["priced_subtotal_per_board_cny"] - reference_subtotal(custom, {"U501"})
result["old_a1_draft_only"] = {"pcb_batch_cny":820.47,"smt_parts_batch_cny":1066.78,"smt_processing_batch_cny":725.32,"smt_custom_services_batch_cny":67.50,"sum_batch_cny":2679.07,"sum_per_board_cny":535.814,"includes_tht_parts":False,"wrong_mpn_mapping_present":True,"can_be_used_as_new_quote":False}
(base / "cost-comparison.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
lines = ["# 五片批次目录材料成本明细", "", "2026-11-04；纯板上净用量，含目录标示税价，不含备损、制造/贴装、THT手焊和运费。缺货项仅参考价格，不能购买整套BOM。A.2为未实施方案。", ""]
for title, board in (("kissqy AMP2.0当前工程411878f", kissqy), ("自主A.2方案", custom)):
    lines += [f"## {title}", "", f"已取得价格的板上用料：{board['priced_component_count']}/{board['component_count']}件；每板小计¥{board['priced_subtotal_per_board_cny']:.4f}，5板¥{board['priced_subtotal_batch_cny']:.4f}。", "", "| 位号 | MPN | C编号 | 每板数量 | 单价¥ | 每板小计¥ | 观察库存 |", "|---|---|---|---:|---:|---:|---:|"]
    for row in board["groups"]:
        unit = f"{row['unit_cny']:.4f}" if row["unit_cny"] is not None else "未取得"
        subtotal = f"{row['per_board_cny']:.4f}" if row["per_board_cny"] is not None else "不计入"
        lines.append(f"| {','.join(row['refs'])} | {row['mpn']} | {row['code'] or '待纠正'} | {row['per_board_qty']} | {unit} | {subtotal} | {row['stock_observed'] if row['stock_observed'] is not None else '未核'} |")
    lines.append("")
(base / "cost-breakdown.md").write_text("\n".join(lines), encoding="utf-8")
print(json.dumps({"kissqy": {key:value for key,value in kissqy.items() if key!='groups'}, "custom": {key:value for key,value in custom.items() if key!='groups'}, "delta":result['priced_subtotal_per_board_delta_cny'], "top_custom":custom['groups'][:8]}, ensure_ascii=False, indent=2))
