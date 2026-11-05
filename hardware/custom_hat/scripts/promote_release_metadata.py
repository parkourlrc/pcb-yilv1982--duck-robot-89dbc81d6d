"""Promote an inspected, fully checked metadata workspace with source guards."""
import argparse
import json
from pathlib import Path
import shutil

import pcbnew
import pipeline


def unfilled_via_smd_contacts(path):
    board = pcbnew.LoadBoard(str(path))
    contacts = set()
    vias = [item for item in board.GetTracks() if item.Type() == pcbnew.PCB_VIA_T
            and not (item.GetFillingMode() == pcbnew.FILLING_MODE_FILLED
                     and item.GetCappingMode() == pcbnew.CAPPING_MODE_CAPPED)]
    for footprint in board.GetFootprints():
        for pad in footprint.Pads():
            if pad.GetAttribute() != pcbnew.PAD_ATTRIB_SMD:
                continue
            for layer, paste in ((pcbnew.F_Cu, pcbnew.F_Paste), (pcbnew.B_Cu, pcbnew.B_Paste)):
                if not pad.IsOnLayer(paste):
                    continue
                for via in vias:
                    if via.IsOnLayer(layer) and pad.GetEffectiveShape(paste).Collide(via.GetPosition(), via.GetDrill() // 2):
                        contacts.add((footprint.GetReference(), pad.GetNumber() or '<paste-window>', via.m_Uuid.AsString(), board.GetLayerName(layer)))
    return contacts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    arguments = parser.parse_args()
    work = pipeline.managed(arguments.project)
    evidence = arguments.evidence.resolve()
    source_before = pipeline.fingerprints(pipeline.PRIMARY)
    manifest = json.loads((work.parent / "manifest.json").read_text(encoding="utf-8"))
    summary = json.loads(arguments.summary.read_text(encoding="utf-8"))
    geometry = json.loads((evidence / "geometry-connectivity-check.json").read_text(encoding="utf-8"))
    if source_before != manifest["source_hashes"]:
        raise RuntimeError("Primary design changed; re-review required")
    if pipeline.fingerprints(work) != summary["source_hashes"]:
        raise RuntimeError("Candidate no longer matches its checked fingerprint")
    if summary["status"] != "checks_clean_not_manufacturing_release" or not geometry["accepted"]:
        raise RuntimeError("Checks did not pass")
    rule_loading = summary.get("custom_rules_loading", {})
    if not rule_loading.get("custom_rules_loaded") or rule_loading.get("rules_sha256") != pipeline.digest(work / (pipeline.STEM + ".kicad_dru")):
        raise RuntimeError("Fresh proof of custom-rule loading is required before promotion")
    if pipeline.digest(work / (pipeline.STEM + ".kicad_pcb")) != geometry["runs"]["after"]["pcb_sha256"]:
        raise RuntimeError("Candidate no longer matches filled-geometry check")
    source_contacts = unfilled_via_smd_contacts(pipeline.PRIMARY / (pipeline.STEM + '.kicad_pcb'))
    candidate_contacts = unfilled_via_smd_contacts(work / (pipeline.STEM + '.kicad_pcb'))
    new_contacts = candidate_contacts - source_contacts
    pipeline.write_json(evidence / 'pre-promotion-via-contact-check.json', {
        'before': sorted(source_contacts), 'after': sorted(candidate_contacts),
        'new_unfilled_via_contacts': sorted(new_contacts), 'accepted': not new_contacts,
        'scope': 'Geometric hole-to-actual-paste aperture intersection, including independent exposed-pad windows; mask clearance and transfer checks remain separate',
    })
    if new_contacts:
        raise RuntimeError('New unfilled via hole overlaps a pasted SMD pad; native same-net DRC is insufficient')
    backup = evidence / "before-metadata"
    if backup.exists():
        raise FileExistsError("Promotion snapshot already exists")
    backup.mkdir()
    changed = []
    for path in pipeline.design_files(work):
        name = path.relative_to(work).as_posix()
        if source_before.get(name) == pipeline.digest(path):
            continue
        target = pipeline.PRIMARY / name
        if target.is_file():
            archived = backup / name
            archived.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, archived)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        changed.append(name)
    report_copy = evidence / "accepted-reports"
    shutil.copytree(arguments.summary.parent, report_copy)
    pipeline.write_json(evidence / "promotion.json", {
        "work": str(work), "changed_files": changed, "before_hashes": source_before,
        "after_hashes": pipeline.fingerprints(pipeline.PRIMARY), "summary": str(arguments.summary),
        "production_ready": False, "hardware_tested": False,
    })
    candidate_path = evidence / "candidate.json"
    if candidate_path.exists():
        candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
        candidate["promoted"] = True
        candidate["promoted_pcb_sha256"] = pipeline.digest(pipeline.PRIMARY / (pipeline.STEM + ".kicad_pcb"))
        pipeline.write_json(candidate_path, candidate)
    print(json.dumps({"changed_files": changed, "pcb_sha256": pipeline.digest(pipeline.PRIMARY / (pipeline.STEM + ".kicad_pcb"))}))


if __name__ == "__main__":
    main()
