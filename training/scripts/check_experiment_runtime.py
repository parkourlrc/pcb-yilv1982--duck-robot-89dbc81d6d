"""固定输入检查奖励配置、旧公式和参数继承，不执行训练更新。"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
import io
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import torch

from mjlab_duck.experiment_config import default_rewards, effective_rewards, parameter_catalog, resolve_config, reward_presets
from mjlab_duck.locomotion_env import MotionState, RAD, Z_HOME
from mjlab_duck.reward_runtime import apply_reward_config
from mjlab_duck.locomotion_logging import RolloutStatistics, merge_summaries


def old_reward(state, actual, previous):
    def track(error, sigma):
        return torch.exp(-(error/sigma)**2)
    velocity, yaw = state.cmd[:, 0], state.cmd[:, 2]
    forward = track(state.vel[:, 0]-velocity, torch.maximum(.25*velocity.abs(), torch.full_like(velocity, .005)))
    turning = track(state.yaw_rate-yaw, torch.maximum(.25*yaw.abs(), torch.full_like(yaw, RAD)))
    turn = yaw.abs() > 1e-6
    stop = (velocity.abs() < 1e-6) & ~turn
    zero_yaw = track(state.yaw_rate, 3*RAD)
    auxiliary = forward*torch.where(turn, turning, zero_yaw)
    posture = track(state.tilt, 20*RAD)*track(state.height-Z_HOME, .03)
    late = ((state.phase == 1) & (state.time-state.brake_start > 3)) | (state.full_active & ~state.full_confirmed & (state.time-state.full_start > 3))
    return torch.stack((3*posture*forward, 3*posture*turn*turning,
                        3*posture*stop*track(state.vel.norm(dim=-1), .01)*zero_yaw,
                        .5*auxiliary*track(state.vel[:, 1], .01), .5*auxiliary*(velocity > 1e-6)*~turn*zero_yaw,
                        auxiliary*(state.phase == 2)*track((state.xy-state.anchor).norm(dim=-1), .03),
                        .5*auxiliary*track(state.tilt, 15*RAD)*track(state.height-Z_HOME, .02),
                        -.05*((actual-previous).square().mean(-1)/.01).clamp_max(1), -.5*late), -1)


def run_checks():
    torch.manual_seed(918)
    state = MotionState(16, "cpu")
    state.cmd[:, 0] = torch.tensor([0., .03, .06, .10]*4)
    state.cmd[:, 2] = torch.tensor([0., 0., .1, -.2]*4)
    state.vel.copy_(torch.randn(16, 2)*.03)
    state.yaw_rate.copy_(torch.randn(16)*.1)
    state.tilt.copy_(torch.rand(16)*.4)
    state.height.copy_(torch.rand(16)*.04+Z_HOME-.02)
    state.xy.copy_(torch.randn(16, 2)*.02)
    state.phase.copy_(torch.arange(16)%3)
    state.time.fill_(5.)
    actual, previous = torch.randn(16, 14)*.1, torch.randn(16, 14)*.1
    original = old_reward(state, actual, previous)
    state.reward(actual, previous)
    difference = float((original-state.reward_terms).abs().max())
    torch.testing.assert_close(state.reward_terms, original, atol=1e-7, rtol=1e-6)
    errors = {}
    for preset, config in reward_presets().items():
        state.reward_config = effective_rewards(config, 1, 25)
        state.gait_air.fill_(.2)
        state.gait_seen.fill_(True)
        state.gait_samples.fill_(10)
        state.gait_clearance_cost.fill_(.04)
        state.gait_landing_cost.fill_(.5)
        state.gait_slip_cost.fill_(.01)
        state.raw_reward_delta.fill_(.2)
        moving = (state.cmd[:, :2].norm(dim=-1)+state.cmd[:, 2].abs() > .01).float()
        expected_feet = torch.tensor([6., -.008, -.125, -.0001])[None, :]*moving[:, None]
        if preset in ("baseline", "rawramp"):
            expected_feet.zero_()
        state.reward(actual, previous)
        torch.testing.assert_close(state.reward_contributions[:, 9:13], expected_feet)
        expected_smooth = -(.2 if "rawramp" in preset else .05)*(
            state.raw_reward_delta.square().sum(-1) if "rawramp" in preset else ((actual-previous).square().mean(-1)/.01).clamp_max(1))
        torch.testing.assert_close(state.reward_terms[:, 7], expected_smooth)
        errors[preset] = float((state.reward_contributions[:, 9:13]-expected_feet).abs().max())
    wrapper = SimpleNamespace(unwrapped=SimpleNamespace(locomotion=state))
    state.gait_air.fill_(.2)
    state.gait_seen.fill_(True)
    apply_reward_config(wrapper, default_rewards(), 1, 0)
    assert not state.gait_seen.any() and not state.gait_air.any()
    apply_reward_config(wrapper, reward_presets()["gait020"], 1, 0)
    assert not state.gait_seen.any()
    state.reward_config["terms"]["failure"]["weight"] = 7.
    state.failed[0] = True
    state.reward(actual, previous)
    assert state.reward_contributions[0, -1] == -7
    invalid = ({"gamma": float("nan")}, {"num_envs": True}, {"learning_rate": 0}, {"Kd": 3},
               {"finite_horizon": 1}, {"reward_config": {"schema": True}},
               {"reward_config": {"terms": {"failure": {"enabled": False}}}},
               {"reward_config": {"schedule": [{"update": 2, "values": {}}, {"update": 1, "values": {}}]}},
               {"stage2": {"stage": 2, "probabilities": [.1]*5}})
    for overrides in invalid:
        try:
            resolve_config(overrides)
        except (ValueError, TypeError):
            pass
        else:
            raise AssertionError(f"invalid configuration accepted: {overrides}")
    left, right = RolloutStatistics("cpu"), RolloutStatistics("cpu")
    for statistics, raw, contribution in ((left, 2., 6.), (right, 4., 12.)):
        statistics.reward_raw_sum[0] = raw
        statistics.reward_weight_sum[0] = 3.
        statistics.reward_contribution_sum[0] = contribution
        statistics.reward_detail_samples = 1
        statistics.count = 1
    merged = merge_summaries([left.summary(), right.summary()])
    assert merged["reward_details"]["forward"]["raw_mean"] == 3.
    assert merged["reward_details"]["forward"]["contribution_mean"] == 9.
    from mjlab_duck.train_locomotion import ConsoleCopy, freeze_startup
    from mjlab_duck.locomotion_train_cfg import LocomotionTrainConfig
    with tempfile.TemporaryDirectory() as temporary:
        folder = Path(temporary)
        freeze_startup(folder, LocomotionTrainConfig(), {"test": "zero_update_startup_snapshot"}, 0)
        snapshot = json.loads((folder/"runtime-environment.json").read_text())
        assert snapshot["dependencies"] and snapshot["source_sha256"] and snapshot["config"]["reward_config"]
        for name in snapshot["source_sha256"]:
            assert (folder/"sources"/name).is_file()
        original, copied = io.StringIO(), io.StringIO()
        stream = ConsoleCopy(original, copied)
        stream.write("startup failure evidence\n")
        stream.flush()
        assert original.getvalue() == copied.getvalue() == "startup failure evidence\n"
    return {"status": "passed", "training_updates": 0, "baseline_max_abs_error": difference,
            "preset_fixed_input_max_errors": errors, "invalid_cases_rejected": len(invalid),
            "catalog_fields": len(parameter_catalog()["fields"]), "foot_history_toggle_reset": True,
            "reward_rank_aggregation": True,
            "startup_source_dependencies_config_and_console": True,
            "rawramp_boundary": "v3 changes at full update boundaries; historical control-step transition may differ by one control step"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run_checks()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")


if __name__ == "__main__":
    main()
