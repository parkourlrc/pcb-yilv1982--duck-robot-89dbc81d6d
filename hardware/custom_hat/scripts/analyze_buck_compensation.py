"""Cross-check the AP64350 compensation network and declared capacitor scenarios."""
import cmath
import csv
import hashlib
import json
import math
from pathlib import Path
import subprocess

import pcbnew

import pipeline


EVIDENCE = pipeline.BASE.parents[1] / "docs/references/hat-simulation-tools-20261029/power-acceptance-20261031"
BASELINE = "a65f2ad8cab72721944b670dbdb6505533ae60988ce5bb3c6be51be81b3ab0a1"
GM = .00015
CURRENT_SENSE = .089


def theoretical(frequency, case):
    frequency_domain = 2j * math.pi * frequency
    top = case["top_ohm"] / (1 + frequency_domain * case["top_ohm"] * case["feedforward_f"])
    feedback = case["bottom_ohm"] / (top + case["bottom_ohm"])
    series = case["comp_ohm"] + 1 / (frequency_domain * case["comp_f"])
    impedance = 1 / (1 / series + frequency_domain * case["hf_f"])
    correct = GM * impedance * feedback
    printed = correct * case["comp_ohm"] / case["bottom_ohm"]
    return feedback, correct, printed


def simulate(case):
    directory = EVIDENCE / "spice" / case["name"]
    directory.mkdir(parents=True, exist_ok=True)
    netlist = ["Isolated small-signal perturbation network, not a regulator model", "Vsignal out 0 DC 0 AC 1",
               "Rupper out fb " + str(case["top_ohm"]), "Rlower fb 0 " + str(case["bottom_ohm"]),
               "Gerror comp 0 fb 0 " + str(GM), "Rcomp comp series " + str(case["comp_ohm"]),
               "Ccomp series 0 " + str(case["comp_f"]), "Rdc comp 0 1e12"]
    if case["feedforward_f"]:
        netlist.append("Cff out fb " + str(case["feedforward_f"]))
    if case["hf_f"]:
        netlist.append("Chf comp 0 " + str(case["hf_f"]))
    netlist.extend([".ac dec 50 10 10Meg", ".control", "set noaskquit", "set wr_singlescale", "set wr_vecnames", "set numdgt=12",
                    "run", "wrdata response.dat v(fb) v(comp)", "quit", ".endc", ".end"])
    circuit = directory / "network.cir"
    circuit.write_text("\n".join(netlist) + "\n", encoding="ascii")
    simulator = Path.home() / "AppData/Local/duck-robot-tools/ngspice-47/Spice64/bin/ngspice_con.exe"
    result = subprocess.run([str(simulator), "-b", str(circuit.resolve())], cwd=directory, capture_output=True, encoding="utf-8", errors="replace", timeout=60)
    (directory / "ngspice.log").write_text(result.stdout + result.stderr, encoding="utf-8")
    if result.returncode:
        raise RuntimeError("Compensation network simulation failed: " + case["name"])
    rows = []
    for line in (directory / "response.dat").read_text(encoding="utf-8").splitlines():
        try:
            values = [float(value) for value in line.split()]
        except ValueError:
            continue
        if len(values) != 5:
            raise RuntimeError("Unexpected ngspice complex-data format")
        frequency = values[0]
        native_feedback = complex(values[1], values[2])
        native_gain = -complex(values[3], values[4])
        feedback, correct, printed = theoretical(frequency, case)
        rows.append({"case": case["name"], "frequency_hz": frequency,
                     "derived_gain_db": 20 * math.log10(abs(correct)), "spice_gain_db": 20 * math.log10(abs(native_gain)),
                     "printed_eq12_gain_db": 20 * math.log10(abs(printed)), "derived_phase_deg": math.degrees(cmath.phase(correct)),
                     "spice_phase_deg": math.degrees(cmath.phase(native_gain)), "relative_error": abs(native_gain - correct) / abs(correct),
                     "feedback_relative_error": abs(native_feedback - feedback) / abs(feedback)})
    if len(rows) < 100:
        raise RuntimeError("Too few AC points")
    maximum = max(row["relative_error"] for row in rows)
    if maximum > 1e-5:
        raise RuntimeError("Independent network calculation differs from SPICE")
    return rows, {"case": case, "points": len(rows), "maximum_relative_error": maximum,
                  "printed_prefactor_ratio": case["comp_ohm"] / case["bottom_ohm"],
                  "printed_gain_offset_db": 20 * math.log10(case["comp_ohm"] / case["bottom_ohm"])}


def main():
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    source = pipeline.PRIMARY / (pipeline.STEM + ".kicad_pcb")
    source_hashes = pipeline.fingerprints(pipeline.PRIMARY)
    if pipeline.digest(source) != BASELINE:
        raise RuntimeError("Power study baseline changed")
    board = pcbnew.LoadBoard(str(source))
    parts = {}
    for reference in ("U301", "R301", "R302", "R303", "R304", "R305", "C301", "C302", "C303", "C304", "C305", "C306", "C307", "C323", "C328", "L301", "D301", "J301"):
        item = board.FindFootprintByReference(reference)
        parts[reference] = {"value": item.GetValue(), "mpn": item.GetFieldText("MPN"), "attributes": int(item.GetAttributes()),
                            "pads": {pad.GetNumber(): {"net": pad.GetNetname(), "position_mm": [pcbnew.ToMM(value) for value in pad.GetPosition()]} for pad in item.Pads()}}
    expected = {"R301": "52.3k", "R302": "10k", "R304": "14k", "C301": "3.3nF"}
    if any(parts[reference]["value"] != value for reference, value in expected.items()):
        raise RuntimeError("Current compensation values differ from the studied network")
    pipeline.write_json(EVIDENCE / "native-power-parts.json", {"source_hashes": source_hashes, "parts": parts})
    cases = [
        {"name": "datasheet_reference", "top_ohm": 115000, "bottom_ohm": 22100, "comp_ohm": 14000, "comp_f": 3.3e-9, "hf_f": 47e-12, "feedforward_f": 0},
        {"name": "current_board", "top_ohm": 52300, "bottom_ohm": 10000, "comp_ohm": 14000, "comp_f": 3.3e-9, "hf_f": 0, "feedforward_f": 0},
        {"name": "same_ratio_double_resistance", "top_ohm": 104600, "bottom_ohm": 20000, "comp_ohm": 14000, "comp_f": 3.3e-9, "hf_f": 0, "feedforward_f": 0},
    ]
    all_rows, summaries = [], []
    for case in cases:
        rows, summary = simulate(case)
        all_rows.extend(rows)
        summaries.append(summary)
    with (EVIDENCE / "compensation-ac.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(all_rows[0]))
        writer.writeheader()
        writer.writerows(all_rows)
    capacitor_path = EVIDENCE.parent / "amp-decoupling-20261031/capacitor-margin.json"
    capacitors = json.loads(capacitor_path.read_text(encoding="utf-8"))["models"]
    bulk = max(capacitors["C323"]["points"], key=lambda item: item["dc_v"])
    bypass = max(capacitors["C328"]["points"], key=lambda item: item["dc_v"])
    local_typical = 2 * bulk["typical_model_effective_uf"]
    local_low_scenario = 2 * min(item["scenario_effective_uf"] for item in bulk["sensitivity_cases"])
    all_typical = 3 * bulk["typical_model_effective_uf"] + bypass["typical_model_effective_uf"]
    crossover = []
    for capacitance_uf in (local_low_scenario, local_typical, all_typical, 100.0, 300.0):
        for upper_factor in (.99, 1, 1.01):
            for lower_factor in (.99, 1, 1.01):
                for comp_factor in (.99, 1, 1.01):
                    beta = 10000 * lower_factor / (52300 * upper_factor + 10000 * lower_factor)
                    frequency = 14000 * comp_factor * GM * beta / (2 * math.pi * capacitance_uf * 1e-6 * CURRENT_SENSE)
                    crossover.append({"capacitance_uf": capacitance_uf, "feedback_upper_factor": upper_factor, "feedback_lower_factor": lower_factor,
                                      "compensation_factor": comp_factor, "first_order_crossover_hz": frequency})
    zero_frequency = 1 / (2 * math.pi * 14000 * 3.3e-9)
    output = {"pcb_sha256": BASELINE, "native_parts": "native-power-parts.json", "compensation_network_checks": summaries,
              "derived_transfer": "A(s)K(s)=gm*Zcomp(s)*beta(s); beta=Rlow/(Rup+Rlow) when feedforward capacitor is open",
              "eq12_discrepancy": "Fig27 ideal network yields Rlow in the low-frequency prefactor; printed Eq12 uses Rcomp. This is a circuit derivation, not an official erratum or full IC model.",
              "compensation_zero_hz": zero_frequency, "nominal_source_voltage_v": .8 * (1 + 52300 / 10000),
              "capacitance_basis": {"source": str(capacitor_path), "sha256": hashlib.sha256(capacitor_path.read_bytes()).hexdigest(),
                                    "local_c305_c306_typical_uf": local_typical, "local_low_assumed_scenario_uf": local_low_scenario,
                                    "all_onboard_5v_caps_typical_uf": all_typical, "c307_dnp_excluded": True},
              "first_order_crossover_scenarios": crossover,
              "maximum_first_order_crossover_hz": max(row["first_order_crossover_hz"] for row in crossover),
              "gm_s": GM, "current_sense_ohm": CURRENT_SENSE,
              "limits": ["Constant nominal gm and sense gain from datasheet, not min/max guarantees", "Eq17 first-order crossover is not phase margin or a stability proof",
                         "Capacitance values are archived typical models and explicit derating scenarios, not guaranteed minima", "Remote and Radxa capacitors cannot simply be lumped at all frequencies",
                         "No current-loop sampling, slope compensation, parasitics, switching, nonlinear load or hardware response model"],
              "hardware_tested": False, "full_loop_verified": False, "source_unchanged": source_hashes == pipeline.fingerprints(pipeline.PRIMARY)}
    pipeline.write_json(EVIDENCE / "compensation-check.json", output)
    print(json.dumps({"network_checks": summaries, "zero_hz": zero_frequency, "capacitance_basis": output["capacitance_basis"],
                      "maximum_first_order_crossover_hz": output["maximum_first_order_crossover_hz"], "source_unchanged": output["source_unchanged"]}))


if __name__ == "__main__":
    main()
