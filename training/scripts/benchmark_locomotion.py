"""同任务短时PPO测速，不输出正式训练候选。"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import statistics
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import torch
import torch.distributed as distributed
from mjlab.envs import ManagerBasedRlEnv
from mjlab.rl import (
    MjlabOnPolicyRunner, RslRlModelCfg, RslRlOnPolicyRunnerCfg,
    RslRlPpoAlgorithmCfg, RslRlVecEnvWrapper,
)
from mjlab_duck.locomotion_cfg import locomotion_env_cfg


def training_config():
    return RslRlOnPolicyRunnerCfg(
        actor=RslRlModelCfg(
            hidden_dims=(128, 128), activation="elu", obs_normalization=True,
            distribution_cfg={"class_name": "GaussianDistribution", "init_std": .30, "std_type": "log"},
        ),
        critic=RslRlModelCfg(hidden_dims=(128, 128), activation="elu", obs_normalization=True),
        algorithm=RslRlPpoAlgorithmCfg(
            learning_rate=3e-4, schedule="adaptive", desired_kl=.01,
            num_learning_epochs=5, num_mini_batches=4, gamma=.995,
            lam=.95, entropy_coef=.005, max_grad_norm=1., value_loss_coef=1.,
            use_clipped_value_loss=True, clip_param=.2,
            normalize_advantage_per_mini_batch=False, optimizer="adam",
        ),
        num_steps_per_env=64, max_iterations=2000, seed=42,
        experiment_name="duck_locomotion_benchmark", logger="tensorboard",
        upload_model=False, clip_actions=None,
    )


def measured_iteration(environment, algorithm, observations, rollout_steps, device):
    if distributed.is_initialized():
        distributed.barrier()
    torch.cuda.synchronize(device)
    started = time.perf_counter()
    terminal_count = torch.zeros((), device=device)
    invalid_count = torch.zeros((), device=device)
    clipped_count = torch.zeros((), device=device)
    with torch.inference_mode():
        for _ in range(rollout_steps):
            actions = algorithm.act(observations)
            observations, rewards, dones, extras = environment.step(actions)
            invalid_count += (~torch.isfinite(rewards)).sum()
            invalid_count += (~torch.isfinite(observations["actor"])).sum()
            clipped_count += (actions.abs() > 1).sum()
            terminal_count += dones.sum()
            algorithm.process_env_step(observations, rewards, dones, extras)
        algorithm.compute_returns(observations)
    torch.cuda.synchronize(device)
    collected = time.perf_counter()
    losses = algorithm.update()
    torch.cuda.synchronize(device)
    updated = time.perf_counter()
    parameters_finite = all(torch.isfinite(parameter).all().item() for model in (algorithm.actor, algorithm.critic) for parameter in model.parameters())
    values = {name: float(value) for name, value in losses.items()}
    if invalid_count.item() or not parameters_finite or not all(math.isfinite(value) for value in values.values()):
        raise RuntimeError("Non-finite observation/reward/loss/parameters invalidate benchmark")
    return observations, {
        "collect_and_returns_s": collected-started,
        "ppo_update_including_sync_s": updated-collected,
        "total_s": updated-started,
        "done_count": int(terminal_count.item()),
        "raw_clip_fraction": clipped_count.item()/(rollout_steps*environment.num_envs*14),
        "losses": values, "parameters_finite": parameters_finite,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--global-envs", type=int, default=64)
    parser.add_argument("--warmup", type=int, default=2)
    parser.add_argument("--iterations", type=int, default=3)
    parser.add_argument("--label", default="local")
    arguments = parser.parse_args()
    world_size = int(os.getenv("WORLD_SIZE", "1"))
    rank = int(os.getenv("RANK", "0"))
    local_rank = int(os.getenv("LOCAL_RANK", "0"))
    if arguments.global_envs % world_size or arguments.iterations < 3 or arguments.warmup < 1:
        raise ValueError("Require divisible global environments, >=3 timed windows, >=1 warmup")
    device = f"cuda:{local_rank}"
    torch.cuda.set_device(device)
    torch.set_num_threads(1)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.set_float32_matmul_precision("highest")
    configuration = training_config()
    env_configuration = locomotion_env_cfg(arguments.global_envs//world_size, seed=42+rank)
    env_configuration.is_finite_horizon = True
    setup_started = time.perf_counter()
    environment = None
    try:
        environment = RslRlVecEnvWrapper(ManagerBasedRlEnv(env_configuration, device=device), clip_actions=None)
        runner = MjlabOnPolicyRunner(environment, asdict(configuration), log_dir=None, device=device)
        algorithm = runner.alg
        algorithm.train_mode()
        if world_size > 1:
            algorithm.broadcast_parameters()
        observations = environment.get_observations()
        assert observations["actor"].shape == (arguments.global_envs//world_size, 61)
        assert environment.num_actions == 14
        assert not environment.episode_length_buf.any()
        torch.cuda.synchronize(device)
        setup_seconds = time.perf_counter()-setup_started
        warmup_windows = []
        for window in range(arguments.warmup):
            observations, measurement = measured_iteration(environment, algorithm, observations, 64, device)
            warmup_windows.append(measurement)
            print(f"rank={rank} warmup={window} seconds={measurement['total_s']:.3f}", flush=True)
        torch.cuda.reset_peak_memory_stats(device)
        timed_windows = []
        for window in range(arguments.iterations):
            observations, measurement = measured_iteration(environment, algorithm, observations, 64, device)
            timed_windows.append(measurement)
            print(f"rank={rank} timed={window} seconds={measurement['total_s']:.3f}", flush=True)
        root = Path(__file__).resolve().parents[2]
        files = ("training/scripts/benchmark_locomotion.py", "training/mjlab_duck/locomotion_env.py", "training/mjlab_duck/locomotion_cfg.py", "training/models/duck_v0.xml", "training/params/home_pose.json")
        record = {
            "label": arguments.label, "utc_time": datetime.now(timezone.utc).isoformat(),
            "rank": rank, "world_size": world_size, "global_envs": arguments.global_envs,
            "local_envs": environment.num_envs, "global_samples_per_iteration": arguments.global_envs*64,
            "device": torch.cuda.get_device_name(device), "python": sys.version,
            "versions": {name: importlib.metadata.version(name) for name in ("torch", "mjlab", "mujoco", "mujoco-warp", "warp-lang", "rsl-rl-lib", "tensordict")},
            "cuda": torch.version.cuda, "nccl": torch.cuda.nccl.version(),
            "tf32": False, "mixed_precision": False, "torch_cpu_threads": 1,
            "configuration": asdict(configuration), "finite_horizon": True,
            "init_at_random_ep_len": False,
            "sha256": {name: hashlib.sha256((root/name).read_bytes()).hexdigest() for name in files},
            "setup_s": setup_seconds, "warmup": warmup_windows, "timed": timed_windows,
            "torch_peak_allocated_bytes": torch.cuda.max_memory_allocated(device),
            "torch_peak_reserved_bytes": torch.cuda.max_memory_reserved(device),
            "memory_note": "PyTorch counters exclude Warp and other CUDA allocators",
            "policy_quality_evaluated": False, "checkpoint_saved": False,
        }
        records = [None for _ in range(world_size)]
        if world_size > 1:
            distributed.all_gather_object(records, record)
        else:
            records[0] = record
        if rank == 0:
            timings = [max(node["timed"][window]["total_s"] for node in records) for window in range(arguments.iterations)]
            result = {
                "scope": "short_PPO_workload_benchmark_not_policy_acceptance",
                "rank_records": records,
                "aggregation": {
                    "method": "max_rank_wall_per_window; global_samples counted once",
                    "window_total_s": timings,
                    "median_iteration_s": statistics.median(timings),
                    "global_transitions_per_s": arguments.global_envs*64*len(timings)/sum(timings),
                    "median_global_transitions_per_s": arguments.global_envs*64/statistics.median(timings),
                    "update_sync_note": "NCCL synchronization included in update; not independently timed",
                },
            }
            arguments.output.parent.mkdir(parents=True, exist_ok=True)
            arguments.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
            print(json.dumps(result["aggregation"], indent=2), flush=True)
    finally:
        if environment is not None:
            environment.close()
        if distributed.is_initialized():
            distributed.destroy_process_group()


if __name__ == "__main__":
    main()
