import hashlib
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from urllib.request import urlopen

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parent / "substitution-sources"
SOURCES = {
    "ap64500": "https://www.diodes.com/assets/Datasheets/AP64500.pdf",
    "ap64500-lcsc-mirror": "https://www.lcsc.com/datasheet/C2070920.pdf",
    "ap64500-lcsc-document": "https://datasheet.lcsc.com/datasheet/pdf/33f261fea70469dad53d64b3fab8d8d9.pdf",
    "ap64500-current": "https://www.diodes.com/datasheet/download/AP64500.pdf",
    "kemet-c0805c332j5gactu": "https://search.kemet.com/component-documentation/download/specsheet/C0805C332J5GACTU",
    "panasonic-erj": "https://industrial.panasonic.com/cdbs/www-data/pdf/RDA0000/AOA0000C304.pdf",
    "panasonic-resistor-lands": "https://industrial.panasonic.com/cdbs/www-data/pdf/RDM0000/DMM0000COL17.pdf",
    "murata-grm32-spec": "https://pim.murata.com/asset/pim4/ceramicCapacitorSMD/GRM32ER71E226KE15-04CA-EN_PDF_CERAMICCAPACITORSMD?lastModifiedDatetime=20260730173647",
    "murata-grm32-characteristics": "https://pimapi.murata.com/public/api/pim/v1/characteristics/search/technical?partNum=GRM32ER71E226KE15%23&productCategoryId=ceramicCapacitorSMD&displayLanguage=en&languageRegion=en-us",
    "murata-grj155-spec": "https://pim.murata.com/asset/pim4/ceramicCapacitorSMD/GRJ155R60J106ME11-02A-EN_PDF_CERAMICCAPACITORSMD?lastModifiedDatetime=20260611113037",
    "murata-grj155-characteristics": "https://pimapi.murata.com/public/api/pim/v1/characteristics/search/technical?partNum=GRJ155R60J106ME11%23&productCategoryId=ceramicCapacitorSMD&displayLanguage=en&languageRegion=en-us",
    "koher-mda1040": "http://www.kohergroup.com/template/default/pdf/MDA1040.pdf",
}


def collect(source):
    name, url = source
    cached_manifest = ROOT / (name + "-manifest.json")
    if cached_manifest.exists():
        cached = json.loads(cached_manifest.read_text(encoding="utf-8"))
        if cached.get("success") and (ROOT / (name + ".pdf")).exists():
            return cached
    record = {"url": url, "date": "2026-11-03", "file": name + ".pdf"}
    try:
        with urlopen(url, timeout=45) as response:
            record["status_code"] = response.status
            record["resolved_url"] = response.url
            content = response.read()
            record["content_type"] = response.headers.get("Content-Type")
        if content.startswith(b"PK"):
            target = ROOT / (name + ".zip")
            target.write_bytes(content)
            record.update(success=True, file=target.name, sha256=hashlib.sha256(content).hexdigest())
            (ROOT / (name + "-manifest.json")).write_text(json.dumps(record, indent=2), encoding="utf-8")
            return record
        if not content.startswith(b"%PDF"):
            raise ValueError("Response is not a PDF")
        target = ROOT / (name + ".pdf")
        target.write_bytes(content)
        reader = PdfReader(target)
        text = "\n".join(
            f"---PDF PAGE {number}---\n{page.extract_text(extraction_mode='layout')}"
            for number, page in enumerate(reader.pages, 1)
        )
        target.with_suffix(".txt").write_text(text, encoding="utf-8")
        record.update(success=True, pages=len(reader.pages), sha256=hashlib.sha256(content).hexdigest())
    except Exception as error:
        record.update(success=False, error=str(error))
    (ROOT / (name + "-manifest.json")).write_text(json.dumps(record, indent=2), encoding="utf-8")
    return record


if __name__ == "__main__":
    ROOT.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        for record in pool.map(collect, SOURCES.items()):
            print(json.dumps(record, ensure_ascii=False))
