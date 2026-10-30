#!/usr/bin/env python3
"""Behavior-level checks for the Custom HAT Rev A.

This module intentionally does not claim to be a SPICE simulator.  It evaluates
the equations used to select/check the power feedback network and the TTL
half-duplex RC edge budget.  All assumptions are emitted in the JSON/Markdown
reports so that measured values can replace them later.
"""

from __future__ import annotations

import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def sweep_power() -> dict:
    """Check a 5 V buck feedback divider and conservative power budget."""
    # AP64501-style 0.8 V feedback is a model assumption until the selected
    # regulator and datasheet revision are frozen.
    vref = 0.8
    r_top = 52_300.0
    r_bottom = 10_000.0
    vout_nom = vref * (1.0 + r_top / r_bottom)
    vref_tolerance = 0.02
    resistor_tolerance = 0.01
    vout_min = (vref * (1.0 - vref_tolerance)) * (
        1.0 + r_top * (1.0 - resistor_tolerance) / (r_bottom * (1.0 + resistor_tolerance))
    )
    vout_max = (vref * (1.0 + vref_tolerance)) * (
        1.0 + r_top * (1.0 + resistor_tolerance) / (r_bottom * (1.0 - resistor_tolerance))
    )

    # Conservative planning loads, not measured currents.
    loads = {
        "+5V_screen": 0.35,
        "+5V_misc": 0.15,
        "+3V3_hat": 0.45,
        "+1V8_codec": 0.12,
    }
    input_voltage_min = 6.0
    efficiency_assumed = 0.85
    input_power = sum(loads.values()) * 5.0 / efficiency_assumed
    input_current = input_power / input_voltage_min
    input_limit_assumed = 2.0
    output_ok = 4.75 <= vout_min <= 5.25 and 4.75 <= vout_max <= 5.25
    current_ok = input_current <= input_limit_assumed
    return {
        "model": "buck_feedback_and_budget_behavior_model",
        "status": "UNVALIDATED",
        "assumed_criteria_met": output_ok and current_ok,
        "assumptions": {
            "regulator_vref_V": vref,
            "regulator_vref_tolerance": vref_tolerance,
            "resistor_tolerance": resistor_tolerance,
            "efficiency": efficiency_assumed,
            "input_voltage_min_V": input_voltage_min,
            "input_current_limit_A": input_limit_assumed,
            "loads_A": loads,
            "note": "Replace with selected regulator datasheet limits and measured load currents.",
        },
        "feedback": {
            "Rtop_ohm": r_top,
            "Rbottom_ohm": r_bottom,
            "Vout_nominal_V": round(vout_nom, 4),
            "Vout_min_corner_V": round(vout_min, 4),
            "Vout_max_corner_V": round(vout_max, 4),
            "target_window_V": [4.75, 5.25],
        },
        "budget": {
            "total_output_current_A": round(sum(loads.values()), 4),
            "estimated_input_power_W": round(input_power, 4),
            "estimated_input_current_A": round(input_current, 4),
            "input_limit_A": input_limit_assumed,
        },
    }


def sweep_ttl() -> dict:
    """Sweep series resistor and capacitive load for a 3.3 V TTL bus.

    The edge metric is the first-order 10--90% rise/fall time: 2.2*R*C.
    The model treats the driver as an ideal Thevenin source and therefore does
    not model a particular transceiver's output resistance or threshold.
    """
    vcc = 3.3
    resistors = [0.0, 22.0, 33.0, 47.0, 68.0, 100.0]
    loads_pf = [20.0, 50.0, 100.0, 200.0, 400.0]
    max_edge_ns = 250.0
    min_high_v = 2.31  # 0.7*VCC planning threshold, assumption
    rows = []
    for resistance in resistors:
        for load_pf in loads_pf:
            # Add 10 ohm assumed driver output resistance for a finite source.
            tau = (resistance + 10.0) * load_pf * 1e-12
            edge_ns = 2.2 * tau * 1e9
            # At 10-90%, the high endpoint is 0.9*VCC; include a simple DC
            # divider check against 1 Mohm receiver leakage.
            high_v = vcc * 1_000_000.0 / (resistance + 1_000_000.0)
            rows.append(
                {
                    "series_resistor_ohm": resistance,
                    "load_capacitance_pF": load_pf,
                    "rise_fall_10_90_ns": round(edge_ns, 3),
                    "steady_high_V": round(high_v, 4),
                    "pass": edge_ns <= max_edge_ns and high_v >= min_high_v,
                }
            )
    passing = [row for row in rows if row["pass"]]
    return {
        "model": "ttl_half_duplex_rc_behavior_model",
        "status": "UNVALIDATED",
        "assumed_criteria_met": len(passing) == len(rows),
        "assumptions": {
            "logic_supply_V": vcc,
            "driver_output_resistance_ohm": 10.0,
            "receiver_leakage_ohm": 1_000_000.0,
            "max_rise_fall_ns": max_edge_ns,
            "min_steady_high_V": min_high_v,
            "note": "No transceiver IBIS/SPICE model, cable impedance, overshoot, or contention is modeled.",
        },
        "sweep": rows,
        "summary": {
            "cases": len(rows),
            "passing_cases": len(passing),
        },
    }


def write_reports(power: dict, ttl: dict) -> None:
    out_json = ROOT / "simulation_report.json"
    out_md = ROOT / "simulation_report.md"
    report = {"tool": "run_simulations.py", "power": power, "ttl": ttl}
    out_json.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    ttl_pass = ttl["summary"]["passing_cases"]
    ttl_cases = ttl["summary"]["cases"]
    md = f"""# Rev A 行为级仿真报告

生成脚本：`run_simulations.py`

## 结论

- 电源反馈分压与假设负载计算：**{power['status']}**。负载表漏计 Radxa，不能用于整板预算。
- TTL RC 参数扫描：**{ttl['status']}**（{ttl_pass}/{ttl_cases} 个点满足自设阈值，非真实总线验收）。
- 这些结果是方程计算，不是 KiCad/ngspice 或实物测量；不可替代器件数据手册、示波器和首板测试。

## 电源

- 反馈电阻：`Rtop={power['feedback']['Rtop_ohm']:.0f} Ω`，`Rbottom={power['feedback']['Rbottom_ohm']:.0f} Ω`。
- 标称输出：`{power['feedback']['Vout_nominal_V']:.4f} V`。
- 角落范围：`{power['feedback']['Vout_min_corner_V']:.4f}..{power['feedback']['Vout_max_corner_V']:.4f} V`。
- 估算总输出电流：`{power['budget']['total_output_current_A']:.3f} A`；最低输入电压下估算输入电流：`{power['budget']['estimated_input_current_A']:.3f} A`。

## TTL

- 使用一阶模型 `t10-90 = 2.2 × (Rseries + Rdriver) × Cload`。
- 扫描串阻：`{', '.join(str(x) for x in [0, 22, 33, 47, 68, 100])} Ω`；负载：`20..400 pF`。
- 撤回原 `33 Ω` 推荐：当前参数没有实际驱动器、接收器和线缆依据，不能据此选型。

## 模型边界

- 电源没有建模电感、补偿网络、开关节点、环路稳定性、启动过冲、热和 PCB 寄生参数。
- TTL 没有建模具体收发器 IBIS/SPICE、3P 舵机线缆阻抗、连接器反射、方向切换时序或总线争用。
- CSI、SPI 屏、BMI088、音频 Codec、Linux 驱动无法由本脚本证明功能。

完整输入假设及每个扫描点见 `simulation_report.json`。
"""
    out_md.write_text(md, encoding="utf-8")


if __name__ == "__main__":
    power_result = sweep_power()
    ttl_result = sweep_ttl()
    write_reports(power_result, ttl_result)
    print(json.dumps({"power": power_result["status"], "ttl": ttl_result["status"]}, ensure_ascii=False))

