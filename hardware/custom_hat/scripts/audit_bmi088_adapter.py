"""Bind the adapter and failure checks to the actual HAT pad assignments."""
import hashlib
import json
from pathlib import Path
import re

import pcbnew
import pipeline

from build_bmi088_adapter import APP, EVIDENCE, SDK_COMMIT, VENDOR
from collect_radxa_driver_sources import ROOT, SOURCES


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    package = APP / "arm64"
    manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
    fault_path = EVIDENCE / "transport-fault-audit.json"
    faults = json.loads(fault_path.read_text(encoding="utf-8"))
    board_path = ROOT / "hardware/custom_hat/rev_a/custom_hat_rev_a.kicad_pcb"
    baseline = pipeline.current_checkpoint()
    board = pcbnew.LoadBoard(str(board_path))
    device = board.FindFootprintByReference("U501")
    pins = {pad.GetNumber(): pad.GetNetname() for pad in device.Pads()}
    expected = {"7": "+3V3", "14": "+3V3", "15": "+3V3", "10": "POWER_GND", "8": "I2C5_SCL", "9": "I2C5_SDA"}
    matches = {pin: {"actual": pins.get(pin), "expected": net, "matches": pins.get(pin) == net} for pin, net in expected.items()}
    dnc = not pins.get("5") or pins["5"].startswith("unconnected-")
    source_mismatches = [name for name in VENDOR if digest(SOURCES / ("bosch-" + name)) != manifest["source_hashes"][name]]
    production_hash = digest(APP / "bmi088_i2c.c")
    source_match = production_hash == manifest["source_hashes"]["bmi088_i2c.c"] == faults["production_source_sha256"]
    artifact_match = digest(package / "bmi088-i2c") == manifest["binary_sha256"]
    fault_binding = manifest["transport_fault_injection_done"] and digest(fault_path) == manifest["transport_fault_audit_sha256"]
    fault_binding = fault_binding and faults["accepted"] and len(faults["cases"]) == 7 and all(case["accepted"] and case["writes"] == 0 for case in faults["cases"])
    broken_links = []
    for document in (EVIDENCE / "research.md", APP / "README.md"):
        for target in re.findall(r"\]\(([^)]+)\)", document.read_text(encoding="utf-8")):
            if target.startswith(("http:", "https:", "#")):
                continue
            if not (document.parent / target.split("#")[0]).exists():
                broken_links.append({"file": str(document), "target": target})
    result = {"pcb_sha256": digest(board_path), "review_binding": baseline["review_binding"], "pcb_review_identity_preserved": digest(board_path) == baseline["pcb_sha256"],
              "sensor_value": device.GetValue(), "pins": matches, "csb2_dnc": dnc,
              "interface_basis": "Bosch Rev1.9 p44 and p48 plus native PCB pins: PS high/CSB1 high, SDO1 high=0x19, SDO2 low=0x68",
              "sdk_commit": SDK_COMMIT, "vendor_source_mismatches": source_mismatches, "source_and_fixture_bound": source_match,
              "binary_hash_matches": artifact_match, "failure_cases_bound_and_pass": fault_binding,
              "license_matches_vendor_archive": digest(APP / "LICENSE.Bosch") == digest(SOURCES / "bosch-LICENSE"),
              "broken_links": broken_links, "hardware_tested": False, "goal_complete": False, "manufacturing_released": False}
    result["accepted_offline"] = all((result["pcb_review_identity_preserved"], device.GetValue() == "BMI088",
        all(row["matches"] for row in matches.values()), dnc, not source_mismatches, source_match, artifact_match, fault_binding,
        result["license_matches_vendor_archive"], not broken_links))
    (EVIDENCE / "final-audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    if not result["accepted_offline"]:
        raise RuntimeError("IMU adapter and HAT contract audit failed")


if __name__ == "__main__":
    main()
