"""Quantify selected positive-conductor losses without assigning a whole-board current rating."""
import json
import math
from pathlib import Path

import pipeline


EVIDENCE = pipeline.BASE.parents[1] / "docs/references/hat-simulation-tools-20261029/power-paths-20261031"


def main():
    contract = json.loads((EVIDENCE / "power-route-contract.json").read_text(encoding="utf-8"))
    records = contract["changes"]
    shared_ids = {"93a89441-6459-41d7-956e-b7dfaa02fade", "e1c190b7-cc1b-41a3-b0ce-d0889a72426a", "e223a735-1756-4d40-87cd-cf00410a7e6e"}
    bridge_ids = {"5c639288-cbd2-443d-a2d3-c5712368da77", "99f29545-b6d2-4e73-804b-8dfdb1bfa242"}
    servo_shared = {"adb2d5dc-8965-460e-9f85-6e5136c45722", "bdc386a8-8fbb-44c6-96d4-e312c5c99d89"}
    groups = {"battery_shared_input": shared_ids, "battery_to_R309": bridge_ids,
              "R309_to_J402_shared": servo_shared,
              "J402_to_J401": {entry["id"] for entry in records if entry["net"] == "SERVO_VBAT"} - servo_shared}
    geometry = {}
    for name, identifiers in groups.items():
        geometry[name] = {}
        for stage in ("before", "after"):
            lengths, squares = [], []
            for entry in records:
                if entry["id"] not in identifiers or entry[stage] is None:
                    continue
                item = entry[stage]
                length = math.dist(item["start"], item["end"])
                lengths.append(length)
                squares.append(length / item["width_mm"])
            if name == "J402_to_J401" and stage == "after":
                for start, end in zip(contract["right_servo_route"], contract["right_servo_route"][1:]):
                    length = math.dist(start[:2], end[:2])
                    lengths.append(length)
                    squares.append(length / 1.2)
            geometry[name][stage] = {"drawn_length_mm": sum(lengths), "squares": sum(squares), "resistance_1oz_25c_ohm": 0.0005 * sum(squares)}
    cases = []
    for input_voltage in (6.6, 7.4, 8.4):
        for efficiency in (0.85, 0.90, 0.95):
            for left, right in ((0, 0), (0, 3), (3, 0), (3, 3)):
                output_5v_a = 2.0
                buck_input = 5 * output_5v_a / (input_voltage * efficiency)
                servo_sum = left + right
                total = buck_input + servo_sum
                currents = {"battery_shared_input": total, "battery_to_R309": servo_sum, "R309_to_J402_shared": servo_sum, "J402_to_J401": right}
                stage_results = {}
                for stage in ("before", "after"):
                    losses = {name: current ** 2 * geometry[name][stage]["resistance_1oz_25c_ohm"] for name, current in currents.items()}
                    drops = {name: current * geometry[name][stage]["resistance_1oz_25c_ohm"] for name, current in currents.items()}
                    stage_results[stage] = {"path_losses_w": losses, "selected_positive_tracks_loss_w": sum(losses.values()),
                                            "selected_tracks_drop_to_J401_v": sum(drops.values())}
                cases.append({"input_v": input_voltage, "assumed_buck_efficiency": efficiency, "5v_load_a": output_5v_a,
                              "J402_load_a": left, "J401_load_a": right, "calculated_shared_input_a": total,
                              "exceeds_conditional_5p7a_contact_comparison": total > 5.7, **stage_results})
    result = {"basis": {"copper": "TI SSZP640 p9: approximate sheet resistance at25C,0.5/1/2oz=1/0.5/0.25mOhm per square;125C=1.4/0.7/0.35mOhm per square",
                        "controller": "Radxa ZERO3W product brief RAD-DOC-0084 v1.12, PDFp6(section5.1):5V/2A adapter andGPIO pins2/4 power; adapter guidance is not measured operating current",
                        "connector": "Archived Samtec TSW catalogue:5.7A per pin when mated withSSW and2positions powered; not a universal header or assembled-board rating",
                        "efficiency_and_load": "Vin6.6/7.4/8.4V,efficiency85/90/95%,5V load2A andservo port0/3A are sensitivity cases,not measured consumption or approved operating limits"},
              "model_limits": "Drawn centerline length/width only; ignores pad shorting,via barrels,R309,connector/contact resistance,ground return,thermal coupling andextra5V peripheral loads. Mixed layer copper weights are not confirmed. Not an upper bound on complete board voltage drop or temperature.",
              "geometry": geometry, "scenarios": cases,
              "design_constraints": {"input_relation": "Iinput=I_J401+I_J402+P_5V/(Vin*efficiency),plus unmodelled input losses",
                                     "each_EH_condition": "3A only under JST AWG22 and specified mating conditions; do not infer motor current from node count",
                                     "not_all_outputs_at_catalog_max_simultaneously": True,
                                     "recommended_copper_intent": "Use>=35um copper on these current-carrying layers for the1oz model; this is a design intent pending fabricator confirmation,not the present as-built stackup"},
              "hardware_measured": False, "whole_board_current_rating_approved": False}
    pipeline.write_json(EVIDENCE / "power-budget-scenarios.json", result)
    example = next(case for case in cases if case["input_v"] == 6.6 and case["assumed_buck_efficiency"] == 0.85 and case["J401_load_a"] == 3 and case["J402_load_a"] == 0)
    print(json.dumps({"geometry": geometry, "example_one_servo_branch": example}, ensure_ascii=False))


if __name__ == "__main__":
    main()
