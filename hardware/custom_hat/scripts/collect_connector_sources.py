"""Archive newly reachable manufacturer connector and inductor documents."""
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import fitz
import collect_bom_sources as collector


EVIDENCE = Path(__file__).resolve().parents[3] / "docs/references/hat-simulation-tools-20261029/connectors-20261031"
SOURCES = {
    "jst-eh.pdf": "https://www.jst-mfg.com/product/pdf/eng/eEH.pdf",
    "jst-sh.pdf": "https://www.jst.com/wp-content/uploads/2021/01/eSH.pdf",
    "wurth-744325550.pdf": "https://www.we-online.com/components/products/datasheet/744325550.pdf",
    "samtec-ssw-spec.pdf": "https://suddendocs.samtec.com/productspecs/tsw-sxx.pdf",
    "samtec-ssw-print.pdf": "https://suddendocs.samtec.com/prints/ssw-1xx-xx-x-x-xx-xx.pdf",
    "samtec-tsw-print.pdf": "https://suddendocs.samtec.com/prints/tsw-1xx-xx-xxx-xx-xx.pdf",
    "jst-sh-202506.pdf": "https://www.jst.com/wp-content/uploads/2025/06/eSH.pdf",
    "wurth-744325550-versioned.pdf": "https://www.we-online.com/components/products/datasheet/744325550_valid_from_2025-02-06.pdf",
    "samtec-ssw-catalog.pdf": "https://suddendocs.samtec.com/catalog_english/ssw_th.pdf",
    "samtec-ssw-mkt.pdf": "https://suddendocs.samtec.com/prints/ssw-1xx-xx-xxx-x-xx-xxx-xx-mkt.pdf",
    "samtec-ssw-footprint.pdf": "https://suddendocs.samtec.com/prints/ssw-d.pdf",
    "samtec-tsw-catalog.pdf": "https://suddendocs.samtec.com/catalog_english/tsw_th.pdf",
    "samtec-tsw-mkt.pdf": "https://suddendocs.samtec.com/prints/tsw-xxx-xx-xxx-x-xx-xxx-mkt.pdf",
    "samtec-tsw-footprint.pdf": "https://suddendocs.samtec.com/prints/tsw-xxx-xx-x-x-xx-xxx-footprint.pdf",
    "samtec-tsw-power.pdf": "https://suddendocs.samtec.com/testreports/tc0838-1970_reportrev2_pwr.pdf",
    "wurth-m25-socket-cap.pdf": "https://marketplacemedia.witglobal.net/source/marketplace/stmedia/wuerth/documents/documents/std.lang.all/29211605.pdf",
    "harwin-m20-783.pdf": "https://content.harwin.com/asset/d6e23765-84b2-4c9c-8c92-6f718b2b03f9/DRG-00386-Technical-Drawing-Datasheet-M20-783-pdf.pdf",
}


def main():
    (EVIDENCE / "sources").mkdir(parents=True, exist_ok=True)
    collector.EVIDENCE = EVIDENCE
    manifest = EVIDENCE / "sources-manifest.json"
    if manifest.exists():
        collector.PREVIOUS = {entry["file"]: entry for entry in json.loads(manifest.read_text(encoding="utf-8"))}
    with ThreadPoolExecutor(max_workers=3) as executor:
        records = list(executor.map(collector.collect, SOURCES.items()))
    manifest.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for record in records:
        if not record.get("success") or not record["file"].endswith(".pdf"):
            continue
        path = EVIDENCE / "sources" / record["file"]
        with fitz.open(path) as document:
            pages = range(len(document)) if "jst-" in path.name or "mkt" in path.name else range(min(2, len(document)))
            for page_number in pages:
                document[page_number].get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False).save(path.with_name(path.stem + f"-p{page_number+1}.png"))
    print(json.dumps(records, ensure_ascii=False))


if __name__ == "__main__":
    main()
