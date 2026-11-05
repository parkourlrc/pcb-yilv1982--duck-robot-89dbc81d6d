"""Archive manufacturer per-part documents needed for effective-capacitance review."""
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import fitz
import collect_bom_sources as collector


EVIDENCE=Path(__file__).resolve().parents[3]/"docs/references/扩展板电路仿真工具/capacitor-models-20261031"
PARTS=("C1206C226M4PACTU","C1206C106K3RACTU","C0805C105K5RACTU","C0402C105K4PACTU","C0805C225K5RACTU",
       "C1206C106K5RACTU","C1206C226M3PACTU","C1210C226K3RACTU","C0805C125K5RACTU")
SOURCES={part+".pdf":"https://search.kemet.com/component-documentation/download/specsheet/"+part for part in PARTS}
SOURCES["kemet-ceramics-guide.pdf"]="https://www.kemet.com/content/dam/kemet/lightning/documents/ec-content/KEMET-Ceramics-FAQ-and-Application-Guide.pdf"


def main():
    (EVIDENCE/"sources").mkdir(parents=True,exist_ok=True)
    collector.EVIDENCE=EVIDENCE
    manifest=EVIDENCE/"sources-manifest.json"
    if manifest.exists():
        collector.PREVIOUS={entry["file"]:entry for entry in json.loads(manifest.read_text(encoding="utf-8"))}
    with ThreadPoolExecutor(max_workers=3) as executor:
        records=list(executor.map(collector.collect,SOURCES.items()))
    for entry in records:
        if not entry.get("success"):
            continue
        path=EVIDENCE/"sources"/entry["file"]
        with fitz.open(path) as document:
            if path.stem in PARTS:
                entry["part_number_found_in_pdf"]=path.stem in "".join(page.get_text() for page in document)
                for index,page in enumerate(document):
                    page.get_pixmap(matrix=fitz.Matrix(1.5,1.5),alpha=False).save(path.with_name(path.stem+f"-p{index+1}.png"))
    manifest.write_text(json.dumps(records,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(records,ensure_ascii=False))


if __name__=="__main__":
    main()
