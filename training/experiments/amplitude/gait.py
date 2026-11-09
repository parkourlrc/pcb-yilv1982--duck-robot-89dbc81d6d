"""独立奖励实验的足部测量；不写入任何物理状态或执行器参数。"""
import torch


def sample(env, valid, ground0, ground1):
    state = env.locomotion
    robot = env.scene["robot"]
    model = env.sim.mj_model
    if not hasattr(env, "_gait_geometry"):
        feet = [next(i for i in range(model.ngeom) if model.geom(i).name.endswith(side+"_foot_collision"))
                for side in ("left", "right")]
        if any(int(model.geom_type[i]) != 6 for i in feet):
            raise ValueError("gait clearance requires the frozen box feet")
        bodies = robot.indexing.body_ids.cpu().tolist()
        local = [bodies.index(int(model.geom_bodyid[i])) for i in feet]
        sizes = torch.as_tensor(model.geom_size[feet].copy(), device=env.device, dtype=torch.float32)
        env._gait_geometry = feet, local, sizes
    feet, bodies, sizes = env._gait_geometry
    pos = env.sim.data.geom_xpos[:, feet]
    rot = env.sim.data.geom_xmat[:, feet].reshape(env.num_envs, 2, 3, 3)
    height = pos[:, :, 2] - (rot[:, :, 2].abs()*sizes).sum(-1)
    center_v = robot.data.body_link_lin_vel_w[:, bodies] + torch.cross(
        robot.data.body_link_ang_vel_w[:, bodies], pos-robot.data.body_link_pos_w[:, bodies], dim=-1)
    contacts = env.sim.data.contact
    geom = contacts.geom[:]
    worlds = contacts.worldid[:].long().clamp(0, env.num_envs-1)
    valid = valid & (contacts.dist[:] <= 0)
    counts, slip = [], []
    for foot, body in zip(feet, bodies):
        mask = valid & ((ground0 & (geom[:, 1] == foot)) | (ground1 & (geom[:, 0] == foot)))
        count = torch.zeros(env.num_envs, device=env.device).scatter_add_(0, worlds, mask.float())
        velocity = robot.data.body_link_lin_vel_w[worlds, body] + torch.cross(
            robot.data.body_link_ang_vel_w[worlds, body],
            contacts.pos[:]-robot.data.body_link_pos_w[worlds, body], dim=-1)
        speed_sq = torch.where(mask, velocity[:, :2].square().sum(-1), 0.)
        slip.append(torch.zeros_like(count).scatter_add_(0, worlds, speed_sq)/count.clamp_min(1))
        counts.append(count)
    contact = torch.stack(counts, -1) > 0
    landing = contact & (state.gait_air > 0) & state.gait_seen
    state.gait_landing_cost += (((state.gait_peak/env._gait_height-1)**2)*landing).sum(-1)
    state.gait_landing_count += landing.sum(-1)
    state.gait_air = torch.where(contact, 0., state.gait_air+env.physics_dt)
    state.gait_peak = torch.where(contact, 0., torch.maximum(state.gait_peak, height.clamp_min(0)))
    state.gait_seen |= contact
    state.gait_contact.copy_(contact)
    state.gait_height.copy_(height)
    state.gait_clearance_cost += ((height-env._gait_height).abs()*center_v[:, :, :2].norm(dim=-1)).sum(-1)
    state.gait_slip_cost += torch.stack(slip, -1).sum(-1)
    state.gait_samples += 1


def reward(env, variant):
    state = env.locomotion
    action = env.action_manager.get_term("joints")
    settings = variant["gait"]
    active = (state.cmd[:, :2].norm(dim=-1)+state.cmd[:, 2].abs() > .01).float()
    air = ((state.gait_air > .125) & (state.gait_air < .300) & state.gait_seen).float().sum(-1)
    samples = state.gait_samples.clamp_min(1)
    foot = torch.stack((3*air, -2*state.gait_clearance_cost/samples,
                        -.25*state.gait_landing_cost, -.1*state.gait_slip_cost/samples), -1)
    foot *= active[:, None]*float(settings["feet_enabled"])
    weight = 0.
    if settings["raw_ramp"]:
        step = 6400 if state.strict else env.common_step_counter
        for threshold, value in ((0,.1),(1600,.2),(3200,.4),(4800,.6),(5760,1.)):
            if step >= threshold:
                weight = value
        state.reward_terms[:, 7] = -weight*(action.raw-action.gait_previous_raw).square().sum(-1)
    state.gait_reward_terms.copy_(foot)
    state.reward_rate = state.reward_terms.sum(-1)+foot.sum(-1)
    values = torch.cat((foot.mean(0), torch.stack((state.gait_height.mean(),
        state.gait_height.max(), (state.gait_contact.sum(-1)==1).float().mean(),
        (state.gait_contact.sum(-1)==0).float().mean(), state.gait_landing_count.mean(),
        (state.gait_slip_cost/samples).mean(), state.reward_terms[:, 7].mean(),
        state.reward_rate.mean(), torch.as_tensor(weight, device=env.device)))))
    if not hasattr(env, "_gait_log_sum"):
        env._gait_log_sum = torch.zeros_like(values)
        env._gait_log_count = 0
    env._gait_log_sum += values
    env._gait_log_count += 1
    state.gait_clearance_cost.zero_()
    state.gait_slip_cost.zero_()
    state.gait_landing_cost.zero_()
    state.gait_landing_count.zero_()
    state.gait_samples.zero_()
    return state.reward_rate


@torch.inference_mode()
def take_log(env):
    names = ("air_reward_rate", "clearance_reward_rate", "swing_reward_rate", "slip_reward_rate",
             "mean_clearance_m", "mean_batch_max_clearance_m", "single_support_fraction",
             "no_support_fraction", "landings_per_env_control_step", "contact_slip_speed_squared",
             "smooth_reward_rate", "total_reward_rate", "raw_smooth_weight")
    values = (env._gait_log_sum/max(env._gait_log_count, 1)).detach().cpu().tolist()
    count = env._gait_log_count
    env._gait_log_sum.zero_()
    env._gait_log_count = 0
    return {**dict(zip(names, values)), "control_steps": count}
