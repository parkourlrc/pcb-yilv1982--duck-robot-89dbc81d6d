"""Qualify a single unchanged-size codec via for a documented small mechanical-hole process."""
import json
import argparse

import pcbnew

import pipeline


EVIDENCE = pipeline.BASE.parents[1] / "docs/references/扩展板电路仿真工具/codec-pth-20261031"
BASELINE = "c6c09b3306832200c0c723443a350882a816cb00a92d79b10551363b588d35df"
IDENTIFIER = "c6ad78c2-361f-4c03-a650-a32f6c415d72"
RULE = '''(rule "Qualified codec small mechanical via"
  (condition "A.Type == 'Via' && A.Via_Type == 'Through' && A.NetName == '+3V3' && A.insideCourtyard('U701') && A.Diameter == 0.35mm && A.Hole == 0.15mm")
  (constraint annular_width (min 0.10mm))
  (constraint via_diameter (min 0.35mm))
  (constraint hole_size (min 0.15mm))
)
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--retry-loaded-rules", action="store_true")
    arguments = parser.parse_args()
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    candidate_path = EVIDENCE / "candidate.json"
    if candidate_path.exists() and not arguments.retry_loaded_rules:
        raise FileExistsError("Inspect existing codec PTH candidate")
    if arguments.retry_loaded_rules:
        previous = json.loads(candidate_path.read_text(encoding="utf-8"))
        if previous.get("promoted"):
            raise RuntimeError("Cannot replace a promoted candidate")
        pipeline.write_json(EVIDENCE / "candidate-before-rule-loading-fix.json", previous)
        old_check = EVIDENCE / "unqualified-through-check.json"
        if old_check.exists():
            pipeline.write_json(EVIDENCE / "unqualified-with-unloaded-rules.json", json.loads(old_check.read_text(encoding="utf-8")))
    source = pipeline.PRIMARY / (pipeline.STEM + ".kicad_pcb")
    if pipeline.digest(source) != BASELINE:
        raise RuntimeError("Primary changed")
    work = pipeline.prepare(pipeline.PRIMARY)
    rule_path = work / (pipeline.STEM + ".kicad_dru")
    original_rules = rule_path.read_text(encoding="utf-8")
    fixed_rules = original_rules
    for number in ("0.09", "0.12", "0.15", "0.125"):
        fixed_rules = fixed_rules.replace("(min " + number + ")", "(min " + number + "mm)")
    rule_path.write_text(fixed_rules, encoding="utf-8")
    pipeline.write_json(EVIDENCE / "rules-unit-change.json", {"original_rules": original_rules, "fixed_rules": fixed_rules,
                        "original_sha256": pipeline.digest(pipeline.PRIMARY / rule_path.name), "fixed_units_sha256": pipeline.digest(rule_path)})
    candidate = {"project": str(work), "baseline": BASELINE, "promoted": False}
    pipeline.write_json(candidate_path, candidate)
    board_path = work / source.name
    board = pcbnew.LoadBoard(str(board_path))
    via = next(item for item in board.GetTracks() if item.m_Uuid.AsString() == IDENTIFIER)
    if not (via.GetViaType() == pcbnew.VIATYPE_MICROVIA and via.GetFrontWidth() == 350000 and via.GetDrill() == 150000
            and via.GetNetname() == "+3V3" and list(via.GetPosition()) == [150362500, 112100000]):
        raise RuntimeError("Codec via does not match the reviewed dimensions")
    via.SetViaType(pcbnew.VIATYPE_THROUGH)
    via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    via.SetWidth(pcbnew.FromMM(.35))
    pcbnew.SaveBoard(str(board_path), board)
    before_reports, before_summary = pipeline.check(work)
    before_drc = json.loads((before_reports / "drc.json").read_text(encoding="utf-8"))
    unexpected = [item for item in before_drc["violations"] if item["type"] not in {"annular_width", "via_diameter", "drill_out_of_range"}
                  or not any(anchor["uuid"] == IDENTIFIER for anchor in item.get("items", []))]
    pipeline.write_json(EVIDENCE / "unqualified-through-check.json", {"summary": str(before_reports / "summary.json"), "violations": before_drc["violations"], "unexpected": unexpected})
    if unexpected or not before_drc["violations"] or before_drc["unconnected_items"] or before_drc["schematic_parity"]:
        raise RuntimeError("Unexpected unqualified through-via result")
    rule_path.write_text(fixed_rules.rstrip() + "\n" + RULE, encoding="utf-8")
    contract_path = work / "net-contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    contract["qualified_codec_pth"] = {"uuid": IDENTIFIER, "net": "+3V3", "position_mm": [150.3625, 112.1],
        "copper_diameter_mm": .35, "nominal_finished_hole_mm": .15, "annular_ring_mm": .1,
        "type": "through", "required_filled": True, "required_copper_capped": True,
        "process_basis": "JLCPCB published small mechanical through-via capability and via-in-pad POFV guide; extra process selection required",
        "supplier_job_acceptance": False, "hardware_tested": False}
    pipeline.write_json(contract_path, contract)
    pipeline.write_json(EVIDENCE / "change-contract.json", {"changed_via": contract["qualified_codec_pth"], "added_rule": RULE,
        "ordinary_through_ring_minimum_mm": .125, "ordinary_hole_minimum_mm": .3, "ordinary_via_diameter_minimum_mm": .5,
        "physical_diameter_drill_position_unchanged": True, "only_added_copper_layers": ["F.Cu", "In1.Cu"],
        "unqualified_summary": str(before_reports / "summary.json"), "manufacturer_acceptance": False})
    reports, summary = pipeline.check(work)
    candidate["summary"] = str(reports / "summary.json")
    pipeline.write_json(candidate_path, candidate)
    print(json.dumps({"project": str(work), "status": summary["status"], "drc": summary["drc"]}))


if __name__ == "__main__":
    main()
