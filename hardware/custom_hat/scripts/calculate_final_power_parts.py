"""Compute explicit ideal-buck and jumper checks without claiming board ratings."""
import itertools
import math

import pipeline


EVIDENCE = pipeline.BASE.parents[1] / "docs/references/hat-simulation-tools-20261029/final-bom-20261031"


def main():
    output_low = 0.8 * 0.99 * (1 + 52300*0.99/(10000*1.01))
    output_high = 0.8 * 1.01 * (1 + 52300*1.01/(10000*0.99))
    minimum_inductance = 5.6e-6 * 0.8 * 0.8
    corners = []
    for input_voltage, output_voltage, frequency, load in itertools.product(
            (6.6, 7.4, 8.4), (output_low, 4.984, output_high), (450000, 500000, 550000), (1.0, 2.0, 3.5)):
        ripple = output_voltage * (input_voltage-output_voltage) / (input_voltage * minimum_inductance * frequency)
        peak = load + ripple/2
        rms = math.sqrt(load*load + ripple*ripple/12)
        corners.append({"vin_v": input_voltage, "vout_v": output_voltage, "frequency_hz": frequency, "load_a": load,
                        "ripple_pp_a": ripple, "inductor_peak_a": peak, "inductor_rms_a": rms, "dcr_loss_25c_w": rms*rms*0.0176})
    worst = max(corners, key=lambda item: item["inductor_peak_a"])
    jumper = [{"current_a": current, "drop_25c_v": current*0.0002, "loss_25c_w": current*current*0.0002,
               "loss_85c_w_nominal_tcr": current*current*0.0002*(1+0.0039*60)} for current in (1.0, 3.0, 5.0, 8.0)]
    result = {
        "basis": {
            "regulator": "AP64350 DS41976 p1/p5: Vref0.8V+-1%, RT200k+-1% gives450-550kHz, HS peak limit minimum4.25A",
            "inductor": "Vishay34315 p1:5.6uH+-20%, 20% L drop at9A typical25C, DCR17.6mOhm max25C",
            "jumper": "Vishay30192 p1-2:0.2mOhm max, nominalTCR3900ppm/C",
            "input_window": "6.6-8.4V is an analysis window, not a measured battery voltage or approved cutoff",
            "bias_assumption": "Extra20% L derating is a conservative assumed scenario; manufacturer9A value is typical, not guaranteed over temperature",
            "model": "Ideal continuous-conduction buck; excludes switch losses, switching/core loss, control-loop dynamics, thermal and input/output ripple feedback"
        },
        "feedback_range_including_reference_and_resistors_v": [output_low, output_high],
        "assumed_minimum_inductance_uh": minimum_inductance*1e6,
        "worst_peak_corner": worst,
        "margin_to_minimum_ic_peak_limit_a": 4.25-worst["inductor_peak_a"],
        "corners": corners, "jumper_scenarios": jumper,
        "speaker_2p5w_4ohm_rms_a_ideal": math.sqrt(2.5/4),
        "connector_limits": {"EH": "3A withAWG22 at manufacturer conditions", "SH": "1A withAWG28 at manufacturer conditions"},
        "production_ready": False, "hardware_measured": False,
    }
    pipeline.write_json(EVIDENCE / "power-part-calculations.json", result)
    print({"vout_range": [output_low, output_high], "worst_peak_a": worst["inductor_peak_a"],
           "minimum_peak_limit_margin_a": result["margin_to_minimum_ic_peak_limit_a"], "jumper": jumper})


if __name__ == "__main__":
    main()
