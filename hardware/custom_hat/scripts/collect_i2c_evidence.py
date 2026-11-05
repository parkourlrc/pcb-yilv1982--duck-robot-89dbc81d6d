"""Archive manufacturer sources used for the I2C pull-up selection."""
import hashlib
import json
from pathlib import Path

import fitz
import requests


ROOT = Path(__file__).resolve().parents[3]
DESTINATION = ROOT / "docs/references/扩展板电路仿真工具/i2c-pullups-20261031/sources"
SOURCES = {
    "vishay-dcrcwe3.pdf": "https://www.vishay.com/docs/20035/dcrcwe3.pdf",
    "ti-slva689.pdf": "https://www.ti.com/lit/an/slva689/slva689.pdf",
}


def main():
    DESTINATION.mkdir(parents=True, exist_ok=True)
    records = []
    for name, url in SOURCES.items():
        path = DESTINATION / name
        if not path.exists():
            response = requests.get(url, timeout=60)
            response.raise_for_status()
            if not response.content.startswith(b"%PDF"):
                raise ValueError(f"Not a PDF: {url}")
            path.write_bytes(response.content)
        with fitz.open(path) as document:
            pages = [f"---PDF PAGE {index + 1}---\n{page.get_text()}" for index, page in enumerate(document)]
        path.with_suffix(".txt").write_text("\n".join(pages), encoding="utf-8")
        records.append({"url": url, "file": name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "pages": len(pages)})
    (DESTINATION / "manifest.json").write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(records))


if __name__ == "__main__":
    main()
