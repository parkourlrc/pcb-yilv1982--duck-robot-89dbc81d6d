"""验收计量的合成正反例；不训练、不作为策略能力通过记录。"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import torch

from mjlab_duck.locomotion_env import DT, RAD, Z_HOME, curriculum_scenario_segments, trajectory_finished
from mjlab_duck.locomotion_evaluator import ScenarioSpec, development_scenarios, full_reference_scenarios, evaluate_trace


def ideal_trace(scenario: ScenarioSpec, initial_yaw: float = 0.) -> dict[str, torch.Tensor]:
    values = []
    current_vx, current_wz = 0., 0.
    for duration, target_vx, target_wz in scenario.segments:
        for _ in range(round(duration/DT)):
            values.append((current_vx, 0., current_wz))
            speed_step = (.05 if target_vx >= current_vx else .10)*DT
            current_vx += max(-speed_step, min(speed_step, target_vx-current_vx))
            current_wz += max(-30*RAD*DT, min(30*RAD*DT, target_wz-current_wz))
    command = torch.tensor(values, dtype=torch.float64)
    subcommands = command.repeat_interleave(10, 0)
    yaw = initial_yaw+(subcommands[:, 2]*.002).cumsum(0)
    world_velocity = torch.stack((subcommands[:, 0]*yaw.cos(), subcommands[:, 0]*yaw.sin()), -1)
    xy = (world_velocity*.002).cumsum(0)
    physics = torch.zeros(len(subcommands), 12, dtype=torch.float64)
    physics[:, :2] = xy
    physics[:, 2] = torch.atan2(yaw.sin(), yaw.cos())
    physics[:, 3:5] = world_velocity
    physics[:, 6] = Z_HOME
    physics[:, 10] = subcommands[:, 0]
    return {"physics": physics.reshape(len(command), 10, 12), "command": command,
            "time": torch.arange(1, len(command)+1, dtype=torch.float64)*DT,
            "initial_xy": torch.zeros(2, dtype=torch.float64), "initial_yaw": torch.tensor(initial_yaw, dtype=torch.float64)}


def run_checks() -> dict:
    torch.set_num_threads(1)
    straight = development_scenarios(1)[3]
    arc = development_scenarios(2)[9]
    inplace = development_scenarios(2)[13]
    joint = development_scenarios(2)[17]
    stand = development_scenarios(2)[-1]
    checks = {}
    positives = (straight, arc, inplace, joint, stand)
    for scenario in positives:
        report = evaluate_trace(scenario, ideal_trace(scenario, 3.1), completed=True)
        assert report.passed, (scenario.name, {key: value for key, value in report.checks.items() if not value["passed"]})
        checks[f"ideal_{scenario.kind}"] = True
    trace = ideal_trace(arc)
    trace["physics"][:, :, 2] = 0.
    report = evaluate_trace(arc, trace, completed=True)
    assert not report.passed and not report.checks["motion_0/yaw_direction"]["passed"]
    checks["no_rotation_rejected"] = True
    trace = ideal_trace(straight)
    trace["physics"][:, :, :2] = 0.
    report = evaluate_trace(straight, trace, completed=True)
    assert not report.checks["motion_0/forward_progress"]["passed"]
    checks["zero_net_progress_rejected"] = True
    trace = ideal_trace(inplace)
    trace["physics"][200, 3, 0] = .051
    report = evaluate_trace(inplace, trace, completed=True)
    assert not report.checks["motion_0/anchored_drift"]["passed"]
    checks["substep_drift_spike_rejected"] = True
    trace = ideal_trace(joint)
    brake_control = round(36/DT)
    trace["physics"][brake_control, 3, 0] += .08
    report = evaluate_trace(joint, trace, completed=True)
    assert not report.checks["motion_2/braking_path"]["passed"]
    checks["brake_path_not_endpoint"] = True
    trace = ideal_trace(joint)
    trace = {key: value[:1000] if key in {"physics", "command", "time"} else value for key, value in trace.items()}
    report = evaluate_trace(joint, trace, completed=False)
    assert not report.passed and "segment_6" in report.unvisited
    checks["missing_later_segments_rejected"] = True
    trace = ideal_trace(stand)
    trace["physics"][:, ::2, 3] = .02
    trace["physics"][:, 1::2, 3] = -.02
    report = evaluate_trace(stand, trace, completed=True)
    assert not report.checks["motion_0/full_stop_3s"]["passed"]
    checks["oscillating_speed_not_cancelled"] = True
    trace = ideal_trace(straight)
    trace["physics"][100, 5, 1] = .051
    report = evaluate_trace(straight, trace, completed=True)
    assert not report.checks["motion_0/straight_lateral"]["passed"]
    checks["straight_substep_lateral_rejected"] = True
    trace = ideal_trace(straight)
    trace["physics"][100, 5, 9] = 1.
    assert not evaluate_trace(straight, trace, completed=True).passed
    checks["nonfoot_contact_rejected"] = True
    assert len(development_scenarios(1)) == 9 and len(development_scenarios(2)) == 22 and len(full_reference_scenarios()) == 96
    assert [sum(segment[0] for segment in curriculum_scenario_segments(2, family, .06, 15*RAD)) for family in range(5)] == [84., 31., 44., 133., 20.]
    checks["scenario_contract"] = True
    from types import SimpleNamespace
    for duration in (23., 31., 84., 133.):
        command = SimpleNamespace(duration=torch.tensor([duration], dtype=torch.float64), manual=torch.tensor([False]))
        env = SimpleNamespace(locomotion=SimpleNamespace(time=torch.tensor([duration-1e-8], dtype=torch.float64)),
                              command_manager=SimpleNamespace(get_term=lambda name: command))
        assert bool(trajectory_finished(env)[0])
        env.locomotion.time -= DT
        assert not bool(trajectory_finished(env)[0])
    checks["natural_completion_float_boundary"] = True
    return checks


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    files = ["training/mjlab_duck/locomotion_env.py", "training/mjlab_duck/locomotion_evaluator.py", "training/scripts/check_locomotion_evaluator.py"]
    result = {"scope": "synthetic_metric_checks_not_policy_acceptance", "checks": run_checks(),
              "sha256": {name: hashlib.sha256((root/name).read_bytes()).hexdigest() for name in files}}
    text = json.dumps(result, ensure_ascii=False, indent=2)+"\n"
    if arguments.output:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
