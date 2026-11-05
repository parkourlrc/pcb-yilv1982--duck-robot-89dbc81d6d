import csv
import hashlib
import json
from pathlib import Path
import zipfile


root=Path(__file__).resolve().parents[3]
project=root/"hardware/custom_hat/rev_b"
review=project/"review-output"
evidence=root/"docs/references/扩展板乙版降本"
manifest=json.loads((project/"checkpoint.json").read_text(encoding="utf-8"))
digest=hashlib.sha256((project/"custom_hat_rev_b.kicad_pcb").read_bytes()).hexdigest()
if digest!=manifest["pcb_sha256"]:
    raise RuntimeError("Source changed after native checkpoint")
output=project/("quote-"+digest[:8])
output.mkdir(exist_ok=True)
archive=output/("CUSTOM-HAT-B0-"+digest[:8]+"-5PCS.zip")
with zipfile.ZipFile(archive,"w",zipfile.ZIP_DEFLATED) as target:
    for path in (review/"gerbers").iterdir():
        if path.is_file() and path.suffix!=".gbrjob":
            target.write(path,path.name)
with (review/"bom-grouped.csv").open(encoding="utf-8-sig",newline="") as stream:
    groups=list(csv.DictReader(stream))
with (output/"BOM.csv").open("w",encoding="utf-8-sig",newline="") as stream:
    writer=csv.writer(stream)
    writer.writerow(["Comment","Designator","Footprint","Manufacturer","Quantity","LCSC Part #","MPN","Function"])
    for group in groups:
        footprint=group["Footprint"].split(":")[-1]
        size=next((size for size in ("0603","1206","1210") if "_"+size+"_" in footprint),footprint)
        writer.writerow([group["MPN"],group["Designator"],size,group["Manufacturer"],group["Quantity"],group["LCSC Part #"],group["MPN"],group["Function"]])
with (review/"cpl-all-fitted.csv").open(encoding="utf-8-sig",newline="") as stream:
    positions=list(csv.DictReader(stream))
with (output/"CPL.csv").open("w",encoding="utf-8-sig",newline="") as stream:
    writer=csv.writer(stream)
    writer.writerow(["Designator","Mid X","Mid Y","Layer","Rotation"])
    for row in positions:
        writer.writerow([row["Designator"],row["Mid X"].removesuffix("mm"),row["Mid Y"].removesuffix("mm"),row["Layer"],row["Rotation"]])
record={"pcb_sha256":digest,"purpose":"5 boards complete assembly quotation only; not manufacturing release","remarks":"","pay":False,"fitted":len(positions),"groups":len(groups),"files":{path.name:hashlib.sha256(path.read_bytes()).hexdigest() for path in output.iterdir() if path.is_file()},"existing_orders_unchanged":["Y6","Y7","Y8"],"actual_quote_cny":None}
(output/"quote-manifest.json").write_text(json.dumps(record,indent=2),encoding="utf-8")
print(json.dumps({"output":str(output),"archive":str(archive),"fitted":len(positions),"groups":len(groups)},ensure_ascii=False))
