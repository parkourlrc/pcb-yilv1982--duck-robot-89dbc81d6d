"""Frozen-source deterministic locomotion replay, controlled through atomic JSON files."""
from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import sys
import time
import threading
import traceback
import uuid


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name+f".{uuid.uuid4().hex}.tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False)+"\n", encoding="utf-8")
    try:
        for attempt in range(12):
            try:
                os.replace(temporary, path)
                return True
            except PermissionError:
                time.sleep(min(.005*(attempt+1), .04))
        return False
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except PermissionError:
            pass


def select_runtime(manifest, explicit, task_version):
    if explicit:
        return Path(explicit).resolve()
    run = manifest.parent.parent.parent
    if (run/"sources/training/mjlab_duck/locomotion_env.py").is_file():
        return run/"sources"
    if task_version in ("v1", "1", "locomotion-v1"):
        return Path(__file__).resolve().parents[1]/"runtime_versions/locomotion-v1"
    raise ValueError("checkpoint lacks a frozen runtime; provide --runtime-root")


def load_source(manifest_path, runtime_root, rank=0):
    import torch
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != 1 or manifest.get("complete") is not True:
        raise ValueError("incomplete checkpoint manifest")
    entry = manifest["rank_files"][str(rank)]
    checkpoint = (manifest_path.parent/entry["path"]).resolve()
    if checkpoint.parent != manifest_path.parent or digest(checkpoint) != entry["sha256"]:
        raise ValueError("checkpoint path or SHA256 invalid")
    payload = torch.load(checkpoint, map_location="cpu", weights_only=False)
    signature = hashlib.sha256(json.dumps(payload["contract"], sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    if signature != manifest["config_hash"] or payload["config_hash"] != signature:
        raise ValueError("checkpoint contract hash invalid")
    for key in ("world_size", "iter", "stage", "experiment_id", "consumed_transitions"):
        if payload[key] != manifest[key]:
            raise ValueError(f"checkpoint {key} differs from manifest")
    if payload["rank"] != rank:
        raise ValueError("checkpoint rank identity mismatch")
    for name, expected in payload["contract"]["sources"].items():
        source = (runtime_root/name).resolve()
        if not source.is_relative_to(runtime_root) or not source.is_file() or digest(source) != expected:
            raise ValueError(f"frozen runtime source mismatch: {name}")
    return manifest, payload, checkpoint


def run(args):
    session = args.output_dir.resolve()
    session.mkdir(parents=True, exist_ok=True)
    status_path = session/"status.json"
    seq = 0
    control_seq = -1
    generation = 0
    speed = 1.
    paused = False
    done = False
    completed_since = None
    status = "initializing"
    identity = {"replay_id": args.replay_id, "rank": args.rank, "task_version": args.task_version}
    status_lock = threading.Lock()
    heartbeat_stop = threading.Event()
    current_status = {}

    def state(value, **extra):
        nonlocal status
        status = value
        with status_lock:
            current_status.clear()
            current_status.update({**identity, "state": value, "status": value,
                                   "utc": datetime.now(timezone.utc).isoformat(), "speed": speed,
                                   "seq": seq, "generation": generation, **extra})
            atomic_json(status_path, current_status)

    def heartbeat():
        while not heartbeat_stop.wait(1.):
            with status_lock:
                atomic_json(status_path, {**current_status, "utc": datetime.now(timezone.utc).isoformat()})

    state("initializing")
    heartbeat_thread = threading.Thread(target=heartbeat, daemon=True)
    heartbeat_thread.start()
    env = None
    try:
        os.environ["WORLD_SIZE"] = "1"
        os.environ["RANK"] = "0"
        os.environ["LOCAL_RANK"] = "0"
        import torch
        from tensordict import TensorDict
        from rsl_rl.models import MLPModel
        from mjlab.envs import ManagerBasedRlEnv

        manifest_path = args.checkpoint.resolve()
        if manifest_path.is_dir():
            manifest_path /= "manifest.json"
        runtime = select_runtime(manifest_path, args.runtime_root, args.task_version).resolve()
        manifest, payload, checkpoint = load_source(manifest_path, runtime, args.rank)
        sys.path.insert(0, str(runtime/"training"))
        from mjlab_duck.locomotion_cfg import locomotion_env_cfg
        from mjlab_duck.locomotion_env import DT, JOINT_ORDER
        from mjlab_duck.locomotion_evaluator import development_scenarios

        torch.set_num_threads(1)
        torch.manual_seed(args.seed)
        torch.cuda.set_device(args.device)
        candidates = development_scenarios(2)
        scenario = next((item for item in candidates if item.name == args.scenario), None)
        if scenario is None:
            raise ValueError("unknown scenario: "+args.scenario)
        scenario = replace(scenario, seed=args.seed)
        actor = MLPModel(TensorDict({"actor": torch.zeros(1, 61)}, batch_size=[1]),
                         {"actor": ["actor"]}, "actor", 14, hidden_dims=(128, 128),
                         activation="elu", obs_normalization=True,
                         distribution_cfg={"class_name": "GaussianDistribution", "init_std": .3, "std_type": "log"})
        actor.load_state_dict(payload["actor_state_dict"], strict=True)
        actor.to(args.device).eval()
        frozen = {name: value.clone() for name, value in actor.state_dict().items()}
        config = locomotion_env_cfg(1, evaluation=True, seed=scenario.seed)
        config.is_finite_horizon = True
        env = ManagerBasedRlEnv(config, device=args.device)
        if payload.get('config', {}).get('reward_config'):
            from mjlab_duck.reward_runtime import apply_reward_config
            original_config = payload['config']
            completed_updates = payload.get('consumed_transitions', 0) // (original_config['num_envs'] * original_config['num_steps_per_env'])
            apply_reward_config(env, original_config['reward_config'], payload['stage'], completed_updates)
            if payload.get('reward_recipe'):
                from copy import deepcopy
                env.locomotion.reward_config = deepcopy(payload['reward_recipe'])
        robot = env.scene["robot"]
        joint_ids, joint_names = robot.find_joints(JOINT_ORDER, preserve_order=True)
        if tuple(joint_names) != JOINT_ORDER:
            raise ValueError("replay joint order differs from frozen contract")
        identity.update(checkpoint=str(manifest_path), checkpoint_sha256=digest(checkpoint),
                        model_iteration=payload["iter"], stage=payload["stage"], scenario=scenario.name,
                        seed=scenario.seed, runtime_root=str(runtime), source_world_size=manifest["world_size"],
                        device=args.device, versions={name: importlib.metadata.version(name) for name in ("torch", "mjlab", "mujoco", "rsl-rl-lib")})
        episode_return = 0.
        episode_steps = 0
        active_seconds = 0.

        def reset():
            nonlocal done, episode_return, episode_steps, active_seconds, completed_since
            torch.manual_seed(scenario.seed)
            env.reset(seed=scenario.seed)
            done, episode_return, episode_steps = False, 0., 0
            completed_since = None
            active_seconds = 0.
            return env.command_manager.get_term("velocity").set_fixed_schedule(scenario.segments)

        started = time.perf_counter()
        frame_clock = started
        deadline = started
        heartbeat_clock = started
        with torch.inference_mode(), (session/"frames.jsonl").open("a", encoding="utf-8", buffering=1) as frames:
            observations = reset()
            state("playing")
            while True:
                for control_name in ("controls.json", "control.json"):
                    control_file = session/control_name
                    if control_file.is_file():
                        try:
                            control = json.loads(control_file.read_text(encoding="utf-8-sig"))
                            requested_seq = int(control.get("seq", control.get("generation", -1)))
                        except (OSError, TypeError, ValueError):
                            continue
                        if requested_seq > control_seq:
                            control_seq = requested_seq
                            action = control.get("action")
                            if action in ("close", "stop"):
                                state("closed")
                                return
                            if action in ("pause", "play", "resume"):
                                paused = action == "pause"
                            elif action == "reset":
                                observations = reset()
                                generation += 1
                                paused = False
                                deadline = time.perf_counter()
                            if "speed" in control:
                                proposed = float(control["speed"])
                                if proposed not in (.5, 1., 2.):
                                    raise ValueError("playback speed must be 0.5, 1 or 2")
                                speed = proposed
                            state("completed" if done else "paused" if paused else "playing", control_seq=control_seq)
                if (session/"STOP").exists():
                    state("closed")
                    return
                if paused or done:
                    if done and not paused and args.idle_timeout > 0 and completed_since is not None and time.perf_counter()-completed_since >= args.idle_timeout:
                        state("closed", control_seq=control_seq, reason="idle_timeout")
                        return
                    if time.perf_counter()-heartbeat_clock >= 1:
                        state("completed" if done else "paused", control_seq=control_seq)
                        heartbeat_clock = time.perf_counter()
                    time.sleep(.04)
                    deadline = time.perf_counter()
                    continue
                active_started = time.perf_counter()
                state_values = env.locomotion
                used_command = state_values.cmd[0].detach().cpu().tolist()
                action = actor(TensorDict(observations, batch_size=[1]), stochastic_output=False)
                if not bool(torch.isfinite(action).all()):
                    raise ValueError("non-finite replay action")
                observations, reward, terminated, truncated, _ = env.step(action)
                episode_steps += 1
                episode_return += float(reward[0])
                done = bool((terminated | truncated)[0])
                if done and completed_since is None:
                    completed_since = time.perf_counter()
                now = time.perf_counter()
                if now-frame_clock >= 1/25 or done or seq == 0:
                    seq += 1
                    root = env.sim.data.qpos[0, robot.indexing.free_joint_q_adr].reshape(7).detach().cpu().tolist()
                    joints = robot.data.joint_pos[0, joint_ids].detach().cpu().tolist()
                    simulation_time = float(state_values.time[0])
                    quat_w, quat_x, quat_y, quat_z = root[3:7]
                    import math
                    attitude = {"roll_rad": math.atan2(2*(quat_w*quat_x+quat_y*quat_z), 1-2*(quat_x*quat_x+quat_y*quat_y)),
                                "pitch_rad": math.asin(max(-1., min(1., 2*(quat_w*quat_y-quat_z*quat_x)))),
                                "yaw_rad": float(state_values.last_yaw[0])}
                    frame = {**identity, "seq": seq, "generation": generation, "utc": datetime.now(timezone.utc).isoformat(),
                             "simulation_time": simulation_time, "sim_time_s": simulation_time,
                             "root_position_m": root[:3], "root_quaternion_wxyz": root[3:7],
                             "joints_rad": dict(zip(joint_names, joints)), "command": used_command,
                             "attitude": attitude,
                             "actual": {"velocity_m_s": state_values.vel[0].detach().cpu().tolist(),
                                        "yaw_rate_rad_s": float(state_values.yaw_rate[0]),
                                        "roll_pitch_rate_rad_s": state_values.rp[0].detach().cpu().tolist(),
                                        "yaw_rad": float(state_values.last_yaw[0])},
                             "episode_return": episode_return, "episode_length": episode_steps,
                             "failed": bool(state_values.failed[0]), "reason": int(state_values.reason[0]),
                             "completed": done and not bool(state_values.failed[0]), "speed": speed,
                             "actual_realtime_factor": episode_steps*DT/max(active_seconds+now-active_started, 1e-9)}
                    frames.write(json.dumps(frame, allow_nan=False)+"\n")
                    atomic_json(session/"latest-frame.json", frame)
                    frame_clock = now
                if now-heartbeat_clock >= 1:
                    state("playing", control_seq=control_seq)
                    heartbeat_clock = now
                if done:
                    if any(not torch.equal(value, actor.state_dict()[name]) for name, value in frozen.items()):
                        raise RuntimeError("replay mutated actor or normalization")
                    state("completed", actor_and_normalization_frozen=True,
                          episode_return=episode_return, episode_length=episode_steps)
                deadline += DT/speed
                time.sleep(max(0., deadline-time.perf_counter()))
                active_seconds += time.perf_counter()-active_started
    except BaseException as error:
        state("failed", error=f"{type(error).__name__}: {error}", traceback=traceback.format_exc())
        raise
    finally:
        heartbeat_stop.set()
        heartbeat_thread.join(timeout=2.)
        if env is not None:
            env.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", "--manifest", dest="checkpoint", type=Path, required=True)
    parser.add_argument("--task-version", default="v1")
    parser.add_argument("--runtime-root", type=Path)
    parser.add_argument("--scenario", default="straight_0.06_101")
    parser.add_argument("--seed", type=int, default=101)
    parser.add_argument("--output-dir", "--session-dir", dest="output_dir", type=Path, required=True)
    parser.add_argument("--replay-id", required=True)
    parser.add_argument("--rank", type=int, default=0)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--idle-timeout", type=float, default=300.,
                        help="seconds to keep a finished replay alive before releasing the GPU; 0 disables")
    run(parser.parse_args())


if __name__ == "__main__":
    main()
