import hashlib
import json
from datetime import datetime
from pathlib import Path
import subprocess
from urllib.request import Request, urlopen

from pypdf import PdfReader


repository = Path(__file__).resolve().parents[3]
output = repository / "docs/references/扩展板乙版降本/sources"
output.mkdir(parents=True, exist_ok=True)
sources = {
    "ap63205.pdf": "https://www.diodes.com/datasheet/download/AP63200-AP63201-AP63203-AP63205.pdf",
    "lm5050-1.pdf": "https://www.ti.com/lit/ds/symlink/lm5050-1.pdf",
    "pam8406.pdf": "https://www.diodes.com/assets/Datasheets/PAM8406.pdf",
    "header-c2977589.pdf": "https://atta.szlcsc.com/upload/public/pdf/source/20251121/B609B00D0B3EB92686A2D2733E4211A9.pdf",
    "servo-c5151076.pdf": "https://atta.szlcsc.com/upload/public/pdf/source/20220909/93F02259E7146615AAD747544D994A1F.pdf",
    "ao3404a.pdf": "https://www.aosmd.com/sites/default/files/res/datasheets/AO3404A.pdf",
    "mic-c7587901.pdf": "https://atta.szlcsc.com/upload/public/pdf/source/20230901/7575319F733F22ECE149FBB07CD99356.pdf",
    "xc6206-umw.pdf": "https://atta.szlcsc.com/upload/public/pdf/source/20260423/ACBED32A813F1E5C9C286FBFCFC9B7FD.pdf",
    "smbj-vishay.pdf": "https://www.vishay.com/docs/88392/smbj.pdf",
    "yxc-12mhz.pdf": "https://atta.szlcsc.com/upload/public/pdf/source/20260116/277ADDA9FE6BD42D3AF503786E6466E2.pdf",
    "a1251-cjt.pdf": "https://atta.szlcsc.com/upload/public/pdf/source/20180913/C273009_2E94D2EE16A658F8B593BE6904D224FC.pdf",
    "murata-output-caps.pdf": "https://atta.szlcsc.com/upload/public/pdf/source/20230811/6AA9DB9766E5496748A2F980D0C94A94.pdf",
}
manifest_path = output / "manifest.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else []
for name, url in sources.items():
    path = output / name
    if path.exists():
        continue
    record = {"file": name, "url": url, "retrieved_at": datetime.now().astimezone().isoformat()}
    try:
        with urlopen(Request(url, headers={"User-Agent": "duck-robot-revb-review"}), timeout=40) as response:
            content = response.read()
        if not content.startswith(b"%PDF"):
            raise ValueError("Not a PDF response")
        path.write_bytes(content)
        document = PdfReader(path)
        text = "\n".join(f"\n--- PAGE {number + 1} ---\n" + page.extract_text() for number, page in enumerate(document.pages))
        path.with_suffix(".txt").write_text(text, encoding="utf-8")
        page_count = min(len(document.pages), 3 if name != "header-c2977589.pdf" else len(document.pages))
        subprocess.run(["pdftoppm", "-f", "1", "-l", str(page_count), "-r", "120", "-png", str(path), str(output / path.stem)], check=True, capture_output=True)
        record.update(success=True, bytes=len(content), pages=len(document.pages), sha256=hashlib.sha256(content).hexdigest())
    except Exception as error:
        record.update(success=False, error=str(error))
    manifest.append(record)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(record, ensure_ascii=False))
