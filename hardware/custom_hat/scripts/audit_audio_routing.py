"""Bind the routing plan to native audio pins, source controls and same-version reviews."""
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re

import pcbnew
import pipeline

from collect_audio_routing_sources import EVIDENCE, ROOT


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    directory = ROOT / "hardware/custom_hat/software/codec"
    tool = directory / "hat_audio.py"
    loader = importlib.util.spec_from_file_location("hat_audio", tool)
    audio = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(audio)
    catalog = json.loads((directory / "control-catalog.json").read_text(encoding="utf-8"))
    verification = json.loads((EVIDENCE / "routing-tool-audit.json").read_text(encoding="utf-8"))
    board_path = ROOT / "hardware/custom_hat/rev_a/custom_hat_rev_a.kicad_pcb"
    prior = pipeline.current_checkpoint()
    board = pcbnew.LoadBoard(str(board_path))
    expected = {
        "U701": {"10": "AUDIO_MIC_AC", "11": "AUDIO_MIC_REF", "15": "AUDIO_MIC_BIAS", "19": "AUDIO_HP_L", "23": "AUDIO_HP_R", "27": "AUDIO_LINE_L"},
        "U803": {"1": "AUDIO_AMP_EN", "3": "AUDIO_AMP_INP", "4": "AUDIO_AMP_INN", "5": "SPK_P", "8": "SPK_N"},
        "J504": {"1": "AUDIO_L", "2": "AUDIO_R", "3": "POWER_GND"}, "J505": {"1": "AUDIO_MIC", "2": "POWER_GND"},
        "J506": {"1": "SPK_P", "2": "SPK_N"}, "C317": {"1": "AUDIO_HP_L", "2": "AUDIO_L"},
        "C318": {"1": "AUDIO_HP_R", "2": "AUDIO_R"}, "C321": {"1": "AUDIO_LINE_L", "2": "AUDIO_AMP_INP"},
        "C322": {"1": "AUDIO_AMP_INN", "2": "POWER_GND"}, "C325": {"1": "AUDIO_MIC", "2": "AUDIO_MIC_AC"},
        "C326": {"1": "POWER_GND", "2": "AUDIO_MIC_REF"}, "R311": {"1": "AUDIO_AMP_EN", "2": "+3V3"},
        "R312": {"1": "AUDIO_MIC_BIAS", "2": "AUDIO_MIC"}}
    mismatches = []
    for reference, pins in expected.items():
        footprint = board.FindFootprintByReference(reference)
        actual = {pad.GetNumber(): pad.GetNetname() for pad in footprint.Pads()}
        mismatches.extend({"reference": reference, "pin": number, "actual": actual.get(number), "expected": net}
                          for number, net in pins.items() if actual.get(number) != net)
    source = EVIDENCE.parent / "driver-compatibility-20261031/sources/exact-sound__soc__codecs__tlv320aic3x.c"
    modules = json.loads((directory / "6.1.84-10-rk2410-nocsf/manifest.json").read_text(encoding="utf-8"))
    source_matches = catalog["codec_source_sha256"] == digest(source) == modules["source_hashes"]["tlv320aic3x.c"]
    verification_matches = digest(tool) == verification["source_sha256"] and digest(directory / "control-catalog.json") == verification["catalog_sha256"]
    plan = audio.make_plan(catalog, "both", True)
    settings = {row["control"]: row["values"] for row in plan["operations"]}
    combination = 2 * 10 ** (-6.5 / 20)
    calculations = {"alsa_output_raw_value": 105, "inverted_register_code": 118 - 105,
        "datasheet_table_10_51_gain_db": -6.5, "coherent_two_channel_linear_sum": combination,
        "coherent_sum_db": 20 * math.log10(combination), "default_pcm_raw": settings["PCM Playback Volume"],
        "default_pcm_nominal_db": -63.5 + .5 * settings["PCM Playback Volume"][0],
        "limit": "Ideal nominal gain arithmetic, not measured audio level, output power or distortion"}
    basis = {"tlv320aic3104": {"file": "../metadata-repair-20261030/sources/tlv320aic3104.pdf", "pages": [5, 65], "sections": ["Table7-1", "Table10-51"]},
             "pam8302a": {"file": "../metadata-repair-20261030/sources/PAM8302A.pdf", "pages": [2], "version": "DS41333 Rev6-2 May2021"}}
    for row in basis.values():
        row["sha256"] = digest(EVIDENCE / row["file"])
    links = []
    for document in (EVIDENCE / "research.md", directory / "AUDIO-ROUTING.md"):
        for target in re.findall(r"\]\(([^)]+)\)", document.read_text(encoding="utf-8")):
            if target.startswith(("http:", "https:", "#")):
                continue
            if not (document.parent / target.split("#")[0]).exists():
                links.append({"file": str(document), "target": target})
    result = {"pcb_sha256": digest(board_path), "review_binding": prior["review_binding"], "pcb_review_identity_preserved": digest(board_path) == prior["pcb_sha256"],
              "native_pin_mismatches": mismatches, "codec_source_and_modules_match": source_matches,
              "tool_and_fixture_report_match": verification_matches, "source_control_count": len(catalog["controls"]),
              "used_control_count": len(settings), "operation_count": len(plan["operations"]),
              "simulated_scenarios": len(verification["scenarios"]), "simulated_profiles": len(verification["profiles"]),
              "calculations": calculations, "manual_datasheet_basis": basis, "broken_links": links,
              "real_alsa_accessed": False, "hardware_tested": False, "manufacturing_released": False, "goal_complete": False}
    result["accepted_offline"] = all((result["pcb_review_identity_preserved"], not mismatches, source_matches, verification_matches,
        verification["accepted_offline"], len(verification["scenarios"]) == 10, len(verification["profiles"]) == 8,
        calculations["inverted_register_code"] == 13, calculations["default_pcm_nominal_db"] == -40, combination < 1, not links))
    (EVIDENCE / "final-audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    if not result["accepted_offline"]:
        raise RuntimeError("Audio source/board/route binding failed")


if __name__ == "__main__":
    main()
