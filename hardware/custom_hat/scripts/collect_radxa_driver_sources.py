"""Archive pinned official kernel packaging and sensor API metadata for review."""
from datetime import datetime, timezone
import argparse
import hashlib
import json
from pathlib import Path
import urllib.error
import urllib.request


ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "docs/references/扩展板电路仿真工具/driver-compatibility-20261031"
SOURCES = EVIDENCE / "sources"


def fetch(name, url, records):
    path = SOURCES / name
    request = urllib.request.Request(url, headers={"User-Agent": "duck-robot-hat-review", "Accept": "application/vnd.github+json"} if "api.github.com" in url else {"User-Agent": "duck-robot-hat-review"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            content, status = response.read(), response.status
        path.write_bytes(content)
        record = {"file": name, "url": url, "status": status, "sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content)}
        records.append(record)
        return content
    except (urllib.error.URLError, TimeoutError) as error:
        records.append({"file": name, "url": url, "error": str(error)})
        return None
    finally:
        (EVIDENCE / "sources-manifest.json").write_text(json.dumps({"retrieved_at": datetime.now(timezone.utc).isoformat(), "sources": records}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--supplement", action="store_true")
    arguments = parser.parse_args()
    SOURCES.mkdir(parents=True, exist_ok=True)
    if arguments.supplement:
        manifest = json.loads((EVIDENCE / "sources-manifest.json").read_text(encoding="utf-8"))
        selection = json.loads((EVIDENCE / "source-selection.json").read_text(encoding="utf-8"))
        records = manifest["sources"]
        source_ref = selection["kernel_source_commit"]
        api = "https://api.github.com/repos/radxa/kernel/contents/"
        raw = "https://raw.githubusercontent.com/radxa/kernel/" + source_ref + "/"
        entries = json.loads(fetch("kernel-rockchip-dts-index.json", api + "arch/arm64/boot/dts/rockchip?ref=" + source_ref, records))
        for entry in entries:
            if "radxa-zero" in entry["name"]:
                fetch("kernel-" + entry["name"], entry["download_url"], records)
        for name in ("arch/arm64/configs/defconfig", "drivers/iio/gyro/Kconfig", "Documentation/devicetree/bindings/sound/tlv320aic3x.txt"):
            fetch("kernel-" + name.replace("/", "__"), raw + name, records)
        fetch("package-local-Makefile", "https://raw.githubusercontent.com/radxa-pkg/linux-rk2410/" + selection["package_commit"] + "/.github/local/Makefile.local", records)
        for directory in ("drivers/input/sensors/accel", "drivers/input/sensors/gyro"):
            result = fetch("kernel-" + directory.replace("/", "__") + "-index.json", api + directory + "?ref=" + source_ref, records)
            if result:
                for entry in json.loads(result):
                    if any(key in entry["name"].lower() for key in ("bmi", "bmg", "kconfig")) and entry["type"] == "file":
                        fetch("kernel-" + entry["path"].replace("/", "__"), entry["download_url"], records)
        bosch_raw = "https://raw.githubusercontent.com/boschsensortec/BMI08x_SensorAPI/" + selection["bosch_commit"] + "/"
        for name in ("bmi08x.h", "bmi08x.c", "examples/bmi08x/common/common.c", "examples/bmi08x/read_sensor_data/read_sensor_data.c"):
            fetch("bosch-" + name.replace("/", "__"), bosch_raw + name, records)
        print(json.dumps({"records": len(records), "new_failures": [row for row in records[30:] if "error" in row]}))
        return
    if (EVIDENCE / "sources-manifest.json").exists():
        raise FileExistsError("Inspect archived source metadata before retry")
    records = []
    base = "https://api.github.com/repos/radxa-pkg/linux-rk2410"
    fetch("package-tags.json", base + "/tags?per_page=100", records)
    package_commit = json.loads(fetch("package-main.json", base + "/commits/main", records))["sha"]
    tree = json.loads(fetch("package-tree.json", base + "/git/trees/" + package_commit + "?recursive=1", records))
    source_entry = next(item for item in tree["tree"] if item["path"] == "src")
    raw = "https://raw.githubusercontent.com/radxa-pkg/linux-rk2410/" + package_commit + "/"
    for name in (".gitmodules", "VERSION", "README.md", "Makefile.extra", "pkg.conf.template"):
        fetch("package-" + name.replace(".", "_"), raw + name, records)
    metadata = json.loads(fetch("package-src.json", base + "/contents/src?ref=" + package_commit, records))
    source_repository = metadata["submodule_git_url"].removesuffix(".git")
    if not source_repository.startswith("https://github.com/radxa/"):
        raise RuntimeError("Unexpected kernel source provider")
    source_ref = source_entry["sha"]
    kernel_raw = source_repository.replace("github.com", "raw.githubusercontent.com") + "/" + source_ref + "/"
    files = ("sound/soc/codecs/tlv320aic3x.c", "sound/soc/codecs/tlv320aic3x-i2c.c", "sound/soc/codecs/Kconfig",
             "drivers/iio/accel/Kconfig", "drivers/iio/gyro/bmg160_i2c.c",
             "arch/arm64/boot/dts/rockchip/rk3566-radxa-zero3w.dts", "arch/arm64/boot/dts/rockchip/rk356x-radxa-zero3.dtsi",
             "arch/arm64/boot/dts/rockchip/rk3568-pinctrl.dtsi", "arch/arm64/configs/rockchip_linux_defconfig")
    for name in files:
        fetch("kernel-" + name.replace("/", "__"), kernel_raw + name, records)
    for item in tree["tree"]:
        if item["type"] == "blob" and any(word in item["path"].lower() for word in ("config", "changelog", "control")):
            fetch("package-" + item["path"].replace("/", "__"), raw + item["path"], records)
    sensor_base = "https://api.github.com/repos/boschsensortec/BMI08x_SensorAPI"
    sensor_commit = json.loads(fetch("bosch-main.json", sensor_base + "/commits/master", records))["sha"]
    fetch("bosch-tree.json", sensor_base + "/git/trees/" + sensor_commit + "?recursive=1", records)
    for name in ("README.md", "LICENSE", "bmi08.h", "bmi08_defs.h", "bmi08a.c", "bmi08g.c"):
        fetch("bosch-" + name.replace("/", "__"), "https://raw.githubusercontent.com/boschsensortec/BMI08x_SensorAPI/" + sensor_commit + "/" + name, records)
    (EVIDENCE / "source-selection.json").write_text(json.dumps({"package_commit": package_commit, "kernel_source_repository": source_repository,
        "kernel_source_commit": source_ref, "bosch_commit": sensor_commit,
        "recorded_runtime_kernel": "6.1.84-10-rk2410-nocsf", "recorded_runtime_date": "2026-10-24",
        "current_runtime_verified": False, "exact_installed_package_equivalence_verified": False}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"files": len(records), "errors": [row for row in records if "error" in row], "package_commit": package_commit, "source_ref": source_ref}))


if __name__ == "__main__":
    main()
