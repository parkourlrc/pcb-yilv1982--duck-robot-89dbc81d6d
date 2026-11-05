import hashlib
import json
import math
from pathlib import Path
from statistics import median

from PIL import Image


root = Path(__file__).resolve().parent
sources = root / "substitution-sources"


def read_red_curve(filename, horizontal, vertical, input_values):
    image = Image.open(sources / filename).convert("RGB")
    left, right, maximum_input = horizontal
    zero_row, lower_row, lower_percent = vertical
    readings = []
    for input_value in input_values:
        column = left + (right - left) * input_value / maximum_input
        pixels = []
        for xpos in range(round(column) - 2, round(column) + 3):
            for ypos in range(zero_row - 15, lower_row + 1):
                red, green, blue = image.getpixel((xpos, ypos))
                if red > 170 and red > green * 1.7 and red > blue * 1.4:
                    pixels.append(ypos)
        if not pixels:
            raise ValueError(f"No red curve at {input_value} in {filename}")
        row = median(pixels)
        change_percent = lower_percent * (row - zero_row) / (lower_row - zero_row)
        readings.append({"voltage_v": input_value, "column_px": column, "row_px": row, "change_percent": change_percent})
    return {"filename": filename, "image_size": image.size, "horizontal_calibration": horizontal, "vertical_calibration": vertical, "readings": readings}


main_caps = read_red_curve("murata-grm32-characteristics.png", [236, 634, 30], [910, 1158, -100], [5.119211, 8.4])
for reading in main_caps["readings"]:
    reading["single_typical_uf"] = 22 * (1 + reading["change_percent"] / 100)
    reading["pair_tolerance_temperature_sensitivity_uf"] = 44 * (0.98 + reading["change_percent"] / 100) * 0.9 * 0.85

audio_caps = read_red_curve("murata-grj155-characteristics.png", [210, 568, 7], [815, 1036, -100], [1.35, 1.65])
for reading in audio_caps["readings"]:
    reading["single_typical_uf"] = 10 * (1 + reading["change_percent"] / 100)
    reading["line_output_10kohm_typical_corner_hz"] = 1 / (2 * math.pi * 10000 * reading["single_typical_uf"] * 1e-6)

original_ldo_path = root.parent / "扩展板电路仿真工具/ldo-capacitors-20261031/electrical-margin.json"
original_ldo = json.loads(original_ldo_path.read_text(encoding="utf-8"))
capacitors = original_ldo["models"]
local_capacitance = capacitors["C0805C225K5RACTU"]["points"][0]["typical_model_effective_uf"] * 1e-6
remote_capacitance = capacitors["C0402C105K4PACTU"]["points"][0]["typical_model_effective_uf"] * 1e-6
esr = original_ldo["esr_readings"]
ldo_scenarios = []
for damping in [0.047, 0.05]:
    for remote_resistance in [0, 0.05, 0.2]:
        for remote_inductance in [0, 20e-9, 100e-9]:
            points = []
            for index, frequency in enumerate(esr["frequencies_hz"]):
                local_esr = esr["ohms"]["C0805C225K5RACTU"][index]
                remote_esr = esr["ohms"]["C0402C105K4PACTU"][index]
                if local_esr is None or remote_esr is None:
                    continue
                omega = 2 * math.pi * frequency
                local = complex(local_esr + damping, omega * 1e-9 - 1 / (omega * local_capacitance))
                remote = complex(remote_esr + remote_resistance, omega * (remote_inductance + 1e-9) - 1 / (omega * remote_capacitance))
                combined = 1 / (1 / local + 1 / remote)
                points.append((frequency, combined.real))
            ldo_scenarios.append({"damping_ohm": damping, "remote_resistance_ohm": remote_resistance, "remote_inductance_h": remote_inductance,
                                  "min_real_10khz_1mhz_ohm": min(value for frequency, value in points if frequency <= 1e6),
                                  "min_real_1mhz_10mhz_ohm": min(value for frequency, value in points if frequency >= 1e6)})

result = {
    "date": "2026-11-03", "hardware_measurement": False, "closed_loop_stability_verified": False,
    "main_capacitors": main_caps, "audio_capacitors": audio_caps, "damping_scenarios": ldo_scenarios,
    "ldo_model_source_sha256": hashlib.sha256(original_ldo_path.read_bytes()).hexdigest(),
    "ldo_full_temperature_output_range_v": [1.8 * 0.95, 1.8 * 1.05],
    "codec_dvdd_recommended_range_v": [1.525, 1.95],
    "inductor_3p5a_dcr_max_delta_w": 3.5 ** 2 * (0.0193 - 0.0176),
    "inductor_temperature_limit_c_old_new": [155, 125],
    "buck_peak_current_limit_max_a_old_new": [5.75, 9.2],
    "limits": "Raster typical curves only, no combined-process guarantee or actual waveforms. Cap sensitivity uses -2 percentage points, -10% tolerance, -15% TCC and no aging allowance. Audio 10kohm load and midrail DC bias are illustrative assumptions, not user load measurements. LDO passive network inherits assumed ESL/trace impedance and contains no regulator loop or resistor inductance model."
}
(root / "substitution-deltas.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps({"main_caps": main_caps["readings"], "audio_caps": audio_caps["readings"], "ldo_50mohm_min_10khz_1mhz": min(item["min_real_10khz_1mhz_ohm"] for item in ldo_scenarios if item["damping_ohm"] == 0.05)}, indent=2))
