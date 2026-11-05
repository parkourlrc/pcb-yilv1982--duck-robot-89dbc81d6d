import hashlib
import json
import math
from pathlib import Path


base = Path(__file__).resolve().parent
repository = base.parents[2]
source = repository / "hardware/custom_hat/rev_a/custom_hat_rev_a.kicad_pcb"
target_voltage = 0.8 * (1 + 52300 / 10000)
ripple_cases = []
for input_voltage in (6.0, 6.6, 8.4):
    for frequency in (500000, 570000):
        ripple = target_voltage * (input_voltage - target_voltage) / (input_voltage * 5.6e-6 * frequency)
        ripple_cases.append({"vin_v": input_voltage, "frequency_hz": frequency, "inductor_nominal_h": 5.6e-6, "ripple_a": ripple})

minimum_inductance_scenario = 5.6e-6 * 0.8 * 0.8
minimum_frequency_scenario = 510000 * 0.94
scenario_ripple = target_voltage * (8.4 - target_voltage) / (8.4 * minimum_inductance_scenario * minimum_frequency_scenario)
document = {
    "date": "2026-11-04",
    "source_pcb_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    "cad_modified": False,
    "analysis_type": "equations_only_not_closed_loop_or_hardware_test",
    "target_voltage_v": target_voltage,
    "feedback_and_compensation_unchanged_candidate": {"upper_ohm": 52300, "lower_ohm": 10000, "comp_r_ohm": 14000, "comp_c_f": 3.3e-9, "zero_hz": 1 / (2 * math.pi * 14000 * 3.3e-9)},
    "soft_start": {"proposed_ref": "C331", "replaces": "R303", "capacitance_f": 22e-9, "datasheet_minimum_f": 10e-9, "nominal_charge_current_a": 4e-6, "nominal_reference_v": 0.8, "nominal_time_ms": 22e-9 * 0.8 / 4e-6 * 1000, "independent_tolerance_temperature_capacitance_f": 22e-9 * 0.9 * 0.85, "limits": "No current-source tolerance, aging, combined bias/temperature or actual startup-load model; capacitor lower scenario is not a guaranteed minimum"},
    "nominal_ripple": ripple_cases,
    "independent_stress_scenario": {"vin_v": 8.4, "minimum_inductance_h": minimum_inductance_scenario, "minimum_frequency_hz": minimum_frequency_scenario, "ripple_a": scenario_ripple, "peak_at_assumed_3p5a_load_a": 3.5 + scenario_ripple / 2, "datasheet_min_peak_limit_a": 4.25, "limits": "L tolerance -20%, additional assumed -20% DC bias, f-min and -6% spread combined conservatively; no transient or actual load guarantee"},
    "audio_thermal_scenario": {"output_power_w": 2.5, "assumed_efficiency": 0.85, "calculated_loss_w": 2.5 * (1 / 0.85 - 1), "datasheet_theta_ja_soic_c_per_w": 115, "datasheet_theta_ja_msop_c_per_w": 180, "calculated_msop_delta_t_c": 2.5 * (1 / 0.85 - 1) * 180, "limits": "Simplified illustration, datasheet board boundary not matched to this HAT; 2.5W is a 10%-THD table point, not a clean continuous audio specification"},
    "pin_contract_changes": [{"ref": "U301", "pin": "4", "old_function": "RT/CLK", "new_function": "SS", "old_net": "BUCK_RT", "new_net": "BUCK_SS"}],
    "source_identity": "AP64351 DS41977 Rev4-2 Aug2019 vendor-authored PDF mirrored by LCSC; not asserted latest",
}
(base / "plan-calculations.json").write_text(json.dumps(document, indent=2), encoding="utf-8")
print(json.dumps({"target_voltage_v": target_voltage, "soft_start_ms": document["soft_start"]["nominal_time_ms"], "stress_peak_a": document["independent_stress_scenario"]["peak_at_assumed_3p5a_load_a"], "audio_msop_delta_t_c": document["audio_thermal_scenario"]["calculated_msop_delta_t_c"]}))
