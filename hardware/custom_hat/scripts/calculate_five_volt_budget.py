"""Compare explicit 5V trunk/entry geometry and labelled load/tolerance scenarios."""
import json
import math

import pipeline


EVIDENCE = pipeline.BASE.parents[1] / "docs/references/hat-simulation-tools-20261029/five-volt-paths-20261031"
RIGHT = {"d3a0f827-09e1-455d-bb90-0f104cf7f343", "5de28ed8-9463-47dd-9b39-9ea257f3d33c", "aee6b79e-1168-4f9f-8d8b-551fb474e514"}
BRIDGE = "281bcde8-5d04-4765-a26d-002d523b7e94"


def main():
    contract = json.loads((EVIDENCE / "header-route-contract.json").read_text(encoding="utf-8"))
    groups = {"shared_trunk": {"before": [], "after": []}, "header_trunk": {"before": [], "after": []},
              "header_entry": {"before": [], "after": []}, "header_pin2_to_pin4": {"before": [], "after": []}}
    for entry in contract["changes"]:
        group = "shared_trunk" if entry["id"] in RIGHT else "header_trunk" if entry["layer"] == "In1.Cu" else "header_pin2_to_pin4" if entry["id"] == BRIDGE else "header_entry"
        for stage in ("before", "after"):
            item = entry[stage]
            if item is not None:
                groups[group][stage].append((math.dist(item["start"], item["end"]), item["width_mm"]))
    for index, route in enumerate(contract["trunk_routes"]):
        group = "shared_trunk" if index == 0 else "header_trunk"
        groups[group]["after"].extend((math.dist(start[:2], end[:2]), 1.2) for start, end in zip(route["points"], route["points"][1:]))
    geometry = {name: {stage: {"drawn_length_mm": sum(length for length, width in entries),
                              "sum_squares": sum(length / width for length, width in entries),
                              "selected_track_resistance_1oz25c_ohm": 0.0005 * sum(length / width for length, width in entries)}
                       for stage, entries in stages.items()} for name, stages in groups.items()}
    voltage_low = 0.8 * 0.99 * (1 + 52300 * 0.99 / (10000 * 1.01))
    voltage_high = 0.8 * 1.01 * (1 + 52300 * 1.01 / (10000 * 0.99))
    cases = []
    for controller in (1.0, 2.0):
        for amplifier in (0, 0.5, 1.0):
            for pin4_fraction in (0, 0.5, 1):
                currents = {"shared_trunk": controller + amplifier, "header_trunk": controller,
                            "header_entry": controller, "header_pin2_to_pin4": controller * pin4_fraction}
                result = {"assumed_radxa_a": controller, "assumed_amp_branch_a": amplifier, "assumed_pin4_fraction": pin4_fraction}
                for stage in ("before", "after"):
                    drops = {name: current * geometry[name][stage]["selected_track_resistance_1oz25c_ohm"] for name, current in currents.items()}
                    result[stage] = {"selected_copper_drop_v": sum(drops.values()),
                                     "source_low_minus_selected_drop_v": voltage_low - sum(drops.values()),
                                     "selected_copper_loss_w": sum(current ** 2 * geometry[name][stage]["selected_track_resistance_1oz25c_ohm"] for name, current in currents.items())}
                cases.append(result)
    result = {"geometry": geometry, "scenarios": cases, "feedback_voltage_corner_v": [voltage_low, voltage_high],
              "basis": "TI SSZP640 p9 approximate1oz25C0.5mOhm/square; AP64350Vref0.8V+-1%,R30152.3k/R30210k each1%; values unchanged from prior checkpoint",
              "limits": "Explicit selected drawn copper only, not the overlap-graph shortest-path cost. No source F.Cu track,via barrel,pad spreading,mating contact,ground return,Radxa ferrite R107,transient or thermal effect. Load splits are hypothetical,not measured. Source voltage minus selected drop is not a whole-board voltage guarantee or pass threshold.",
              "vendor_gpio_voltage_acceptance_window_found": False, "hardware_measured": False, "whole_board_power_approved": False}
    pipeline.write_json(EVIDENCE / "five-volt-budget.json", result)
    example = next(case for case in cases if case["assumed_radxa_a"] == 2 and case["assumed_amp_branch_a"] == 0.5 and case["assumed_pin4_fraction"] == 1)
    print(json.dumps({"geometry": geometry, "example": example, "source_corner_v": result["feedback_voltage_corner_v"]}))


if __name__ == "__main__":
    main()
