import hashlib
import json
from pathlib import Path
import zipfile


base = Path(__file__).resolve().parent
root = base.parents[2]
source = root / "hardware/custom_hat/order-submission/20261103-five-hats/HAT-A1-86654c03-single-unit-PCB.zip"
target = base / "CUSTOM-HAT-A1-86654c03-5PCS.zip"
files = []
excluded = []
with zipfile.ZipFile(source) as original, zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as output:
    for item in original.infolist():
        name = Path(item.filename).name
        if name in {"ORDER-NOTES.txt", "via-process-requirements.csv"}:
            excluded.append(item.filename)
            continue
        if item.is_dir():
            continue
        data = original.read(item)
        output.writestr(item, data)
        files.append({"file": item.filename, "sha256": hashlib.sha256(data).hexdigest()})
reference = root / "docs/references/自主扩展板与社区版成本比较/kissqy-HAT-AMP2.0-411878f.epro2"
reference_target = base / "KISSQY-HAT-AMP2-411878f-5PCS.epro2"
reference_target.write_bytes(reference.read_bytes())
reference_zip = base / "KISSQY-HAT-AMP2-411878f-5PCS.zip"
with zipfile.ZipFile(reference_zip, "w", zipfile.ZIP_DEFLATED) as output:
    output.writestr(reference_target.name, reference_target.read_bytes())
manifest = {
    "date": "2026-11-04", "purpose": "two designs 5 units each quotation orders, no free-text remarks, no payment",
    "custom_source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    "custom_output": target.name, "custom_output_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
    "custom_fabrication_files_byte_identical": True, "custom_excluded_text_attachments": excluded, "custom_files": files,
    "kissqy_output": reference_target.name, "kissqy_sha256": hashlib.sha256(reference_target.read_bytes()).hexdigest(),
    "kissqy_zip": reference_zip.name, "kissqy_zip_sha256": hashlib.sha256(reference_zip.read_bytes()).hexdigest(),
    "cad_modified": False, "manufacturing_released": False,
}
(base / "quote-packages.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(manifest, ensure_ascii=False))
