"""固定公式的奖励配置与只读足部测量。"""
from __future__ import annotations

import torch

from .experiment_config import BASE_NAMES, FOOT_NAMES, REWARD_TERMS, default_rewards, effective_rewards


@torch.inference_mode()
def apply_reward_config(env, config, stage, completed_updates):
    resolved = effective_rewards(config, stage, completed_updates)
    state = env.unwrapped.locomotion
    previous = state.reward_config
    changed = any(previous["terms"][name]["enabled"] != resolved["terms"][name]["enabled"] for name in FOOT_NAMES)
    changed |= any(previous["scales"][name] != resolved["scales"][name] for name in ("target_height_m", "air_min_s", "air_max_s"))
    if changed:
        for name in ("gait_air", "gait_peak", "gait_height", "gait_seen", "gait_contact", "gait_landing_cost",
                     "gait_clearance_cost", "gait_slip_cost", "gait_samples"):
            getattr(state, name).zero_()
    state.reward_config = resolved
    return resolved


def initialize_reward_state(state):
    state.reward_config = default_rewards()
    state.reward_raw = torch.zeros(state.count_envs, len(REWARD_TERMS), device=state.device)
    state.reward_weights = torch.zeros_like(state.reward_raw)
    state.reward_contributions = torch.zeros_like(state.reward_raw)
    state.raw_reward_delta = torch.zeros(state.count_envs, 14, device=state.device)
    for name in ("gait_air", "gait_peak", "gait_height"):
        setattr(state, name, torch.zeros(state.count_envs, 2, device=state.device))
    for name in ("gait_seen", "gait_contact"):
        setattr(state, name, torch.zeros(state.count_envs, 2, device=state.device, dtype=torch.bool))
    for name in ("gait_landing_cost", "gait_clearance_cost", "gait_slip_cost", "gait_samples"):
        setattr(state, name, torch.zeros(state.count_envs, device=state.device))


def sample_feet(env, valid, ground0, ground1):
    state = env.locomotion
    config = state.reward_config
    if not any(config["terms"][name]["enabled"] for name in FOOT_NAMES):
        return
    robot = env.scene["robot"]
    model = env.sim.mj_model
    if not hasattr(env, "_reward_foot_geometry"):
        feet = [next(index for index in range(model.ngeom) if model.geom(index).name.endswith(side+"_foot_collision"))
                for side in ("left", "right")]
        if any(int(model.geom_type[index]) != 6 for index in feet):
            raise ValueError("foot rewards require the frozen box feet")
        body_ids = robot.indexing.body_ids.cpu().tolist()
        bodies = [body_ids.index(int(model.geom_bodyid[index])) for index in feet]
        sizes = torch.as_tensor(model.geom_size[feet].copy(), device=env.device, dtype=torch.float32)
        env._reward_foot_geometry = feet, bodies, sizes
    feet, bodies, sizes = env._reward_foot_geometry
    position = env.sim.data.geom_xpos[:, feet]
    rotation = env.sim.data.geom_xmat[:, feet].reshape(env.num_envs, 2, 3, 3)
    height = position[:, :, 2]-(rotation[:, :, 2].abs()*sizes).sum(-1)
    center_velocity = robot.data.body_link_lin_vel_w[:, bodies]+torch.cross(
        robot.data.body_link_ang_vel_w[:, bodies], position-robot.data.body_link_pos_w[:, bodies], dim=-1)
    contacts = env.sim.data.contact
    geometry = contacts.geom[:]
    worlds = contacts.worldid[:].long().clamp(0, env.num_envs-1)
    valid = valid & (contacts.dist[:] <= 0)
    counts, slips = [], []
    for foot, body in zip(feet, bodies):
        mask = valid & ((ground0 & (geometry[:, 1] == foot)) | (ground1 & (geometry[:, 0] == foot)))
        count = torch.zeros(env.num_envs, device=env.device).scatter_add_(0, worlds, mask.float())
        velocity = robot.data.body_link_lin_vel_w[worlds, body]+torch.cross(
            robot.data.body_link_ang_vel_w[worlds, body], contacts.pos[:]-robot.data.body_link_pos_w[worlds, body], dim=-1)
        speed_squared = torch.where(mask, velocity[:, :2].square().sum(-1), 0.)
        slips.append(torch.zeros_like(count).scatter_add_(0, worlds, speed_squared)/count.clamp_min(1))
        counts.append(count)
    contact = torch.stack(counts, -1) > 0
    landing = contact & (state.gait_air > 0) & state.gait_seen
    target = config["scales"]["target_height_m"]
    state.gait_landing_cost += (((state.gait_peak/target-1)**2)*landing).sum(-1)
    state.gait_air = torch.where(contact, 0., state.gait_air+env.physics_dt)
    state.gait_peak = torch.where(contact, 0., torch.maximum(state.gait_peak, height.clamp_min(0)))
    state.gait_seen |= contact
    state.gait_contact.copy_(contact)
    state.gait_height.copy_(height)
    state.gait_clearance_cost += ((height-target).abs()*center_velocity[:, :, :2].norm(dim=-1)).sum(-1)
    state.gait_slip_cost += torch.stack(slips, -1).sum(-1)
    state.gait_samples += 1


def reward_components(state, actual, previous, home_height):
    config, scales = state.reward_config, state.reward_config["scales"]

    def track(error, sigma):
        return torch.exp(-(error/sigma)**2)

    velocity_command, yaw_command = state.cmd[:, 0], state.cmd[:, 2]
    velocity_track = track(state.vel[:, 0]-velocity_command, torch.maximum(
        scales["velocity_relative_sigma"]*velocity_command.abs(), torch.full_like(velocity_command, scales["velocity_min_sigma"])))
    yaw_track = track(state.yaw_rate-yaw_command, torch.maximum(
        scales["velocity_relative_sigma"]*yaw_command.abs(), torch.full_like(yaw_command, scales["yaw_min_sigma"])))
    turn = yaw_command.abs() > 1e-6
    stop = (velocity_command.abs() < 1e-6) & ~turn
    yaw_zero = track(state.yaw_rate, scales["yaw_zero_sigma"])
    auxiliary = velocity_track*torch.where(turn, yaw_track, yaw_zero)
    posture = track(state.tilt, scales["posture_gate_tilt_sigma"])*track(state.height-home_height, scales["posture_gate_height_sigma"])
    late = ((state.phase == 1) & (state.time-state.brake_start > 3)) | (
        state.full_active & ~state.full_confirmed & (state.time-state.full_start > 3))
    smooth = (state.raw_reward_delta.square().sum(-1) if config["smoothing"] == "raw" else
              ((actual-previous).square().mean(-1)/scales["smooth_sigma_squared"]).clamp_max(1))
    moving = (state.cmd[:, :2].norm(dim=-1)+state.cmd[:, 2].abs() > .01).float()
    airborne = ((state.gait_air > scales["air_min_s"]) & (state.gait_air < scales["air_max_s"]) & state.gait_seen).float().sum(-1)
    samples = state.gait_samples.clamp_min(1)
    raw = torch.stack((posture*velocity_track, posture*turn*yaw_track,
                       posture*stop*track(state.vel.norm(dim=-1), scales["stand_sigma"])*yaw_zero,
                       auxiliary*track(state.vel[:, 1], scales["lateral_sigma"]),
                       auxiliary*(velocity_command > 1e-6)*~turn*yaw_zero,
                       auxiliary*(state.phase == 2)*track((state.xy-state.anchor).norm(dim=-1), scales["anchor_sigma"]),
                       auxiliary*track(state.tilt, scales["posture_tilt_sigma"])*track(state.height-home_height, scales["posture_height_sigma"]),
                       smooth, late.float(), moving*airborne, moving*state.gait_clearance_cost/samples,
                       moving*state.gait_landing_cost, moving*state.gait_slip_cost/samples, state.failed.float()), -1)
    weights = torch.tensor([info[1]*config["terms"][name]["weight"]*config["terms"][name]["enabled"]
                            for name, info in REWARD_TERMS.items()], device=state.device, dtype=raw.dtype)
    state.reward_raw.copy_(raw)
    state.reward_weights.copy_(weights.expand_as(raw))
    state.reward_contributions.copy_(raw*weights)
    state.reward_terms = state.reward_contributions[:, :len(BASE_NAMES)]
    state.reward_rate = state.reward_contributions[:, :-1].sum(-1)
    state.gait_clearance_cost.zero_()
    state.gait_slip_cost.zero_()
    state.gait_landing_cost.zero_()
    state.gait_samples.zero_()
    return state.reward_rate
