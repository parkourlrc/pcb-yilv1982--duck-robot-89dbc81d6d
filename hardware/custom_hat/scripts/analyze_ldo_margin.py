"""Evaluate typical capacitor/ESR scenarios without claiming LDO loop stability."""
import csv
import json
import math
import statistics

from PIL import Image

import pipeline
from digitize_capacitor_bias import decode_curve


EVIDENCE = pipeline.BASE.parents[1] / "docs/references/扩展板电路仿真工具/ldo-capacitors-20261031"
SOURCES = EVIDENCE.parent / "capacitor-models-20261031/sources"
PARTS = {"C0805C105K5RACTU": {"nominal_uf": 1, "rated_v": 50, "tolerance": 0.10, "aging_pct_per_decade": 3, "voltages": [1.8, 3.3]},
         "C0805C225K5RACTU": {"nominal_uf": 2.2, "rated_v": 50, "tolerance": 0.10, "aging_pct_per_decade": 3, "voltages": [1.8, 3.3]},
         "C0402C105K4PACTU": {"nominal_uf": 1, "rated_v": 16, "tolerance": 0.10, "aging_pct_per_decade": 5, "voltages": [1.8]}}
ESR_AXES = {"C0805C105K5RACTU": (272.2, 74.45), "C0805C225K5RACTU": (247.0, 74.55),
            "C0402C105K4PACTU": (262.6, 71.2)}


def read_esr(part, frequencies):
    image = Image.open(SOURCES / (part + "-impedance-esr.png")).convert("RGB")
    axis_zero, pixels_per_decade = ESR_AXES[part]
    result = []
    for frequency in frequencies:
        xpos = 80 + 60 * (math.log10(frequency) - 2)
        columns = []
        for column in (math.floor(xpos), math.ceil(xpos)):
            rows = []
            for ypos in range(35, 430):
                red, green, blue = image.getpixel((column, ypos))
                if 90 < red < 180 and green > red + 7 and blue > green + 20:
                    rows.append(ypos)
            if not rows:
                columns.append(None)
            else:
                columns.append(statistics.median(rows))
        if None in columns:
            result.append(None)
        else:
            fraction = xpos - math.floor(xpos)
            ypos = columns[0] + fraction * (columns[1] - columns[0])
            result.append(10 ** ((axis_zero - ypos) / pixels_per_decade))
    return result


def main():
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    models = {part: decode_curve(part, profile) for part, profile in PARTS.items()}
    frequencies = [10 ** (4 + index / 40) for index in range(121)]
    esrs = {part: read_esr(part, frequencies) for part in PARTS}
    new_cap = models["C0805C225K5RACTU"]["points"][0]
    old_cap = models["C0805C105K5RACTU"]["points"][0]
    remote_cap = models["C0402C105K4PACTU"]["points"][0]
    rows = []
    summaries = []
    for name, part, resistor in (("old_local_1uF", "C0805C105K5RACTU", 0),
                                 ("new_2u2_no_damping", "C0805C225K5RACTU", 0),
                                 ("new_2u2_47mOhm", "C0805C225K5RACTU", 0.047)):
        local_cap = old_cap if part == "C0805C105K5RACTU" else new_cap
        for remote_r in (0, 0.05, 0.2):
            for remote_l in (0, 20e-9, 100e-9):
                values = []
                for index, frequency in enumerate(frequencies):
                    local_esr = esrs[part][index]
                    remote_esr = esrs["C0402C105K4PACTU"][index]
                    if local_esr is None or remote_esr is None:
                        continue
                    omega = 2 * math.pi * frequency
                    local = complex(local_esr + resistor, omega * 1e-9 - 1 / (omega * local_cap["typical_model_effective_uf"] * 1e-6))
                    remote = complex(remote_esr + remote_r, omega * (remote_l + 1e-9) - 1 / (omega * remote_cap["typical_model_effective_uf"] * 1e-6))
                    combined = 1 / (1 / local + 1 / remote)
                    row = {"case": name, "remote_route_r_ohm": remote_r, "remote_route_l_h": remote_l,
                           "frequency_hz": frequency, "combined_real_ohm": combined.real, "combined_abs_ohm": abs(combined)}
                    rows.append(row)
                    values.append(row)
                summaries.append({"case": name, "remote_route_r_ohm": remote_r, "remote_route_l_h": remote_l,
                                  "min_real_10khz_1mhz_ohm": min(row["combined_real_ohm"] for row in values if row["frequency_hz"] <= 1e6),
                                  "min_real_1mhz_10mhz_ohm": min(row["combined_real_ohm"] for row in values if row["frequency_hz"] >= 1e6)})
    with (EVIDENCE / "passive-output-network.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    document = {"models": models, "esr_axes_pixels": ESR_AXES, "esr_readings": {"frequencies_hz": frequencies, "ohms": esrs},
                "passive_network_summaries": summaries,
                "model_scope": "Typical manufacturer raster ESR, DC-biased C, assumed local/remote ESL1nH, remote traceR0/50/200mOhm and L0/20/100nH; sensitivity cases, not extracted parasitics.",
                "limits": "No LDO feedback/open-loop model, joint voltage/temperature/AC-frequency ageing model or ESR guaranteed range. TI does not specify an ESR test frequency in9.2.2.4;10kHz-1MHz window is only a chosen sensitivity window. C311 shunts R703 at high frequency;47mOhm is not a whole-rail ESR lower bound.",
                "resistor_47mohm": {"initial_1pct_range_ohm": [0.04653, 0.04747], "tcr_ppm_per_c": 110,
                                   "tcr_scope": "Vishay30122 p2 footnote:25C to155C; sub25C behaviour requires vendor clarification",
                                   "power_at_assumed_0p5a_rms_w": 0.5 ** 2 * 0.047,
                                   "not_load_ground": True},
                "old_output_capacitance_is_not_proven_insufficient": True,
                "old_output_reason": "C311 also loads1V8. Its capacitance must be included; isolated C309 value does not establish whole-rail insufficiency.",
                "closed_loop_stability_verified": False, "hardware_measurement": False}
    pipeline.write_json(EVIDENCE / "electrical-margin.json", document)
    print(json.dumps({"capacities": {part: [{"v": point["dc_v"], "typical_uf": point["typical_model_effective_uf"],
                       "scenarios": point["sensitivity_cases"]} for point in model["points"]] for part, model in models.items()}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
