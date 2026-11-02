"""Audit source, ABI and DT artifacts while preserving the board review identity."""
import hashlib
import json
from pathlib import Path
import re
import pipeline

from collect_radxa_driver_sources import EVIDENCE, ROOT, SOURCES
from inspect_radxa_runtime_package import KERNEL


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    package = ROOT / "hardware/custom_hat/software/codec" / KERNEL
    modules = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
    overlay = json.loads((package / "overlay-manifest.json").read_text(encoding="utf-8"))
    preparation = json.loads((EVIDENCE / "module-build-preparation.json").read_text(encoding="utf-8"))
    headers = Path(preparation["headers_directory"])
    failed = []
    for entry in modules["modules"]:
        if digest(package / entry["file"]) != entry["sha256"] or not entry["accepted"] or entry["symbol_crc_mismatches"]:
            failed.append(entry["file"])
    for filename, expected in modules["source_hashes"].items():
        if digest(SOURCES / ("exact-sound__soc__codecs__" + filename)) != expected:
            failed.append(filename)
    expected_files = {"manifest.json", "overlay-manifest.json", "duck-hat-audio.dtbo", "snd-soc-tlv320aic3x.ko", "snd-soc-tlv320aic3x-i2c.ko"}
    file_set_matches = {path.name for path in package.iterdir() if path.is_file()} == expected_files
    overlay_matches = digest(package / "duck-hat-audio.dtbo") == overlay["overlay_sha256"]
    overlay_matches = overlay_matches and digest(package.parent / "duck-hat-audio.dts") == overlay["overlay_source_sha256"]
    overlay_matches = overlay_matches and digest(ROOT / "hardware/custom_hat/rev_a/net-contract.json") == overlay["net_contract_sha256"]
    required_checks = ("accepted", "reset_gpio_matches", "codec_selects_reset_pinmux", "controller_selects_all_i2s_pins",
                       "i2c_m0_selected", "i2c_pins_match_header", "three_3v3_supplies_match", "header_supply_is_3v3",
                       "core_1v8_supply_matches", "core_supply_parent_matches", "cpu_dai_matches", "codec_dai_matches", "cpu_is_clock_master")
    variant_checks = len(overlay["base_checks"]) == 2 and all(all(row[key] for key in required_checks) for row in overlay["base_checks"])
    headers_match = digest(headers / ".config") == digest(SOURCES / ("runtime-config-" + KERNEL))
    prior = pipeline.current_checkpoint()
    pcb_hash = digest(ROOT / "hardware/custom_hat/rev_a/custom_hat_rev_a.kicad_pcb")
    broken_links = []
    documents = [EVIDENCE / "research.md", package.parent / "README.md", ROOT / "docs/specs/20261028-custom-hat/order-checklist.md"]
    for document in documents:
        for target in re.findall(r"\]\(([^)]+)\)", document.read_text(encoding="utf-8")):
            if target.startswith(("http:", "https:", "#")):
                continue
            if not (document.parent / target.split("#")[0]).exists():
                broken_links.append({"file": str(document), "target": target})
    result = {"kernel": KERNEL, "review_binding": prior["review_binding"], "module_count": len(modules["modules"]),
              "imported_symbol_crc_checks": sum(row["imported_symbols"] for row in modules["modules"]),
              "hash_or_abi_failures": failed, "package_file_set_matches": file_set_matches,
              "overlay_hashes_match": overlay_matches, "both_official_variants_checked": variant_checks,
              "headers_config_matches_official_image": headers_match, "headers_config_sha256": digest(headers / ".config"),
              "pcb_sha256": pcb_hash, "pcb_review_identity_preserved": pcb_hash == prior["pcb_sha256"],
              "broken_links": broken_links, "installed": False, "hardware_tested": False,
              "goal_complete": False, "manufacturing_released": False}
    result["accepted_offline"] = all((not failed, file_set_matches, overlay_matches, variant_checks, headers_match,
                                     result["pcb_review_identity_preserved"], not broken_links))
    (EVIDENCE / "offline-package-final-audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    if not result["accepted_offline"]:
        raise RuntimeError("Offline package audit failed")


if __name__ == "__main__":
    main()
