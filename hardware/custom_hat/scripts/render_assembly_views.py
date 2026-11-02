"""Plot clear native assembly views from a temporary display-only copy."""
import argparse
import csv
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

import pcbnew

import pipeline
from verify_release_metadata import snapshot


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--evidence", required=True, type=Path)
    arguments = parser.parse_args()
    output, evidence = arguments.output.resolve(), arguments.evidence.resolve()
    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    source_hashes = pipeline.fingerprints(pipeline.PRIMARY)
    if source_hashes != manifest["design_hashes"]:
        raise RuntimeError("Assembly package does not match current design")
    source_board = pipeline.PRIMARY / (pipeline.STEM + ".kicad_pcb")
    before = snapshot(source_board)
    with (output / "bom-tracking.csv").open(encoding="utf-8-sig", newline="") as stream:
        fitted = {reference for row in csv.DictReader(stream) if row["DNP"] == "False" for reference in row["Reference"].split(",")}
    reference_changes = []
    with tempfile.TemporaryDirectory(prefix="assembly-display-only-", dir=evidence) as temporary:
        project = Path(temporary).resolve()
        if not project.is_relative_to(evidence):
            raise RuntimeError("Temporary cleanup target is outside the evidence directory")
        for path in pipeline.design_files(pipeline.PRIMARY):
            target = project / path.relative_to(pipeline.PRIMARY)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
        board_path = project / source_board.name
        board = pcbnew.LoadBoard(str(board_path))
        for footprint in board.GetFootprints():
            footprint.Value().SetText("")
            if footprint.GetReference() == "TP803":
                for item in footprint.GraphicalItems():
                    if hasattr(item, "GetText") and "REFERENCE" in item.GetText().upper():
                        item.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(132.48), pcbnew.FromMM(122.95)))
                        item.SetTextAngle(pcbnew.EDA_ANGLE(0, pcbnew.DEGREES_T))
                        item.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(.8), pcbnew.FromMM(.8)))
                reference_changes.append({"reference": "TP803", "view_action": "move Fab label above test pad to avoid board-name overlap; source unchanged"})
            if footprint.GetReference() not in fitted:
                continue
            fabrication_layer = pcbnew.F_Fab if footprint.GetLayer() == pcbnew.F_Cu else pcbnew.B_Fab
            has_reference_text = any(hasattr(item, "GetText") and item.GetLayer() == fabrication_layer
                                     and ("REFERENCE" in item.GetText().upper() or item.GetText() in {"%R", footprint.GetReference()})
                                     for item in footprint.GraphicalItems())
            if has_reference_text:
                footprint.Reference().SetVisible(False)
                reference_changes.append({"reference": footprint.GetReference(), "view_action": "use existing fabrication reference text"})
            elif not footprint.Reference().IsVisible():
                footprint.Reference().SetVisible(True)
                footprint.Reference().SetLayer(fabrication_layer)
                footprint.Reference().SetPosition(footprint.GetPosition())
                footprint.Reference().SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(0.8), pcbnew.FromMM(0.8)))
                reference_changes.append({"reference": footprint.GetReference(), "view_action": "show otherwise missing reference at component origin"})
        pcbnew.SaveBoard(str(board_path), board)
        after = snapshot(board_path)
        if any(before[key] != after[key] for key in ("pads", "nets", "tracks", "connections")):
            raise RuntimeError("Display-only assembly copy changed electrical geometry")
        commands = []
        for side, name, mirror in (("F", "front", False), ("B", "back", True)):
            target = output / ("assembly-" + name + ".svg")
            archived = evidence / ("assembly-before-render-" + name + ".svg")
            if target.exists() and not archived.exists():
                shutil.copy2(target, archived)
            command = [str(pipeline.find_cli()), "pcb", "export", "svg", "--layers", f"{side}.Fab,{side}.Silkscreen,Edge.Cuts",
                       "--crossout-DNP-footprints-on-fab-layers", "--mode-single", "--fit-page-to-board", "--exclude-drawing-sheet", "--output", str(target)]
            if mirror:
                command.append("--mirror")
            command.append(str(board_path))
            result = subprocess.run(command, capture_output=True, encoding="utf-8", errors="replace", check=True)
            (evidence / ("assembly-" + name + ".log")).write_text(result.stdout + result.stderr, encoding="utf-8")
            commands.append(command)
            manifest["outputs"][target.name] = pipeline.digest(target)
    if pipeline.fingerprints(pipeline.PRIMARY) != source_hashes:
        raise RuntimeError("Primary changed during assembly rendering")
    record = {"source_pcb_sha256": source_hashes[source_board.name], "temporary_display_copy_removed": True,
              "source_values_unchanged": True, "pad_net_track_geometry_equal": True,
              "display_policy": "In a disposable complete project copy,suppress values and duplicate reference fields; show any otherwise missing reference. Ref strings,body/pad geometry andDNP crosses retained. Use BOM for values/MPNs.",
              "reference_display_changes": reference_changes,
              "front_view_mirrored": False, "back_view_mirrored": True,
              "csv_coordinates_mirrored_again": False, "commands": commands, "manufacturing_released": False}
    manifest["assembly_view_policy"] = record
    pipeline.write_json(manifest_path, manifest)
    pipeline.write_json(evidence / "assembly-view-policy.json", record)
    print(json.dumps({key: value for key, value in record.items() if key != "commands"}))


if __name__ == "__main__":
    main()
