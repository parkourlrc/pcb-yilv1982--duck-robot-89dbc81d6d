"""独立真值评估：完整轨迹、物理子步极值和逐项验收。"""
from __future__ import annotations

from dataclasses import dataclass, field
import math
from pathlib import Path
from typing import Any, Callable, Iterable

import torch

from .locomotion_env import DT, RAD, Z_HOME, evaluation_scenarios, scenario_segments


@dataclass(frozen=True)
class ScenarioSpec:
    name: str
    seed: int
    segments: tuple[tuple[float, float, float], ...]
    kind: str = "unknown"


@dataclass
class EpisodeReport:
    name: str
    seed: int
    passed: bool = False
    completed: bool = False
    failed: bool = False
    reason: int | None = None
    observed: dict[str, Any] = field(default_factory=dict)
    checks: dict[str, dict[str, Any]] = field(default_factory=dict)
    unvisited: list[str] = field(default_factory=list)

    def check(self, name: str, ok: bool, observed: Any = None, threshold: Any = None) -> None:
        self.checks[name] = {"passed": bool(ok), "observed": observed, "threshold": threshold}


@dataclass
class SuiteReport:
    stage: str
    episodes: list[EpisodeReport]

    @property
    def passed_count(self) -> int:
        return sum(episode.passed for episode in self.episodes)

    @property
    def total(self) -> int:
        return len(self.episodes)

    @property
    def passed(self) -> bool:
        return bool(self.episodes) and self.passed_count == self.total

    @property
    def straight_passed_count(self) -> int:
        return sum(episode.passed for episode in self.episodes if episode.name.startswith("straight_"))


def development_scenarios(stage: int) -> list[ScenarioSpec]:
    straight = [ScenarioSpec(f"straight_{speed}_{seed}", seed, ((23., speed, 0.),), "straight")
                for speed in (.03, .06, .10) for seed in (101, 102, 103)]
    if stage == 1:
        return straight
    if stage != 2:
        raise ValueError("stage must be 1 or 2")
    arcs = [ScenarioSpec(f"arc_{yaw}", 101, ((23., .06, yaw*RAD), (13., .06, -yaw*RAD), (8., 0., 0.)), "arc")
            for yaw in (-15, 15, -30, 30)]
    turns = [ScenarioSpec(f"inplace_{yaw}", 101, tuple(scenario_segments(0, 0., yaw*RAD)), "inplace")
             for yaw in (-15, 15, -30, 30)]
    joint = [ScenarioSpec(f"joint_{speed}_{yaw}", 101, tuple(scenario_segments(3, speed, yaw*RAD)), "joint")
             for speed in (.03, .10) for yaw in (-30, 30)]
    return straight + arcs + turns + joint + [ScenarioSpec("stand", 101, ((20., 0., 0.),), "stand")]


def full_reference_scenarios() -> list[ScenarioSpec]:
    result = []
    for item in evaluation_scenarios():
        name = item["name"]
        kind = "joint" if name.startswith("sequence_") else "straight_stop" if name.startswith("straight_stop_") else name.split("_")[0]
        result.append(ScenarioSpec(name, item["seed"], tuple(item["segments"]), kind))
    return result


def causal_mean(values: torch.Tensor, width: int = 10) -> torch.Tensor:
    sums = torch.cat((torch.zeros_like(values[:1]), values.cumsum(0)), 0)
    ends = torch.arange(1, len(values)+1)
    starts = (ends-width).clamp_min(0)
    count = (ends-starts).reshape((-1,) + (1,)*(values.ndim-1))
    return (sums[ends]-sums[starts])/count


def _confirmation(mask: torch.Tensor, required: int = 25) -> int | None:
    count = 0
    for index, valid in enumerate(mask.tolist()):
        count = count+1 if valid else 0
        if count >= required:
            return index
    return None


def _rmse(values: torch.Tensor) -> float:
    return float(values.square().mean().sqrt()) if values.numel() else math.inf


def _merged_segments(scenario: ScenarioSpec):
    result = []
    for duration, vx, wz in scenario.segments:
        if result and (vx, wz) == result[-1][1:]:
            result[-1] = (result[-1][0]+duration, vx, wz)
        else:
            result.append((duration, vx, wz))
    return result


def evaluate_trace(scenario: ScenarioSpec, trace: dict[str, torch.Tensor], *, completed: bool,
                   reason: int = 0, failed: bool = False) -> EpisodeReport:
    report = EpisodeReport(scenario.name, scenario.seed, completed=completed, failed=failed, reason=reason)
    known = scenario.kind in {"straight", "straight_stop", "arc", "joint", "inplace", "stand"}
    report.check("known_scenario", known, scenario.kind)
    if not known:
        return report
    required = {"physics", "time", "command", "initial_xy", "initial_yaw"}
    report.check("trace_fields", required <= trace.keys())
    if not required <= trace.keys():
        return report
    samples = trace["physics"].detach().cpu().double()
    times = trace["time"].detach().cpu().double()
    commands = trace["command"].detach().cpu().double()
    initial_xy = trace["initial_xy"].detach().cpu().double()
    initial_yaw = trace["initial_yaw"].detach().cpu().double().reshape(())
    shape_ok = samples.ndim == 3 and tuple(samples.shape[1:]) == (10, 12) and len(samples) == len(times) == len(commands) and commands.shape[-1] == 3
    report.check("trace_shape", shape_ok)
    finite = all(bool(torch.isfinite(trace[key]).all()) for key in required)
    report.check("finite_inputs", finite)
    if not shape_ok or not finite or not len(times):
        report.unvisited.append("trajectory")
        return report
    count = len(times)
    expected_steps = round(sum(segment[0] for segment in scenario.segments)/DT)
    report.check("continuous_clock", bool(torch.allclose(times, torch.arange(1, count+1, dtype=torch.float64)*DT, atol=2e-5, rtol=0)))
    report.check("complete_trajectory", completed and count == expected_steps, count, expected_steps)
    report.check("no_failure", not failed and reason == 0, reason, 0)
    report.check("upright", bool((samples[:, :, 5] < 45*RAD).all()), float(samples[:, :, 5].max()), 45*RAD)
    report.check("height", bool((samples[:, :, 6] >= .6*Z_HOME).all()), float(samples[:, :, 6].min()), .6*Z_HOME)
    report.check("foot_contacts_only", not bool((samples[:, :, 9] != 0).any()))
    physical = samples.reshape(-1, 12)
    positions = torch.cat((initial_xy[None], physical[:, :2]), 0)
    raw_yaw = torch.cat((initial_yaw[None], physical[:, 2]), 0)
    deltas = torch.atan2(torch.sin(raw_yaw[1:]-raw_yaw[:-1]), torch.cos(raw_yaw[1:]-raw_yaw[:-1]))
    unwrapped = torch.cat((initial_yaw[None], initial_yaw+deltas.cumsum(0)), 0)
    path_steps = (positions[1:]-positions[:-1]).norm(dim=-1)
    raw_heading_velocity = samples[:, :, 10:12].mean(1)
    raw_world_velocity = samples[:, :, 3:5].mean(1)
    filtered_velocity = causal_mean(raw_heading_velocity)
    filtered_world = causal_mean(raw_world_velocity)
    filtered_speed = causal_mean(samples[:, :, 3:5].norm(dim=-1).mean(1))
    raw_yaw_rate = deltas.reshape(count, 10).sum(-1)/DT
    filtered_yaw = causal_mean(raw_yaw_rate)
    rp_rms = causal_mean(samples[:, :, 7:9].square().mean(1)).sqrt()
    stable = (filtered_speed <= .01+1e-9) & (samples[:, :, 5].amax(1) <= 15*RAD) & (rp_rms <= 15*RAD).all(-1)
    full_stable = stable & (filtered_yaw.abs() <= 3*RAD+1e-9)
    world_acceleration = torch.diff(filtered_world, dim=0, prepend=torch.zeros_like(filtered_world[:1])).norm(dim=-1)/DT
    yaw_acceleration = torch.diff(filtered_yaw, prepend=torch.zeros_like(filtered_yaw[:1])).abs()/DT
    original_end = 0
    for segment_index, segment in enumerate(scenario.segments):
        original_start = original_end
        original_end += round(segment[0]/DT)
        if count <= original_start:
            report.unvisited.append(f"segment_{segment_index}")
        report.check(f"segment_{segment_index}/complete", count >= original_end, min(max(count-original_start, 0), original_end-original_start), original_end-original_start)
    anchor = initial_xy.clone()
    previous_vx = 0.
    start = 0
    for segment_index, (duration, vx, wz) in enumerate(_merged_segments(scenario)):
        end = start+round(duration/DT)
        prefix = f"motion_{segment_index}"
        actual_end = min(end, count)
        if actual_end <= start:
            start = end
            previous_vx = vx
            continue
        transition_end = min(start+round(3/DT), actual_end)
        transition = slice(start, transition_end)
        report.check(f"{prefix}/horizontal_acceleration", bool((world_acceleration[transition] <= .30+1e-7).all()), float(world_acceleration[transition].max()), .30)
        report.check(f"{prefix}/yaw_acceleration", bool((yaw_acceleration[transition] <= 120*RAD+1e-7).all()), float(yaw_acceleration[transition].max()), 120*RAD)
        speed_error = _rmse(filtered_velocity[transition, 0]-commands[transition, 0])
        yaw_error = _rmse(filtered_yaw[transition]-commands[transition, 2])
        report.check(f"{prefix}/transition_forward_tracking", speed_error <= .03, speed_error, .03)
        report.check(f"{prefix}/transition_yaw_tracking", yaw_error <= 8*RAD, yaw_error, 8*RAD)
        speed_tolerance = max(.005, .2*vx)
        yaw_tolerance = max(RAD, .2*abs(wz))
        response = ((filtered_velocity[:, 0]-vx).abs() <= speed_tolerance) if vx > 0 else stable
        response = response & ((filtered_yaw-wz).abs() <= (yaw_tolerance if wz else 3*RAD))
        confirmation = _confirmation(response[transition])
        report.check(f"{prefix}/response_3s", confirmation is not None, None if confirmation is None else (confirmation+1)*DT, 3.)
        if vx == 0:
            translation_confirm = _confirmation(stable[transition])
            if previous_vx > 0:
                report.check(f"{prefix}/translation_stop_3s", translation_confirm is not None, None if translation_confirm is None else (translation_confirm+1)*DT, 3.)
                brake_end = start+(translation_confirm+1 if translation_confirm is not None else transition_end-start)
                path = float(path_steps[start*10:brake_end*10].sum())
                radial = float((positions[start*10:brake_end*10+1]-positions[start*10]).norm(dim=-1).max())
                report.check(f"{prefix}/braking_path", path <= .15, path, .15)
                report.observed[f"{prefix}/braking_radial_max"] = radial
                if translation_confirm is not None:
                    anchor = positions[brake_end*10].clone()
                    anchor_start = brake_end*10
                else:
                    anchor_start = actual_end*10
            else:
                anchor_start = start*10
            drift = float((positions[anchor_start:actual_end*10+1]-anchor).norm(dim=-1).max())
            report.check(f"{prefix}/anchored_drift", drift <= .05+1e-9, drift, .05)
            if wz == 0:
                stop_confirm = _confirmation(full_stable[transition])
                hold_start = start+(stop_confirm+1 if stop_confirm is not None else actual_end-start)
                hold_steps = actual_end-hold_start
                held = stop_confirm is not None and hold_steps >= round(5/DT) and bool(full_stable[hold_start:actual_end].all())
                report.check(f"{prefix}/full_stop_3s", stop_confirm is not None, None if stop_confirm is None else (stop_confirm+1)*DT, 3.)
                report.check(f"{prefix}/stop_hold_5s", held, hold_steps*DT, 5.)
        steady_start = start+round(3/DT)
        if (vx > 0 or wz != 0) and end > steady_start:
            steady_end = min(end, count)
            steady = slice(steady_start, max(steady_start, steady_end))
            expected_steady = (end-steady_start)*DT
            report.check(f"{prefix}/steady_duration", count >= end, max(steady_end-steady_start, 0)*DT, expected_steady)
            if steady_end > steady_start:
                if vx > 0:
                    rmse = _rmse(filtered_velocity[steady, 0]-vx)
                    ratio = float((filtered_velocity[steady, 0] > 0).double().mean())
                    side = _rmse(filtered_velocity[steady, 1])
                    report.check(f"{prefix}/forward_rmse", rmse <= speed_tolerance, rmse, speed_tolerance)
                    report.check(f"{prefix}/forward_direction", ratio >= .95, ratio, .95)
                    report.check(f"{prefix}/lateral_rmse", side <= .01, side, .01)
                    if wz == 0:
                        start_heading = unwrapped[start*10]
                        forward_axis = torch.stack((start_heading.cos(), start_heading.sin()))
                        net = float(torch.dot(positions[steady_end*10]-positions[steady_start*10], forward_axis))
                    else:
                        net = float(raw_heading_velocity[steady, 0].sum()*DT)
                    report.check(f"{prefix}/forward_progress", net >= vx*expected_steady*.8, net, vx*expected_steady*.8)
                if wz != 0:
                    rmse = _rmse(filtered_yaw[steady]-wz)
                    ratio = float((filtered_yaw[steady]*wz > 0).double().mean())
                    progress = float((unwrapped[steady_end*10]-unwrapped[steady_start*10])*math.copysign(1., wz))
                    report.check(f"{prefix}/yaw_rmse", rmse <= yaw_tolerance, rmse, yaw_tolerance)
                    report.check(f"{prefix}/yaw_direction", ratio >= .95, ratio, .95)
                    report.check(f"{prefix}/yaw_progress", progress >= abs(wz)*expected_steady*.8, progress, abs(wz)*expected_steady*.8)
        if vx > 0 and wz == 0:
            segment_positions = positions[start*10:actual_end*10+1]-positions[start*10]
            start_heading = unwrapped[start*10]
            normal = torch.stack((-start_heading.sin(), start_heading.cos()))
            lateral = float((segment_positions@normal).abs().max())
            heading_error = float((unwrapped[start*10:actual_end*10+1]-start_heading).abs().max())
            report.check(f"{prefix}/straight_lateral", lateral <= .05+1e-9, lateral, .05)
            report.check(f"{prefix}/straight_heading", heading_error <= 10*RAD, heading_error, 10*RAD)
        start = end
        previous_vx = vx
    report.observed.update({"controls": count, "simulation_seconds": float(times[-1]),
                            "max_raw_horizontal_speed": float(physical[:, 3:5].norm(dim=-1).max()),
                            "max_raw_yaw_rate": float(raw_yaw_rate.abs().max()),
                            "maximum_tilt_rad": float(physical[:, 5].max())})
    report.passed = bool(report.checks) and not report.unvisited and all(check["passed"] for check in report.checks.values())
    return report


def evaluate_episode(policy: Callable[[Any], torch.Tensor], scenario: ScenarioSpec,
                     env_factory: Callable[[ScenarioSpec], Any]) -> EpisodeReport:
    env = env_factory(scenario)
    try:
        if env.num_envs != 1 or env.cfg.auto_reset or not env.locomotion.capture_substeps:
            raise ValueError("Evaluation requires one strict native environment, substep capture and auto_reset=False")
        obs, _ = env.reset(seed=scenario.seed)
        command = env.command_manager.get_term("velocity")
        obs = command.set_fixed_schedule(scenario.segments)
        state = env.locomotion
        trace = {"initial_xy": state.xy[0].detach().cpu().clone(), "initial_yaw": state.last_yaw[0].detach().cpu().clone()}
        records = {name: [] for name in ("physics", "time", "command")}
        failed, completed, reason = False, False, 0
        expected_steps = round(sum(segment[0] for segment in scenario.segments)/DT)
        with torch.inference_mode():
            for control in range(expected_steps):
                if not all(bool(torch.isfinite(value).all()) for value in obs.values()):
                    failed, reason = True, 4
                    break
                action = policy(obs)
                if not bool(torch.isfinite(action).all()):
                    failed, reason = True, 4
                    break
                used_command = state.cmd[0].detach().cpu().clone()
                obs, reward, terminated, truncated, _ = env.step(action)
                records["physics"].append(state.physics_trace[0].detach().cpu().clone())
                records["time"].append(state.time[0].detach().cpu().clone())
                records["command"].append(used_command)
                failed = bool(state.failed[0]) or not bool(torch.isfinite(reward).all())
                reason = int(state.reason[0]) if bool(state.failed[0]) else (4 if failed else 0)
                done = bool((terminated | truncated)[0])
                if done or failed:
                    completed = done and not failed and control+1 == expected_steps and bool(truncated[0]) and not bool(terminated[0])
                    if not completed and not failed:
                        failed, reason = True, 10
                    break
        for name, values in records.items():
            shape = (0, 10, 12) if name == "physics" else (0, 3) if name == "command" else (0,)
            trace[name] = torch.stack(values) if values else torch.empty(shape)
        if getattr(env, "evaluation_trace_directory", None):
            destination = Path(env.evaluation_trace_directory)
            destination.mkdir(parents=True, exist_ok=True)
            torch.save({"scenario": {"name": scenario.name, "seed": scenario.seed, "segments": scenario.segments},
                        "trace": trace, "completed": completed, "failed": failed, "reason": reason},
                       destination/f"{scenario.name}-seed{scenario.seed}.pt")
        return evaluate_trace(scenario, trace, completed=completed, failed=failed, reason=reason)
    finally:
        env.close()


def evaluate_suite(policy: Callable[[Any], torch.Tensor], scenarios: Iterable[ScenarioSpec],
                   env_factory: Callable[[ScenarioSpec], Any], stage: str) -> SuiteReport:
    return SuiteReport(stage, [evaluate_episode(policy, scenario, env_factory) for scenario in scenarios])
