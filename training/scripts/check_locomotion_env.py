"""第③步必要接口/计量检查；不训练，不宣称行为目标通过。"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import torch
from mjlab.envs import ManagerBasedRlEnv
from mjlab_duck.locomotion_cfg import locomotion_env_cfg
from mjlab_duck.locomotion_env import (
    DT, RAD, Z_HOME, JOINT_ORDER, MotionState, FAMILY_PROBABILITIES,
    evaluation_scenarios, scenario_segments, horizontal_velocity, wrap_angle,
)


def synthetic_checks():
    state = MotionState(2, "cpu")
    ids = torch.arange(2)
    state.reset(ids, torch.zeros(2, 2), torch.zeros(2), torch.tensor([[.1, 0, 0], [.1, 0, 0]]))
    state.set_request(torch.tensor([[0., 0, 30*RAD], [0., 0, 0]]))
    def tick(speed=0., yaw_speed=0., xy=None):
        if xy is None: xy = state.xy.clone()
        for _ in range(10):
            state.substep(xy, state.last_yaw+yaw_speed*.002,
                          torch.tensor([[speed, 0., 0.]]).repeat(2, 1),
                          torch.zeros(2), torch.full((2,), Z_HOME), torch.zeros(2, 2), torch.zeros(2, dtype=torch.bool))
        state.finish_control()
    for _ in range(25): tick(yaw_speed=30*RAD)
    assert (state.phase == 2).all(), "nonzero yaw must allow translational stop"
    assert not state.full_confirmed[1], "full stop must wait for yaw"
    anchor = state.anchor.clone()
    state.set_request(torch.tensor([[0., 0, -30*RAD], [0., 0, 0]]))
    for _ in range(130): tick(yaw_speed=30*RAD)
    assert torch.equal(anchor, state.anchor), "direction reversal must not reanchor"
    assert state.strict_full_stop[1] and not state.strict_stop[0]
    for _ in range(155): tick(yaw_speed=30*RAD)
    assert state.failed[1] and state.reason[1] == 7
    untouched = state.time[1].clone()
    state.reset(torch.tensor([0]), torch.zeros(1, 2), torch.zeros(1), torch.zeros(1, 3))
    assert state.time[1] == untouched and state.window_count[0] == 0
    assert torch.allclose(horizontal_velocity(torch.tensor([[0., 1., 0.]]), torch.tensor([torch.pi/2])), torch.tensor([[1., 0.]]), atol=1e-6)
    assert abs(float(wrap_angle(torch.tensor(-358*RAD))) - 2*RAD) < 1e-6
    drift = MotionState(1, "cpu"); drift.reset(torch.tensor([0]), torch.zeros(1, 2), torch.zeros(1), torch.zeros(1, 3))
    for value in (.03, .06, 0.):
        drift.substep(torch.tensor([[value, 0.]]), torch.zeros(1), torch.zeros(1, 3), torch.zeros(1), torch.full((1,), Z_HOME), torch.zeros(1, 2), torch.zeros(1, dtype=torch.bool))
    assert abs(float(drift.max_drift)-.06) < 1e-6 and drift.strict_drift[0] and not drift.failed[0]
    path = MotionState(1, "cpu", strict=True)
    path.reset(torch.tensor([0]), torch.zeros(1, 2), torch.zeros(1), torch.tensor([[.1, 0., 0.]]))
    path.set_request(torch.zeros(1, 3))
    for value in (.1, 0.):
        path.substep(torch.tensor([[value, 0.]]), torch.zeros(1), torch.zeros(1, 3), torch.zeros(1), torch.full((1,), Z_HOME), torch.zeros(1, 2), torch.zeros(1, dtype=torch.bool))
    assert abs(float(path.brake_path)-.2) < 1e-6 and path.strict_path[0] and path.reason[0] == 9
    holding = MotionState(2, "cpu")
    holding.reset(torch.arange(2), torch.zeros(2, 2), torch.zeros(2), torch.zeros(2, 3))
    original_anchor = holding.anchor.clone()
    def hold_tick(violate=False):
        for _ in range(10):
            yaw_rates = torch.tensor([0., 30*RAD if violate else 0.])
            holding.substep(holding.xy.clone(), holding.last_yaw+yaw_rates*.002,
                            torch.zeros(2, 3), torch.zeros(2), torch.full((2,), Z_HOME),
                            torch.zeros(2, 2), torch.zeros(2, dtype=torch.bool))
        holding.finish_control()
    for _ in range(25): hold_tick()
    assert holding.full_confirmed.all() and not holding.hold_complete.any()
    for _ in range(50): hold_tick()
    for _ in range(2): hold_tick(violate=True)
    for _ in range(250): hold_tick()
    assert holding.hold_complete[0] and not holding.strict_hold[0]
    assert holding.strict_hold[1] and not holding.hold_complete[1]
    assert holding.full_confirmed[1] and torch.equal(original_anchor, holding.anchor)
    cases = evaluation_scenarios()
    assert len(cases) == 96 and len({(cos_yaw["name"], cos_yaw["seed"]) for cos_yaw in cases}) == 96
    assert sum(FAMILY_PROBABILITIES) == 1 and max(sum(value[0] for value in cos_yaw["segments"]) for cos_yaw in cases) == 133
    assert all(sum(value[0] for value in scenario_segments(family_id, .1, 30*RAD)) < 150 for family_id in range(5))
    return {"anchor_reversal": True, "turning_translation_stop": True,
            "full_stop_timeout": True, "partial_reset": True, "substep_maximum": True,
            "path_not_endpoint": True, "full_stop_hold_success": True,
            "full_stop_hold_failure_latched": True,
            "velocity_heading": True, "heading_wrap": True, "scenario_count": len(cases),
            "max_scenario_s": 133}


def runtime_checks():
    env = ManagerBasedRlEnv(locomotion_env_cfg(2, evaluation=True), device="cuda:0")
    try:
        obs, _ = env.reset(seed=0)
        assert obs["actor"].shape == (2, 61) and obs["critic"].shape == (2, 61)
        assert env.action_manager.total_action_dim == 14
        assert torch.allclose(env.scene["robot"].data.root_link_pos_w[:, 2], torch.full((2,), Z_HOME, device=env.device), atol=1e-6)
        assert obs["actor"][:, 6:20].abs().max() <= .005001
        assert env.sim.mj_model.opt.integrator == 3
        assert torch.count_nonzero(obs["actor"][:, 49]) == 0
        assert torch.count_nonzero(obs["actor"][:, 51:]) == 0
        action = env.action_manager.get_term("joints")
        assert tuple(env.scene["robot"].joint_names[index] for index in action.ids.tolist()) == JOINT_ORDER
        actions = torch.full((2, 14), .002, device=env.device)
        steps = 0; done_seen = False
        for _ in range(5):
            obs, reward, terminated, truncated, _ = env.step(actions)
            steps += 1
            assert torch.isfinite(obs["actor"]).all() and torch.isfinite(reward).all()
            assert torch.allclose(obs["actor"][:, 34:48], actions)
            assert torch.allclose(reward, env.locomotion.reward_rate*DT-100*terminated.float(), atol=1e-5)
            if (terminated | truncated).any():
                done_seen = True; break
        env.reset(seed=1)
        command = env.command_manager.get_term("velocity")
        command.set_manual_request(torch.tensor([[.1, 0., 0.], [.1, 0., 0.]], device=env.device))
        env.step(actions)
        assert env.locomotion.time[1] > 0 and env.locomotion.window_count[1] > 0
        assert action.raw[1].abs().sum() > 0 and action.actual[1].abs().sum() > 0 and env.locomotion.cmd[1].abs().sum() > 0
        snapshot = {name: getattr(env.locomotion, name)[1].clone() for name in ("time", "window", "window_count", "cmd")}
        action_snapshot = {name: getattr(action, name)[1].clone() for name in ("raw", "actual", "previous")}
        env.reset(env_ids=torch.tensor([0], device=env.device))
        assert all(torch.equal(getattr(env.locomotion, name)[1], value) for name, value in snapshot.items())
        assert all(torch.equal(getattr(action, name)[1], value) for name, value in action_snapshot.items())
        action.process_actions(torch.full((2, 14), 3., device=env.device))
        limits = env.scene["robot"].data.joint_pos_limits[:, action.ids]
        assert (action.target <= limits[..., 1]).all() and (action.target >= limits[..., 0]).all()
        assert (action.raw == 3).all()
        env.reset(seed=1)
        invalid = torch.zeros(2, 14, device=env.device); invalid[0, 0] = float("nan")
        _, reward, terminated, _, _ = env.step(invalid)
        assert terminated[0] and env.locomotion.reason[0] == 4 and torch.isfinite(reward).all()
        assert not env.locomotion.failed[1], "invalid one environment must not contaminate other"
        env.reset(seed=2)
        command.set_manual_request(torch.tensor([[.1, 0., 0.], [.1, 0., 0.]], device=env.device))
        env.step(actions)
        env.cfg.auto_reset = True
        before_time = env.locomotion.time[1].clone()
        invalid.copy_(actions); invalid[0, 0] = float("nan")
        obs, reward, terminated, _, extras = env.step(invalid)
        assert terminated[0] and not terminated[1] and extras["locomotion"]["reason"][0] == 4
        assert env.locomotion.time[0] == 0 and env.locomotion.window_count[0] == 0
        assert torch.count_nonzero(action.raw[0]) == 0 and torch.count_nonzero(action.actual[0]) == 0
        assert torch.count_nonzero(obs["actor"][0, 34:51]) == 0
        assert env.locomotion.time[1] > before_time and env.locomotion.window_count[1] == 2
        assert torch.equal(action.raw[1], actions[1]) and env.locomotion.cmd[1, 0] > 0
        return {"device": env.device, "observation_dim": 61, "action_dim": 14,
                "control_steps": steps, "physics_substeps": steps*10,
                "finite": True, "raw_action_history": True, "limits": True,
                "invalid_isolation": True, "reward_dt_once": True,
                "partial_reset_nonzero_state": True, "auto_reset_terminal_snapshot": True,
                "early_termination": done_seen, "behavior_acceptance": "not_run"}
    finally:
        env.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--synthetic-only", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    files = ("training/mjlab_duck/locomotion_env.py", "training/mjlab_duck/locomotion_cfg.py", "training/scripts/check_locomotion_env.py", "training/models/duck_v0.xml", "training/params/home_pose.json")
    result = {"stage": 3, "scope": "environment_contract_not_policy_acceptance",
              "utc_time": datetime.now(timezone.utc).isoformat(), "command": sys.argv,
              "python": sys.version, "versions": {name: importlib.metadata.version(name) for name in ("torch", "mujoco", "mjlab")},
              "sha256": {name: hashlib.sha256((root/name).read_bytes()).hexdigest() for name in files},
              "synthetic": synthetic_checks()}
    if not args.synthetic_only:
        result["runtime"] = runtime_checks()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__": main()
