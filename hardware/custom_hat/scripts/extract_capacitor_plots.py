"""Extract the original plot images embedded in manufacturer per-part PDFs."""
import hashlib
import json

import fitz
from collect_capacitor_models import EVIDENCE, PARTS


def main():
    results=[]
    names=("impedance-esr","capacitance-frequency","inductance-frequency","ripple-current","ripple-voltage","dc-bias")
    for part in PARTS:
        pdf=EVIDENCE/"sources"/(part+".pdf")
        if not pdf.exists():
            print("Skipping absent source PDF: "+part)
            continue
        with fitz.open(pdf) as document:
            page=document[1]
            images=[]
            for entry in page.get_images():
                if entry[2:4]!=(640,480):
                    continue
                rectangle=page.get_image_rects(entry[0])[0]
                images.append((rectangle.y0,rectangle.x0,entry[0]))
            images.sort()
            if len(images)!=6:
                raise RuntimeError("Unexpected plot layout for "+part)
            for name,(_,_,xref) in zip(names,images):
                data=document.extract_image(xref)
                path=EVIDENCE/"sources"/(part+"-"+name+"."+data["ext"])
                path.write_bytes(data["image"])
                results.append({"part":part,"pdf":pdf.name,"pdf_page":2,"xref":xref,"plot":name,"file":path.name,"sha256":hashlib.sha256(path.read_bytes()).hexdigest()})
    (EVIDENCE/"plot-manifest.json").write_text(json.dumps(results,indent=2)+"\n",encoding="utf-8")
    print("Extracted "+str(len(results))+" original manufacturer plot images")


if __name__=="__main__":
    main()
