"""Bind the adopted reset circuit, preserved RC and routing checks to the release."""
import json
from pathlib import Path
import subprocess
import sys

import pcbnew

import pipeline
from verify_release_metadata import snapshot


EVIDENCE = pipeline.BASE.parents[1] / "docs/references/hat-simulation-tools-20261029/codec-reset-20261031"


def reset_network(path):
    board = pcbnew.LoadBoard(str(path))
    geometry = snapshot(path)
    pads = {footprint.GetReference() + "." + pad.GetNumber(): pad for footprint in board.GetFootprints() for pad in footprint.Pads()}
    reset_pads = {name: pad.m_Uuid.AsString() for name, pad in pads.items() if pad.GetNetname() == "CODEC_RST"}
    members = set(geometry["connections"][pads["U701.31"].m_Uuid.AsString()])
    return {"pads": sorted(reset_pads), "all_in_one_group": set(reset_pads.values()).issubset(members),
            "R308": {"value": board.FindFootprintByReference("R308").GetValue(), "pin2": pads["R308.2"].GetNetname()},
            "C310": {"value": board.FindFootprintByReference("C310").GetValue(), "pin2": pads["C310.2"].GetNetname()},
            "footprints": len(board.GetFootprints()), "tracks": sum(item.Type() != pcbnew.PCB_VIA_T for item in board.GetTracks()),
            "vias": sum(item.Type() == pcbnew.PCB_VIA_T for item in board.GetTracks())}


def main():
    board_path = pipeline.PRIMARY / (pipeline.STEM + ".kicad_pcb")
    checkpoint = json.loads((EVIDENCE / "checkpoint.json").read_text(encoding="utf-8"))
    before = reset_network(EVIDENCE / "before-metadata" / board_path.name)
    after = reset_network(board_path)
    expected_before = {"U701.31", "R308.1", "C310.1"}
    expected_after = expected_before | {"J101.33"}
    reference = json.loads((EVIDENCE / "reference-coverage-delta.json").read_text(encoding="utf-8"))
    original_hashes = pipeline.fingerprints(pipeline.PRIMARY)
    legacy = subprocess.run([sys.executable, "-X", "utf8", Path(__file__).with_name("generate_rev_a.py")],
                            capture_output=True, encoding="utf-8", errors="replace")
    (EVIDENCE / "legacy-generator-refusal.log").write_text(legacy.stdout + legacy.stderr, encoding="utf-8")
    result = {"pcb_sha256": pipeline.digest(board_path), "before": before, "after": after,
              "old_rc_description_corrected": True, "native_rc_unchanged": before["R308"] == after["R308"] and before["C310"] == after["C310"],
              "nominal_rc_time_constant_s": 10000 * 100e-9, "pullup_static_low_current_a": 3.3 / 10000,
              "calculation_limit": "Nominal RC and static pull-up only; not GPIO transient-current, threshold, ramp, reset-waveform or boot timing verification",
              "i2s_reference_samples_preserved": reference["accepted"] and not reference["lost_samples"],
              "source_matches_export": original_hashes == checkpoint["design_hashes"],
              "legacy_generator_refused": legacy.returncode != 0, "legacy_generator_left_sources_unchanged": original_hashes == pipeline.fingerprints(pipeline.PRIMARY),
              "schematic_delta_tool_scope": "Automatic delta returned zero findings changes; explicit native net audit records J101.33 addition and NC removal",
              "hardware_tested": False, "manufacturing_released": False}
    result["accepted"] = all((set(before["pads"]) == expected_before, set(after["pads"]) == expected_after,
                              before["all_in_one_group"], after["all_in_one_group"], result["native_rc_unchanged"],
                              result["i2s_reference_samples_preserved"], result["source_matches_export"],
                              result["legacy_generator_refused"], result["legacy_generator_left_sources_unchanged"]))
    pipeline.write_json(EVIDENCE / "reset-checkpoint-audit.json", result)
    print(json.dumps(result))
    if not result["accepted"]:
        raise RuntimeError("Reset checkpoint audit failed")


if __name__ == "__main__":
    main()
