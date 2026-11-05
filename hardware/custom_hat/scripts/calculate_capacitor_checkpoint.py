"""Bind archived typical capacitor models to the promoted buck checkpoint."""
import json

import pipeline


EVIDENCE = pipeline.BASE.parents[1] / "docs/references/扩展板电路仿真工具/capacitor-upgrade-20261031"
MODELS = EVIDENCE.parent / "capacitor-models-20261031/bias-sensitivity.json"


def main():
    checkpoint = json.loads((EVIDENCE / "checkpoint.json").read_text(encoding="utf-8"))
    model = json.loads(MODELS.read_text(encoding="utf-8"))
    selected = model["models"]["C1210C226K3RACTU"]
    cases = []
    for point in selected["points"]:
        role = "output_C305_C306" if point["dc_v"] < 6 else "input_C303_C304"
        for scenario in point["sensitivity_cases"]:
            entry = {"role": role, "voltage_v": point["dc_v"], "quantity": 2,
                     "age_hours": scenario["age_hours_from_reference"],
                     "single_typical_uf": point["typical_model_effective_uf"],
                     "combined_scenario_uf": 2 * scenario["scenario_effective_uf"]}
            if role.startswith("output"):
                entry["eq17_crossover_hz"] = 14140 / (4670 * 4.852137029702971 * entry["combined_scenario_uf"] * 1e-6)
                entry["margin_to_first_order_cout_reference"] = entry["combined_scenario_uf"] / model["eq17_minimum_effective_cout_for_45khz_uf"]
            cases.append(entry)
    result = {"pcb_sha256": checkpoint["pcb_sha256"], "mpn": "C1210C226K3RACTU",
              "model_source": str(MODELS), "model_source_sha256": pipeline.digest(MODELS),
              "assumptions": model["scenario_assumptions"], "unmodelled_effects": model["unmodelled_effects"],
              "lifetime_scope": model["operating_lifetime_not_specified_by_user"],
              "manufacturer_guaranteed_lower_bound": False, "hardware_measurement": False,
              "closed_loop_stability_verified": False, "c307_dnp": True, "cases": cases}
    pipeline.write_json(EVIDENCE / "effective-capacitance.json", result)
    print(json.dumps(cases, ensure_ascii=False))


if __name__ == "__main__":
    main()
