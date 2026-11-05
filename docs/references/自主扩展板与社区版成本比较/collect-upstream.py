import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import Request, urlopen


base = Path(__file__).resolve().parent
sources = {
    "upstream-head.json": "https://api.github.com/repos/kissqy/Microduck-kissqy/commits/main",
    "upstream-hardware-readme.md": "https://raw.githubusercontent.com/kissqy/Microduck-kissqy/main/hardware/README.md",
    "upstream-amp-bom.json": "https://raw.githubusercontent.com/kissqy/Microduck-kissqy/main/hardware/AMP2.0-BOM.json",
    "upstream-amp-version.md": "https://raw.githubusercontent.com/kissqy/Microduck-kissqy/main/hardware/AMP2.0-VERSION.md",
    "upstream-timeline.md": "https://raw.githubusercontent.com/kissqy/Microduck-kissqy/main/hardware/HAT-TIMELINE.md",
}


def collect(item):
    name, url = item
    record = {"file": name, "url": url, "date": "2026-11-04"}
    try:
        with urlopen(Request(url, headers={"User-Agent": "duck-robot-design-review"}), timeout=35) as response:
            content = response.read()
        (base / name).write_bytes(content)
        record.update(success=True, bytes=len(content), sha256=hashlib.sha256(content).hexdigest())
    except Exception as error:
        record.update(success=False, error=str(error))
    return record


if __name__ == "__main__":
    with ThreadPoolExecutor(max_workers=5) as pool:
        result = list(pool.map(collect, sources.items()))
    (base / "upstream-manifest.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
