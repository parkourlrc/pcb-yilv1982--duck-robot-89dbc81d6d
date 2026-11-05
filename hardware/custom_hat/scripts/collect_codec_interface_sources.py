"""Archive the primary reset, header and reference-kernel interface sources."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "docs/references/扩展板电路仿真工具/codec-reset-20261031"


def main():
    directory = EVIDENCE / "sources"
    directory.mkdir(parents=True, exist_ok=True)
    base = "https://raw.githubusercontent.com/torvalds/linux/v6.1/"
    requests_list = [
        ("radxa-hardware-interface.html", "https://docs.radxa.com/en/zero/zero3/hardware-design/hardware-interface"),
        ("linux-v6.1-tlv320aic3x.c", base + "sound/soc/codecs/tlv320aic3x.c"),
        ("linux-v6.1-tlv320aic3x-binding.txt", base + "Documentation/devicetree/bindings/sound/tlv320aic3x.txt"),
        ("linux-v6.1-rk3568-pinctrl.dtsi", base + "arch/arm64/boot/dts/rockchip/rk3568-pinctrl.dtsi"),
        ("linux-v6.1-accel-Kconfig.txt", base + "drivers/iio/accel/Kconfig"),
        ("linux-v6.1-bmg160-i2c.c", base + "drivers/iio/gyro/bmg160_i2c.c"),
    ]
    manifest = []
    for name, url in requests_list:
        record = {"file": name, "url": url, "retrieved_at": datetime.now(timezone.utc).isoformat()}
        try:
            response = requests.get(url, timeout=45)
            record["status"] = response.status_code
            response.raise_for_status()
            (directory / name).write_bytes(response.content)
            record["sha256"] = hashlib.sha256(response.content).hexdigest()
            record["bytes"] = len(response.content)
        except requests.RequestException as error:
            record["error"] = str(error)
        manifest.append(record)
    datasheet = EVIDENCE.parent / "metadata-repair-20261030/sources/tlv320aic3104.pdf"
    manifest.append({"file": datasheet.relative_to(ROOT).as_posix(), "url": "https://www.ti.com/lit/ds/symlink/tlv320aic3104.pdf",
                     "sha256": hashlib.sha256(datasheet.read_bytes()).hexdigest(), "pages": [22, 91], "version": "SLAS510G", "fresh_download": False})
    (EVIDENCE / "sources-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest))


if __name__ == "__main__":
    main()
