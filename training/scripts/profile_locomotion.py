"""采样路径短时性能诊断；不修改任务语义或保存策略。"""
from __future__ import annotations

import argparse
from contextlib import nullcontext
from dataclasses import asdict
from datetime import datetime, timezone
import functools
import gzip
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
import time

import torch

from benchmark_locomotion import measured_iteration, training_config
from mjlab.envs import ManagerBasedRlEnv
from mjlab.rl import MjlabOnPolicyRunner, RslRlVecEnvWrapper
from mjlab_duck.locomotion_cfg import locomotion_env_cfg


class Instrumentation:
    def __init__(self):
        self.enabled = False
        self.originals = []

    def scope(self, name):
        return torch.profiler.record_function("profile/" + name) if self.enabled else nullcontext()

    def wrap(self, owner, method, name):
        original = getattr(owner, method)

        @functools.wraps(original)
        def wrapped(*args, **kwargs):
            with self.scope(name):
                return original(*args, **kwargs)

        self.originals.append((owner, method, original))
        setattr(owner, method, wrapped)

    def restore(self):
        for owner, method, original in reversed(self.originals):
            setattr(owner, method, original)


def snapshot():
    command = ["nvidia-smi", "--query-gpu=name,driver_version,memory.total,memory.used,utilization.gpu,power.draw,temperature.gpu,clocks.sm,clocks.mem", "--format=csv"]
    result = subprocess.run(command, capture_output=True, text=True, timeout=10)
    return {"command": command, "returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr}


def profiler():
    return torch.profiler.profile(
        activities=[torch.profiler.ProfilerActivity.CPU, torch.profiler.ProfilerActivity.CUDA],
        record_shapes=False, profile_memory=False, with_stack=False,
    )


def save_trace(recording, path):
    recording.export_chrome_trace(str(path))
    compressed = path.with_suffix(path.suffix + ".gz")
    with path.open("rb") as source, gzip.open(compressed, "wb") as destination:
        import shutil
        shutil.copyfileobj(source, destination)
    path.unlink()
    return {"path": str(compressed), "bytes": compressed.stat().st_size, "sha256": hashlib.sha256(compressed.read_bytes()).hexdigest()}


def split_iteration(environment, algorithm, observations, instrumentation, probe_steps, trace_root=None):
    device = environment.device
    torch.cuda.synchronize(device)
    terminal_count = torch.zeros((), device=device)
    invalid_count = torch.zeros((), device=device)
    clipped_count = torch.zeros((), device=device)
    traces = {}

    def collect(count):
        nonlocal observations, terminal_count, invalid_count, clipped_count
        for _ in range(count):
            with instrumentation.scope("policy_act"):
                actions = algorithm.act(observations)
            with instrumentation.scope("environment_step"):
                observations, rewards, dones, extras = environment.step(actions)
            with instrumentation.scope("benchmark_statistics"):
                invalid_count += (~torch.isfinite(rewards)).sum()
                invalid_count += (~torch.isfinite(observations["actor"])).sum()
                clipped_count += (actions.abs() > 1).sum()
                terminal_count += dones.sum()
            with instrumentation.scope("process_env_step"):
                algorithm.process_env_step(observations, rewards, dones, extras)

    with torch.inference_mode():
        recording = profiler() if trace_root else nullcontext()
        with recording:
            instrumentation.enabled = trace_root is not None
            with instrumentation.scope("sampling_window"):
                started = time.perf_counter()
                collect(probe_steps)
                with instrumentation.scope("sampling_end_drain"):
                    torch.cuda.synchronize(device)
                probe_seconds = time.perf_counter() - started
            instrumentation.enabled = False
        if trace_root:
            traces["sampling"] = save_trace(recording, trace_root / "sampling.json")
        remainder_started = time.perf_counter()
        collect(64 - probe_steps)
        torch.cuda.synchronize(device)
        remainder_seconds = time.perf_counter() - remainder_started
        return_recording = profiler() if trace_root else nullcontext()
        with return_recording:
            instrumentation.enabled = trace_root is not None
            with instrumentation.scope("returns_window"):
                returns_started = time.perf_counter()
                with instrumentation.scope("compute_returns"):
                    algorithm.compute_returns(observations)
                with instrumentation.scope("returns_end_drain"):
                    torch.cuda.synchronize(device)
                returns_seconds = time.perf_counter() - returns_started
            instrumentation.enabled = False
        if trace_root:
            traces["returns"] = save_trace(return_recording, trace_root / "returns.json")
    update_started = time.perf_counter()
    losses = algorithm.update()
    torch.cuda.synchronize(device)
    update_seconds = time.perf_counter() - update_started
    if invalid_count.item():
        raise RuntimeError("Non-finite sample")
    return observations, {
        "probe_steps": probe_steps, "probe_s": probe_seconds,
        "remaining_sampling_s": remainder_seconds, "returns_s": returns_seconds,
        "ppo_update_s": update_seconds, "done_count": int(terminal_count.item()),
        "losses": {name: float(value) for name, value in losses.items()},
        "traces": traces,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--trace-dir", type=Path, required=True)
    parser.add_argument("--num-envs", type=int, default=4096)
    parser.add_argument("--warmup", type=int, default=5)
    parser.add_argument("--baseline", type=int, default=3)
    parser.add_argument("--probe-steps", type=int, default=8)
    arguments = parser.parse_args()
    if not 1 <= arguments.probe_steps <= 64 or arguments.warmup < 1 or arguments.baseline < 1:
        raise ValueError("Invalid sample sizes")
    if arguments.output.exists() or arguments.trace_dir.exists():
        raise FileExistsError("Use new output and trace directory")
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.trace_dir.mkdir(parents=True)
    torch.cuda.set_device(0)
    torch.set_num_threads(1)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.set_float32_matmul_precision("highest")
    root = Path(__file__).resolve().parents[2]
    source_paths = [Path(__file__), root / "training/scripts/benchmark_locomotion.py"]
    source_paths += list((root / "training/mjlab_duck").glob("locomotion*.py"))
    source_paths += [root / "training/models/duck_v0.xml", root / "training/params/home_pose.json"]
    result = {
        "utc_time": datetime.now(timezone.utc).isoformat(), "command": sys.argv,
        "device": torch.cuda.get_device_name(), "python": sys.version,
        "versions": {name: importlib.metadata.version(name) for name in ("torch", "mjlab", "mujoco", "mujoco-warp", "warp-lang", "rsl-rl-lib", "tensordict")},
        "cuda": torch.version.cuda, "tf32": False, "mixed_precision": False,
        "torch_cpu_threads": 1, "num_envs": arguments.num_envs, "rollout": 64,
        "source_sha256": {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest() for path in source_paths},
        "before": snapshot(), "warmup": [], "baseline": [],
        "scope": "current_source_local_diagnostic_not_historical_reproduction_or_policy_acceptance",
    }
    environment = None
    instrumentation = Instrumentation()
    try:
        configuration = locomotion_env_cfg(arguments.num_envs, seed=42)
        configuration.is_finite_horizon = True
        base = ManagerBasedRlEnv(configuration, device="cuda:0")
        environment = RslRlVecEnvWrapper(base, clip_actions=None)
        runner = MjlabOnPolicyRunner(environment, asdict(training_config()), log_dir=None, device="cuda:0")
        algorithm = runner.alg
        algorithm.train_mode()
        observations = environment.get_observations()
        result["use_cuda_graph"] = base.sim.use_cuda_graph
        for index in range(arguments.warmup):
            observations, measurement = measured_iteration(environment, algorithm, observations, 64, "cuda:0")
            result["warmup"].append(measurement)
            print(f"warmup {index}: {measurement['total_s']:.6f}s", flush=True)
        for index in range(arguments.baseline):
            observations, measurement = split_iteration(environment, algorithm, observations, instrumentation, arguments.probe_steps)
            result["baseline"].append(measurement)
            print(f"baseline {index}: probe={measurement['probe_s']:.6f}s", flush=True)
        for owner, method, label in (
            (base.sim, "step", "physics_step"), (base.sim, "forward", "physics_forward"),
            (base.sim, "sense", "physics_sense"), (base.sim, "reset", "physics_reset"),
            (base.metrics_manager, "compute_substep", "substep_metrics"),
            (base.metrics_manager, "compute", "step_metrics"),
            (base.command_manager, "compute", "commands"),
            (base.observation_manager, "compute", "observations"),
            (base.reward_manager, "compute", "rewards"),
            (base.termination_manager, "compute", "terminations"),
            (base, "_reset_idx", "reset_envs"),
            (base.action_manager, "process_action", "action_process"),
            (base.action_manager, "apply_action", "action_apply"),
            (base.scene, "write_data_to_sim", "scene_write"),
            (base.scene, "update", "scene_update"),
        ):
            instrumentation.wrap(owner, method, label)
        observations, result["profile"] = split_iteration(environment, algorithm, observations, instrumentation, arguments.probe_steps, arguments.trace_dir)
        instrumentation.restore()
        observations, result["after_baseline"] = split_iteration(environment, algorithm, observations, instrumentation, arguments.probe_steps)
        result["after"] = snapshot()
        result["status"] = "completed"
    except Exception as error:
        result["status"] = "failed"
        result["error"] = repr(error)
        raise
    finally:
        instrumentation.enabled = False
        instrumentation.restore()
        arguments.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if environment is not None:
            environment.close()


if __name__ == "__main__":
    main()
