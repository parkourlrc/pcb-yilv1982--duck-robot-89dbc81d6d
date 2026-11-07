"""一致检查点与不会因回退返还额度的实验账本。"""
from __future__ import annotations

import hashlib
import json
import math
import os
import random
import socket
import uuid
from pathlib import Path

import numpy as np
import torch
import torch.distributed as distributed

ROOT = Path(__file__).resolve().parents[2]
CONTRACT_FILES = (
    "training/models/duck_v0.xml", "training/params/home_pose.json",
    "training/mjlab_duck/locomotion_env.py", "training/mjlab_duck/locomotion_cfg.py",
    "training/mjlab_duck/locomotion_train_cfg.py", "training/mjlab_duck/locomotion_evaluator.py",
    "training/mjlab_duck/train_locomotion.py", "training/mjlab_duck/locomotion_logging.py",
    "training/mjlab_duck/locomotion_checkpoint.py",
)


def sha_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sha_dict(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def sync_directory(path):
    if hasattr(os, "O_DIRECTORY"):
        descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def contract(cfg, world_size):
    return {"schema": 1, "config": cfg.as_dict(), "world_size": world_size,
            "sources": {name: sha_file(ROOT/name) for name in CONTRACT_FILES},
            "observation": "61:omega3,gravity3,q14,dq14,raw_previous_action14,command3,reserved10",
            "action": "14:HOME+0.5*clip(raw,-1,1),joint_limits", "normalization": "rank_local",
            "finite_horizon": True, "restart": "HOME_new_episode"}


def atomic_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name+f".{uuid.uuid4().hex}.tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    sync_directory(path.parent)


def atomic_torch(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name+f".{uuid.uuid4().hex}.tmp")
    with temporary.open("wb") as stream:
        torch.save(data, stream)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    sync_directory(path.parent)


def cpu_copy(value):
    if isinstance(value, torch.Tensor):
        return value.detach().cpu().clone()
    if isinstance(value, dict):
        return {key: cpu_copy(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return tuple(cpu_copy(item) for item in value)
    if isinstance(value, list):
        return [cpu_copy(item) for item in value]
    return value


def rng_state():
    return {"torch": torch.get_rng_state(), "python": random.getstate(), "numpy": np.random.get_state(),
            "cuda": torch.cuda.get_rng_state_all() if torch.cuda.is_available() else []}


def restore_rng(state):
    torch.set_rng_state(state["torch"].cpu())
    random.setstate(state["python"])
    np.random.set_state(state["numpy"])
    if state["cuda"] and torch.cuda.is_available():
        torch.cuda.set_rng_state_all([value.cpu() for value in state["cuda"]])


class BudgetLedger:
    """Only rank zero writes this experiment-level, fsync-backed reservation log."""
    def __init__(self, path, transitions_per_update, max_transitions=None, experiment_id=None):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.transitions_per_update = transitions_per_update
        self.max_transitions = max_transitions
        self.experiment_id = experiment_id

    def entries(self):
        if not self.path.exists():
            return []
        raw = self.path.read_bytes()
        if raw and not raw.endswith(b"\n"):
            raise ValueError("torn budget ledger; refuse to refund unknown reserved work")
        result = [json.loads(line) for line in raw.decode("utf-8").splitlines()]
        for item in result:
            if item["event"] not in ("begin", "complete") or item["transitions"] != self.transitions_per_update:
                raise ValueError("invalid budget ledger event or workload")
            if self.experiment_id and item.get("experiment_id") != self.experiment_id:
                raise ValueError("ledger belongs to a different experiment")
        return result

    def consumed(self):
        entries = self.entries()
        reservations = [item["reservation"] for item in entries if item["event"] == "begin"]
        if len(reservations) != len(set(reservations)):
            raise ValueError("duplicate budget reservation")
        return len(reservations)*self.transitions_per_update

    def append(self, event, reservation, iteration):
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({"event": event, "reservation": reservation, "model_iteration": iteration,
                                     "transitions": self.transitions_per_update, "experiment_id": self.experiment_id})+"\n")
            stream.flush()
            os.fsync(stream.fileno())
        sync_directory(self.path.parent)

    def begin(self, iteration):
        if self.max_transitions is not None and self.consumed()+self.transitions_per_update > self.max_transitions:
            raise ValueError("experiment transition budget exhausted")
        reservation = uuid.uuid4().hex
        self.append("begin", reservation, iteration)
        return reservation

    def complete(self, iteration, reservation=None):
        if reservation is None:
            begins = [item for item in self.entries() if item["event"] == "begin"]
            if not begins:
                raise ValueError("completion without reservation")
            reservation = begins[-1]["reservation"]
        self.append("complete", reservation, iteration)


class ExperimentLease:
    def __init__(self, root):
        self.path = Path(root)/"active.lock"
        self.token = uuid.uuid4().hex

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            previous = json.loads(self.path.read_text())
            if previous.get("host") != socket.gethostname():
                raise RuntimeError("experiment lock belongs to another host; verify its process before removing lock")
            try:
                os.kill(int(previous["pid"]), 0)
            except ProcessLookupError:
                self.path.unlink()
            else:
                raise RuntimeError("experiment is already active; concurrent budget writers are prohibited")
        with self.path.open("x", encoding="utf-8") as stream:
            json.dump({"pid": os.getpid(), "host": socket.gethostname(), "token": self.token}, stream)
            stream.flush()
            os.fsync(stream.fileno())
        return self

    def __exit__(self, *args):
        if self.path.exists() and json.loads(self.path.read_text()).get("token") == self.token:
            self.path.unlink()


class RankCoordinator:
    def __init__(self, group=None):
        self.group = group
        self.world_size = distributed.get_world_size() if distributed.is_initialized() else 1
        self.rank = distributed.get_rank() if distributed.is_initialized() else 0

    def broadcast(self, value):
        objects = [value if self.rank == 0 else None]
        if self.world_size > 1:
            distributed.broadcast_object_list(objects, src=0, group=self.group)
        return objects[0]

    def root_call(self, callback):
        result = None
        if self.rank == 0:
            try:
                result = {"ok": True, "value": callback()}
            except BaseException as error:
                result = {"ok": False, "error": f"{type(error).__name__}: {error}"}
        result = self.broadcast(result)
        if not result["ok"]:
            raise RuntimeError(result["error"])
        return result["value"]

    def gather(self, value):
        objects = [None]*self.world_size if self.rank == 0 else None
        if self.world_size > 1:
            distributed.gather_object(value, objects, dst=0, group=self.group)
        else:
            objects = [value]
        return objects

    def all_call(self, callback):
        value = None
        try:
            value = callback()
            status = {"rank": self.rank, "ok": True}
        except BaseException as error:
            status = {"rank": self.rank, "ok": False, "error": f"{type(error).__name__}: {error}"}
        statuses = self.gather(status)
        def require_all():
            failures = [item for item in statuses if not item["ok"]]
            if failures:
                raise RuntimeError("rank-local operation failed: "+json.dumps(failures, ensure_ascii=False))
        self.root_call(require_all)
        return value

    def check(self, bad, message, device):
        flag = torch.tensor(int(bad), dtype=torch.int32, device=device)
        if self.world_size > 1:
            distributed.all_reduce(flag, op=distributed.ReduceOp.MAX)
        if flag.item():
            raise RuntimeError(message)


def make_payload(runner, cfg, state, metadata, rank=0, world_size=1, contract_data=None):
    result = cpu_copy(runner.alg.save())
    current_lr = float(runner.alg.learning_rate)
    if not math.isfinite(current_lr) or any(abs(group["lr"]-current_lr) > 1e-15 for group in runner.alg.optimizer.param_groups):
        raise ValueError("algorithm and optimizer learning rates disagree")
    signature = contract_data or contract(cfg, world_size)
    result.update({"schema": 1, "rank": rank, "world_size": world_size, "state": state,
                   "iter": state["model_iteration"], "stage": state["stage"],
                   "learning_rate": current_lr, "rng": cpu_copy(rng_state()),
                   "contract": signature, "config_hash": sha_dict(signature),
                   "config": cfg.as_dict(), **metadata})
    return result


def restore_payload(runner, payload, expected_contract):
    if payload["config_hash"] != sha_dict(expected_contract):
        raise ValueError("checkpoint configuration, task sources, model or world size changed")
    learning_rate = float(payload["learning_rate"])
    if any(abs(group["lr"]-learning_rate) > 1e-15 for group in payload["optimizer_state_dict"]["param_groups"]):
        raise ValueError("saved optimizer and adaptive learning rate mismatch")
    with torch.inference_mode():
        runner.alg.load(payload, {"actor": True, "critic": True, "optimizer": False, "iteration": True, "rnd": False}, strict=True)
    runner.alg.optimizer.load_state_dict(payload["optimizer_state_dict"])
    runner.alg.learning_rate = learning_rate
    for group in runner.alg.optimizer.param_groups:
        group["lr"] = learning_rate
    runner.alg.storage.clear()
    runner.current_learning_iteration = payload["state"]["model_iteration"]
    restore_rng(payload["rng"])
    return payload


def write_manifest(directory, payloads, label="checkpoint"):
    if not payloads or {item["rank"] for item in payloads} != set(range(len(payloads))):
        raise ValueError("complete rank set required")
    first = payloads[0]
    for item in payloads:
        for key in ("world_size", "iter", "stage", "config_hash", "consumed_transitions", "experiment_id"):
            if item[key] != first[key]:
                raise ValueError(f"checkpoint ranks disagree on {key}")
        if item["world_size"] != len(payloads):
            raise ValueError("missing rank payload")
        if item["state"] != first["state"]:
            raise ValueError("checkpoint curriculum/gate states disagree")
    directory = Path(directory)/f"{label}_{first['iter']:06d}_{uuid.uuid4().hex[:10]}"
    directory.mkdir(parents=True, exist_ok=False)
    rank_files = {}
    for item in payloads:
        path = directory/f"rank{item['rank']}.pt"
        atomic_torch(path, item)
        rank_files[str(item["rank"])] = {"path": path.name, "sha256": sha_file(path)}
    manifest = {"schema": 1, "complete": True, "world_size": len(payloads), "rank_files": rank_files,
                **{key: first[key] for key in ("iter", "stage", "config_hash", "consumed_transitions", "experiment_id")}}
    pending = first.get("pending_decision") if label == "evaluated" else None
    manifest.update(resumable=not bool(pending), pending_decision=pending,
                    resume_reason="curriculum decision pending; select final or stage2 checkpoint" if pending else None)
    path = directory/"manifest.json"
    atomic_json(path, manifest)
    return str(path.resolve())


def validate_manifest(path, *, rank=None, expected_world_size=None):
    path = Path(path).resolve()
    data = json.loads(path.read_text(encoding="utf-8"))
    world_size = data.get("world_size", 0)
    if data.get("schema") != 1 or data.get("complete") is not True or world_size < 1:
        raise ValueError("incomplete checkpoint manifest")
    if expected_world_size is not None and world_size != expected_world_size:
        raise ValueError("checkpoint world size differs")
    if set(data["rank_files"]) != {str(value) for value in range(world_size)}:
        raise ValueError("manifest is missing a rank")
    if rank is not None and str(rank) not in data["rank_files"]:
        raise ValueError("rank not in manifest")
    reference_state = None
    for rank_text, entry in data["rank_files"].items():
        file_path = (path.parent/entry["path"]).resolve()
        if file_path.parent != path.parent or not file_path.is_file() or sha_file(file_path) != entry["sha256"]:
            raise ValueError("checkpoint path or SHA256 invalid")
        payload = torch.load(file_path, map_location="cpu", weights_only=False)
        if payload["rank"] != int(rank_text):
            raise ValueError("rank identity mismatch")
        for key in ("world_size", "iter", "stage", "config_hash", "consumed_transitions", "experiment_id"):
            if payload[key] != data[key]:
                raise ValueError(f"payload {key} differs from manifest")
        if sha_dict(payload["contract"]) != data["config_hash"]:
            raise ValueError("payload contract hash invalid")
        if payload["state"]["model_iteration"] != payload["iter"] or payload["state"]["stage"] != payload["stage"]:
            raise ValueError("payload counters disagree with curriculum state")
        if reference_state is None:
            reference_state = payload["state"]
        elif reference_state != payload["state"]:
            raise ValueError("mixed curriculum states")
    return data


def save_collective(runner, cfg, state, metadata, directory, coordinator, contract_data, label="checkpoint"):
    payload = coordinator.all_call(lambda: make_payload(runner, cfg, state, metadata, coordinator.rank, coordinator.world_size, contract_data))
    gathered = coordinator.gather(payload)
    return coordinator.root_call(lambda: write_manifest(directory, gathered, label))


def load_collective(runner, path, coordinator, contract_data, experiment_id):
    manifest = coordinator.root_call(lambda: validate_manifest(path, expected_world_size=coordinator.world_size))
    def require_local_contract():
        if manifest.get("resumable") is False:
            raise ValueError(manifest.get("resume_reason") or "checkpoint is inference-only")
        if manifest["experiment_id"] != experiment_id or manifest["config_hash"] != sha_dict(contract_data):
            raise ValueError("resume requires original experiment ledger and matching contract")
    coordinator.all_call(require_local_contract)
    selected = None
    for rank in range(coordinator.world_size):
        payload = coordinator.root_call(lambda: torch.load(Path(path).parent/manifest["rank_files"][str(rank)]["path"], map_location="cpu", weights_only=False))
        if rank == coordinator.rank:
            selected = payload
    coordinator.all_call(lambda: restore_payload(runner, selected, contract_data))
    return selected
