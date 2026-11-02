"""Verify the codec through-via, rule-loading guard and tightly scoped process rule."""
import json
from pathlib import Path
import uuid

import pcbnew

import pipeline
from qualify_codec_pth import EVIDENCE, IDENTIFIER, RULE
from verify_release_metadata import snapshot
from verify_buck_control import protection


def fill(project, label):
    path = project / (pipeline.STEM + ".kicad_pcb")
    report = project.parent / ("codec-filled-" + label + "-" + uuid.uuid4().hex[:8] + ".json")
    commands = []
    pipeline.run_command([pipeline.find_cli(), "pcb", "drc", "--format", "json", "--severity-all", "--schematic-parity", "--refill-zones", "--save-board", "--output", report, path],
                         EVIDENCE, "filled-" + label, commands, report)
    data = json.loads(report.read_text(encoding="utf-8"))
    return {"project": str(project), "pcb_sha256": pipeline.digest(path), "commands": commands,
            "violations": len(data["violations"]), "unconnected": len(data["unconnected_items"]), "parity": len(data["schematic_parity"])}


def negative_control(source, mode, original_rules):
    work = pipeline.prepare(source)
    path = work / (pipeline.STEM + ".kicad_pcb")
    identifier = None
    if mode == "missing_units":
        (work / (pipeline.STEM + ".kicad_dru")).write_text(original_rules, encoding="utf-8")
    else:
        board = pcbnew.LoadBoard(str(path))
        if mode == "qualified_size_changed":
            via = next(item for item in board.GetTracks() if item.m_Uuid.AsString() == IDENTIFIER)
            via.SetWidth(pcbnew.FromMM(.34))
        else:
            candidates = [item for item in board.GetTracks() if item.Type() == pcbnew.PCB_VIA_T and item.GetNetname() == "POWER_GND"
                          and item.GetDrill() == 300000 and item.GetFillingMode() != pcbnew.FILLING_MODE_FILLED]
            via = sorted(candidates, key=lambda item: item.m_Uuid.AsString())[0]
            via.SetWidth(pcbnew.FromMM(.5))
        identifier = via.m_Uuid.AsString()
        pcbnew.SaveBoard(str(path), board)
    directories_before = set((work.parent / "reports").glob("*")) if (work.parent / "reports").exists() else set()
    try:
        reports, summary = pipeline.check(work)
        if mode == "missing_units":
            return {"mode": mode, "project": str(work), "accepted_as_negative_control": False, "summary": str(reports / "summary.json")}
        drc = json.loads((reports / "drc.json").read_text(encoding="utf-8"))
        found = [row for row in drc["violations"] if row["type"] == "annular_width" and any(item["uuid"] == identifier for item in row.get("items", []))]
        return {"mode": mode, "project": str(work), "target_uuid": identifier, "summary": str(reports / "summary.json"),
                "rule_loading": summary["custom_rules_loading"], "annular_violations": found,
                "accepted_as_negative_control": bool(found) and summary["status"] == "design_blocked"}
    except RuntimeError as error:
        created = set((work.parent / "reports").glob("*")) - directories_before
        report_dir = next(iter(created)) if len(created) == 1 else None
        guard = json.loads((report_dir / "rules-loading.json").read_text(encoding="utf-8")) if report_dir and (report_dir / "rules-loading.json").exists() else {}
        return {"mode": mode, "project": str(work), "error": str(error), "rule_loading": guard,
                "summary": str(report_dir / "summary.json") if report_dir else None,
                "accepted_as_negative_control": mode == "missing_units" and guard.get("custom_rules_loaded") is False}


def main():
    candidate_path = EVIDENCE / "candidate.json"
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    after = pipeline.managed(Path(candidate["project"]))
    baseline = json.loads((EVIDENCE / "units-fixed-baseline-cli.json").read_text(encoding="utf-8"))
    before = pipeline.managed(Path(baseline["project"]))
    unit_change = json.loads((EVIDENCE / "rules-unit-change.json").read_text(encoding="utf-8"))
    runs = {"before": fill(before, "before"), "after": fill(after, "after")}
    original = snapshot(before / (pipeline.STEM + ".kicad_pcb"))
    repaired = snapshot(after / (pipeline.STEM + ".kicad_pcb"))
    uncorrected = snapshot(pipeline.PRIMARY / (pipeline.STEM + ".kicad_pcb"))
    lost = {identifier: sorted(set(group) - set(repaired["connections"].get(identifier, []))) for identifier, group in original["connections"].items()
            if not set(group).issubset(repaired["connections"].get(identifier, []))}
    lost_from_primary = {identifier: sorted(set(group) - set(repaired["connections"].get(identifier, []))) for identifier, group in uncorrected["connections"].items()
                         if not set(group).issubset(repaired["connections"].get(identifier, []))}
    changed_tracks = {identifier: {"before": values, "after": repaired["tracks"].get(identifier)} for identifier, values in original["tracks"].items()
                      if values != repaired["tracks"].get(identifier)}
    only_via_layers = set(changed_tracks) == {IDENTIFIER} and all(original["tracks"][IDENTIFIER][key] == repaired["tracks"][IDENTIFIER][key]
                                                               for key in original["tracks"][IDENTIFIER] if key != "layers")
    old_board = pcbnew.LoadBoard(str(before / (pipeline.STEM + ".kicad_pcb")))
    board = pcbnew.LoadBoard(str(after / (pipeline.STEM + ".kicad_pcb")))
    vias = [item for item in board.GetTracks() if item.Type() == pcbnew.PCB_VIA_T]
    target = next(item for item in vias if item.m_Uuid.AsString() == IDENTIFIER)
    courtyard = board.FindFootprintByReference("U701").GetCourtyard(pcbnew.B_CrtYd)
    eligible = [item.m_Uuid.AsString() for item in vias if item.GetViaType() == pcbnew.VIATYPE_THROUGH and item.GetNetname() == "+3V3"
                and item.GetFrontWidth() == 350000 and item.GetDrill() == 150000 and courtyard.Contains(item.GetPosition())]
    diameters = {board.GetLayerName(layer): pcbnew.ToMM(target.GetWidth(layer)) for layer in (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu)}
    other_rings = [pcbnew.ToMM(item.GetFrontWidth() - item.GetDrill()) / 2 for item in vias if item.m_Uuid.AsString() != IDENTIFIER]
    controls = [negative_control(after, mode, unit_change["original_rules"]) for mode in ("missing_units", "ordinary_ring_reduced", "qualified_size_changed")]
    pipeline.write_json(EVIDENCE / "rule-negative-controls.json", controls)
    expected_rules = unit_change["fixed_rules"].rstrip() + "\n" + RULE
    result = {"runs": runs, "original_pad_geometry_unchanged": original["pads"] == repaired["pads"] == uncorrected["pads"],
              "original_pad_nets_unchanged": original["nets"] == repaired["nets"] == uncorrected["nets"],
              "lost_connections_from_corrected_baseline": lost, "lost_connections_from_primary": lost_from_primary,
              "changed_tracks": changed_tracks, "only_target_via_layer_set_changed": only_via_layers,
              "copper_object_ids_unchanged": set(original["tracks"]) == set(repaired["tracks"]),
              "target_type_through": target.GetViaType() == pcbnew.VIATYPE_THROUGH, "qualified_rule_matches_only": eligible,
              "target_copper_diameters_mm": diameters, "other_vias_minimum_annular_mm": min(other_rings),
              "through_vias": sum(item.GetViaType() == pcbnew.VIATYPE_THROUGH for item in vias), "total_vias": len(vias),
              "filled_capped_fields_preserved": protection(old_board) == protection(board),
              "project_settings_unchanged": pipeline.digest(after / (pipeline.STEM + ".kicad_pro")) == pipeline.digest(pipeline.PRIMARY / (pipeline.STEM + ".kicad_pro")),
              "rules_match_reviewed_change": (after / (pipeline.STEM + ".kicad_dru")).read_text(encoding="utf-8") == expected_rules,
              "negative_controls_passed": all(row["accepted_as_negative_control"] for row in controls),
              "hardware_tested": False, "production_ready": False}
    result["accepted"] = all((result["original_pad_geometry_unchanged"], result["original_pad_nets_unchanged"], not lost, not lost_from_primary,
        only_via_layers, result["copper_object_ids_unchanged"], result["target_type_through"], eligible == [IDENTIFIER], all(value == .35 for value in diameters.values()),
        min(other_rings) >= .125, result["through_vias"] == result["total_vias"], result["filled_capped_fields_preserved"], result["project_settings_unchanged"],
        result["rules_match_reviewed_change"], result["negative_controls_passed"],
        all(not stage[key] for stage in runs.values() for key in ("violations", "unconnected", "parity"))))
    pipeline.write_json(EVIDENCE / "geometry-connectivity-check.json", result)
    print(json.dumps({key: value for key, value in result.items() if key not in {"runs", "changed_tracks"}}))
    if not result["accepted"]:
        raise RuntimeError("Codec PTH acceptance failed")
    reports, summary = pipeline.check(after)
    candidate["summary"] = str(reports / "summary.json")
    pipeline.write_json(candidate_path, candidate)
    print(json.dumps({"status": summary["status"], "rules_loading": summary["custom_rules_loading"]}))


if __name__ == "__main__":
    main()
