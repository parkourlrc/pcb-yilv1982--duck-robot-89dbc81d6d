"""自建联合策略的双节点训练、评估、预算与显式续训入口。"""
from __future__ import annotations

import argparse
from contextlib import nullcontext
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import importlib.metadata
import json
import math
import os
from pathlib import Path
import random
import shutil
import signal
import socket
import subprocess
import sys
import time
import uuid

import torch
import torch.distributed as distributed

from .locomotion_checkpoint import (
    ROOT, CONTRACT_FILES, BudgetLedger, ExperimentLease, RankCoordinator, atomic_json,
    atomic_torch, contract, load_collective, make_payload, restore_payload, restore_rng,
    rng_state, save_collective, sha_dict, sha_file, validate_manifest, write_manifest, initialize_actor,
)
from .locomotion_logging import JsonlLogger, RolloutStatistics, merge_summaries, RunEvents, EpisodeAccumulator, EpisodeWindow
from .locomotion_train_cfg import LocomotionTrainConfig, ppo_config
from .reward_runtime import apply_reward_config
from experiment_archive import register_runtime, validate_workflow

STOP_REQUESTED = False


def freeze_startup(directory, cfg, workflow, rank):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    if rank != 0:
        return
    names = set(CONTRACT_FILES)
    names.update(str(path.relative_to(ROOT)).replace("\\", "/") for path in (ROOT/"training/mjlab_duck").glob("*.py"))
    hashes = {}
    for name in sorted(names):
        destination = directory/"sources"/name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT/name, destination)
        hashes[name] = sha_file(destination)
    dependencies = {distribution.metadata["Name"]: distribution.version for distribution in importlib.metadata.distributions()
                    if distribution.metadata.get("Name")}
    atomic_json(directory/"runtime-environment.json", {
        "created_utc": datetime.now(timezone.utc).isoformat(), "command": sys.argv,
        "python": sys.version, "executable": sys.executable, "dependencies": dependencies,
        "config": cfg.as_dict(), "workflow": workflow, "source_sha256": hashes,
        "contract": contract(cfg, int(os.getenv("WORLD_SIZE", "1"))), "status": "before_runtime_initialization"})


class ConsoleCopy:
    def __init__(self, original, output):
        self.original, self.output = original, output

    def write(self, value):
        self.output.write(value)
        self.output.flush()
        return self.original.write(value)

    def flush(self):
        self.output.flush()
        self.original.flush()


def request_stop(signum, frame):
    global STOP_REQUESTED
    STOP_REQUESTED = True


@dataclass
class TrainingState:
    model_iteration: int = 0
    stage: int = 1
    stage_updates: int = 0
    stage1_streak: int = 0
    regression_streak: int = 0
    empty_windows: int = 0
    last_eval_iteration: int = -1
    last_eval_id: str = ""
    last_evaluation: dict | None = None
    diagnostic_joint_samples: int = 0
    diagnostic_updates: int = 0
    stage1_passed: str | None = None
    parent_checkpoint: str | None = None

    def record_evaluation(self, iteration, checkpoint_id, straight_passed, total_passed, total, interval):
        expected = 9 if self.stage == 1 else 22
        if interval < 1 or iteration < 1 or iteration % interval:
            raise ValueError("only scheduled evaluation points may advance curriculum")
        if total != expected or not 0 <= straight_passed <= 9 or not straight_passed <= total_passed <= total:
            raise ValueError("invalid development evaluation coverage")
        if iteration <= self.last_eval_iteration or checkpoint_id == self.last_eval_id:
            raise ValueError("repeated or stale checkpoint cannot advance the evaluation gate")
        adjacent = self.last_eval_iteration >= 0 and iteration-self.last_eval_iteration == interval
        self.last_eval_iteration = iteration
        self.last_eval_id = checkpoint_id
        self.last_evaluation = {"iteration": iteration, "checkpoint": checkpoint_id,
                                "stage": self.stage, "passed": total_passed, "total": total}
        if self.stage == 1:
            passed = straight_passed == 9 and total_passed == 9
            self.stage1_streak = (self.stage1_streak+1 if adjacent else 1) if passed else 0
            return "stage2" if self.stage1_streak >= 2 else "continue"
        self.regression_streak = (self.regression_streak+1 if adjacent else 1) if straight_passed < 9 else 0
        if self.regression_streak >= 2:
            return "pause_regression"
        return "full_reference" if total_passed == 22 else "continue"

    def record_diagnostic(self, joint_later_samples):
        if self.stage != 2:
            return False
        self.empty_windows = self.empty_windows+1 if joint_later_samples == 0 else 0
        return self.empty_windows >= 2

    def enter_stage2(self, checkpoint):
        self.stage = 2
        self.stage_updates = 0
        self.stage1_passed = checkpoint
        self.parent_checkpoint = checkpoint
        self.regression_streak = 0
        self.empty_windows = 0
        self.last_eval_iteration = -1
        self.last_eval_id = ""
        self.diagnostic_joint_samples = 0
        self.diagnostic_updates = 0


def build_runtime(cfg, stage=1, device=None, control_timeout_s=3600):
    from mjlab.envs import ManagerBasedRlEnv
    from mjlab.rl import MjlabOnPolicyRunner, RslRlVecEnvWrapper
    from .locomotion_cfg import locomotion_env_cfg

    class TrainingRunner(MjlabOnPolicyRunner):
        def _configure_multi_gpu(self):
            self.gpu_world_size = int(os.getenv("WORLD_SIZE", "1"))
            self.gpu_global_rank = int(os.getenv("RANK", "0"))
            self.gpu_local_rank = int(os.getenv("LOCAL_RANK", "0"))
            self.is_distributed = self.gpu_world_size > 1
            self.cfg["multi_gpu"] = None
            if self.is_distributed:
                if self.device != f"cuda:{self.gpu_local_rank}":
                    raise ValueError("GPU device must match LOCAL_RANK")
                self.cfg["multi_gpu"] = {"global_rank": self.gpu_global_rank,
                                         "local_rank": self.gpu_local_rank, "world_size": self.gpu_world_size}
                if not distributed.is_initialized():
                    distributed.init_process_group("nccl", rank=self.gpu_global_rank,
                                                   world_size=self.gpu_world_size,
                                                   timeout=timedelta(seconds=control_timeout_s))
                elif distributed.get_world_size() != self.gpu_world_size or distributed.get_rank() != self.gpu_global_rank:
                    raise ValueError("existing process group differs from launcher")

    world_size = int(os.getenv("WORLD_SIZE", "1"))
    rank = int(os.getenv("RANK", "0"))
    if cfg.num_envs % world_size or cfg.num_envs//world_size*cfg.num_steps_per_env % cfg.num_mini_batches:
        raise ValueError("environment and minibatch counts must divide evenly across ranks")
    device = device or f"cuda:{int(os.getenv('LOCAL_RANK', '0'))}"
    torch.cuda.set_device(device)
    torch.set_num_threads(1)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.set_float32_matmul_precision("highest")
    random.seed(cfg.seed+rank)
    torch.manual_seed(cfg.seed+rank)
    course = cfg.stage1 if stage == 1 else cfg.stage2
    env_cfg = locomotion_env_cfg(cfg.num_envs//world_size, stage=stage, probabilities=course.probabilities, seed=cfg.seed+rank)
    env_cfg.is_finite_horizon = True
    env = RslRlVecEnvWrapper(ManagerBasedRlEnv(env_cfg, device=device), clip_actions=None)
    try:
        runner = TrainingRunner(env, ppo_config(cfg), log_dir=None, device=device)
        runner.experiment_config = cfg
        runner.reward_completed_updates = 0
        runner.reward_recipe = apply_reward_config(env, cfg.reward_config, stage, 0)
        group = distributed.new_group(backend="gloo", timeout=timedelta(seconds=control_timeout_s)) if world_size > 1 else None
        coordinator = RankCoordinator(group)
        if world_size > 1:
            runner.alg.broadcast_parameters()
        runner.alg.train_mode()
        observations = env.get_observations()
        if observations["actor"].shape != (cfg.num_envs//world_size, 61) or env.num_actions != 14 or env.episode_length_buf.any():
            raise ValueError("61/14/HOME contract differs")
        return runner, env, coordinator
    except BaseException:
        env.close()
        raise


def checkpoint_payload(runner, cfg, *, iteration, stage, parent_checkpoint, consumed_transitions, gate_streak=0, diagnostic_windows=0):
    state = TrainingState(model_iteration=iteration, stage=stage, stage1_streak=gate_streak,
                          empty_windows=diagnostic_windows, parent_checkpoint=parent_checkpoint)
    world_size = int(os.getenv("WORLD_SIZE", "1"))
    return make_payload(runner, cfg, asdict(state), {"consumed_transitions": consumed_transitions,
                                                  "experiment_id": "standalone_check", "parent_checkpoint": parent_checkpoint},
                        int(os.getenv("RANK", "0")), world_size)


def save_rank_checkpoint(runner, cfg, directory, **kwargs):
    payload = checkpoint_payload(runner, cfg, **kwargs)
    path = Path(directory)/f"checkpoint_{payload['iter']:06d}.rank{payload['rank']}.pt"
    atomic_torch(path, payload)
    return path


def write_rank_manifest(directory, iteration, rank_paths, *, stage, consumed_transitions):
    payloads = [torch.load(path, map_location="cpu", weights_only=False) for _, path in sorted(rank_paths.items(), key=lambda item: int(item[0]))]
    if any(item["iter"] != iteration or item["stage"] != stage or item["consumed_transitions"] != consumed_transitions for item in payloads):
        raise ValueError("rank metadata differs")
    return Path(write_manifest(directory, payloads))


def load_checkpoint(runner, path, cfg, *, map_location=None):
    payload = torch.load(path, map_location=map_location or "cpu", weights_only=False)
    if payload["rank"] != int(os.getenv("RANK", "0")):
        raise ValueError("explicit rank checkpoint belongs to another rank")
    return restore_payload(runner, payload, contract(cfg, int(os.getenv("WORLD_SIZE", "1"))))


def _environment_stage(env, cfg, stage):
    command = env.unwrapped.command_manager.get_term("velocity")
    command.stage = stage
    command.probabilities = (cfg.stage1 if stage == 1 else cfg.stage2).probabilities
    command.cfg.stage = stage
    command.cfg.probabilities = command.probabilities
    with torch.inference_mode():
        observations, _ = env.reset()
    return observations


def _suite_record(suite):
    if isinstance(suite, dict):
        return suite
    episodes = [asdict(episode) for episode in suite.episodes]
    straight = [episode for episode in episodes if episode["name"].startswith("straight_")]
    return {"episodes": episodes, "total": suite.total, "passed_count": suite.passed_count,
            "passed": suite.passed, "straight_passed": sum(episode["passed"] for episode in straight),
            "straight_total": len(straight)}


def evaluate_policy(runner, stage, full=False):
    from mjlab.envs import ManagerBasedRlEnv
    from tensordict import TensorDict
    from .locomotion_cfg import locomotion_env_cfg
    from .locomotion_evaluator import development_scenarios, full_reference_scenarios, evaluate_suite

    saved_rng = rng_state()
    actor_mode, critic_mode = runner.alg.actor.training, runner.alg.critic.training
    runner.alg.eval_mode()
    before = {key: tensor.detach().clone() for key, tensor in runner.alg.actor.obs_normalizer.state_dict().items()}
    try:
        def policy(observations):
            tensor_observations = TensorDict(observations, batch_size=[1]).to(runner.device)
            return runner.alg.get_policy()(tensor_observations, stochastic_output=False)

        def env_factory(scenario):
            configuration = locomotion_env_cfg(1, evaluation=True, seed=scenario.seed)
            configuration.is_finite_horizon = True
            environment = ManagerBasedRlEnv(configuration, device=runner.device)
            if getattr(runner, "evaluation_trace_root", None):
                suite_name = "full96" if full else f"stage{stage}"
                environment.evaluation_trace_directory = runner.evaluation_trace_root/f"{runner.reward_completed_updates:06d}-{suite_name}"
            if hasattr(runner, "experiment_config"):
                apply_reward_config(environment, runner.experiment_config.reward_config, stage, runner.reward_completed_updates)
            return environment

        scenarios = full_reference_scenarios() if full else development_scenarios(stage)
        with torch.inference_mode():
            report = evaluate_suite(policy, scenarios, env_factory, "full96" if full else f"stage{stage}")
        if any(not torch.equal(value, runner.alg.actor.obs_normalizer.state_dict()[key]) for key, value in before.items()):
            raise RuntimeError("evaluation mutated observation normalization")
        return _suite_record(report)
    finally:
        runner.alg.actor.train(actor_mode)
        runner.alg.critic.train(critic_mode)
        restore_rng(saved_rng)


def _prepare_experiment(root, cfg, signature, resume_manifest, check_mode):
    root = Path(root)
    path = root/"experiment.json"
    if path.exists():
        experiment = json.loads(path.read_text(encoding="utf-8"))
        if not resume_manifest:
            raise ValueError("existing experiment requires an explicit resume manifest")
        if experiment["config_hash"] != sha_dict(signature) or experiment["check_mode"] != check_mode:
            raise ValueError("experiment contract changed; budget cannot be silently reset")
        if not (root/"budget.jsonl").exists():
            raise ValueError("resume requires original durable budget ledger")
        return experiment
    if resume_manifest:
        raise ValueError("cannot resume into an empty experiment; preserve the original ledger")
    experiment = {"id": uuid.uuid4().hex, "config_hash": sha_dict(signature), "contract": signature,
                  "check_mode": check_mode, "max_transitions": cfg.max_transitions,
                  "created_utc": datetime.now(timezone.utc).isoformat()}
    atomic_json(path, experiment)
    with (root/"budget.jsonl").open("x") as stream:
        stream.flush()
        os.fsync(stream.fileno())
    return experiment


def _run_manifest(directory, cfg, signature, coordinator, check_mode):
    rank_records = coordinator.gather({"rank": coordinator.rank, "host": socket.gethostname(),
                                       "device": torch.cuda.get_device_name(), "cuda": torch.version.cuda,
                                       "nccl": torch.cuda.nccl.version(),
                                       "versions": {name: importlib.metadata.version(name) for name in
                                                    ("torch", "mjlab", "mujoco", "mujoco-warp", "warp-lang", "rsl-rl-lib", "tensordict")}})
    def create():
        directory.mkdir(parents=True, exist_ok=True)
        files = set(CONTRACT_FILES) | {str(path.relative_to(ROOT)).replace("\\", "/") for path in (ROOT/"training/mjlab_duck").glob("*.py")}
        hashes = {}
        for name in sorted(files):
            target = directory/"sources"/name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT/name, target)
            hashes[name] = sha_file(target)
        git_command = ["git", "status", "--short"]
        try:
            git = subprocess.run(git_command, cwd=ROOT, text=True, capture_output=True, timeout=15)
            git_status = git.stdout
            git_error = git.stderr if git.returncode else None
        except subprocess.TimeoutExpired:
            git_status = None
            git_error = "git status timed out after 15 seconds; explicit source snapshots are retained"
        except OSError as error:
            git_status = None
            git_error = f"git status unavailable: {error}"
        manifest = {"created_utc": datetime.now(timezone.utc).isoformat(), "command": sys.argv,
                    "git_status": git_status, "git_error": git_error, "git_command": git_command,
                    "source_sha256": hashes, "config": cfg.as_dict(), "contract": signature,
                    "check_mode": check_mode, "formal_policy_candidate": not check_mode,
                    "versions": {name: importlib.metadata.version(name) for name in ("torch", "mjlab", "mujoco", "rsl-rl-lib", "tensordict")},
                    "device": torch.cuda.get_device_name(), "tf32": False, "torch_cpu_threads": torch.get_num_threads(),
                    "is_finite_horizon": True, "init_at_random_ep_len": False,
                    "normalization": "rank-local actor and critic; evaluation uses rank0"}
        manifest["rank_records"] = rank_records
        atomic_json(directory/"run.json", manifest)
    coordinator.root_call(create)


def reserve_run_directory(output_dir, experiment_dir, coordinator):
    output_dir, experiment_dir = Path(output_dir).resolve(), Path(experiment_dir).resolve()
    if experiment_dir.is_relative_to(output_dir):
        raise ValueError("experiment ledger must be outside the per-run output directory")
    present = coordinator.gather(output_dir.exists())
    def reserve():
        if any(present):
            raise ValueError("run output directory already exists; resume requires a fresh output directory")
        output_dir.mkdir(parents=True, exist_ok=False)
    coordinator.root_call(reserve)


def train_loop(runner, env, cfg, *, output_dir, stage=1, start_iteration=0, parent_checkpoint=None,
               eval_callback=None, diagnostic_callback=None, gate_callback=None, max_new_updates=None,
               resume_manifest=None, experiment_dir=None, check_mode=False, coordinator=None,
               run_id=None, stop_file=None, warm_start_manifest=None, workflow=None):
    validate_workflow(workflow, cfg.as_dict())
    if resume_manifest and warm_start_manifest:
        raise ValueError("resume and warm start are mutually exclusive")
    coordinator = coordinator or RankCoordinator()
    run_started = time.perf_counter()
    output_dir = Path(output_dir)
    experiment_dir = Path(experiment_dir) if experiment_dir is not None else output_dir.with_name(output_dir.name+"-experiment")
    signature = contract(cfg, coordinator.world_size)
    if coordinator.world_size not in (1, 2):
        raise ValueError("supported execution topologies have one or two ranks")
    if max_new_updates is not None and max_new_updates < 1:
        raise ValueError("max_new_updates must be positive")
    reserve_run_directory(output_dir, experiment_dir, coordinator)
    runner.evaluation_trace_root = output_dir/"evaluation-traces"
    coordinator.root_call(lambda: atomic_json(output_dir/"workflow.json", workflow))
    events = RunEvents(output_dir, run_id or output_dir.name, coordinator.rank)
    events.emit("initializing")
    stop_file = Path(stop_file) if stop_file else output_dir/"STOP"
    lease = ExperimentLease(experiment_dir) if coordinator.rank == 0 else nullcontext()
    coordinator.root_call(lambda: lease.__enter__())
    writer = None
    last_manifest = None
    result = None
    try:
        experiment = coordinator.root_call(lambda: _prepare_experiment(experiment_dir, cfg, signature, resume_manifest, check_mode))
        ledger = BudgetLedger(experiment_dir/"budget.jsonl", cfg.global_transitions_per_update,
                              cfg.max_transitions, experiment["id"])
        state = TrainingState(stage=stage, model_iteration=start_iteration, parent_checkpoint=parent_checkpoint)
        consumed = coordinator.root_call(ledger.consumed)
        if resume_manifest:
            loaded = load_collective(runner, resume_manifest, coordinator, signature, experiment["id"])
            if consumed < loaded["consumed_transitions"]:
                raise ValueError("ledger would refund previously consumed transitions")
            state = TrainingState(**loaded["state"])
            state.parent_checkpoint = str(resume_manifest)
        elif start_iteration != 0 or parent_checkpoint:
            raise ValueError("continuation requires explicit manifest and original experiment ledger")
        initialization = None
        if warm_start_manifest:
            initialization = coordinator.all_call(lambda: initialize_actor(runner, warm_start_manifest, signature))
            coordinator.root_call(lambda: atomic_json(output_dir/"initialization.json", initialization))
        observations = _environment_stage(env, cfg, state.stage)
        runner.reward_completed_updates = consumed//cfg.global_transitions_per_update
        runner.reward_recipe = apply_reward_config(env, cfg.reward_config, state.stage, runner.reward_completed_updates)
        episodes = EpisodeAccumulator(env.num_envs, runner.device)
        episode_window = EpisodeWindow()
        runner.alg.storage.clear()
        runner.alg.train_mode()
        _run_manifest(output_dir, cfg, signature, coordinator, check_mode)
        logger = JsonlLogger(output_dir/"updates.jsonl") if coordinator.rank == 0 else None
        episode_logger = JsonlLogger(output_dir/f"episodes.rank{coordinator.rank}.jsonl")
        if coordinator.rank == 0:
            from torch.utils.tensorboard import SummaryWriter
            writer = SummaryWriter(str(output_dir/"tensorboard"))
        metadata = {"experiment_id": experiment["id"], "consumed_transitions": consumed,
                    "parent_checkpoint": state.parent_checkpoint, "check_mode": check_mode,
                    "initialization": initialization}
        events.emit("saving", model_iteration=state.model_iteration)
        last_manifest = save_collective(runner, cfg, asdict(state), metadata, output_dir/"checkpoints", coordinator, signature, "start")
        new_updates = 0
        previous_recipe = None
        status = "budget_exhausted"
        while consumed+cfg.global_transitions_per_update <= cfg.max_transitions:
            stop_flag = torch.tensor(int(STOP_REQUESTED or stop_file.exists()), device=runner.device, dtype=torch.int32)
            if coordinator.world_size > 1:
                distributed.all_reduce(stop_flag, op=distributed.ReduceOp.MAX)
            if stop_flag.item():
                status = "interrupted_at_update_boundary"
                events.emit("stopping", model_iteration=state.model_iteration)
                break
            if max_new_updates is not None and new_updates >= max_new_updates:
                status = "check_limit" if check_mode else "requested_update_limit"
                break
            runner.reward_completed_updates = consumed//cfg.global_transitions_per_update
            recipe = apply_reward_config(env, cfg.reward_config, state.stage, runner.reward_completed_updates)
            runner.reward_recipe = recipe
            if recipe != previous_recipe:
                events.emit("reward_recipe", model_iteration=state.model_iteration+1, stage=state.stage,
                            completed_budget_updates=runner.reward_completed_updates, recipe=recipe)
                previous_recipe = recipe
            reservation = coordinator.root_call(lambda: ledger.begin(state.model_iteration+1))
            consumed = coordinator.root_call(ledger.consumed)
            statistics = RolloutStatistics(runner.device)
            events.emit("training", model_iteration=state.model_iteration+1)
            torch.cuda.synchronize(runner.device)
            started = time.perf_counter()
            with torch.inference_mode():
                for _ in range(cfg.num_steps_per_env):
                    actions = runner.alg.act(observations)
                    coordinator.check(not bool(torch.isfinite(actions).all()), "non-finite policy action", runner.device)
                    observations, rewards, dones, extras = env.step(actions)
                    snapshot = extras.get("locomotion")
                    if snapshot is None:
                        raise RuntimeError("terminal snapshot missing")
                    finite = torch.isfinite(rewards).all() & torch.isfinite(observations["actor"]).all() & torch.isfinite(observations["critic"]).all()
                    invalid = (snapshot["reason"] == 4).any() | ~finite
                    premature = dones.bool() & ~snapshot["failed"].bool() & (snapshot["time"] < snapshot["duration"]-1e-4)
                    invalid |= premature.any() | (snapshot["time"] >= 150-1e-4).any()
                    coordinator.check(bool(invalid), "NaN/Inf or unexpected trajectory truncation", runner.device)
                    runner.alg.process_env_step(observations, rewards, dones, extras)
                    statistics.collect(snapshot, dones, actions, rewards, episodes.collect(rewards, dones))
                runner.alg.compute_returns(observations)
            torch.cuda.synchronize(runner.device)
            collected = time.perf_counter()
            losses = runner.alg.update()
            torch.cuda.synchronize(runner.device)
            updated = time.perf_counter()
            losses = {name: float(value) for name, value in losses.items()}
            finite_parameters = all(bool(torch.isfinite(parameter).all()) for model in (runner.alg.actor, runner.alg.critic) for parameter in model.parameters())
            coordinator.check(not finite_parameters or not all(math.isfinite(value) for value in losses.values()), "non-finite PPO update", runner.device)
            state.model_iteration += 1
            state.stage_updates += 1
            state.diagnostic_updates += 1
            new_updates += 1
            coordinator.root_call(lambda: ledger.complete(state.model_iteration, reservation))
            summary = statistics.summary()
            summary["collect_s"], summary["update_s"] = collected-started, updated-collected
            summaries = coordinator.gather(summary)
            global_stats = coordinator.root_call(lambda: merge_summaries(summaries))
            terminal_records = coordinator.gather(statistics.terminals)
            rolling_episodes = coordinator.root_call(lambda: episode_window.add(terminal_records))
            state.diagnostic_joint_samples += global_stats["joint_later_samples"]
            episode_logger.write_many([{**record, "model_iteration": state.model_iteration, "stage": state.stage,
                                        "rank": coordinator.rank, "run_id": run_id or output_dir.name,
                                        "utc": datetime.now(timezone.utc).isoformat()} for record in statistics.terminals])
            timing = coordinator.root_call(lambda: {"collect_s": max(item["collect_s"] for item in summaries),
                                                    "update_s": max(item["update_s"] for item in summaries)})
            elapsed = timing["collect_s"]+timing["update_s"]
            if coordinator.rank == 0:
                record = {"run_id": run_id or output_dir.name, "rank": 0, "seq": new_updates,
                          "utc": datetime.now(timezone.utc).isoformat(), "elapsed_s": time.perf_counter()-run_started,
                          "model_iteration": state.model_iteration, "stage": state.stage, "stage_updates": state.stage_updates,
                          "consumed_transitions": consumed, "remaining_transitions": cfg.max_transitions-consumed,
                          **timing, "transitions_per_s": cfg.global_transitions_per_update/elapsed,
                          "losses_rank0": losses, "learning_rate": float(runner.alg.learning_rate),
                          "action_std_rank0": runner.alg.get_policy().output_std.detach().mean().item(),
                          "torch_peak_bytes": torch.cuda.max_memory_allocated(runner.device),
                          "memory_scope": "PyTorch only; excludes Warp", "kl": None, "kl_status": "not_exposed_by_library",
                          "statistics": global_stats, "episodes": rolling_episodes,
                          "reward_recipe": {"stage": state.stage, "completed_budget_updates": runner.reward_completed_updates,
                                            "hash": sha_dict(recipe), "smoothing": recipe["smoothing"]},
                          "sampling_transitions_per_s": cfg.global_transitions_per_update/max(timing["collect_s"], 1e-9),
                          "overall_transitions_per_s": new_updates*cfg.global_transitions_per_update/max(time.perf_counter()-run_started, 1e-9)}
                logger.write(record)
                for name, value in losses.items():
                    writer.add_scalar(f"loss/{name}", value, consumed)
                writer.add_scalar("training/transitions_per_s", record["transitions_per_s"], consumed)
                writer.add_scalar("training/lr", record["learning_rate"], consumed)
                print(json.dumps({key: record[key] for key in ("model_iteration", "stage", "consumed_transitions", "transitions_per_s")}), flush=True)
            decision = "continue"
            if state.diagnostic_updates >= cfg.diagnostic_interval:
                pause = state.record_diagnostic(state.diagnostic_joint_samples)
                diagnostic = {"stage": state.stage, "stage_updates": state.stage_updates,
                              "joint_later_samples": state.diagnostic_joint_samples, "empty_windows": state.empty_windows,
                              "pause": pause}
                if coordinator.rank == 0:
                    JsonlLogger(output_dir/"diagnostics.jsonl").write(diagnostic)
                if diagnostic_callback is not None:
                    coordinator.root_call(lambda: diagnostic_callback(runner, state.stage, state.model_iteration))
                state.diagnostic_joint_samples = 0
                state.diagnostic_updates = 0
                if pause:
                    decision = "pause_coverage"
            metadata.update(consumed_transitions=consumed, parent_checkpoint=state.parent_checkpoint)
            save_due = state.model_iteration % cfg.save_interval == 0
            eval_due = state.model_iteration % cfg.eval_interval == 0 and (not check_mode or eval_callback is not None)
            if save_due or eval_due:
                events.emit("saving", model_iteration=state.model_iteration)
                last_manifest = save_collective(runner, cfg, asdict(state), metadata, output_dir/"checkpoints", coordinator, signature)
                if eval_due:
                    events.emit("evaluating", model_iteration=state.model_iteration, checkpoint=last_manifest)
                    evaluation = coordinator.root_call(lambda: _suite_record(eval_callback(runner, state.stage, state.model_iteration)) if eval_callback else evaluate_policy(runner, state.stage))
                    if evaluation.get("straight_total") != 9:
                        raise ValueError("straight regression suite must contain exactly nine complete scenarios")
                    evaluation_decision = state.record_evaluation(state.model_iteration, last_manifest,
                                                                  evaluation["straight_passed"], evaluation["passed_count"],
                                                                  evaluation["total"], cfg.eval_interval)
                    coordinator.root_call(lambda: atomic_json(output_dir/f"evaluation_{state.model_iteration:06d}.json",
                                                              {"checkpoint": last_manifest, "model_iteration": state.model_iteration,
                                                               "stage": state.stage, "suite": f"dev{evaluation['total']}",
                                                               "utc": datetime.now(timezone.utc).isoformat(), **evaluation}))
                    if decision == "continue":
                        decision = evaluation_decision
                    if gate_callback is not None:
                        keep = coordinator.root_call(lambda: gate_callback(state.stage, state.stage1_streak, evaluation))
                        if not keep:
                            decision = "pause_callback"
                    events.emit("saving", model_iteration=state.model_iteration)
                    metadata["pending_decision"] = decision if decision != "continue" else None
                    last_manifest = save_collective(runner, cfg, asdict(state), metadata, output_dir/"checkpoints", coordinator, signature, "evaluated")
                    metadata.pop("pending_decision", None)
            if decision == "full_reference":
                final = coordinator.root_call(lambda: evaluate_policy(runner, state.stage, full=True))
                coordinator.root_call(lambda: atomic_json(output_dir/f"full96_{state.model_iteration:06d}.json",
                                                          {"checkpoint": last_manifest, **final}))
                decision = "accepted" if final["total"] == 96 and final["passed_count"] == 96 else "continue"
            if decision == "stage2":
                state.enter_stage2(last_manifest)
                runner.alg.storage.clear()
                observations = _environment_stage(env, cfg, state.stage)
                runner.reward_completed_updates = consumed//cfg.global_transitions_per_update
                runner.reward_recipe = apply_reward_config(env, cfg.reward_config, state.stage, runner.reward_completed_updates)
                episodes = EpisodeAccumulator(env.num_envs, runner.device)
                metadata["parent_checkpoint"] = state.parent_checkpoint
                last_manifest = save_collective(runner, cfg, asdict(state), metadata, output_dir/"checkpoints", coordinator, signature, "stage2")
            elif decision.startswith("pause") or decision == "accepted":
                status = decision
                break
            stop_flag = torch.tensor(int(STOP_REQUESTED or stop_file.exists()), device=runner.device, dtype=torch.int32)
            if coordinator.world_size > 1:
                distributed.all_reduce(stop_flag, op=distributed.ReduceOp.MAX)
            if stop_flag.item():
                status = "interrupted_at_update_boundary"
                events.emit("stopping", model_iteration=state.model_iteration)
                break
        metadata.update(consumed_transitions=consumed, parent_checkpoint=state.parent_checkpoint)
        events.emit("saving", model_iteration=state.model_iteration)
        last_manifest = save_collective(runner, cfg, asdict(state), metadata, output_dir/"checkpoints", coordinator, signature, "final")
        result = {"updates": new_updates, "consumed_transitions": consumed, "stage": state.stage,
                  "model_iteration": state.model_iteration, "max_transitions": cfg.max_transitions,
                  "checkpoint_manifest": last_manifest, "status": status, "check_mode": check_mode,
                  "wall_seconds_including_evaluation_and_checkpoint": time.perf_counter()-run_started,
                  "node_hours_including_evaluation_and_checkpoint": (time.perf_counter()-run_started)*coordinator.world_size/3600}
        coordinator.root_call(lambda: atomic_json(output_dir/"result.json", result))
        events.emit("stopped" if status == "interrupted_at_update_boundary" else "completed", **result)
        return result
    except BaseException as error:
        events.emit("failed", error=f"{type(error).__name__}: {error}")
        if coordinator.rank == 0:
            atomic_json(output_dir/"failure.json", {"error": f"{type(error).__name__}: {error}",
                                                   "last_complete_checkpoint": last_manifest,
                                                   "budget_policy": "all durable begin reservations remain spent"})
        raise
    finally:
        events.close()
        if writer is not None:
            writer.close()
        if coordinator.rank == 0:
            lease.__exit__(None, None, None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--experiment-dir", type=Path)
    parser.add_argument("--resume-manifest", type=Path)
    parser.add_argument("--warm-start-manifest", "--initialize-manifest", dest="warm_start_manifest", type=Path)
    parser.add_argument("--workflow-record", type=Path)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--stop-file", type=Path)
    parser.add_argument("--print-config", action="store_true")
    parser.add_argument("--check-mode", action="store_true")
    parser.add_argument("--check-envs", type=int, default=4)
    parser.add_argument("--check-budget-updates", type=int, default=4)
    parser.add_argument("--max-new-updates", type=int)
    parser.add_argument("--control-timeout-s", type=int, default=3600)
    args = parser.parse_args()
    cfg = LocomotionTrainConfig.from_dict(json.loads(args.config.read_text(encoding="utf-8"))) if args.config else (
        LocomotionTrainConfig(num_envs=args.check_envs, max_updates=args.check_budget_updates) if args.check_mode else LocomotionTrainConfig())
    if args.print_config:
        print(json.dumps({"training": cfg.as_dict(), "ppo": ppo_config(cfg)}, indent=2))
        return
    if int(os.getenv("WORLD_SIZE", "1")) not in (1, 2):
        raise ValueError("training requires one or two ranks")
    if args.workflow_record is None:
        parser.error("training requires --workflow-record with validated steps, config hash and budget")
    workflow = json.loads(args.workflow_record.read_text(encoding="utf-8-sig"))
    if args.output.exists():
        raise ValueError("run output directory already exists; use a new output directory")
    if args.resume_manifest and args.warm_start_manifest:
        parser.error("resume and warm start are mutually exclusive")
    if int(os.getenv("RANK", "0")) == 0:
        register_runtime(args.output, workflow, cfg.as_dict(), run_id=args.run_id, source_root=ROOT,
                         initialization="resume" if args.resume_manifest else "warm" if args.warm_start_manifest else "scratch")
    else:
        validate_workflow(workflow, cfg.as_dict())
    rank = int(os.getenv("RANK", "0"))
    startup_directory = args.output.with_name(args.output.name+"-startup")
    freeze_startup(startup_directory, cfg, workflow, rank)
    console_log = (startup_directory/f"console.rank{rank}.log").open("a", encoding="utf-8")
    original_stdout, original_stderr = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = ConsoleCopy(sys.stdout, console_log), ConsoleCopy(sys.stderr, console_log)
    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)
    startup = RunEvents(startup_directory, args.run_id or args.output.name, rank)
    startup.emit("initializing")
    try:
        runner, env, coordinator = build_runtime(cfg, control_timeout_s=args.control_timeout_s)
    except BaseException as error:
        startup.emit("failed", error=f"{type(error).__name__}: {error}")
        import traceback
        traceback.print_exc()
        sys.stdout, sys.stderr = original_stdout, original_stderr
        console_log.close()
        raise
    finally:
        startup.close()
    try:
        train_loop(runner, env, cfg, output_dir=args.output, experiment_dir=args.experiment_dir,
                   resume_manifest=args.resume_manifest, max_new_updates=args.max_new_updates,
                   check_mode=args.check_mode, coordinator=coordinator, run_id=args.run_id, stop_file=args.stop_file,
                   warm_start_manifest=args.warm_start_manifest, workflow=workflow)
    finally:
        env.close()
        if distributed.is_initialized():
            distributed.destroy_process_group()
        sys.stdout, sys.stderr = original_stdout, original_stderr
        console_log.close()


if __name__ == "__main__":
    main()
