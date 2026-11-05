"""Export a geometry-equivalent RS-274-X derivative of the reviewed HAT package."""
import argparse
import copy
from datetime import datetime, timezone
import json
import hashlib
from pathlib import Path
import re
import shutil
import subprocess
import zipfile

import pipeline
from generate_rev_a import children, dump, first, parse
from export_dnp_stencil import LAYERS


GERBER_SUFFIXES = {".gtl", ".gbl", ".g1", ".g2", ".gts", ".gbs", ".gto", ".gbo", ".gm1", ".gtp", ".gbp"}


def drawing_commands(path):
    commands = []
    apertures = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("G04") or re.match(r"^%T[FAOD]", line) or not line.strip():
            continue
        definition = re.fullmatch(r"%ADD(\d+)(.*)\*%", line)
        selection = re.fullmatch(r"D(\d+)\*", line)
        if definition:
            apertures[int(definition[1])] = definition[2]
        elif selection and int(selection[1]) >= 10:
            commands.append("APERTURE:" + apertures[int(selection[1])])
        else:
            commands.append(line)
    return commands


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package-version", default="20261102")
    parser.add_argument("--evidence",type=Path)
    arguments = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,31}", arguments.package_version):
        parser.error("package-version must use 1-32 lowercase letters, digits or hyphens")
    checkpoint = pipeline.current_checkpoint()
    root = pipeline.BASE.parents[1]
    evidence = arguments.evidence.resolve() if arguments.evidence else root / "docs/references/归档扩展板嘉立创规则自查"
    old_output = root / checkpoint["review_binding"]["production_package"]
    old_manifest = json.loads((old_output / "manifest.json").read_text(encoding="utf-8"))
    if old_manifest["design_hashes"] != checkpoint["design_hashes"]:
        raise RuntimeError("Original output does not match current source")
    for name, expected in old_manifest["outputs"].items():
        if pipeline.digest(old_output / name) != expected:
            raise RuntimeError("Original output changed: " + name)
    work = pipeline.prepare(pipeline.PRIMARY)
    board_path = work / (pipeline.STEM + ".kicad_pcb")
    original = parse(board_path.read_text(encoding="utf-8"))
    transformed = copy.deepcopy(original)
    changes = []
    for footprint in children(transformed, "footprint"):
        if "dnp" not in (first(footprint, "attr") or []):
            continue
        for pad in children(footprint, "pad"):
            layers = first(pad, "layers")
            if any(layer in {"F.Paste", "B.Paste"} for layer in layers):
                changes.append({"uuid": first(pad, "uuid")[1], "layers": list(layers)})
                layers[:] = [layer for layer in layers if layer not in {"F.Paste", "B.Paste"}]
    board_path.write_text(dump(transformed), encoding="utf-8")
    restored = parse(board_path.read_text(encoding="utf-8"))
    restore_layers = {entry["uuid"]: entry["layers"] for entry in changes}
    for footprint in children(restored, "footprint"):
        for pad in children(footprint, "pad"):
            identifier = first(pad, "uuid")[1]
            if identifier in restore_layers:
                first(pad, "layers")[:] = restore_layers[identifier]
    if restored != original:
        raise RuntimeError("Plot copy changed more than DNP paste memberships")
    plotted = work.parent / "jlc-rs274x-plot"
    plotted.mkdir()
    command = [pipeline.find_cli(), "pcb", "export", "gerbers", "--no-x2", "--no-netlist", "--layers", LAYERS,
               "--output", str(plotted), board_path]
    result = subprocess.run(list(map(str, command)), capture_output=True, encoding="utf-8", errors="replace", timeout=180)
    (evidence / "rs274x-export.log").write_text(result.stdout + result.stderr, encoding="utf-8")
    pipeline.write_json(evidence / "rs274x-command.json", {"command": list(map(str, command)), "returncode": result.returncode})
    if result.returncode:
        raise RuntimeError("Native RS-274-X export failed")
    comparisons = []
    for name in old_manifest["outputs"]:
        if Path(name).suffix not in GERBER_SUFFIXES:
            continue
        exported = plotted / name
        content = exported.read_text(encoding="utf-8")
        previous_commands = drawing_commands(old_output / name)
        current_commands = drawing_commands(exported)
        equal = previous_commands == current_commands
        comparisons.append({"file": name, "original_sha256": pipeline.digest(old_output / name),
                            "rs274x_sha256": pipeline.digest(exported), "drawing_commands_equal": equal,
                            "extended_attribute_commands": len(re.findall(r"^%T[FAOD]", content, re.M)),
                            "drawing_command_count": len(current_commands)})
        if not equal:
            (evidence / (name + "-original.commands")).write_text("\n".join(previous_commands), encoding="utf-8")
            (evidence / (name + "-rs274x.commands")).write_text("\n".join(current_commands), encoding="utf-8")
    pipeline.write_json(evidence / "rs274x-comparison.json", {"comparisons": comparisons, "plot_copy_dnp_pad_changes": changes})
    if len(comparisons) != 11 or any(not row["drawing_commands_equal"] or row["extended_attribute_commands"] for row in comparisons):
        raise RuntimeError("Gerber geometry/format comparison failed; no delivery package created")
    folder = pipeline.BASE / "release-review" / ("HAT-A1-JLC-RS274X-" + checkpoint["pcb_sha256"][:12] + "-" + arguments.package_version)
    folder.mkdir(exist_ok=False)
    fabrication = folder / "fabrication"
    fabrication.mkdir()
    for name in old_manifest["outputs"]:
        source = plotted / name if Path(name).suffix in GERBER_SUFFIXES else old_output / name
        shutil.copy2(source, fabrication / name)
    shutil.copy2(evidence / "delivery-notes.md", folder / "README.md")
    for name in ('material-process-matrix.csv','assembly-process-basis.md','manufacturing-spec.md','manufacturing-spec.json'):
        if (evidence/name).is_file():
            shutil.copy2(evidence/name,folder/name)
    portable = {"revision": "A.1", "pcb_sha256": checkpoint["pcb_sha256"], "gerber_format": "RS-274-X",
                "purpose": "Fabrication preparation; outstanding panel and process selections remain; no order authorization",
                "manufacturing_released": False, "hardware_tested": False,
                "files": {path.relative_to(folder).as_posix(): pipeline.digest(path) for path in sorted(folder.rglob("*")) if path.is_file()}}
    pipeline.write_json(folder / "MANIFEST.json", portable)
    archive = folder.with_suffix(".zip")
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED) as bundle:
        for path in sorted(folder.rglob("*")):
            if path.is_file():
                bundle.write(path, path.relative_to(folder).as_posix())
    with zipfile.ZipFile(archive) as bundle:
        if bundle.testzip() or set(bundle.namelist()) != set(portable["files"]) | {"MANIFEST.json"}:
            raise RuntimeError("Archive integrity failed")
        if any(hashlib.sha256(bundle.read(name)).hexdigest() != digest for name, digest in portable["files"].items()):
            raise RuntimeError("Archive member changed")
    if pipeline.fingerprints(pipeline.PRIMARY) != checkpoint["design_hashes"]:
        raise RuntimeError("Main design changed during export")
    record = {"created_at_utc": datetime.now(timezone.utc).isoformat(), "pcb_sha256": checkpoint["pcb_sha256"],
              "archive": archive.relative_to(root).as_posix(), "sha256": pipeline.digest(archive), "size_bytes": archive.stat().st_size,
              "gerber_layers_checked": len(comparisons), "geometry_equivalent": True, "non_gerber_files_unchanged": len(old_manifest["outputs"]) - len(comparisons),
              "dnp_stencil_preserved": True, "primary_unchanged": True, "manufacturing_released": False, "uploaded": False}
    pipeline.write_json(evidence / "rs274x-delivery.json", record)
    print(json.dumps(record, ensure_ascii=False))


if __name__ == "__main__":
    main()
