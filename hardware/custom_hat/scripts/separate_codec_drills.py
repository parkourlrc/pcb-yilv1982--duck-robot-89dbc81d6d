"""Split this checkpoint's PTH/NPTH outputs while preserving the prior mixed file."""
import json
import os
from pathlib import Path
import shutil

import pipeline
from qualify_codec_pth import EVIDENCE


OUTPUT = pipeline.PRIMARY / "production-20261031-pth-review"


def main():
    output = OUTPUT.resolve()
    if not output.is_relative_to(pipeline.PRIMARY.resolve()) or not output.name.startswith("production-"):
        raise RuntimeError("Unexpected manufacturing output directory")
    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest["design_hashes"] != pipeline.fingerprints(pipeline.PRIMARY):
        raise RuntimeError("Package does not match the current design")
    mixed = output / (pipeline.STEM + ".drl")
    archive = EVIDENCE / "mixed-drill-before-separation.drl"
    if archive.exists() or not mixed.is_file() or pipeline.digest(mixed) != manifest["outputs"].get(mixed.name):
        raise RuntimeError("Unexpected prior drill state")
    if len(list(output.glob("*.drl"))) != 1:
        raise RuntimeError("Refusing to replace an unexpected drill file set")
    commands = []
    pipeline.run_command([pipeline.find_cli(), "pcb", "export", "drill", "--format", "excellon", "--drill-origin", "absolute",
                          "--excellon-units", "mm", "--excellon-separate-th", "--output", str(output) + os.sep,
                          pipeline.PRIMARY / (pipeline.STEM + ".kicad_pcb")], EVIDENCE, "export-separate-drill", commands)
    names = [pipeline.STEM + "-PTH.drl", pipeline.STEM + "-NPTH.drl"]
    if any(not (output / name).is_file() for name in names):
        raise RuntimeError("Expected separate drill files were not generated")
    shutil.copy2(mixed, archive)
    if pipeline.digest(mixed) != pipeline.digest(archive):
        raise RuntimeError("Mixed drill archive failed")
    mixed.unlink()
    manifest["outputs"].pop(mixed.name)
    for name in names:
        manifest["outputs"][name] = pipeline.digest(output / name)
    manifest["drill_policy"] = {"separate_pth_npth": True, "units": "mm", "origin": "absolute", "y_negated_from_kicad_board": True,
                                "blind_buried_drill_files": [], "previous_mixed_file": archive.name}
    if pipeline.fingerprints(pipeline.PRIMARY) != manifest["design_hashes"]:
        raise RuntimeError("Source changed during drill export")
    pipeline.write_json(manifest_path, manifest)
    pipeline.write_json(EVIDENCE / "drill-separation.json", {"source_hashes": manifest["design_hashes"], "commands": commands,
                        "outputs": {name: manifest["outputs"][name] for name in names}, "old_file_sha256": pipeline.digest(archive),
                        "old_mixed_file_had_plating_attributes": True, "improvement": "Explicit plating separation; not a claim that the old mixed format lacked plating information"})
    print(json.dumps(manifest["drill_policy"]))


if __name__ == "__main__":
    main()
