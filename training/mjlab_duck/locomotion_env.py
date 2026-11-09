"""自建联合行走环境组件；仅仿真，不加载上游策略。"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

import torch
from mjlab.managers.action_manager import ActionTerm, ActionTermCfg
from mjlab.managers.command_manager import CommandTerm, CommandTermCfg

from .reward_runtime import initialize_reward_state, reward_components, sample_feet

ROOT = Path(__file__).resolve().parents[1]
HOME = json.loads((ROOT / "params/home_pose.json").read_text(encoding="utf-8"))["joint_pos"]
JOINT_ORDER = (
    "left_hip_yaw", "left_hip_roll", "left_hip_pitch", "left_knee", "left_ankle",
    "neck_pitch", "head_pitch", "head_yaw", "head_roll",
    "right_hip_yaw", "right_hip_roll", "right_hip_pitch", "right_knee", "right_ankle",
)
Z_HOME = 0.1182
DT = 0.02
RAD = math.pi / 180
FAMILY_PROBABILITIES = (0.25, 0.20, 0.25, 0.25, 0.05)
STAGE_PROBABILITIES = {1: (0.0, 1.0, 0.0, 0.0, 0.0), 2: (0.20, 0.30, 0.30, 0.15, 0.05)}


def wrap_angle(action):
    return torch.atan2(torch.sin(action), torch.cos(action))


def heading(root_state):
    quat_w, value, quat_y, quat_z = root_state.unbind(-1)
    return torch.atan2(2 * (quat_w*quat_z + value*quat_y), 1 - 2 * (quat_y*quat_y + quat_z*quat_z))


def horizontal_velocity(velocity, yaw):
    cos_yaw, sin_yaw = yaw.cos(), yaw.sin()
    return torch.stack((cos_yaw*velocity[:, 0] + sin_yaw*velocity[:, 1], -sin_yaw*velocity[:, 0] + cos_yaw*velocity[:, 1]), -1)


def scenario_segments(family: int, vx: float, wz: float):
    """(duration, vx request, wz request); stage changes never reset physics."""
    if family == 0:
        return [(63., 0., wz), (13., 0., -wz), (8., 0., 0.)]
    if family == 1:
        return [(23., vx, 0.), (8., 0., 0.)]
    if family == 2:
        return [(23., vx, wz), (13., vx, -wz), (3., 0., -wz), (60., 0., -wz), (8., 0., 0.)]
    if family == 3:
        return [(23., vx, 0.), (13., vx, wz), (3., 0., wz), (60., 0., wz),
                (13., vx, wz), (13., vx, -wz), (8., 0., 0.)]
    if family == 4:
        return [(20., 0., 0.)]
    raise ValueError(f"Unknown trajectory family {family}")


def curriculum_scenario_segments(stage: int, family: int, vx: float, wz: float):
    """Versioned training schedules; legacy ``scenario_segments`` stays unchanged."""
    if stage == 1:
        if family != 1:
            raise ValueError("stage 1 only samples forward trajectories")
        return [(23.0, vx, 0.0)]
    if stage != 2:
        raise ValueError("stage must be 1 or 2")
    if family == 0:
        return [(63.0, 0.0, wz), (13.0, 0.0, -wz), (8.0, 0.0, 0.0)]
    if family == 1:
        return [(23.0, vx, 0.0), (8.0, 0.0, 0.0)]
    if family == 2:
        return [(23.0, vx, wz), (13.0, vx, -wz), (8.0, 0.0, 0.0)]
    if family == 3:
        return scenario_segments(3, vx, wz)
    if family == 4:
        return [(20.0, 0.0, 0.0)]
    raise ValueError(f"Unknown curriculum family {family}")


def evaluation_scenarios():
    """96 deterministic scenarios, distinct from randomly sampled training."""
    cases = []
    for seed in (0, 1, 2):
        for speed in (-30, -15, -5, 5, 15, 30):
            cases.append(dict(name=f"inplace_{speed}", seed=seed, segments=[(63., 0., speed*RAD)]))
        cases.append(dict(name="stand", seed=seed, segments=[(60., 0., 0.)]))
        cases.append(dict(name="inplace_reverse_stop", seed=seed, segments=scenario_segments(0, 0, 30*RAD)))
        for vx in (.03, .06, .10):
            cases.append(dict(name=f"straight_{vx}", seed=seed, segments=[(23., vx, 0.)]))
            cases.append(dict(name=f"straight_stop_{vx}", seed=seed, segments=scenario_segments(1, vx, 0)))
            for yaw in (-30, -15, 15, 30):
                cases.append(dict(name=f"arc_{vx}_{yaw}", seed=seed, segments=[(23., vx, yaw*RAD)]))
            for yaw in (-30, 30):
                cases.append(dict(name=f"sequence_{vx}_{yaw}", seed=seed, segments=scenario_segments(3, vx, yaw*RAD)))
    return cases


class MotionState:
    """Batched state machine; can also consume synthetic signals for verification."""
    def __init__(self, count_envs, device, strict=False):
        self.count_envs, self.device, self.strict = count_envs, device, strict
        def zeros(*shape, dtype=torch.float32):
            return torch.zeros(count_envs, *shape, device=device, dtype=dtype)
        self.time = zeros(dtype=torch.float64); self.request = zeros(3); self.cmd = zeros(3)
        self.phase = zeros(dtype=torch.long)
        self.xy = zeros(2); self.anchor = zeros(2); self.last_xy = zeros(2)
        self.brake_start = zeros(dtype=torch.float64); self.brake_path = zeros(); self.max_drift = zeros()
        self.anchor_time = zeros(dtype=torch.float64); self.stable_duration = zeros()
        self.full_active = zeros(dtype=torch.bool); self.full_start = zeros(dtype=torch.float64)
        self.full_duration = zeros(); self.full_confirmed = zeros(dtype=torch.bool)
        self.hold_elapsed = zeros(); self.hold_complete = zeros(dtype=torch.bool)
        self.strict_drift = zeros(dtype=torch.bool); self.strict_stop = zeros(dtype=torch.bool); self.strict_path = zeros(dtype=torch.bool)
        self.strict_full_stop = zeros(dtype=torch.bool); self.strict_hold = zeros(dtype=torch.bool)
        self.failed = zeros(dtype=torch.bool); self.reason = zeros(dtype=torch.long)
        self.window = zeros(10, 6); self.window_count = zeros(dtype=torch.long)
        self.last_yaw = zeros(); self.yaw_sum = zeros(); self.vel_sum = zeros(2); self.speed_sum = zeros()
        self.substeps = zeros(dtype=torch.long); self.vel = zeros(2); self.yaw_rate = zeros()
        self.tilt = zeros(); self.height = zeros(); self.rp = zeros(2)
        self.filtered = zeros(6); self.max_tilt = zeros(); self.min_height = zeros()
        self.reward_terms = zeros(9); self.reward_rate = zeros()
        self.capture_substeps = strict
        self.physics_trace = zeros(10, 12)
        self.rp_square_sum = zeros(2)
        initialize_reward_state(self)

    def reset(self, ids, xy, yaw, request):

        for value in vars(self).values():
            if isinstance(value, torch.Tensor) and value.ndim and value.shape[0] == self.count_envs:
                value[ids] = 0
        self.xy[ids] = xy; self.last_xy[ids] = xy; self.anchor[ids] = xy
        self.last_yaw[ids] = yaw; self.height[ids] = Z_HOME; self.min_height[ids] = Z_HOME
        self.phase[ids] = 2
        self.set_request(request, ids)

    def set_request(self, request, ids=None):
        if ids is None:
            ids = torch.arange(self.count_envs, device=self.device)
        if not torch.isfinite(request).all() or (request[:, 0] < 0).any() or (request[:, 0] > .100001).any() or (request[:, 1].abs() > 1e-6).any() or (request[:, 2].abs() > 30*RAD+1e-6).any():
            raise ValueError("Command outside [0,.10] x {0} x [-30,30] deg/s")
        moving = request[:, 0] > 1e-6
        braking = ~moving & (self.phase[ids] == 0)
        braking_ids = ids[braking]
        self.phase[braking_ids] = 1; self.brake_start[braking_ids] = self.time[braking_ids]
        self.brake_path[braking_ids] = 0; self.stable_duration[braking_ids] = 0
        self.phase[ids[moving]] = 0
        full = (request.abs() < 1e-6).all(-1)
        new = ids[full & ~self.full_active[ids]]
        self.full_start[new] = self.time[new]; self.full_duration[new] = 0
        self.full_confirmed[new] = False; self.hold_elapsed[new] = 0
        self.hold_complete[new] = False
        self.full_active[ids] = full
        self.request[ids] = request

    def slew(self, dt, ids):
        delta = self.request[ids] - self.cmd[ids]
        xlimit = torch.where(delta[:, 0] >= 0, .05, .10) * dt
        self.cmd[ids, 0] += torch.maximum(torch.minimum(delta[:, 0], xlimit), -xlimit)
        self.cmd[ids, 2] += delta[:, 2].clamp(-30*RAD*dt, 30*RAD*dt)

    def fail(self, mask, code):
        first = mask & ~self.failed
        self.reason[first] = code
        self.failed |= mask

    def substep(self, xy, yaw, velocity_w, tilt, height, rp, bad_contact, dt=.002):
        finite = torch.isfinite(torch.cat((xy, yaw[:, None], velocity_w, tilt[:, None], height[:, None], rp), -1)).all(-1)
        self.fail(~finite, 4)
        xy, yaw, velocity_w, tilt, height, rp = [torch.nan_to_num(velocity) for velocity in (xy, yaw, velocity_w, tilt, height, rp)]
        distance = (xy-self.last_xy).norm(dim=-1)
        self.brake_path += distance * (self.phase == 1)
        self.strict_path |= (self.phase == 1) & (self.brake_path > .15)
        if self.strict:
            self.fail(self.strict_path, 9)
        self.xy.copy_(xy); self.last_xy.copy_(xy)
        drift = (xy-self.anchor).norm(dim=-1)
        anchored = self.phase == 2
        self.max_drift = torch.maximum(self.max_drift, torch.where(anchored, drift, 0.))
        self.strict_drift |= anchored & (drift > .05)
        self.fail(anchored & (drift > (.05 if self.strict else .20)), 5)
        self.fail(tilt >= 45*RAD, 1); self.fail(height < .6*Z_HOME, 2)
        self.fail(bad_contact, 3)
        self.max_tilt = torch.maximum(self.max_tilt, tilt)
        self.min_height = torch.minimum(self.min_height, height)
        self.vel_sum += horizontal_velocity(velocity_w, yaw)
        self.speed_sum += velocity_w[:, :2].norm(dim=-1)
        self.rp_square_sum += rp.square()
        if self.capture_substeps:
            sample = torch.cat((xy, yaw[:, None], velocity_w[:, :2], tilt[:, None], height[:, None],
                                rp, bad_contact[:, None].float(), horizontal_velocity(velocity_w, yaw)), -1)
            self.physics_trace[torch.arange(self.count_envs, device=self.device), self.substeps.clamp_max(9)] = sample
        self.yaw_sum += wrap_angle(yaw-self.last_yaw) / dt
        self.last_yaw.copy_(yaw); self.substeps += 1
        self.tilt.copy_(tilt); self.height.copy_(height); self.rp.copy_(rp)
        self.time += dt

    def finish_control(self):
        count = self.substeps.clamp_min(1)
        self.vel = self.vel_sum / count[:, None]; self.yaw_rate = self.yaw_sum / count

        values = torch.cat((self.vel, (self.speed_sum/count)[:, None], self.yaw_rate[:, None], self.rp_square_sum/count[:, None]), -1)
        self.window = torch.roll(self.window, 1, dims=1); self.window[:, 0] = values
        self.window_count = (self.window_count+1).clamp_max(10)
        mask = torch.arange(10, device=self.device)[None, :] < self.window_count[:, None]
        self.filtered = (self.window*mask[:, :, None]).sum(1) / self.window_count[:, None]
        stable = (self.filtered[:, 2] <= .01) & (self.tilt <= 15*RAD) & (self.filtered[:, 4:].sqrt() <= 15*RAD).all(-1) & ~self.failed
        self.stable_duration = torch.where(stable, self.stable_duration+DT, 0.)
        braking = self.phase == 1
        ready = braking & (self.stable_duration >= .5-1e-6)
        elapsed = self.time-self.brake_start
        self.strict_stop |= braking & (elapsed >= 3-1e-4) & (~ready | (elapsed > 3+1e-4))
        self.fail(braking & ~ready & (elapsed >= (3 if self.strict else 6)-1e-4), 6)
        self.anchor[ready] = self.xy[ready]; self.anchor_time[ready] = self.time[ready]
        self.phase[ready] = 2
        full_ok = stable & (self.filtered[:, 3].abs() <= 3*RAD)
        waiting = self.full_active & ~self.full_confirmed
        self.full_duration = torch.where(waiting & full_ok, self.full_duration+DT, 0.)
        confirmed = waiting & (self.full_duration >= .5-1e-6)
        full_elapsed = self.time-self.full_start
        self.strict_full_stop |= waiting & (full_elapsed >= 3-1e-4) & (~confirmed | (full_elapsed > 3+1e-4))
        self.fail(waiting & ~confirmed & (full_elapsed >= (3 if self.strict else 6)-1e-4), 7)
        holding = self.full_active & self.full_confirmed
        self.strict_hold |= holding & ~full_ok
        if self.strict:
            self.fail(holding & ~full_ok, 8)
        self.hold_elapsed += holding * DT
        self.hold_complete |= holding & (self.hold_elapsed >= 5-1e-4) & ~self.strict_hold
        self.full_confirmed |= confirmed
        self.vel_sum.zero_(); self.speed_sum.zero_(); self.yaw_sum.zero_(); self.substeps.zero_()
        self.rp_square_sum.zero_()

    def reward(self, actual, previous):
        return reward_components(self, actual, previous, Z_HOME)


class LocomotionCommand(CommandTerm):
    def __init__(self, cfg, env):
        super().__init__(cfg, env)
        self.state = MotionState(self.num_envs, self.device, cfg.strict)
        env.locomotion = self.state
        self.family = torch.zeros(self.num_envs, dtype=torch.long, device=self.device)
        self.schedule = torch.zeros(self.num_envs, 7, 3, device=self.device)
        self.ends = torch.full((self.num_envs, 7), float("inf"), device=self.device)
        self.duration = torch.zeros(self.num_envs, device=self.device)
        self.just_reset = torch.ones(self.num_envs, dtype=torch.bool, device=self.device)
        self.manual = torch.zeros_like(self.just_reset)
        self.stage = int(getattr(cfg, "stage", 0))
        self.probabilities = tuple(getattr(cfg, "probabilities", FAMILY_PROBABILITIES))
        if self.stage not in (0, 1, 2) or len(self.probabilities) != 5 or any(value < 0 or not math.isfinite(value) for value in self.probabilities) or abs(sum(self.probabilities)-1) > 1e-6:
            raise ValueError("Invalid curriculum stage or family probabilities")
        if self.stage == 1 and self.probabilities != STAGE_PROBABILITIES[1]:
            raise ValueError("Curriculum probabilities differ from the confirmed stage")

    @property
    def command(self):
        return self.state.cmd

    def _resample_command(self, ids):
        self.family[ids] = torch.multinomial(torch.tensor(self.probabilities, device=self.device), len(ids), replacement=True)

        for index in ids.tolist():
            family = int(self.family[index])
            vx = float(torch.tensor((.03, .06, .10), device=self.device)[torch.randint(3, (), device=self.device)]) if torch.rand((), device=self.device) < .5 else float(torch.empty((), device=self.device).uniform_(.03 if self.stage else .01, .10))
            sign = -1 if torch.rand((), device=self.device) < .5 else 1
            if self.stage == 2 and family == 0:
                amplitude = (float(torch.tensor((5., 15., 30.), device=self.device)[torch.randint(3, (), device=self.device)])
                             if torch.rand((), device=self.device) < .5 else float(torch.empty((), device=self.device).uniform_(5, 30)))
            elif self.stage == 2 and family in (2, 3):
                amplitude = (float(torch.tensor((15., 30.), device=self.device)[torch.randint(2, (), device=self.device)])
                             if torch.rand((), device=self.device) < .5 else float(torch.empty((), device=self.device).uniform_(5, 30)))
            else:
                amplitude = float(torch.tensor((5., 15., 30.), device=self.device)[torch.randint(3, (), device=self.device)]) if family == 0 and torch.rand((), device=self.device) < .5 else (float(torch.empty((), device=self.device).uniform_(5, 30)) if family == 0 else float(torch.tensor((15., 30.), device=self.device)[torch.randint(2, (), device=self.device)]))
            if self.stage in (1, 2):
                segments = curriculum_scenario_segments(self.stage, family, vx, sign*amplitude*RAD)
            else:
                segments = scenario_segments(family, vx, sign*amplitude*RAD)
            self.set_schedule(index, segments)

    def set_fixed_schedule(self, segments, ids=None):
        """Install deterministic evaluation schedules without changing default sampling."""
        if ids is None:
            ids = torch.arange(self.num_envs, device=self.device)
        for index in ids.tolist():
            self.manual[index] = False
            self.set_schedule(index, segments)
        robot = self._env.scene["robot"]
        root_state = self._env.sim.data.qpos[:, robot.indexing.free_joint_q_adr].reshape(self.num_envs, 7)
        requests = self.schedule[ids, 0]
        self.state.reset(ids, root_state[ids, :2], heading(root_state[ids, 3:7]), requests)
        self.just_reset[ids] = False
        self._env.obs_buf = self._env.observation_manager.compute(update_history=False)
        return self._env.obs_buf

    def set_schedule(self, index, segments):
        if not 1 <= len(segments) <= 7 or any(not math.isfinite(value) for segment in segments for value in segment):
            raise ValueError("A finite schedule must contain 1 to 7 segments")
        if any(duration <= 0 or not 0 <= vx <= .1+1e-6 or abs(wz) > 30*RAD+1e-7 for duration, vx, wz in segments):
            raise ValueError("Invalid schedule duration or command")
        self.ends[index] = float("inf"); self.schedule[index] = 0
        total = 0.
        for stage_index, (duration, vx, wz) in enumerate(segments):
            total += duration; self.ends[index, stage_index] = total
            self.schedule[index, stage_index] = torch.tensor((min(vx, .1), 0., max(-30*RAD, min(wz, 30*RAD))), device=self.device)
        self.duration[index] = total
        self.schedule[index, len(segments):] = self.schedule[index, len(segments)-1]

    def reset(self, env_ids):
        self._resample_command(env_ids)
        self.manual[env_ids] = False
        robot = self._env.scene["robot"]
        root_state = self._env.sim.data.qpos[:, robot.indexing.free_joint_q_adr].reshape(self.num_envs, 7)
        self.state.reset(env_ids, root_state[env_ids, :2], heading(root_state[env_ids, 3:7]), self.schedule[env_ids, 0])
        self.just_reset[env_ids] = True
        return {}

    def compute(self, dt):
        ids = (~self.just_reset & ~self.state.failed).nonzero().flatten()
        if dt > 0 and len(ids):
            stage = (self.state.time[:, None]+1e-6 >= self.ends).sum(-1).clamp_max(6)
            req = self.schedule[torch.arange(self.num_envs, device=self.device), stage]
            scheduled = ids[~self.manual[ids]]
            self.state.set_request(req[scheduled], scheduled)
            self.state.slew(dt, ids)
        self.just_reset[:] = False

    def set_manual_request(self, request, ids=None):
        if ids is None:
            ids = torch.arange(self.num_envs, device=self.device)
        self.manual[ids] = True
        self.state.set_request(request, ids)

    def _update_command(self):
        pass

    def _update_metrics(self):
        pass


@dataclass(kw_only=True)
class LocomotionCommandCfg(CommandTermCfg):
    strict: bool = False
    stage: int = 0
    probabilities: tuple[float, ...] = FAMILY_PROBABILITIES
    def build(self, env):
        return LocomotionCommand(self, env)


class OrderedAction(ActionTerm):
    def __init__(self, cfg, env):
        super().__init__(cfg, env)
        ids, names = self._entity.find_joints(JOINT_ORDER, preserve_order=True)
        if tuple(names) != JOINT_ORDER:
            raise ValueError("Joint mapping differs from 14D contract")
        self.ids = torch.tensor(ids, device=self.device)
        self.home = torch.tensor([HOME[value] for value in JOINT_ORDER], device=self.device)
        self.raw = torch.zeros(self.num_envs, 14, device=self.device)
        self.previous_raw = torch.zeros_like(self.raw)
        self.actual = torch.zeros_like(self.raw); self.previous = torch.zeros_like(self.raw)
        self.target = self.home.repeat(self.num_envs, 1)
    @property
    def action_dim(self): return 14
    @property
    def raw_action(self): return self.raw
    def reset(self, env_ids=None):
        ids = slice(None) if env_ids is None else env_ids
        self.raw[ids] = 0; self.actual[ids] = 0; self.previous[ids] = 0
        self.previous_raw[ids] = 0
        self.target[ids] = self.home
    def process_actions(self, actions):
        invalid = ~torch.isfinite(actions).all(-1)
        self._env.locomotion.fail(invalid, 4)
        self.previous_raw.copy_(self.raw)
        self.raw.copy_(torch.nan_to_num(actions, nan=0., posinf=0., neginf=0.))
        self.previous.copy_(self.actual)
        limits = self._entity.data.joint_pos_limits[:, self.ids]
        self.target = (self.home+.5*self.raw.clamp(-1, 1)).clamp(limits[..., 0], limits[..., 1])
        self.actual = (self.target-self.home)/.5
    def apply_actions(self):
        self._entity.set_joint_position_target(self.target, joint_ids=self.ids)


@dataclass(kw_only=True)
class OrderedActionCfg(ActionTermCfg):
    def build(self, env): return OrderedAction(self, env)


def observation(env):
    robot = env.scene["robot"]; action = env.action_manager.get_term("joints")
    values = torch.cat((robot.data.root_link_ang_vel_b, robot.data.projected_gravity_b,
                      robot.data.joint_pos[:, action.ids]-action.home,
                      robot.data.joint_vel[:, action.ids], action.raw, env.locomotion.cmd,
                      torch.zeros(env.num_envs, 10, device=env.device)), -1)
    env.locomotion.fail(~torch.isfinite(values).all(-1), 4)
    return torch.nan_to_num(values, nan=0., posinf=0., neginf=0.)


def measure_substep(env):

    env.sim.forward()
    robot = env.scene["robot"]; state = env.locomotion
    state.fail(~torch.isfinite(env.sim.data.qpos[:]).all(-1) | ~torch.isfinite(env.sim.data.qvel[:]).all(-1), 4)
    root_state = env.sim.data.qpos[:, robot.indexing.free_joint_q_adr].reshape(env.num_envs, 7)
    velocity = env.sim.data.qvel[:, robot.indexing.free_joint_v_adr].reshape(env.num_envs, 6)
    quaternion = root_state[:, 3:7]
    tilt = torch.acos((1-2*(quaternion[:, 1].square()+quaternion[:, 2].square())).clamp(-1, 1))
    contact = env.sim.data.contact
    geom = contact.geom[:]; worlds = contact.worldid[:]
    valid = torch.arange(geom.shape[0], device=env.device) < env.sim.data.nacon[0]

    if not hasattr(env, "_locomotion_ground_ids"):
        model = env.sim.mj_model
        ground = [index for index in range(model.ngeom) if model.geom_bodyid[index] == 0]
        feet = [index for index in range(model.ngeom) if model.geom(index).name.endswith(("left_foot_collision", "right_foot_collision"))]
        env._locomotion_ground_ids = torch.tensor(ground, device=env.device)
        env._locomotion_foot_ids = torch.tensor(feet, device=env.device)
    ground0 = torch.isin(geom[:, 0], env._locomotion_ground_ids)
    ground1 = torch.isin(geom[:, 1], env._locomotion_ground_ids)
    other = torch.where(ground0, geom[:, 1], geom[:, 0])
    bad = valid & (ground0 | ground1) & ~torch.isin(other, env._locomotion_foot_ids) & (contact.dist[:] <= 0)
    bad_contact = torch.zeros(env.num_envs, device=env.device, dtype=torch.int32)
    bad_contact.scatter_add_(0, worlds.clamp(0, env.num_envs-1).long(), bad.int())
    state.substep(root_state[:, :2], heading(quaternion), velocity[:, :3], tilt, root_state[:, 2], velocity[:, 3:5], bad_contact > 0, env.physics_dt)
    sample_feet(env, valid, ground0, ground1)
    if env._sim_step_counter % env.cfg.decimation == 0:
        state.finish_control()
    return state.max_drift


def failure(env): return env.locomotion.failed


def trajectory_finished(env):
    command = env.command_manager.get_term("velocity")
    return (env.locomotion.time >= command.duration-1e-6) & ~command.manual


def reward_rate(env):
    action = env.action_manager.get_term("joints")
    env.locomotion.raw_reward_delta.copy_(action.raw-action.previous_raw)
    result = env.locomotion.reward(action.actual, action.previous)
    names = ("time", "request", "cmd", "vel", "yaw_rate", "filtered", "xy", "anchor", "anchor_time",
             "max_drift", "brake_path", "strict_drift", "strict_stop", "strict_path",
             "strict_full_stop", "strict_hold", "reward_terms", "reason", "phase", "failed",
             "hold_complete", "full_confirmed", "tilt", "max_tilt", "min_height", "last_yaw",
             "reward_raw", "reward_weights", "reward_contributions")
    env.extras["locomotion"] = {name: getattr(env.locomotion, name).clone() for name in names}
    command = env.command_manager.get_term("velocity")
    current_segment = ((env.locomotion.time[:, None]-1e-6) >= command.ends).sum(-1).clamp_max(6)
    reached = env.locomotion.time[:, None] > torch.cat((torch.zeros_like(command.ends[:, :1]), command.ends[:, :-1]), -1)+1e-6
    env.extras["locomotion"].update({
        "family": command.family.clone(), "segment": current_segment,
        "reached_segments": reached, "duration": command.duration.clone(),
        "trajectory_end": trajectory_finished(env).clone(),
        "time_limit": (env.episode_length_buf >= env.max_episode_length).clone(),
        "terminal": env.reset_buf.clone(), "terminated": env.reset_terminated.clone(),
        "truncated": env.reset_time_outs.clone(),
    })
    if env.locomotion.capture_substeps:
        env.extras["locomotion"]["physics_trace"] = env.locomotion.physics_trace.clone()
    return result


def failure_cost_rate(env):

    return -env.locomotion.reward_config["terms"]["failure"]["weight"] * env.locomotion.failed.float() / env.step_dt


def metric(env, name):
    return getattr(env.locomotion, name).float()
