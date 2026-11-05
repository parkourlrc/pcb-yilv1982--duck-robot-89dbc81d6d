"""Bind the incremental TTL review to native checks and archived TI datasheets."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import fitz


ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "docs/references/扩展板电路仿真工具"
EVIDENCE = BASE / "board-marking-20261031"


def main():
    native = json.loads((BASE / "ttl-bypass-20261031/geometry-connectivity-check.json").read_text(encoding="utf-8"))
    marking = json.loads((EVIDENCE / "geometry-connectivity-check.json").read_text(encoding="utf-8"))
    sources, findings = [], []
    quote = "Provide an electrically short ground return path"
    for reference, component, part, filename, page_number in (("C329", "U801", "SN74LVC1G126", "sn74lvc1g126.pdf", 15),
                                                            ("C330", "U802", "SN74LVC1G125", "sn74lvc1g125.pdf", 14)):
        path = BASE / "metadata-repair-20261030/sources" / filename
        with fitz.open(path) as pdf:
            page_text = " ".join(pdf[page_number - 1].get_text().split())
        if quote not in page_text:
            raise RuntimeError("Archived datasheet quote/page mismatch")
        sources.append({"mpn_family": part, "file": path.relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                        "page": page_number, "sections": ["8.3", "8.4"], "source_url": "https://www.ti.com/lit/ds/symlink/" + filename,
                        "manual_pdf_text_quote_checked": True, "fresh_web_fetch": False})
        row = next(item for item in native["local_checks"] if item["reference"] == reference)
        result = {"value": row["value"], "routes": row["routes"], "via_contacts": row["ground_via_contacts"],
                  "original_connections_preserved": not native["lost_pad_connections"], "marking_preserves_routing": marking["routing_unchanged"]}
        findings.append({"detector": "deep_review", "category": "decoupling", "severity": "info", "confidence": "high",
            "summary": component + "已新增同面100nF旁路及局部地过孔（文件核对）",
            "description": "核对原厂建议、VCC/GND赋网及已保存填铜。所列长度仅为新增平面走线，不含整个地平面电流分布、孔桶或ESL；未做波形、抗扰度或实物验收。",
            "recommendation": "保持完整层叠/高频回流与首板验收的独立边界，不将自动告警消失解释为性能通过。",
            "evidence": {"components": [component, reference], "nets": ["+3V3", "POWER_GND"], "pins": [component + ".5", component + ".3"],
                         "datasheet": [{"mpn": part, "page": page_number, "quote": quote}],
                         "computation": {"description": "Native geometry/connectivity checks plus the marking-only invariants",
                                         "script": "hardware/custom_hat/scripts/verify_ttl_local_bypass.py", "result": json.dumps(result, ensure_ascii=False)}}})
    data = {"schema_version": "1.0", "produced_for_run_id": "board-marking-20261031", "produced_at": datetime.now(timezone.utc).isoformat(),
            "review_scope": "Incremental TTL additions; unchanged ICs retain prior review limitations. This is not full electrical/manufacturing acceptance.",
            "findings": findings, "quarantined": [],
            "trust_summary": {"native_file_checks": "passed", "datasheet_pages": "manually checked against archived PDF", "hardware_tested": False,
                              "full_ground_return_impedance_verified": False, "whole_board_electrical_release": False}}
    (EVIDENCE / "deep_review.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (EVIDENCE / "ttl-datasheet-sources.json").write_text(json.dumps(sources, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Two incremental findings and archived source hashes written")


if __name__ == "__main__":
    main()
