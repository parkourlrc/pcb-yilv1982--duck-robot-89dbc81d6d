"""第④步必要合同、恢复和短程 PPO 检查；不验证策略行为达标。"""
from __future__ import annotations

import argparse
import copy
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import torch

from mjlab_duck.locomotion_train_cfg import LocomotionTrainConfig, STAGE1, STAGE2, ppo_config

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "docs/specs/20261105-原地转圈策略/checks/training-check.json"


def assert_rejected(callback, message):
    try:
        callback()
    except (ValueError, RuntimeError, KeyError):
        return
    raise AssertionError(message)


def nested_equal(expected, actual):
    if isinstance(expected, torch.Tensor):
        return isinstance(actual, torch.Tensor) and torch.equal(expected.cpu(), actual.cpu())
    if isinstance(expected, dict):
        return isinstance(actual, dict) and expected.keys() == actual.keys() and all(nested_equal(value, actual[key]) for key, value in expected.items())
    if isinstance(expected, (list, tuple)):
        return isinstance(actual, (list, tuple)) and len(expected) == len(actual) and all(nested_equal(left, right) for left, right in zip(expected, actual))
    return expected == actual


def checks():
    from mjlab_duck.locomotion_env import curriculum_scenario_segments
    from mjlab_duck.locomotion_evaluator import development_scenarios, full_reference_scenarios
    from mjlab_duck.locomotion_checkpoint import BudgetLedger, atomic_json, sha_dict, sha_file, validate_manifest, write_manifest
    from mjlab_duck.train_locomotion import TrainingState, reserve_run_directory
    from mjlab_duck.locomotion_checkpoint import RankCoordinator

    cfg = LocomotionTrainConfig()
    assert cfg.global_transitions_per_update == 262144 and cfg.max_transitions == 262144000
    assert STAGE1.probabilities == (0., 1., 0., 0., 0.)
    assert STAGE2.probabilities == (.20, .30, .30, .15, .05)
    assert len(development_scenarios(1)) == 9 and len(development_scenarios(2)) == 22
    assert len(full_reference_scenarios()) == 96
    assert sum(segment[0] for segment in curriculum_scenario_segments(2, 3, .1, .5)) == 133
    ppo = ppo_config(cfg)
    assert ppo["obs_groups"] == {"actor": ("actor",), "critic": ("critic",)}
    assert ppo["actor"]["obs_normalization"] and ppo["critic"]["obs_normalization"]
    assert ppo["actor"]["distribution_cfg"] == {"class_name": "GaussianDistribution", "init_std": .30, "std_type": "log"}
    assert ppo["algorithm"]["normalize_advantage_per_mini_batch"] is False
    assert ppo["is_finite_horizon"] and ppo["clip_actions"] is None
    gate = TrainingState()
    assert gate.record_evaluation(100, "first", 9, 9, 9, 100) == "continue"
    assert_rejected(lambda: gate.record_evaluation(100, "first", 9, 9, 9, 100), "same checkpoint counted twice")
    assert gate.record_evaluation(200, "second", 9, 9, 9, 100) == "stage2"
    regression = TrainingState(stage=2)
    assert regression.record_evaluation(300, "third", 8, 20, 22, 100) == "continue"
    assert regression.record_evaluation(400, "fourth", 8, 20, 22, 100) == "pause_regression"
    coverage = TrainingState(stage=2)
    assert not coverage.record_diagnostic(0)
    assert coverage.record_diagnostic(0)
    recovered = TrainingState(stage=2)
    assert not recovered.record_diagnostic(0)
    assert not recovered.record_diagnostic(5)
    assert not recovered.record_diagnostic(0)
    with tempfile.TemporaryDirectory(prefix="duck-contract-") as temporary:
        directory = Path(temporary)
        existing_run = directory / "previous-run"
        existing_run.mkdir()
        marker = existing_run / "run.json"
        marker.write_text('{"previous_run":true}\n', encoding="utf-8")
        previous_bytes = marker.read_bytes()
        assert_rejected(lambda: reserve_run_directory(existing_run, directory / "experiment", RankCoordinator()), "existing run directory accepted")
        assert marker.read_bytes() == previous_bytes
        assert_rejected(lambda: reserve_run_directory(directory / "new-run", directory / "new-run/experiment", RankCoordinator()), "nested experiment accepted")
        ledger = BudgetLedger(directory / "budget.jsonl", 128, 384, "contract-check")
        first = ledger.begin(1)
        ledger.complete(1, first)
        ledger.begin(2)
        assert ledger.consumed() == 256
        ledger.begin(1)
        assert ledger.consumed() == 384
        assert_rejected(lambda: ledger.begin(2), "rollback refunded the budget")
        with ledger.path.open("ab") as stream:
            stream.write(b'{"event":')
        assert_rejected(ledger.consumed, "torn ledger silently dropped reserved work")
        signature = {"schema": 1, "test": "two ranks"}
        payloads = [{"schema": 1, "rank": rank, "world_size": 2, "iter": 7, "stage": 1,
                     "state": {"model_iteration": 7, "stage": 1}, "contract": signature,
                     "config_hash": sha_dict(signature), "consumed_transitions": 512,
                     "experiment_id": "contract-check", "rank_local_stat": torch.tensor([float(rank)])}
                    for rank in (0, 1)]
        assert_rejected(lambda: write_manifest(directory, payloads[:1]), "missing rank accepted")
        mixed = copy.deepcopy(payloads)
        mixed[1]["iter"] = 6
        assert_rejected(lambda: write_manifest(directory, mixed), "mixed iterations accepted")
        manifest_path = Path(write_manifest(directory, payloads))
        manifest = validate_manifest(manifest_path, expected_world_size=2)
        assert_rejected(lambda: validate_manifest(manifest_path, expected_world_size=1), "changed world size accepted")
        absent = copy.deepcopy(manifest)
        absent["rank_files"].pop("1")
        atomic_json(manifest_path, absent)
        assert_rejected(lambda: validate_manifest(manifest_path), "missing manifest rank accepted")
        atomic_json(manifest_path, manifest)
        rank_file = manifest_path.parent / manifest["rank_files"]["1"]["path"]
        altered = torch.load(rank_file, map_location="cpu", weights_only=False)
        altered["iter"] -= 1
        torch.save(altered, rank_file)
        assert_rejected(lambda: validate_manifest(manifest_path), "hash corruption accepted")
        manifest["rank_files"]["1"]["sha256"] = sha_file(rank_file)
        atomic_json(manifest_path, manifest)
        assert_rejected(lambda: validate_manifest(manifest_path), "mixed payload iteration accepted after digest update")
    return {"configuration": True, "curriculum_scenarios": True, "evaluation_counts": {"dev1": 9, "dev2": 22, "full": 96},
            "gate_distinct_checkpoints": True, "regression_pause": True, "coverage_pause": True,
            "rollback_and_pending_budget": True, "torn_ledger_rejected": True,
            "existing_output_and_nested_experiment_rejected": True,
            "manifest_missing_rank_hash_mixed_iteration_rejected": True}


class TinyAlgorithm:
    def __init__(self, rank):
        self.actor = torch.nn.Linear(3, 2)
        self.actor.register_buffer("rank_normalizer", torch.tensor([float(rank)]))
        self.critic = torch.nn.Linear(3, 1)
        self.learning_rate = .0001 * (rank + 1)
        self.optimizer = torch.optim.Adam(list(self.actor.parameters()) + list(self.critic.parameters()), lr=self.learning_rate)
        self.storage = SimpleNamespace(clear=lambda: None)
        loss = self.actor(torch.ones(1, 3)).square().sum() + self.critic(torch.ones(1, 3)).square().sum()
        loss.backward()
        self.optimizer.step()

    def save(self):
        return {"actor_state_dict": self.actor.state_dict(), "critic_state_dict": self.critic.state_dict(),
                "optimizer_state_dict": self.optimizer.state_dict()}

    def load(self, payload, load_cfg, strict):
        self.actor.load_state_dict(payload["actor_state_dict"], strict=strict)
        self.critic.load_state_dict(payload["critic_state_dict"], strict=strict)
        self.optimizer.load_state_dict(payload["optimizer_state_dict"])


def collective_worker(rank, directory, rendezvous):
    import torch.distributed as distributed
    from mjlab_duck.locomotion_checkpoint import RankCoordinator, cpu_copy, load_collective, save_collective

    torch.set_num_threads(1)
    distributed.init_process_group("gloo", init_method=rendezvous, rank=rank, world_size=2,
                                   timeout=timedelta(seconds=60))
    try:
        coordinator = RankCoordinator()
        runner = SimpleNamespace(alg=TinyAlgorithm(rank), current_learning_iteration=0)
        before = cpu_copy(runner.alg.save())
        cfg = LocomotionTrainConfig(num_envs=4, max_updates=3)
        signature = {"schema": 1, "world_size": 2, "name": "cpu_transport_test"}
        state = {"model_iteration": 2, "stage": 1, "gate_streak": 1}
        metadata = {"consumed_transitions": 512, "experiment_id": "gloo-check", "parent_checkpoint": None}
        local_directory = Path(directory) / f"rank{rank}"
        local_directory.mkdir()
        manifest = save_collective(runner, cfg, state, metadata, local_directory, coordinator, signature)
        fresh = SimpleNamespace(alg=TinyAlgorithm(rank + 10), current_learning_iteration=0)
        explicit_path = manifest if rank == 0 else str(local_directory / "manifest-not-on-this-node.json")
        restored = load_collective(fresh, explicit_path, coordinator, signature, "gloo-check")
        assert nested_equal(before, fresh.alg.save())
        assert fresh.alg.learning_rate == runner.alg.learning_rate
        assert restored["state"] == state and restored["consumed_transitions"] == 512
        assert float(fresh.alg.actor.rank_normalizer) == rank
        if rank == 1:
            assert not list(local_directory.rglob("*.pt"))
        mismatched_signature = {**signature, "rank1_mismatch": True} if rank == 1 else signature
        assert_rejected(lambda: load_collective(fresh, explicit_path, coordinator, mismatched_signature, "gloo-check"),
                        "one-rank contract error did not reject all ranks")
        original_load = fresh.alg.load
        def reject_load(*args, **kwargs):
            raise RuntimeError("synthetic rank1 restoration failure")
        if rank == 1:
            fresh.alg.load = reject_load
        try:
            assert_rejected(lambda: load_collective(fresh, explicit_path, coordinator, signature, "gloo-check"),
                            "one-rank restore error did not reject all ranks")
        finally:
            fresh.alg.load = original_load
        previous_lr = fresh.alg.learning_rate
        if rank == 1:
            fresh.alg.learning_rate = float("nan")
        try:
            assert_rejected(lambda: save_collective(fresh, cfg, state, metadata, local_directory, coordinator, signature),
                            "one-rank payload error did not reject all ranks")
        finally:
            fresh.alg.learning_rate = previous_lr
        (local_directory / "result.json").write_text(json.dumps({"rank": rank, "restored": True,
                                                                 "rank_local_normalizer": float(fresh.alg.actor.rank_normalizer),
                                                                 "consumed_transitions": restored["consumed_transitions"],
                                                                 "synchronized_rejections": ["rank1_contract_mismatch", "rank1_restore_failure", "rank1_payload_failure"]}), encoding="utf-8")
    finally:
        distributed.destroy_process_group()


def collective_check(directory):
    import torch.multiprocessing as multiprocessing

    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    previous_cuda = os.environ.get("CUDA_VISIBLE_DEVICES")
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    try:
        with tempfile.TemporaryDirectory(prefix="duck-gloo-") as rendezvous_root:
            rendezvous = "file://" + str(Path(rendezvous_root) / "rendezvous")
            multiprocessing.spawn(collective_worker, args=(str(directory), rendezvous), nprocs=2, join=True)
    finally:
        if previous_cuda is None:
            os.environ.pop("CUDA_VISIBLE_DEVICES", None)
        else:
            os.environ["CUDA_VISIBLE_DEVICES"] = previous_cuda
    records = [json.loads((directory / f"rank{rank}/result.json").read_text(encoding="utf-8")) for rank in (0, 1)]
    return {"transport": "cpu_gloo", "world_size": 2, "physical_spark_validation": False,
            "independent_rank_directories": True, "rank_records": records}


def evaluator_smoke(runner):
    from mjlab.envs import ManagerBasedRlEnv
    from tensordict import TensorDict
    from mjlab_duck.locomotion_cfg import locomotion_env_cfg
    from mjlab_duck.locomotion_checkpoint import cpu_copy, rng_state, restore_rng
    from mjlab_duck.locomotion_evaluator import development_scenarios, evaluate_episode

    previous_rng = rng_state()
    modes = (runner.alg.actor.training, runner.alg.critic.training)
    before = [cpu_copy(model.obs_normalizer.state_dict()) for model in (runner.alg.actor, runner.alg.critic)]
    runner.alg.eval_mode()
    try:
        def policy(observations):
            values = TensorDict(observations, batch_size=[1]).to(runner.device)
            return runner.alg.get_policy()(values, stochastic_output=False)

        def factory(scenario):
            configuration = locomotion_env_cfg(1, evaluation=True, seed=scenario.seed)
            configuration.is_finite_horizon = True
            return ManagerBasedRlEnv(configuration, device=runner.device)

        scenario = development_scenarios(1)[0]
        with torch.inference_mode():
            report = evaluate_episode(policy, scenario, factory)
        assert report.checks["trace_fields"]["passed"] and report.checks["trace_shape"]["passed"]
        assert report.observed["controls"] > 0
        after = [cpu_copy(model.obs_normalizer.state_dict()) for model in (runner.alg.actor, runner.alg.critic)]
        assert nested_equal(before, after)
        return {"scope": "one_real_episode_pipeline_not_behavior_gate", "normalizers_frozen": True,
                "trace_shape_valid": True, "episode": asdict(report)}
    finally:
        runner.alg.actor.train(modes[0])
        runner.alg.critic.train(modes[1])
        restore_rng(previous_rng)


def course_smoke(run_root, world_size):
    from mjlab_duck.locomotion_checkpoint import cpu_copy
    from mjlab_duck.train_locomotion import build_runtime, train_loop

    cfg = LocomotionTrainConfig(num_envs=max(4, world_size * 2), max_updates=3, save_interval=1)
    runner, env, coordinator = build_runtime(cfg)
    evidence = {"home_boundary": False, "optimizer_inherited": False, "stage2_updates": 0}
    original_act, original_update = runner.alg.act, runner.alg.update
    saved_optimizer = None
    completed_updates = 0
    try:
        def checked_act(observations):
            command = env.unwrapped.command_manager.get_term("velocity")
            if command.stage == 2 and not evidence["home_boundary"]:
                state = env.unwrapped.locomotion
                action = env.unwrapped.action_manager.get_term("joints")
                assert not state.time.any() and not state.window_count.any() and not env.episode_length_buf.any()
                assert not state.cmd.any() and not action.raw.any() and not action.actual.any() and not action.previous.any()
                assert tuple(command.probabilities) == STAGE2.probabilities
                assert saved_optimizer is not None and nested_equal(saved_optimizer, cpu_copy(runner.alg.optimizer.state_dict()))
                evidence["home_boundary"] = True
                evidence["optimizer_inherited"] = True
            return original_act(observations)

        def checked_update():
            nonlocal saved_optimizer, completed_updates
            losses = original_update()
            completed_updates += 1
            if completed_updates == 2:
                saved_optimizer = cpu_copy(runner.alg.optimizer.state_dict())
            if env.unwrapped.command_manager.get_term("velocity").stage == 2:
                evidence["stage2_updates"] += 1
            return losses

        def synthetic_report(active_runner, stage, iteration):
            if stage == 1:
                return {"straight_total": 9, "straight_passed": 9, "total": 9, "passed_count": 9, "passed": True,
                        "scope": "synthetic_gate_input_not_behavior_acceptance"}
            return {"straight_total": 9, "straight_passed": 8, "total": 22, "passed_count": 20, "passed": False,
                    "scope": "synthetic_gate_input_not_behavior_acceptance"}

        runner.alg.act = checked_act
        runner.alg.update = checked_update
        result = train_loop(runner, env, cfg, output_dir=run_root / "course", experiment_dir=run_root / "course-experiment",
                            eval_callback=synthetic_report, max_new_updates=3, check_mode=True, coordinator=coordinator)
        assert result["stage"] == 2 and result["updates"] == 3 and evidence["stage2_updates"] == 1
        assert evidence["home_boundary"] and evidence["optimizer_inherited"]
        records = coordinator.gather({"rank": coordinator.rank, **evidence})
        return coordinator.broadcast({"scope": "real_stage_switch_with_synthetic_pass_reports", "behavior_acceptance": "not_run",
                                      "rank_records": records, "result": result} if coordinator.rank == 0 else None)
    finally:
        env.close()


def runtime_check(output, num_envs=64, updates=2):
    import torch.distributed as distributed
    from mjlab_duck.locomotion_checkpoint import cpu_copy, load_collective, contract
    from mjlab_duck.train_locomotion import build_runtime, train_loop

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required for --runtime")
    if updates < 2:
        raise ValueError("at least two updates are required to check continuity")
    cfg = LocomotionTrainConfig(num_envs=num_envs, max_updates=updates + 2, save_interval=100)
    runner = env = coordinator = None
    run_root = Path(output).parent / (Path(output).stem + "-artifacts")
    experiment_dir = run_root / "experiment"
    try:
        runner, env, coordinator = build_runtime(cfg)
        initial_parameters = cpu_copy(runner.alg.actor.state_dict())
        original_update = runner.alg.update
        original_act = runner.alg.act
        boundary = {"state": None, "checked": 0}

        def environment_history():
            motion = env.unwrapped.locomotion
            action = env.unwrapped.action_manager.get_term("joints")
            return {"time": motion.time.clone(), "command": motion.cmd.clone(), "filter": motion.window.clone(),
                    "raw_action": action.raw.clone(), "actual_action": action.actual.clone()}

        def checked_update():
            before_update = environment_history()
            losses = original_update()
            assert nested_equal(before_update, environment_history())
            boundary["state"] = before_update
            return losses

        def checked_act(observations):
            if boundary["state"] is not None:
                assert nested_equal(boundary["state"], environment_history())
                boundary["checked"] += 1
                boundary["state"] = None
            return original_act(observations)

        runner.alg.update = checked_update
        runner.alg.act = checked_act
        first = train_loop(runner, env, cfg, output_dir=run_root / "initial", experiment_dir=experiment_dir,
                           max_new_updates=updates, check_mode=True, coordinator=coordinator)
        assert first["updates"] == updates
        assert boundary["checked"] == updates - 1
        saved_algorithm = cpu_copy(runner.alg.save())
        assert not nested_equal(initial_parameters, saved_algorithm["actor_state_dict"])
        for model in (runner.alg.actor, runner.alg.critic):
            assert all(torch.isfinite(parameter).all() for parameter in model.parameters())
        probe = env.get_observations().clone()
        runner.alg.eval_mode()
        with torch.inference_mode():
            expected_action = runner.alg.get_policy()(probe).detach().clone()
        expected_lr = runner.alg.learning_rate
        env.close()
        env = None
        fresh, env, coordinator = build_runtime(cfg)
        experiment = coordinator.root_call(lambda: json.loads((experiment_dir / "experiment.json").read_text(encoding="utf-8")))
        restored = load_collective(fresh, first["checkpoint_manifest"], coordinator, contract(cfg, coordinator.world_size), experiment["id"])
        assert nested_equal(saved_algorithm, cpu_copy(fresh.alg.save()))
        assert expected_lr == fresh.alg.learning_rate
        fresh.alg.eval_mode()
        with torch.inference_mode():
            restored_action = fresh.alg.get_policy()(probe)
        assert torch.equal(expected_action, restored_action)
        assert restored["consumed_transitions"] == updates * cfg.global_transitions_per_update
        second = train_loop(fresh, env, cfg, output_dir=run_root / "resumed", experiment_dir=experiment_dir,
                            max_new_updates=1, resume_manifest=first["checkpoint_manifest"], check_mode=True, coordinator=coordinator)
        assert second["updates"] == 1 and second["model_iteration"] == updates + 1
        assert second["consumed_transitions"] == (updates + 1) * cfg.global_transitions_per_update
        preserved = coordinator.root_call(lambda: {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                                                   for path in (run_root / "initial/run.json", run_root / "initial/updates.jsonl", experiment_dir / "budget.jsonl")})
        assert_rejected(lambda: train_loop(fresh, env, cfg, output_dir=run_root / "initial", experiment_dir=experiment_dir,
                                          max_new_updates=1, resume_manifest=first["checkpoint_manifest"], check_mode=True,
                                          coordinator=coordinator), "resume overwrote a previous output directory")
        unchanged = coordinator.root_call(lambda: {path: hashlib.sha256(Path(path).read_bytes()).hexdigest() for path in preserved})
        assert preserved == unchanged
        evaluation = coordinator.root_call(lambda: evaluator_smoke(fresh))
        local_record = {"rank": coordinator.rank, "world_size": coordinator.world_size,
                        "device": torch.cuda.get_device_name(), "local_envs": env.num_envs,
                        "parameter_change": True, "parameters_finite": True,
                        "rollout_boundaries_preserve_environment_history": boundary["checked"],
                        "new_runner_actor_critic_normalizer_optimizer_equal": True,
                        "adaptive_lr_equal": True, "deterministic_action_equal": True,
                        "same_output_resume_rejected_without_mutation": True,
                        "resume_updates": 1, "first": first, "resumed": second}
        records = coordinator.gather(local_record)
        result = coordinator.broadcast({"rank_records": records, "scope": "short_runtime_and_restore_not_behavior_acceptance"} if coordinator.rank == 0 else None)
        result["evaluator_pipeline"] = evaluation
        env.close()
        env = None
        result["stage_transition"] = course_smoke(run_root, coordinator.world_size)
        return result
    finally:
        if env is not None:
            env.close()
        if distributed.is_initialized():
            distributed.destroy_process_group()


def provenance():
    paths = [Path("training/mjlab_duck") / name for name in ("locomotion_env.py", "locomotion_cfg.py", "locomotion_evaluator.py", "locomotion_train_cfg.py", "locomotion_checkpoint.py", "locomotion_logging.py", "train_locomotion.py")]
    paths += [Path("training/scripts/check_locomotion_training.py"), Path("training/models/duck_v0.xml"), Path("training/params/home_pose.json")]
    return {"utc_time": datetime.now(timezone.utc).isoformat(), "command": sys.argv, "python": sys.version,
            "versions": {name: importlib.metadata.version(name) for name in ("torch", "mjlab", "rsl-rl-lib", "mujoco", "mujoco-warp", "warp-lang", "tensordict")},
            "sha256": {path.as_posix(): hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in paths}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--runtime", action="store_true")
    parser.add_argument("--collective", action="store_true")
    parser.add_argument("--num-envs", type=int, default=64)
    parser.add_argument("--updates", type=int, default=2)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result = {"scope": "step4_integration_not_policy_acceptance", "behavior_acceptance": "not_run", **provenance()}
    result["cpu"] = checks()
    if args.collective:
        if int(os.getenv("WORLD_SIZE", "1")) > 1:
            raise ValueError("--collective spawns its own CPU workers; do not nest inside torchrun")
        result["collective"] = collective_check(args.output.parent / (args.output.stem + "-collective"))
    if args.runtime:
        result["runtime"] = runtime_check(args.output, args.num_envs, args.updates)
    if int(os.getenv("RANK", "0")) == 0:
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
