"""Audit the r18 handoff, drill coordinates and copper-flash registration."""
from collections import Counter
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import zipfile

import pcbnew
import pipeline
from audit_codec_drills import read_drills

ROOT = pipeline.BASE.parents[1]
EVIDENCE = ROOT / "docs/references/扩展板邮票孔与电源修复"
PANEL = pipeline.BASE / "panels/a1-smt-2up-20261102-r18"


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def copper_flash_centers(path):
    text = path.read_text(encoding="utf-8")
    if "%FSLAX46Y46*%" not in text or "%MOMM*%" not in text:
        raise RuntimeError("Unreviewed Gerber coordinate format")
    positions = set()
    xpos, ypos, region, dark = None, None, False, True
    for line in text.splitlines():
        if line == "G36*":
            region = True
        elif line == "G37*":
            region = False
        elif line == "%LPD*%":
            dark = True
        elif line == "%LPC*%":
            dark = False
        operation = re.fullmatch(r"(?:X(-?\d+))?(?:Y(-?\d+))?D0([123])\*", line)
        if operation:
            xpos = int(operation[1]) if operation[1] is not None else xpos
            ypos = int(operation[2]) if operation[2] is not None else ypos
            if operation[3] == "3":
                if region or not dark or xpos is None or ypos is None:
                    raise RuntimeError("Unreviewed copper flash mode")
                positions.add((xpos, ypos))
    return positions


def main():
    checkpoint = pipeline.current_checkpoint()
    panel_path = PANEL / "hat_a1_smt_2up.kicad_pcb"
    board = pcbnew.LoadBoard(str(panel_path))
    bundle_record = read_json(EVIDENCE / "pcba-review-bundle.json")
    archive = ROOT / bundle_record["archive"]
    package = archive.with_suffix("")
    manifest = read_json(package / "MANIFEST.json")
    if pipeline.digest(archive) != bundle_record["sha256"]:
        raise RuntimeError("Archive identity changed")
    with zipfile.ZipFile(archive) as compressed:
        if compressed.testzip() or set(compressed.namelist()) != set(manifest["files"]) | {"MANIFEST.json"}:
            raise RuntimeError("Invalid archive members")
        for name, expected in manifest["files"].items():
            if pipeline.digest(package / name) != expected or hashlib.sha256(compressed.read(name)).hexdigest() != expected:
                raise RuntimeError("Invalid archive member: " + name)
    panel_verification = read_json(EVIDENCE / "panel-verification.json")
    for path, key in [(panel_path, "panel_sha256"), (panel_path.with_suffix(".kicad_pro"), "panel_project_sha256"),
                      (panel_path.with_suffix(".kicad_dru"), "panel_rules_sha256"),
                      (PANEL / "edge-copper-reference-check.json", "edge_audit_sha256")]:
        if pipeline.digest(path) != panel_verification[key]:
            raise RuntimeError("Panel evidence identity mismatch: " + key)
    if bundle_record["pcb_sha256"] != checkpoint["pcb_sha256"] or bundle_record["panel_sha256"] != pipeline.digest(panel_path):
        raise RuntimeError("Bundle source mismatch")
    expected_holes = Counter()
    for footprint in board.GetFootprints():
        for pad in footprint.Pads():
            drill = pad.GetDrillSize()
            if drill.x:
                if drill.x != drill.y:
                    raise RuntimeError("Unreviewed slot")
                point = pad.GetPosition()
                plating = "npth" if pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH else "pth"
                expected_holes[(plating, round(pcbnew.ToMM(drill.x), 6), pcbnew.ToMM(point.x), -pcbnew.ToMM(point.y))] += 1
    for item in board.GetTracks():
        if item.Type() == pcbnew.PCB_VIA_T:
            point = item.GetPosition()
            expected_holes[("pth", round(pcbnew.ToMM(item.GetDrillValue()), 6), pcbnew.ToMM(point.x), -pcbnew.ToMM(point.y))] += 1
    actual_holes = Counter()
    for name, plating in [("hat_a1_smt_2up-PTH.drl", "pth"), ("hat_a1_smt_2up-NPTH.drl", "npth")]:
        for row in read_drills(package / name, plating):
            actual_holes[(plating, round(row["diameter_mm"], 6), round(row["cam_mm"][0], 3), round(row["cam_mm"][1], 3))] += 1
    unmatched = list(expected_holes.elements())
    quantization_errors = []
    for hit in actual_holes.elements():
        candidates = [row for row in unmatched if row[:2] == hit[:2] and math.dist(row[2:], hit[2:]) <= .001]
        if len(candidates) != 1:
            raise RuntimeError("Unmatched or ambiguous drill hit: " + repr(hit))
        match = candidates[0]
        unmatched.remove(match)
        quantization_errors.append(math.dist(match[2:], hit[2:]))
    if unmatched or sum(actual_holes.values()) != 370:
        raise RuntimeError("Native/excellon hole count mismatch")
    copper_checks = []
    for layer, suffix, name in [(pcbnew.F_Cu, "gtl", "F_Cu"), (pcbnew.In1_Cu, "g1", "In1_Cu"),
                                (pcbnew.In2_Cu, "g2", "In2_Cu"), (pcbnew.B_Cu, "gbl", "B_Cu")]:
        positions = copper_flash_centers(package / ("hat_a1_smt_2up-" + name + "." + suffix))
        checked, missing = 0, []
        for footprint in board.GetFootprints():
            for pad in footprint.Pads():
                if not pad.IsOnLayer(layer) or pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                    continue
                point = pad.GetPosition()
                checked += 1
                if (point.x, -point.y) not in positions:
                    missing.append(footprint.GetReference() + "." + pad.GetNumber())
        copper_checks.append({"layer": board.GetLayerName(layer), "native_copper_pads_checked": checked, "missing_center_flashes": missing})
    if any(row["missing_center_flashes"] for row in copper_checks):
        raise RuntimeError("Copper pad center registration mismatch: " + json.dumps(copper_checks))
    deltas = {}
    for name in ["schematic", "pcb", "cross", "emc"]:
        prior = read_json(EVIDENCE.parent / "归档扩展板钢网分窗审查" / (name + ".json"))
        current = read_json(EVIDENCE / (name + ".json"))
        before = Counter((row.get("rule_id"), row.get("severity"), row.get("summary")) for row in prior["findings"])
        after = Counter((row.get("rule_id"), row.get("severity"), row.get("summary")) for row in current["findings"])
        deltas[name] = {"added": list((after-before).elements()), "removed": list((before-after).elements()),
                        "summary": current["summary"], "trust_summary": current.get("trust_summary")}
    pipeline.write_json(EVIDENCE / "review-delta-summary.json", deltas)
    images = []
    for name in ["bmi-bridge.svg", "bmi-bridge-detail.png", "panel-r18-front.svg", "panel-r18-front.png",
                 "panel-r18-back.svg", "panel-r18-back.png", "panel-r18-mouse-bites.svg", "panel-r18-mouse-bites.png"]:
        images.append({"file": name, "date": "2026-11-03" if name.startswith("panel") else "2026-11-02",
                       "sha256": pipeline.digest(EVIDENCE / name), "opened": name.endswith(".png"),
                       "source": "Native KiCad source86654c03 / r18fd6cd170; SVG raster or crop; not a hardware photograph",
                       "back_mirrored": "back" in name, "hardware_photo": False})
    pipeline.write_json(EVIDENCE / "image-manifest.json", images)
    software = []
    for folder, name in [("driver-compatibility-20261031", "offline-package-final-audit.json"),
                         ("bmi088-adapter-20261031", "final-audit.json"), ("audio-routing-20261031", "final-audit.json")]:
        path = EVIDENCE.parent / "扩展板电路仿真工具" / folder / name
        audit = read_json(path)
        if not audit["accepted_offline"] or audit["pcb_sha256"] != checkpoint["pcb_sha256"]:
            raise RuntimeError("Software audit not bound to current PCB")
        software.append({"file": str(path.relative_to(ROOT)), "sha256": pipeline.digest(path), "accepted_offline": True})
    for name in ["research.md", "remaining-actions.md", "requirements-status.md"]:
        if not (EVIDENCE / name).is_file():
            raise RuntimeError("Missing review documentation: " + name)
    diff = subprocess.run(["git", "diff", "--check"], cwd=ROOT, capture_output=True, text=True)
    if diff.returncode:
        raise RuntimeError(diff.stdout + diff.stderr)
    result = {"date": datetime.now().date().isoformat(), "pcb_sha256": checkpoint["pcb_sha256"],
              "panel_sha256": pipeline.digest(panel_path), "source_binding_valid": True, "zip_members_valid": True,
              "archive": bundle_record["archive"], "archive_sha256": bundle_record["sha256"],
              "tht_process_addendum": manifest.get("tht_process_addendum", {"included": False}),
              "depanel_process_addendum": manifest.get("depanel_process_addendum", {"included": False}),
              "panel_rules_and_edge_audit_hashes_valid": True, "native_drill_locations_match": True,
              "holes": 370, "matching_tolerance_mm": .001, "maximum_drill_quantization_error_mm": max(quantization_errors),
              "pth": sum(count for key, count in actual_holes.items() if key[0] == "pth"),
              "npth": sum(count for key, count in actual_holes.items() if key[0] == "npth"),
              "copper_pad_center_checks": copper_checks, "counts": manifest["counts"],
              "software_audits": software, "git_diff_check_pass": True,
              "manufacturing_released": False, "hardware_tested": False, "committed": False,
              "limits": ["Copper center matching rejects systematic layer shifts but is not complete CAM geometry verification",
                         "Existing native/edge/paste audits remain separate evidence; automated warnings retained"]}
    pipeline.write_json(EVIDENCE / "completion-check.json", result)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
