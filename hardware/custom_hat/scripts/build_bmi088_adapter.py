"""Build the pinned Bosch API with the HAT Linux I2C adapter, without hardware I/O."""
from datetime import datetime, timezone
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess

from build_codec_module import linux_path, wsl
from collect_radxa_driver_sources import ROOT, SOURCES


EVIDENCE = ROOT / "docs/references/hat-simulation-tools-20261029/bmi088-adapter-20261031"
APP = ROOT / "hardware/custom_hat/software/imu"
SDK_COMMIT = "c1ed227e7bb7da1fa600bbd4e5c82d0da1eb416a"
VENDOR = ("bmi08a.c", "bmi08g.c", "bmi08xa.c", "bmi08.h", "bmi08_defs.h", "bmi08x.h")


def execute(name, arguments, expected=0):
    result = subprocess.run(arguments, capture_output=True, encoding="utf-8", errors="replace")
    (EVIDENCE / (name + ".log")).write_text(result.stdout + result.stderr, encoding="utf-8")
    if result.returncode != expected:
        raise RuntimeError(name + " failed; see saved output")
    return result.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replace-reviewed", action="store_true")
    arguments = parser.parse_args()
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    output = APP / "arm64"
    if output.exists() and not arguments.replace_reviewed:
        raise FileExistsError("Inspect current IMU binary before replacement")
    source_manifest = json.loads((SOURCES.parent / "sources-manifest.json").read_text(encoding="utf-8"))["sources"]
    expected = {row["file"]: row["sha256"] for row in source_manifest if row.get("sha256") and SDK_COMMIT in row["url"]}
    build = Path(os.environ["LOCALAPPDATA"]) / "duck-robot-tools/bmi088-hat" / SDK_COMMIT[:12]
    build.mkdir(parents=True, exist_ok=True)
    build = build.resolve()
    if output.exists():
        previous = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
        if hashlib.sha256((output / previous["binary"]).read_bytes()).hexdigest() != previous["binary_sha256"]:
            raise RuntimeError("Existing output differs from its manifest")
        history = EVIDENCE / "build-history" / previous["binary_sha256"][:16]
        if not history.exists():
            cached_source = build / "bmi088_i2c.c"
            if hashlib.sha256(cached_source.read_bytes()).hexdigest() != previous["source_hashes"][cached_source.name]:
                raise RuntimeError("Previous source must be preserved before replacement")
            shutil.copytree(output, history)
            shutil.copy2(cached_source, history / cached_source.name)
            fault_report = EVIDENCE / "transport-fault-audit.json"
            if fault_report.is_file():
                shutil.copy2(fault_report, history / fault_report.name)
    hashes = {}
    for filename in VENDOR:
        source = SOURCES / ("bosch-" + filename)
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        if digest != expected.get(source.name):
            raise RuntimeError("Bosch archive identity mismatch: " + filename)
        hashes[filename] = digest
        shutil.copy2(source, build / filename)
    source = APP / "bmi088_i2c.c"
    shutil.copy2(source, build / source.name)
    hashes[source.name] = hashlib.sha256(source.read_bytes()).hexdigest()
    build_linux = linux_path(build)
    sources = [build_linux + "/" + name for name in ("bmi088_i2c.c", "bmi08a.c", "bmi08g.c", "bmi08xa.c")]
    flags = ["-std=c11", "-O2", "-Wall", "-Wextra", "-Werror", "-I" + build_linux]
    host = build / "bmi088-i2c-host"
    target = build / "bmi088-i2c-arm64"
    execute("native-build", wsl("gcc", *flags, *sources, "-o", linux_path(host)))
    execute("arm64-build", wsl("aarch64-linux-gnu-gcc", *flags, "-static", *sources, "-o", linux_path(target)))
    description = json.loads(execute("describe-no-hardware", wsl(linux_path(host), "--describe")))
    execute("missing-mode-refused", wsl(linux_path(host)), expected=1)
    execute("missing-device-refused", wsl(linux_path(host), "--stream"), expected=1)
    execute("invalid-count-refused", wsl(linux_path(host), "--stream", "--device", "/nonexistent", "--samples", "-1"), expected=1)
    execute("non-i2c-device-refused", wsl(linux_path(host), "--probe", "--device", "/dev/null"), expected=1)
    elf = execute("arm64-elf", wsl("aarch64-linux-gnu-readelf", "-h", "-l", "-d", linux_path(target)))
    data = target.read_bytes()
    machine = struct.unpack("<H", data[18:20])[0]
    accepted = machine == 183 and "INTERP" not in elf and "There is no dynamic section" in elf
    accepted = accepted and description == {"sensor": "BMI088", "sdk_commit": SDK_COMMIT, "accel_address": 25, "gyro_address": 104,
                                          "expected_accel_id": 30, "expected_gyro_id": 15, "profile_odr_hz": 100, "hardware_accessed": False}
    if not accepted:
        raise RuntimeError("Static ARM64 or adapter description check failed")
    output.mkdir(exist_ok=True)
    shutil.copy2(target, output / "bmi088-i2c")
    shutil.copy2(SOURCES / "bosch-LICENSE", APP / "LICENSE.Bosch")
    result = {"built_at": datetime.now(timezone.utc).isoformat(), "sdk_commit": SDK_COMMIT, "source_hashes": hashes,
              "binary": "bmi088-i2c", "binary_sha256": hashlib.sha256(data).hexdigest(), "binary_bytes": len(data),
              "elf_machine": machine, "static_linked": True, "host_description": description,
              "checks": ["native and ARM64 builds with warnings as errors", "describe without hardware", "missing action/device and invalid count refused", "non-I2C device refused before transfers", "ARM64 static ELF"],
              "hardware_exercised": False, "transport_fault_injection_done": False, "installed": False,
              "limits": ["No real I2C transfer or sensor sampling", "Polling is not accel/gyro synchronization", "No robot-frame transform or calibration", "Static glibc build not yet run on the target"],
              "accepted_offline": True}
    for path in (output / "manifest.json", EVIDENCE / "build-audit.json"):
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
