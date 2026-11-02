"""Calculate labelled transient and input-current scenarios without assigning a board rating."""
import json
import math
from pathlib import Path

import pipeline
from analyze_buck_compensation import EVIDENCE, BASELINE


def main():
    if pipeline.digest(pipeline.PRIMARY / (pipeline.STEM + ".kicad_pcb")) != BASELINE:
        raise RuntimeError("Power scenario baseline changed")
    compensation = json.loads((EVIDENCE / "compensation-check.json").read_text(encoding="utf-8"))
    capacitor_path = EVIDENCE.parent / "amp-decoupling-20261031/capacitor-margin.json"
    capacitor_data = json.loads(capacitor_path.read_text(encoding="utf-8"))["models"]
    bulk_points = capacitor_data["C323"]["points"]
    nominal_bulk = min(bulk_points, key=lambda row: abs(row["dc_v"] - 4.984))
    high_bulk = max(bulk_points, key=lambda row: row["dc_v"])
    high_bypass = max(capacitor_data["C328"]["points"], key=lambda row: row["dc_v"])
    cap_cases = {
        "local_low_scenario": compensation["capacitance_basis"]["local_low_assumed_scenario_uf"],
        "local_typical_high_voltage": compensation["capacitance_basis"]["local_c305_c306_typical_uf"],
        "onboard_lumped_low_scenario": 3 * min(row["scenario_effective_uf"] for row in high_bulk["sensitivity_cases"]) + min(row["scenario_effective_uf"] for row in high_bypass["sensitivity_cases"]),
        "onboard_lumped_typical": compensation["capacitance_basis"]["all_onboard_5v_caps_typical_uf"],
    }
    transient = []
    maximum_inductance = 5.6e-6 * 1.2
    for name, capacitance_uf in cap_cases.items():
        for input_voltage in (6.6, 7.4, 8.4):
            for allowed_excursion in (.1, .2, .3):
                output_voltage = 5.119210505050505
                headroom = min(output_voltage, input_voltage - output_voltage)
                maximum_step = math.sqrt(capacitance_uf * 1e-6 * allowed_excursion * headroom / maximum_inductance)
                transient.append({"capacitance_case": name, "capacitance_uf": capacitance_uf, "vin_v": input_voltage,
                                  "vout_assumed_v": output_voltage, "assumed_allowed_excursion_v": allowed_excursion,
                                  "eq11_step_boundary_a": maximum_step, "inductance_assumed_h": maximum_inductance})
    input_cases = []
    for input_voltage in (6.6, 7.4, 8.4):
        for load in (1, 2, 2.5, 3.5):
            for first_servo, second_servo in ((0, 0), (1.5, 1.5), (3, 0), (3, 3)):
                efficiency = .85
                current = first_servo + second_servo + 5 * load / (input_voltage * efficiency)
                input_cases.append({"vin_v": input_voltage, "five_volt_load_a": load, "assumed_efficiency": efficiency,
                                    "j401_current_a": first_servo, "j402_current_a": second_servo, "input_current_a": current,
                                    "above_5p7a_catalog_comparison": current > 5.7})
    nominal_local_cap = 2 * nominal_bulk["typical_model_effective_uf"]
    recommended_comp_f = 4.984 * nominal_local_cap * 1e-6 / (3.5 * 14000)
    result = {"pcb_sha256": BASELINE, "compensation_eq18_nominal_local_case": {"capacitance_uf": nominal_local_cap,
                  "assumed_iout_a": 3.5, "suggested_ccomp_f": recommended_comp_f, "selected_ccomp_f": 3.3e-9},
              "transient_scenarios": transient, "input_current_scenarios": input_cases,
              "limits": ["Eq11 boundary is a datasheet sizing screen, not a guaranteed measured load step",
                         "Excursion values are scenario inputs, not a Radxa acceptance window",
                         "Only local capacitors are conservative for fast events; remote lumped cases require impedance verification",
                         "Typical capacitance and independent derating assumptions are not guaranteed minima",
                         "5.7A is a conditional Samtec catalog comparison for specified mating/loading conditions, not this board or harness rating",
                         "Two 3A connector scenarios do not establish permissible simultaneous loads", "No actual battery/BMS, thermal or transient measurements"],
              "board_current_rating_assigned": False, "hardware_tested": False}
    pipeline.write_json(EVIDENCE / "power-envelope.json", result)
    example = [row for row in transient if row["vin_v"] == 6.6 and row["assumed_allowed_excursion_v"] == .2]
    current_example = next(row for row in input_cases if row["vin_v"] == 6.6 and row["five_volt_load_a"] == 2.5 and row["j401_current_a"] == 3 and row["j402_current_a"] == 3)
    print(json.dumps({"eq18_local_nominal": result["compensation_eq18_nominal_local_case"], "eq11_example": example, "input_example": current_example}))


if __name__ == "__main__":
    main()
