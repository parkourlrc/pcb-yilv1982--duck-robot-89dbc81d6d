"""Match the separate Excellon outputs to every native round hole and the codec via."""
import csv
import argparse
import json
import math
import re
from pathlib import Path

import pcbnew

import pipeline
from qualify_codec_pth import EVIDENCE, IDENTIFIER
from separate_codec_drills import OUTPUT


def read_drills(path, plating):
    text = path.read_text(encoding="utf-8")
    marker = "Plated" if plating == "pth" else "NonPlated"
    if "METRIC" not in text or "G90" not in text or "TF.FileFunction," + marker + ",1,4" not in text:
        raise RuntimeError("Unexpected Excellon coordinate/plating format")
    tools, hits, selected = {}, [], None
    for line in text.splitlines():
        definition = re.fullmatch(r"T(\d+)C([0-9.]+)", line)
        selection = re.fullmatch(r"T(\d+)", line)
        coordinate = re.fullmatch(r"X(-?[0-9.]+)Y(-?[0-9.]+)", line)
        if definition:
            tools[definition.group(1)] = float(definition.group(2))
        elif selection:
            selected = selection.group(1)
        elif coordinate:
            if selected not in tools:
                raise RuntimeError("Drill coordinate without a known tool")
            hits.append({"file": path.name, "plating": plating, "tool": selected, "diameter_mm": tools[selected],
                         "cam_mm": [float(coordinate.group(1)), float(coordinate.group(2))]})
        elif line.startswith("X") or "G85" in line:
            raise RuntimeError("Unsupported coordinate/slot syntax; cannot claim complete audit")
    return hits


def main():
    global EVIDENCE, OUTPUT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    EVIDENCE = arguments.evidence.resolve() if arguments.evidence else EVIDENCE
    OUTPUT = arguments.output.resolve() if arguments.output else OUTPUT
    board_path = pipeline.PRIMARY / (pipeline.STEM + ".kicad_pcb")
    board = pcbnew.LoadBoard(str(board_path))
    expected = []
    for footprint in board.GetFootprints():
        for pad in footprint.Pads():
            drill = pad.GetDrillSize()
            if not drill.x:
                continue
            if drill.x != drill.y:
                raise RuntimeError("Slot requires its own export audit")
            expected.append({"id": footprint.GetReference() + "." + pad.GetNumber(), "diameter_mm": pcbnew.ToMM(drill.x),
                             "plating": "npth" if pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH else "pth",
                             "cam_mm": [pcbnew.ToMM(pad.GetPosition().x), -pcbnew.ToMM(pad.GetPosition().y)]})
    for via in board.GetTracks():
        if via.Type() != pcbnew.PCB_VIA_T:
            continue
        if via.GetViaType() != pcbnew.VIATYPE_THROUGH:
            raise RuntimeError("Blind/buried via remains; expected all-through design")
        expected.append({"id": via.m_Uuid.AsString(), "diameter_mm": pcbnew.ToMM(via.GetDrill()), "plating": "pth",
                         "cam_mm": [pcbnew.ToMM(via.GetPosition().x), -pcbnew.ToMM(via.GetPosition().y)]})
    expected_files = {pipeline.STEM + "-PTH.drl", pipeline.STEM + "-NPTH.drl"}
    if {path.name for path in OUTPUT.glob("*.drl")} != expected_files:
        raise RuntimeError("Unexpected or stale drill files in manufacturing package")
    unmatched = list(expected)
    matches = []
    for plating in ("pth", "npth"):
        for hit in read_drills(OUTPUT / (pipeline.STEM + "-" + plating.upper() + ".drl"), plating):
            candidates = [row for row in unmatched if row["plating"] == plating and abs(row["diameter_mm"] - hit["diameter_mm"]) < 1e-6
                          and math.dist(row["cam_mm"], hit["cam_mm"]) <= .001]
            if len(candidates) != 1:
                raise RuntimeError("Unmatched or ambiguous Excellon hit: " + str(hit))
            match = candidates[0]
            unmatched.remove(match)
            matches.append({"source_id": match["id"], **hit, "quantization_error_mm": math.dist(match["cam_mm"], hit["cam_mm"])})
    with (OUTPUT / "via-process-requirements.csv").open(encoding="utf-8-sig", newline="") as stream:
        processes = list(csv.DictReader(stream))
    frames_valid = all(abs(float(row["CAM_X_nominal_mm"]) - float(row["X_mm"])) < 1e-9 and
                       abs(float(row["CAM_Y_nominal_mm"]) + float(row["Y_mm"])) < 1e-9 for row in processes)
    codec = next(row for row in matches if row["source_id"] == IDENTIFIER)
    result = {"pcb_sha256": pipeline.digest(board_path), "matched_round_holes": len(matches),
              "pth_hits": sum(row["plating"] == "pth" for row in matches), "npth_hits": sum(row["plating"] == "npth" for row in matches),
              "unmatched_native_holes": unmatched, "maximum_quantization_error_mm": max(row["quantization_error_mm"] for row in matches),
              "matching_tolerance_mm": .001, "codec_hole": codec, "process_csv_coordinate_frames_valid": frames_valid,
              "drill_files": {name: pipeline.digest(OUTPUT / name) for name in sorted(expected_files)},
              "matches": matches, "manufacturing_approved": False}
    result["accepted"] = not unmatched and len(matches) == len(expected) and frames_valid and codec["plating"] == "pth" and codec["diameter_mm"] == .15
    pipeline.write_json(EVIDENCE / "drill-export-audit.json", result)
    print(json.dumps({key: value for key, value in result.items() if key != "matches"}))
    if not result["accepted"]:
        raise RuntimeError("Drill export audit failed")


if __name__ == "__main__":
    main()
