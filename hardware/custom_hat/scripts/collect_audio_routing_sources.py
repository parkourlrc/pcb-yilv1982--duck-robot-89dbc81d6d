"""Archive exact ASoC naming and ALSA control-format references for routing review."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import urllib.request


ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "docs/references/hat-simulation-tools-20261029/audio-routing-20261031"
SOURCES = EVIDENCE / "sources"


def main():
    SOURCES.mkdir(parents=True, exist_ok=True)
    references = {
        "soc-dapm.c": "https://raw.githubusercontent.com/radxa/kernel/e6d12a77c8bc0ea6decbd3e4604ec131d4032c30/sound/soc/soc-dapm.c",
        "amixer-v1.2.8.c": "https://raw.githubusercontent.com/alsa-project/alsa-utils/v1.2.8/amixer/amixer.c",
        "alsa-control-interface.html": "https://www.alsa-project.org/alsa-doc/alsa-lib/control.html",
    }
    rows = []
    for name, url in references.items():
        target = SOURCES / name
        if target.exists():
            raise FileExistsError(target)
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "duck-robot-hat-review"}), timeout=30) as response:
            data = response.read()
        target.write_bytes(data)
        rows.append({"file": name, "url": url, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)})
    (EVIDENCE / "sources-manifest.json").write_text(json.dumps({"retrieved_at": datetime.now(timezone.utc).isoformat(), "sources": rows}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(rows))


if __name__ == "__main__":
    main()
