"""Archive manufacturer documents and unsuccessful fetches for BOM selection."""
import hashlib
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import fitz
import requests


ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "docs/references/hat-simulation-tools-20261029/bom-passives-20261031"
PREVIOUS = {}
SOURCES = {
    "jst-sh.pdf": "https://www.jst-mfg.com/product/pdf/eng/eSH.pdf",
    "jst-eh.pdf": "https://www.jst-mfg.com/product/pdf/eng/eEH.pdf",
    "tdk-mlcc-general.pdf": "https://product.tdk.com/system/files/dam/doc/product/capacitor/ceramic/mlcc/catalog/mlcc_commercial_general_en.pdf",
    "st-smbj.pdf": "https://www.st.com/resource/en/datasheet/smbj.pdf",
    "vishay-wslp.pdf": "https://www.vishay.com/docs/30122/wslp.pdf",
    "coilcraft-mss1278.html": "https://www.coilcraft.com/en-us/products/power/shielded-inductors/ferrite-drum-surface-mount/mss/mss1278/",
    "tdk-c1005-1uf.html": "https://product.tdk.com/en/search/capacitor/ceramic/mlcc/info?part_no=C1005X5R1C105K050BC",
    "kyocera-x7r.pdf": "https://datasheets.kyocera-avx.com/X7RDielectric.pdf",
    "kyocera-x5r.pdf": "https://datasheets.kyocera-avx.com/X5RDielectric.pdf",
    "kyocera-c0g.pdf": "https://datasheets.kyocera-avx.com/C0GNP0-Dielectric.pdf",
    "kemet-x7r.pdf": "https://content.kemet.com/datasheets/KEM_C1002_X7R_SMD.pdf",
    "kemet-x5r.pdf": "https://content.kemet.com/datasheets/KEM_C1009_X5R_SMD.pdf",
    "kemet-x5r-c1006.pdf": "https://content.kemet.com/datasheets/KEM_C1006_X5R_SMD.pdf",
    "jst-sh-us.pdf": "https://www.jst.com/wp-content/uploads/2021/01/eSH.pdf",
    "jst-eh-us.pdf": "https://www.jst.com/wp-content/uploads/2021/01/eEH.pdf",
    "littelfuse-smbj.pdf": "https://www.littelfuse.com/assetdocs/littelfuse-tvs-diode-smbj-datasheet?assetguid=3d0a1c53-7d65-40b4-a581-36bd1e31079a",
    "vishay-smbj.pdf": "https://www.vishay.com/docs/88392/smbj.pdf",
    "wurth-744325550.pdf": "https://www.we-online.com/components/products/datasheet/744325550.pdf",
    "wurth-744325550-catalog.pdf": "https://www.we-online.com/katalog/datasheet/744325550.pdf",
    "wurth-744325550-pbs.pdf": "https://katalog.we-online.com/pbs/datasheet/744325550.pdf",
    "samtec-ssq.pdf": "https://suddendocs.samtec.com/catalog_english/ssq.pdf",
    "samtec-tsw.pdf": "https://suddendocs.samtec.com/catalog_english/tsw.pdf",
    "jst-sh-jp.pdf": "https://www.jst-mfg.com/product/pdf/jpn/jSH.pdf",
    "jst-eh-jp.pdf": "https://www.jst-mfg.com/product/pdf/jpn/jEH.pdf",
}


def collect(entry):
    filename, url = entry
    target = EVIDENCE / "sources" / filename
    previous = PREVIOUS.get(filename)
    if previous and previous.get("url") == url and not previous.get("success") and not target.exists():
        return {**previous, "not_retried": True}
    record = {"url": url, "file": filename}
    try:
        if target.exists():
            payload = target.read_bytes()
            record["cached"] = True
        else:
            response = requests.get(url, timeout=60)
            record["status_code"] = response.status_code
            record["resolved_url"] = response.url
            response.raise_for_status()
            payload = response.content
            if filename.endswith(".pdf") and not payload.startswith(b"%PDF"):
                raise ValueError("Expected PDF response")
            target.write_bytes(payload)
        record["sha256"] = hashlib.sha256(payload).hexdigest()
        if filename.endswith(".pdf"):
            with fitz.open(target) as document:
                pages = [f"---PDF PAGE {index + 1}---\n{page.get_text()}" for index, page in enumerate(document)]
            target.with_suffix(".txt").write_text("\n".join(pages), encoding="utf-8")
            record["pages"] = len(pages)
        record["success"] = True
    except Exception as error:
        record["success"] = False
        record["error"] = str(error)
    return record


def main():
    global PREVIOUS
    (EVIDENCE / "sources").mkdir(parents=True, exist_ok=True)
    manifest = EVIDENCE / "sources-manifest.json"
    if manifest.exists():
        PREVIOUS = {entry["file"]: entry for entry in json.loads(manifest.read_text(encoding="utf-8"))}
    with ThreadPoolExecutor(max_workers=4) as executor:
        records = list(executor.map(collect, SOURCES.items()))
    (EVIDENCE / "sources-manifest.json").write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for filename, pages in {"kemet-x7r.pdf": (1, 4), "kemet-x5r-c1006.pdf": (0, 1, 3, 4, 5), "kyocera-c0g.pdf": (2,), "vishay-smbj.pdf": (1, 3, 4), "vishay-wslp.pdf": (1,)}.items():
        path = EVIDENCE / "sources" / filename
        if path.exists():
            with fitz.open(path) as document:
                for page_number in pages:
                    if page_number < len(document):
                        document[page_number].get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False).save(path.with_name(path.stem + f"-p{page_number + 1}.png"))
    print(json.dumps(records, ensure_ascii=False))


if __name__ == "__main__":
    main()
