from collections import defaultdict
from decimal import Decimal
import json
from pathlib import Path
import re


root=Path(__file__).resolve().parents[3]
evidence=root/"docs/references/扩展板乙版降本"
parts=json.loads((root/"hardware/custom_hat/rev_b/design-components.json").read_text(encoding="utf-8"))
prices={row["code"]:row for row in json.loads((root/"docs/references/自主扩展板与社区版成本比较/live-prices.json").read_text(encoding="utf-8"))}
for row in json.loads((evidence/"stock-details.json").read_text(encoding="utf-8")):
    content=row["text"]
    mpn=re.search(r"厂家型号\s*\n([^\n]+)",content)
    stock=re.search(r"库存总量\s*(\d+) PCS",content)
    tiers=[{"quantity":int(quantity),"unit_cny":float(value)} for quantity,value in re.findall(r"(\d+)\+\s*¥([\d.]+)/个",content)]
    if mpn and stock and tiers:
        prices[row["code"]]={"mpn":mpn[1],"tiers":tiers,"stock":int(stock[1]),"evidence":"stock-details.json","date":row["at"]}
for code,mpn,unit,stock,source in (
    ("C30010","AO3404A",0.701,13345,"ao3404a-stock-observation.txt"),
    ("C5333427","A1251WV-2P",0.344,8578,"../两套扩展板订单与报价/kissqy-y8-connector-mpn-check.txt"),
    ("C5151076","CNJM A2007WV-3P",0.18,386,"amp2007wv-stock-observation.txt"),
):
    prices[code]={"mpn":mpn,"tiers":[{"quantity":1,"unit_cny":unit}],"stock":stock,"evidence":source,"date":"2026-11-04"}
groups=defaultdict(list)
for part in parts:
    if part["code"]:
        groups[(part["mpn"],part["code"],part["footprint"],part["manufacturer"])].append(part)
rows=[]
net_total=Decimal(0)
missing=[]
for (mpn,code,footprint,manufacturer),items in groups.items():
    quantity=len(items)*5
    price=prices.get(code,{})
    exact=price.get("mpn")==mpn
    tiers=[tier for tier in price.get("tiers",[]) if tier["quantity"]<=quantity] if exact else []
    tier=max(tiers,key=lambda entry:entry["quantity"]) if tiers else {"quantity":1,"unit_cny":price["single_reference_price"]} if exact and price.get("single_reference_price") is not None else None
    amount=Decimal(str(tier["unit_cny"]))*quantity if tier else None
    if amount is not None:
        net_total+=amount
    else:
        missing.append(code)
    rows.append({"refs":[item["ref"] for item in items],"mpn":mpn,"code":code,"footprint":footprint,"manufacturer":manufacturer,"qty_5":quantity,"unit_cny":tier["unit_cny"] if tier else None,"net_cny":float(amount) if amount is not None else None,"observed_stock":price.get("stock") if exact else None,"evidence":price.get("evidence") if exact else None,"date":price.get("date") if exact else None,"attrition_and_minimum_loaded_quantity_confirmed":False})
record={"date":"2026-11-04","method":"Exact MPN/code match; same-day archived catalogue and current observed tier; net component quantity only","batch_boards":5,"groups":rows,"priced_groups":len(rows)-len(missing),"unpriced_codes":missing,"priced_net_material_subtotal_cny":float(net_total),"complete_material_total_cny":None,"actual_complete_pcba_quote_cny":None,"cost_target_met":False,"limits":["No attrition/minimum-load charge confirmation","No manufacturing quote","Stock is observational, not reserved","Missing prices are not zero"]}
(evidence/"cost-candidate.json").write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding="utf-8")
lines=["# Rev B.0成本闸门（未达标）","","2026-11-04。用户上限为5块全部焊好≤750元，运费另计。以下不是实际完整报价。","",f"已取得精确MPN匹配目录价的物料组：{record['priced_groups']}/{len(rows)}；这些组5板净用量小计¥{net_total:.4f}。缺价组：{', '.join(missing)}。缺项不是0元。","","备损、最低上机数、换料、PCB、钢网、工程/插件/治具/税费均须以新的完整报价为准，不将历史Y7/Y8草稿折半认作B.0报价。","","| 位号 | 精确MPN | C编号 | 5板净量 | 单价¥ | 净额¥ | 观察库存 |","|---|---|---|---:|---:|---:|---:|"]
for row in rows:
    lines.append("| "+" | ".join([",".join(row["refs"]),row["mpn"],row["code"],str(row["qty_5"]),str(row["unit_cny"]) if row["unit_cny"] is not None else "待核",f"{row['net_cny']:.4f}" if row["net_cny"] is not None else "待核",str(row["observed_stock"]) if row["observed_stock"] is not None else "待核"])+" |")
lines.extend(["","## 下一步","","先完成被滑动验证阻断的剩余现货/精确型号核对与产线准入，再用同版本BOM/CPL/Gerber取得5块全焊实际报价。保留TLV的单面标准型先报价；超750元才按授权进一步处理换料组/连接器/工序及codec替换。当前最低实际价与差额均未知。"])
(evidence/"cost-gate.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
print(json.dumps({key:value for key,value in record.items() if key!="groups"},ensure_ascii=False))
