"""冻结策略的500 Hz执行器/接触诊断；不修改依赖文件，不训练策略。"""
from pathlib import Path
import argparse
from dataclasses import asdict
import hashlib
import json
import os
import sys

os.environ.setdefault("MUJOCO_GL", "egl")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+"\n", encoding="utf-8")


def summarize(trace, substeps, names):
    import numpy as np
    time = trace["time"]
    post_time = np.arange(1, len(substeps["q_post"])+1)*.002
    steady = post_time >= 3.
    control_steady = time >= 3.
    if steady.sum() < 100:
        return {"valid": False, "reason": "insufficient steady duration"}
    q = substeps["q_post"]
    feet = {}
    all_events = []
    cycle_ranges = {name: [] for name in names}
    for side_index, side in enumerate(("left", "right")):
        height = substeps["clearance"][:, side_index]
        contact = substeps["contact_count"][:, side_index] > 0
        air = (height > .003) & ~contact & steady
        edges = np.diff(np.r_[False, air, False].astype(int))
        events = []
        for start, end in zip(np.where(edges == 1)[0], np.where(edges == -1)[0]):
            if end-start >= 20 and start > 0 and end < len(air):
                events.append({"start_s": float(post_time[start]), "end_s": float(post_time[end-1]),
                               "max_clearance_mm": float(height[start:end].max()*1000),
                               "start": int(start), "end": int(end)})
                all_events.append((float(post_time[start]), side))
        for first, second in zip(events, events[1:]):
            for j, name in enumerate(names):
                if name.startswith(side+"_"):
                    cycle_ranges[name].append(float(np.rad2deg(np.ptp(q[first["start"]:second["start"], j]))))
        contact_steady = contact & steady
        feet[side] = {"events": events, "event_count": len(events),
                      "clearance_min_max_mm": [float(height[steady].min()*1000), float(height[steady].max()*1000)],
                      "contact_fraction": float(contact[steady].mean()),
                      "contact_point_horizontal_speed_mean_m_s": float(substeps["contact_speed"][contact_steady, side_index].mean()) if contact_steady.any() else None}
    all_events.sort()
    alternate = [a[1] != b[1] and b[0]-a[0] >= .04 for a, b in zip(all_events, all_events[1:])]
    alternation = float(np.mean(alternate)) if alternate else 0.
    joints = {}
    for j, name in enumerate(names):
        target = trace["target"][control_steady, j]
        power = np.abs(np.fft.rfft(target-target.mean()))**2
        freq = np.fft.rfftfreq(len(target), .02)
        joints[name] = {
            "actual_range_deg": float(np.rad2deg(np.ptp(q[steady, j]))),
            "target_range_deg": float(np.rad2deg(np.ptp(target))),
            "target_dominant_hz": float(freq[1+np.argmax(power[1:])]),
            "target_power_above_5hz": float(power[freq>5].sum()/max(power.sum(), 1e-30)),
            "torque_saturation_fraction": float((np.abs(substeps["torque_raw"][steady, j])>.94).mean()),
            "target_error_rms_deg": float(np.rad2deg(np.sqrt(np.mean((substeps["target"][steady, j]-substeps["q_pre"][steady, j])**2)))),
            "cycle_median_range_deg": float(np.median(cycle_ranges[name])) if cycle_ranges[name] else None,
            "cycle_count": len(cycle_ranges[name]),
        }
    return {"valid": True, "joints": joints, "feet": feet, "alternation_fraction": alternation,
            "foot_gate_passed": all(foot["event_count"] >= 5 for foot in feet.values()) and alternation >= .8,
            "body_vx_mean_m_s": float(trace["physics"][control_steady, :, 10].mean()),
            "raw_clip_fraction": float((np.abs(trace["action"])>1).mean()),
            "pd_clip_identity_max_error": float(np.abs(substeps["torque"]-np.clip(substeps["torque_raw"], -.94, .94)).max()),
            "contact_definition": "generated ground-foot pair, dist<=0, world0; no contact-force measurement",
            "sample_alignment": "q_pre/qd_pre/target/torque before physics; q_post/clearance/contact after physics+existing forward",
            "cycle_definition": "same-foot successive qualifying >3mm/no-contact swing intervals; undefined if insufficient cycles"}


def run(args):
    import numpy as np
    import torch
    from tensordict import TensorDict
    from rsl_rl.models import MLPModel
    from mjlab.envs import ManagerBasedRlEnv
    torch.set_num_threads(1)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.set_float32_matmul_precision("highest")
    root = args.base/"frozen"
    sys.path.insert(0, str(root/"training"))
    from mjlab_duck.locomotion_cfg import locomotion_env_cfg
    from mjlab_duck.locomotion_env import JOINT_ORDER
    from mjlab_duck.locomotion_evaluator import development_scenarios, evaluate_trace
    result = json.loads((args.base/"run/result.json").read_text())
    manifest_path = Path(result["checkpoint_manifest"])
    manifest = json.loads(manifest_path.read_text())
    checkpoint = manifest_path.parent/manifest["rank_files"]["0"]["path"]
    if digest(checkpoint) != manifest["rank_files"]["0"]["sha256"]:
        raise ValueError("checkpoint digest mismatch")
    payload = torch.load(checkpoint, map_location="cpu", weights_only=False)
    for name, expected in payload["contract"]["sources"].items():
        if digest(root/name) != expected:
            raise ValueError(f"source contract mismatch: {name}")
    actor = MLPModel(TensorDict({"actor": torch.zeros(1,61)}, batch_size=[1]), {"actor": ["actor"]}, "actor", 14,
                     hidden_dims=(128,128), activation="elu", obs_normalization=True,
                     distribution_cfg={"class_name":"GaussianDistribution", "init_std":.3, "std_type":"log"})
    actor.load_state_dict(payload["actor_state_dict"], strict=True)
    actor.to("cuda:0").eval()
    before = {k:v.clone() for k,v in actor.state_dict().items()}
    args.output.mkdir(parents=True, exist_ok=False)
    reports = []
    scenarios = [s for s in development_scenarios(1) if s.name.startswith("straight_0.06_") and s.seed in args.seeds]
    for scenario in scenarios:
        cfg = locomotion_env_cfg(1, evaluation=True, seed=scenario.seed)
        cfg.is_finite_horizon = True
        env = ManagerBasedRlEnv(cfg, device="cuda:0")
        robot = env.scene["robot"]
        action_term = env.action_manager.get_term("joints")
        if len(robot.actuators) != 1:
            raise ValueError("diagnostic expects one 14-joint ideal PD group")
        actuator = robot.actuators[0]
        if list(actuator._target_names) != list(JOINT_ORDER):
            raise ValueError("actuator order differs")
        actuator_compute = actuator.compute
        pending = {}
        arrays = {k:[] for k in ("q_pre","qd_pre","target","torque_raw","torque","q_post","qd_post","clearance","contact_count","contact_speed")}
        def compute(cmd):
            torque = actuator_compute(cmd)
            pending.update(q_pre=cmd.pos[0].clone(), qd_pre=cmd.vel[0].clone(), target=cmd.position_target[0].clone(),
                           torque_raw=(actuator.stiffness*(cmd.position_target-cmd.pos)+actuator.damping*(cmd.velocity_target-cmd.vel)+cmd.effort_target)[0].clone(),
                           torque=torque[0].clone())
            return torque
        actuator.compute = compute
        compute_substep = env.metrics_manager.compute_substep
        model = env.sim.mj_model
        foot_ids = [i for i in range(model.ngeom) if model.geom(i).name.endswith(("left_foot_collision","right_foot_collision"))]
        foot_ids.sort(key=lambda i: 0 if model.geom(i).name.endswith("left_foot_collision") else 1)
        global_bodies = robot.indexing.body_ids.cpu().tolist()
        body_ids = [global_bodies.index(int(model.geom_bodyid[i])) for i in foot_ids]
        sizes = torch.as_tensor(model.geom_size[foot_ids].copy(), device=env.device, dtype=torch.float32)
        def collect_substep():
            value = compute_substep()
            pos = env.sim.data.geom_xpos[0, foot_ids]
            rot = env.sim.data.geom_xmat[0, foot_ids].reshape(2,3,3)
            height = pos[:,2]-(rot[:,2].abs()*sizes).sum(-1)
            contact = env.sim.data.contact
            geom = contact.geom[:]
            valid = (torch.arange(len(geom),device=env.device)<env.sim.data.nacon[0]) & (contact.worldid[:]==0) & (contact.dist[:]<=0)
            ground0 = torch.isin(geom[:,0],env._locomotion_ground_ids)
            ground1 = torch.isin(geom[:,1],env._locomotion_ground_ids)
            counts, speeds = [], []
            for foot, body in zip(foot_ids, body_ids):
                mask = valid & ((ground0 & (geom[:,1]==foot)) | (ground1 & (geom[:,0]==foot)))
                velocity = robot.data.body_link_lin_vel_w[0,body]+torch.cross(robot.data.body_link_ang_vel_w[0,body].expand(len(geom),3), contact.pos[:]-robot.data.body_link_pos_w[0,body],dim=-1)
                counts.append(mask.sum())
                speeds.append((velocity[:,:2].norm(dim=-1)*mask).sum()/mask.sum().clamp_min(1))
            pending.update(q_post=robot.data.joint_pos[0,action_term.ids].clone(),qd_post=robot.data.joint_vel[0,action_term.ids].clone(),
                           clearance=height.clone(),contact_count=torch.stack(counts),contact_speed=torch.stack(speeds))
            for k in arrays:
                arrays[k].append(pending[k])
            return value
        env.metrics_manager.compute_substep = collect_substep
        try:
            with torch.inference_mode():
                obs,_ = env.reset(seed=scenario.seed)
                obs = env.command_manager.get_term("velocity").set_fixed_schedule(scenario.segments)
                state = env.locomotion
                trace = {"initial_xy":state.xy[0].cpu().clone(), "initial_yaw":state.last_yaw[0].cpu().clone()}
                records = {k:[] for k in ("physics","time","command","action","target","qpos","reward_terms")}
                completed, failed, reason = False,False,0
                for i in range(1150):
                    action = actor(TensorDict(obs,batch_size=[1]),stochastic_output=False)
                    command = state.cmd[0].clone()
                    obs,reward,terminated,truncated,_ = env.step(action)
                    values = {"physics":state.physics_trace[0],"time":state.time[0],"command":command,
                              "action":action[0],"target":action_term.target[0],"qpos":env.sim.data.qpos[0],"reward_terms":state.reward_terms[0]}
                    for key,value in values.items():records[key].append(value.detach().cpu().clone())
                    failed = bool(state.failed[0]) or not bool(torch.isfinite(reward).all())
                    reason = int(state.reason[0]) if bool(state.failed[0]) else (4 if failed else 0)
                    if bool((terminated|truncated)[0]) or failed:
                        completed = i==1149 and not failed and bool(truncated[0]) and not bool(terminated[0])
                        break
                trace.update({k:torch.stack(v) for k,v in records.items()})
                report = asdict(evaluate_trace(scenario,trace,completed=completed,failed=failed,reason=reason))
                raw = {k:v.numpy() for k,v in trace.items()}
                sub = {k:torch.stack(v).cpu().numpy() for k,v in arrays.items()}
                assert len(sub["q_pre"])==len(raw["time"])*10
                folder = args.output/scenario.name
                folder.mkdir()
                np.savez_compressed(folder/"trace.npz",**raw)
                np.savez_compressed(folder/"substeps.npz",**sub)
                metrics = summarize(raw,sub,JOINT_ORDER)
                write_json(folder/"metrics.json",metrics)
                write_json(folder/"evaluation.json",report)
                reports.append({"scenario":scenario.name,"evaluation":report,"metrics":metrics})
                if args.render and scenario.seed==101:
                    render(model,raw["qpos"],folder)
                print(json.dumps({"scenario":scenario.name,"passed":report["passed"],"feet":metrics.get("feet")}),flush=True)
        finally:
            env.close()
    if any(not torch.equal(v,actor.state_dict()[k]) for k,v in before.items()):
        raise RuntimeError("diagnostic mutated actor")
    write_json(args.output/"summary.json",{"checkpoint":str(checkpoint),"checkpoint_sha256":digest(checkpoint),
               "diagnostic_sha256":digest(__file__),"actor_unchanged":True,"torch_threads":1,"tf32":False,
               "joint_order":JOINT_ORDER,"reports":reports})


def render(model, positions, folder):
    import mujoco
    import imageio.v2 as imageio
    data = mujoco.MjData(model)
    camera = mujoco.MjvCamera()
    camera.azimuth,camera.elevation,camera.distance = 135,-25,.55
    camera.lookat[:] = [0,0,.08]
    renderer = mujoco.Renderer(model,height=480,width=640)
    try:
        with imageio.get_writer(folder/"replay-50fps.mp4",fps=50,macro_block_size=None) as writer:
            for i,position in enumerate(positions):
                data.qpos[:] = position
                mujoco.mj_forward(model,data)
                camera.lookat[:2] = position[:2]
                renderer.update_scene(data,camera=camera)
                frame = renderer.render()
                writer.append_data(frame)
                if i==min(500,len(positions)-1): imageio.imwrite(folder/"preview.png",frame)
    finally:
        renderer.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--seeds",type=int,nargs="+",default=[101,102,103])
    parser.add_argument("--render",action="store_true")
    run(parser.parse_args())
