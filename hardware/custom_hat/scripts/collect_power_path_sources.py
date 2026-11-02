"""Archive manufacturer power-interface and copper-resistance evidence."""
import hashlib
import json
from pathlib import Path

import fitz
import requests


ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "docs/references/hat-simulation-tools-20261029/power-paths-20261031"
SOURCES = [
    ("ti-smps-layout.pdf", "https://www.ti.com/lit/pdf/sszp640"),
    ("radxa-zero3w-brief.pdf", "https://dl.radxa.com/zero3/docs/hw/3w/radxa_zero_3w_product_brief.pdf"),
    ("jst-eh-official.pdf", "https://order.jst-mfg.com/InternetShop/app/pdf_show?kbn=1&key=EH.pdf"),
]


def main():
    folder = EVIDENCE / "sources"
    folder.mkdir(parents=True, exist_ok=True)
    records = []
    for name, url in SOURCES:
        path = folder / name
        record = {"url": url, "file": name, "cached": path.exists()}
        try:
            if not path.exists():
                response = requests.get(url, timeout=45)
                response.raise_for_status()
                if not response.content.startswith(b"%PDF"):
                    raise ValueError("Response is not a PDF")
                path.write_bytes(response.content)
                record["final_url"] = response.url
            with fitz.open(path) as document:
                pages = [page.get_text() for page in document]
                record["pages"] = len(pages)
                record["relevant_pages"] = [index + 1 for index, text in enumerate(pages)
                                             if any(term.lower() in text.lower() for term in ("Counting squares", "5V/2A", "Power Requirements", "AWG#22", "定格電流"))]
                path.with_suffix(".txt").write_text("\n".join(f"---PDF PAGE {index + 1}---\n{text}" for index, text in enumerate(pages)), encoding="utf-8")
                for page_number in record["relevant_pages"]:
                    document[page_number - 1].get_pixmap(matrix=fitz.Matrix(1.3, 1.3), alpha=False).save(folder / (path.stem + f"-p{page_number}.png"))
            record["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
            record["success"] = True
        except Exception as error:
            record.update(success=False, error=str(error))
        records.append(record)
    (EVIDENCE / "sources-manifest.json").write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(records, ensure_ascii=False))


if __name__ == "__main__":
    main()
