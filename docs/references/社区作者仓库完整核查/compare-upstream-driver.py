import hashlib
import json
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen


base = Path(__file__).resolve().parent
checkout = Path("E:/Projects/kissqy-Microduck-analysis-20261104")
publication = json.loads((checkout / "microduck-hd1910/PUBLICATION-MANIFEST.json").read_text(encoding="utf-8"))
upstream = publication["upstream_firmware"]
source_url = f"https://raw.githubusercontent.com/pollen-robotics/microduck/{upstream['commit']}/tof/src/imu.rs"
record = {"observed_at": datetime.now().astimezone().isoformat(), "url": source_url, "publication_upstream": upstream}
try:
    with urlopen(Request(source_url, headers={"User-Agent": "duck-robot-hat-review"}), timeout=30) as response:
        content = response.read()
    (base / "pollen-pinned-head-imu.rs").write_bytes(content)
    current = (checkout / "microduck-hd1910/firmware/tof/src/imu.rs").read_bytes()
    record.update(success=True, bytes=len(content), sha256=hashlib.sha256(content).hexdigest(), kissqy_sha256=hashlib.sha256(current).hexdigest(), byte_identical=content == current, newline_normalized_identical=content.replace(b"\r\n", b"\n") == current.replace(b"\r\n", b"\n"))
except Exception as error:
    record.update(success=False, error=str(error))
(base / "pollen-driver-comparison.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(record, ensure_ascii=False, indent=2))
