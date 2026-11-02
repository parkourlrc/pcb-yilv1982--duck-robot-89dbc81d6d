"""Exclude DNP pad paste in a complete plotting copy and audit all remaining geometry."""
from collections import Counter
import copy
import json
from pathlib import Path
import re
import shutil
import subprocess

import pipeline
from generate_rev_a import children, dump, first, parse
from repair_release_metadata import properties


PASTE_SUFFIXES = ("-F_Paste.gtp", "-B_Paste.gbp")
LAYERS = "F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts"


def normalize_plot(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    return "\n".join(line for line in lines if not line.startswith(("%TF.CreationDate,", "%TF.MD5,"))
                     and not re.match(r"G04 Created by KiCad \(.*\) date .*\*", line))


def paste_flashes(path):
    text = path.read_text(encoding="utf-8")
    if "%FSLAX46Y46*%" not in text or "%MOMM*%" not in text:
        raise RuntimeError("Unreviewed paste coordinate format")
    apertures = {int(number): definition for number, definition in re.findall(r"^%ADD(\d+)(.+)\*%$", text, re.M)}
    macros = re.findall(r"%AM.*?%", text, re.S)
    if "G36*" in text or "G37*" in text:
        raise RuntimeError("Paste regions need an additional geometry audit")
    reference, aperture, xpos, ypos = None, None, None, None
    flashes = Counter()
    for line in text.splitlines():
        component = re.fullmatch(r"%TO\.C,(.*)\*%", line)
        selected = re.fullmatch(r"D(\d+)\*", line)
        operation = re.fullmatch(r"(?:X(-?\d+))?(?:Y(-?\d+))?D0([123])\*", line)
        if component:
            reference = component[1]
        elif line == "%TD*%":
            reference = None
        elif selected and int(selected[1]) >= 10:
            aperture = int(selected[1])
        elif operation:
            xpos = int(operation[1]) if operation[1] is not None else xpos
            ypos = int(operation[2]) if operation[2] is not None else ypos
            if operation[3] != "3" or xpos is None or ypos is None or aperture not in apertures:
                raise RuntimeError("Unsupported paste drawing primitive")
            flashes[(reference, xpos, ypos, apertures[aperture])] += 1
    return flashes, macros


def audit_stencil_policy(output, evidence, policy, dnp_references, pcb_sha256):
    results = []
    valid = bool(policy and policy.get("accepted") and policy.get("source_pcb_sha256") == pcb_sha256)
    valid = valid and set(policy.get("dnp_references", [])) == set(dnp_references)
    for comparison in policy.get("comparisons", []):
        name = comparison["file"]
        before_path = evidence / "unfiltered-paste" / name
        after_path = output / name
        before, before_macros = paste_flashes(before_path)
        after, after_macros = paste_flashes(after_path)
        expected = Counter({key: count for key, count in before.items() if key[0] not in dnp_references})
        accepted = pipeline.digest(before_path) == comparison["before_sha256"] and pipeline.digest(after_path) == comparison["final_sha256"]
        accepted = accepted and expected == after and before_macros == after_macros and not any(key[0] in dnp_references for key in after)
        results.append({"file": name, "before_flashes": before.total(), "after_flashes": after.total(), "accepted": accepted})
    valid = valid and len(results) == 2 and all(row["accepted"] for row in results)
    return {"accepted": valid, "dnp_references": sorted(dnp_references), "files": results}


def export_dnp_stencil(source, output, evidence):
    source, output, evidence = Path(source), Path(output), Path(evidence)
    original_hashes = pipeline.fingerprints(source.parent)
    original = parse(source.read_text(encoding="utf-8"))
    transformed = copy.deepcopy(original)
    changed_pads, dnp_references = [], []
    for footprint in children(transformed, "footprint"):
        if "dnp" not in (first(footprint, "attr") or []):
            continue
        reference = properties(footprint)["Reference"]
        dnp_references.append(reference)
        for pad in children(footprint, "pad"):
            layers = first(pad, "layers")
            removed = [layer for layer in layers[1:] if layer in {"F.Paste", "B.Paste"}]
            if removed:
                changed_pads.append({"reference": reference, "pin": str(pad[1]), "uuid": first(pad, "uuid")[1],
                                     "original_layers": list(layers), "removed_layers": removed})
                layers[:] = [entry for entry in layers if entry not in removed]
    if not changed_pads:
        archive = evidence / "unfiltered-paste"
        archive.mkdir(exist_ok=False)
        comparisons = []
        for suffix in PASTE_SUFFIXES:
            path = output / (source.stem + suffix)
            flashes, _ = paste_flashes(path)
            if any(key[0] in dnp_references for key in flashes):
                raise RuntimeError("DNP graphics produce paste not covered by pad-layer filtering")
            shutil.copy2(path, archive / path.name)
            comparisons.append({"file": path.name, "before_sha256": pipeline.digest(path), "final_sha256": pipeline.digest(path),
                                "before_flash_count": flashes.total(), "after_flash_count": flashes.total(), "removed_flashes": [],
                                "non_dnp_apertures_unchanged": True, "macro_definitions_unchanged": True, "changed_geometry": False})
        record = {"source_pcb_sha256": pipeline.digest(source), "policy": "no DNP paste pads present", "dnp_references": sorted(dnp_references),
                  "changed_files": [], "comparisons": comparisons, "accepted": True, "manufacturing_released": False}
        pipeline.write_json(evidence / "dnp-stencil-policy.json", record)
        return record
    work = pipeline.prepare(source.parent)
    plot_source = work / source.name
    plot_source.write_text("\n".join(line.rstrip() for line in dump(transformed).splitlines()) + "\n", encoding="utf-8")
    restored = parse(plot_source.read_text(encoding="utf-8"))
    original_layers = {row["uuid"]: row["original_layers"] for row in changed_pads}
    for footprint in children(restored, "footprint"):
        for pad in children(footprint, "pad"):
            identifier = first(pad, "uuid")[1]
            if identifier in original_layers:
                first(pad, "layers")[:] = original_layers[identifier]
    if restored != original:
        raise RuntimeError("Stencil copy changed fields other than reviewed DNP paste layers")
    plotted = work.parent / "dnp-stencil-plot"
    plotted.mkdir()
    command = [str(pipeline.find_cli()), "pcb", "export", "gerbers", "--output", str(plotted), "--layers", LAYERS, str(plot_source)]
    result = subprocess.run(command, capture_output=True, encoding="utf-8", errors="replace")
    (evidence / "dnp-stencil-export.log").write_text(result.stdout + result.stderr, encoding="utf-8")
    if result.returncode:
        raise RuntimeError("Native stencil plot failed")
    reference_files = sorted(path for path in output.iterdir() if path.is_file() and path.suffix in {".gtl", ".gbl", ".g1", ".g2", ".gts", ".gbs", ".gto", ".gbo", ".gm1"})
    if len(reference_files) != 9:
        raise RuntimeError("Expected four copper, two mask, two silk and one outline layer")
    differences = [path.name for path in reference_files if normalize_plot(path) != normalize_plot(plotted / path.name)]
    if differences:
        raise RuntimeError("Non-paste geometry changed: " + str(differences))
    comparisons = []
    for suffix in PASTE_SUFFIXES:
        name = source.stem + suffix
        before, macros_before = paste_flashes(output / name)
        after, macros_after = paste_flashes(plotted / name)
        expected = Counter({key: count for key, count in before.items() if key[0] not in dnp_references})
        comparison = {"file": name, "before_sha256": pipeline.digest(output / name), "plotted_sha256": pipeline.digest(plotted / name),
                      "before_flash_count": before.total(), "after_flash_count": after.total(),
                      "removed_flashes": [{"reference": key[0], "x_mm": key[1] / 1e6, "cam_y_mm": key[2] / 1e6,
                                           "aperture": key[3], "count": count} for key, count in (before - after).items()],
                      "non_dnp_apertures_unchanged": expected == after, "macro_definitions_unchanged": macros_before == macros_after,
                      "changed_geometry": before != after}
        if not comparison["non_dnp_apertures_unchanged"] or not comparison["macro_definitions_unchanged"]:
            raise RuntimeError("Fitted-parts stencil aperture geometry differs")
        comparisons.append(comparison)
    if pipeline.fingerprints(source.parent) != original_hashes:
        raise RuntimeError("Source changed during stencil export")
    archive = evidence / "unfiltered-paste"
    archive.mkdir(exist_ok=False)
    changed = []
    for comparison in comparisons:
        name = comparison["file"]
        shutil.copy2(output / name, archive / name)
        if comparison["changed_geometry"]:
            shutil.copy2(plotted / name, output / name)
            changed.append(name)
        comparison["final_sha256"] = pipeline.digest(output / name)
    record = {"source_pcb_sha256": pipeline.digest(source), "plot_copy_pcb_sha256": pipeline.digest(plot_source),
              "plot_work": str(work), "policy": "Exclude DNP pad apertures from stencil only; keep original PCB copper/mask/pads",
              "dnp_references": sorted(dnp_references), "changed_pads": changed_pads, "changed_files": changed,
              "comparisons": comparisons, "non_paste_layers_equal_excluding_creation_metadata": True,
              "non_paste_checked_files": [path.name for path in reference_files], "only_paste_layer_memberships_changed": True,
              "primary_unchanged": original_hashes == pipeline.fingerprints(source.parent), "command": command,
              "accepted": True, "fabricator_accepted": False, "manufacturing_released": False}
    pipeline.write_json(evidence / "dnp-stencil-policy.json", record)
    return record
