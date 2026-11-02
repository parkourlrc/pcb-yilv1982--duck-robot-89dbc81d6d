"""Check identity and transaction failure handling with no real device access."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

from build_codec_module import linux_path, wsl
from build_bmi088_adapter import APP, EVIDENCE, SDK_COMMIT, VENDOR, execute


def main():
    manifest_path = APP / "arm64/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    source = APP / "bmi088_i2c.c"
    if hashlib.sha256(source.read_bytes()).hexdigest() != manifest["source_hashes"][source.name]:
        raise RuntimeError("Production binary source no longer matches the reviewed source")
    build = (Path(os.environ["LOCALAPPDATA"]) / "duck-robot-tools/bmi088-hat" / SDK_COMMIT[:12]).resolve()
    build_linux = linux_path(build)
    executable = build / "bmi088-i2c-fixture"
    shim = APP / "bmi088_fault_shim.c"
    wrappers = ["-Wl,--wrap=" + name for name in ("open", "fstat", "flock", "close", "ioctl")]
    sources = [linux_path(source), linux_path(shim)] + [build_linux + "/" + name for name in VENDOR if name.endswith(".c")]
    execute("fault-fixture-build", wsl("gcc", "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror", "-I" + build_linux,
                                      *sources, *wrappers, "-o", linux_path(executable)))
    cases = [
        ("probe", "--probe", 0, 2, True),
        ("wrong-accel", "--stream", 1, 2, False),
        ("wrong-gyro", "--stream", 1, 2, False),
        ("partial-accel", "--probe", 1, 1, None),
        ("partial-gyro", "--probe", 1, 2, None),
        ("read-nack", "--probe", 1, 1, None),
        ("kernel-owned", "--stream", 1, 0, None),
    ]
    results = []
    for scenario, mode, exit_status, expected_reads, identity in cases:
        command = wsl("env", "BMI088_FIXTURE=" + scenario, linux_path(executable), mode, "--device", "/dev/i2c-fixture")
        result = subprocess.run(command, capture_output=True, encoding="utf-8", errors="replace")
        (EVIDENCE / ("fault-" + scenario + ".log")).write_text(result.stdout + result.stderr, encoding="utf-8")
        counters = json.loads(re.search(r"FIXTURE (\{.*\})", result.stderr)[1])
        objects = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
        actual_identity = objects[0]["identities_match"] if objects else None
        accepted = result.returncode == exit_status and counters == {"reads": expected_reads, "writes": 0, "malformed": 0}
        accepted = accepted and actual_identity == identity and not any(row["type"] in {"profile", "sample"} for row in objects)
        results.append({"scenario": scenario, "exit_status": result.returncode, **counters, "identity": actual_identity, "accepted": accepted})
    report = {"verified_at": datetime.now(timezone.utc).isoformat(), "production_source_sha256": manifest["source_hashes"][source.name],
              "shim_sha256": hashlib.sha256(shim.read_bytes()).hexdigest(), "cases": results,
              "accepted": all(row["accepted"] for row in results), "hardware_accessed": False,
              "scope": "Native-host source linked with fake device system calls; checks IDs and failed reads before any configuration write. Does not test successful configuration, sampling, ARM64 execution, or physical I2C."}
    report_path = EVIDENCE / "transport-fault-audit.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if not report["accepted"]:
        raise RuntimeError("A hardware-write prevention case failed")
    manifest["transport_fault_injection_done"] = True
    manifest["transport_fault_audit_sha256"] = hashlib.sha256(report_path.read_bytes()).hexdigest()
    manifest["transport_fault_scope"] = report["scope"]
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
