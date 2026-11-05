import json
import re
from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw


base = Path(__file__).resolve().parent
source = json.loads((base.parent / "自主扩展板与社区版成本比较/comparison-boms.json").read_text(encoding="utf-8"))
report = {"date": "2026-11-04", "basis": "visible webpage table cells versus archived source BOM", "boards": {}}

for board, filename, source_key in (
    ("custom_a1", "custom-y7-smt-auto-match-cells.json", "custom_a1"),
    ("kissqy", "kissqy-y8-smt-auto-match-cells.json", "kissqy"),
):
    rows = json.loads((base / filename).read_text(encoding="utf-8"))
    expected = {part["ref"]: part for part in source[source_key]}
    references = []
    sides = Counter()
    shortages = []
    code_differences = []
    material_rows = []
    for row in rows:
        if len(row) != 10 or "替换" not in row[9]:
            continue
        top = re.findall(r"\b[A-Z]+\d+\b", row[1])
        bottom = re.findall(r"\b[A-Z]+\d+\b", row[2])
        refs = top + bottom
        references.extend(refs)
        sides.update(top=len(top), bottom=len(bottom))
        codes = re.findall(r"\bC\d+\b", row[5])
        code = codes[0] if codes else None
        needed_match = re.search(r"使用：\s*(\d+)", row[7])
        stock_match = re.search(r"(?:库存|私有库)：\s*(\d+)", row[7])
        needed = int(needed_match[1]) if needed_match else None
        stock = int(stock_match[1]) if stock_match else None
        record = {"refs": refs, "matched_code": code, "required_with_loss": needed, "stock": stock, "private_stock": "私有库：" in row[7], "tht": "插装" in row[6]}
        material_rows.append(record)
        if needed is not None and stock is not None and stock < needed:
            shortages.append(record)
        for reference in refs:
            if reference in expected and code != expected[reference]["code"]:
                code_differences.append({"ref": reference, "expected_code": expected[reference]["code"], "matched_code": code, "expected_mpn": expected[reference]["mpn"]})
    counts = Counter(references)
    report["boards"][board] = {
        "source_parts": len(expected),
        "matched_parts": len(references),
        "unique_refs": len(counts),
        "matching_rows": len(material_rows),
        "sides": dict(sides),
        "tht_parts": sum(len(row["refs"]) for row in material_rows if row["tht"]),
        "missing_refs": sorted(set(expected) - set(references)),
        "unexpected_refs": sorted(set(references) - set(expected)),
        "duplicate_refs": {reference: count for reference, count in counts.items() if count != 1},
        "shortage_rows": shortages,
        "code_differences": code_differences,
    }

report["known_mapping_limitations"] = {
    "custom_a1": "Historical source code map already contains rejected C377773 for C308/C309/C328; code equality does not validate the KEMET MPN.",
    "kissqy": "J1/J2/J9 automatically map C225090 to C5333427; visible search verifies CJT A1251WV-2P on C5333427, same source manufacturer/MPN. Mechanical placement remains unreviewed.",
}
(base / "quote-row-audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

raw_screenshot = Path("C:/Users/yilv/AppData/Local/Temp/hat-two-orders-pcb-raw.jpg")
with Image.open(raw_screenshot) as screenshot:
    output = screenshot.crop((274, 120, 1227, 432))
    drawing = ImageDraw.Draw(output)
    drawing.rectangle((362, 0, 575, 31), fill="#f5f5f5")
    drawing.rectangle((362, 162, 575, 192), fill="#f5f5f5")
    output.save(base / "pcb-y7-y8-unpaid-redacted.png")

print(json.dumps(report, ensure_ascii=False, indent=2))
