"""Archive observed manufacturer documents for the remaining BOM selections."""
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import fitz
import collect_bom_sources as collector


EVIDENCE = Path(__file__).resolve().parents[3] / "docs/references/hat-simulation-tools-20261029/final-bom-20261031"
SOURCES = {
    "jst-sh-sparkfun.pdf": "https://cdn.sparkfun.com/assets/0/e/1/5/8/JST-SH_right_angle_PRT-25271.pdf",
    "jst-catalogue-120.pdf": "https://www.jst.fr/doc/jst/pdf/jst-connector-catalogue-vol-120e.pdf",
    "vishay-wsl9.pdf": "https://www.vishay.com/docs/30192/wsl-9.pdf",
    "bourns-crf-j.pdf": "https://www.bourns.com/docs/product-datasheets/CRF-J.pdf",
    "wurth-catalogue-rs.pdf": "https://docs.rs-online.com/a613/0900766b80dcc54b.pdf",
    "vishay-ihlp4040dz-5a.pdf": "https://www.vishay.com/docs/34315/ihlp-4040dz-5a.pdf",
    "vishay-ihlp4040dz-11.pdf": "https://www.vishay.com/docs/34192/ihlp-4040dz-11.pdf",
    "wurth-pcn-farnell.pdf": "https://www.farnell.com/datasheets/4792449.pdf",
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
        if not record.get("success"):
            continue
        path = EVIDENCE / "sources" / record["file"]
        with fitz.open(path) as document:
            if "catalogue" in path.name:
                pages = [index for index, page in enumerate(document) if any(term in page.get_text() for term in ("B3B-EH-A", "BM04B-SRSS-TB", "744325550"))]
                if path.name == "jst-catalogue-120.pdf":
                    pages = sorted(set(pages) | {33, 34, 35})
            else:
                pages = range(min(3, len(document)))
            if path.name == "vishay-ihlp4040dz-5a.pdf":
                pages = (0, 1, 3)
            for page_number in pages:
                document[page_number].get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False).save(path.with_name(path.stem + f"-p{page_number+1}.png"))
            record["rendered_pdf_pages"] = [page+1 for page in pages]
    with fitz.open(EVIDENCE / "sources/jst-sh-sparkfun.pdf") as document:
        document[0].get_pixmap(matrix=fitz.Matrix(3, 3), clip=fitz.Rect(20, 420, 580, 590), alpha=False).save(EVIDENCE / "sources/jst-sh-land-pattern.png")
    manifest.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(records, ensure_ascii=False))


if __name__ == "__main__":
    main()
