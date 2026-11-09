"""只使用 reset 前快照的分族日志与覆盖统计。"""
from __future__ import annotations

import json
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
import time
import threading

import torch

from .experiment_config import REWARD_TERMS

REWARD_NAMES = ("forward", "yaw", "stand", "lateral", "straight_yaw", "anchor", "posture", "smooth", "late")
FAMILY_NAMES = ("inplace", "straight", "moving_turn", "joint", "stand")
FLAGS = ("strict_drift", "strict_stop", "strict_path", "strict_full_stop", "strict_hold")


class JsonlLogger:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, record):
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, allow_nan=False)+"\n")

    def write_many(self, records):
        with self.path.open("a", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(record, ensure_ascii=False, allow_nan=False)+"\n")


class RunEvents:
    def __init__(self, directory, run_id, rank):
        self.directory = Path(directory)
        self.run_id, self.rank, self.seq = run_id, rank, 0
        self.started = time.perf_counter()
        self.logger = JsonlLogger(self.directory/f"events.rank{rank}.jsonl")
        self.root_logger = JsonlLogger(self.directory/"events.jsonl") if rank == 0 else None
        self.lock = threading.Lock()
        self.finished = threading.Event()
        self.current = None
        self.worker = threading.Thread(target=self._heartbeat, daemon=True)
        self.worker.start()

    def _heartbeat(self):
        from .locomotion_checkpoint import atomic_json
        while not self.finished.wait(1.):
            with self.lock:
                if self.current is not None:
                    atomic_json(self.directory/f"status.rank{self.rank}.json",
                                {**self.current, "utc": datetime.now(timezone.utc).isoformat(),
                                 "elapsed_s": time.perf_counter()-self.started})

    def close(self):
        self.finished.set()
        self.worker.join(timeout=2.)

    def emit(self, phase, **fields):
        from .locomotion_checkpoint import atomic_json
        self.seq += 1
        record = {"run_id": self.run_id, "rank": self.rank, "seq": self.seq,
                  "utc": datetime.now(timezone.utc).isoformat(),
                  "elapsed_s": time.perf_counter()-self.started, "phase": phase, **fields}
        self.logger.write(record)
        if self.root_logger is not None:
            self.root_logger.write(record)
        with self.lock:
            self.current = record
            atomic_json(self.directory/f"status.rank{self.rank}.json", record)
        return record


class EpisodeAccumulator:
    def __init__(self, count, device):
        self.returns = torch.zeros(count, device=device, dtype=torch.float64)
        self.lengths = torch.zeros(count, device=device, dtype=torch.long)

    def collect(self, rewards, dones):
        self.returns += rewards
        self.lengths += 1
        indices = dones.bool().nonzero().flatten()
        records = {int(index): {"episode_return": float(self.returns[index]),
                               "episode_length": int(self.lengths[index])} for index in indices}
        self.returns[indices] = 0
        self.lengths[indices] = 0
        return records


class EpisodeWindow:
    def __init__(self, count=100):
        self.records = deque(maxlen=count)

    def add(self, rank_records):
        ordered = [(record.get("rollout_step", 0), rank, record["env_id"], record)
                   for rank, records in enumerate(rank_records) for record in records]
        self.records.extend(item[3] for item in sorted(ordered, key=lambda item: item[:3]))
        count = len(self.records)
        return {"samples": count,
                "return_mean": sum(item["episode_return"] for item in self.records)/count if count else None,
                "length_mean": sum(item["episode_length"] for item in self.records)/count if count else None,
                "failed_count": sum(bool(item.get("failed")) for item in self.records),
                "natural_completed_count": sum(not bool(item.get("failed")) for item in self.records),
                "scope": "most recent completed episodes; rollout step, rank and environment order break ties"}


class RolloutStatistics:
    def __init__(self, device):
        self.device = device
        self.samples = torch.zeros(5, device=device, dtype=torch.long)
        self.starts = torch.zeros_like(self.samples)
        self.completes = torch.zeros_like(self.samples)
        self.segment_steps = torch.zeros(5, 7, device=device, dtype=torch.long)
        self.reached = torch.zeros(5, 7, device=device, dtype=torch.long)
        self.failures = torch.zeros(10, device=device, dtype=torch.long)
        self.reward_terms = torch.zeros(9, device=device)
        self.reward_sum = torch.zeros((), device=device)
        self.clipped = torch.zeros((), device=device)
        self.failure_count = torch.zeros((), device=device)
        self.count = 0
        self.terminals = []
        self.command_samples = []
        self.rollout_step = 0
        self.reward_raw_sum = torch.zeros(len(REWARD_TERMS), device=device, dtype=torch.float64)
        self.reward_weight_sum = torch.zeros_like(self.reward_raw_sum)
        self.reward_contribution_sum = torch.zeros_like(self.reward_raw_sum)
        self.reward_detail_samples = 0
        self.failure_cost = torch.zeros((), device=device, dtype=torch.float64)

    def collect(self, snapshot, dones, actions, rewards, episodes=None):
        self.rollout_step += 1
        family = snapshot["family"].long()
        segment = snapshot["segment"].long().clamp(0, 6)
        self.samples += torch.bincount(family, minlength=5)
        self.starts += torch.bincount(family[snapshot["time"] <= .020001], minlength=5)
        encoded = family*7+segment
        self.segment_steps += torch.bincount(encoded, minlength=35).reshape(5, 7)
        terminal = dones.bool()
        natural = terminal & ~snapshot["failed"].bool() & (snapshot["time"] >= snapshot["duration"]-1e-4)
        self.completes += torch.bincount(family[natural], minlength=5)
        self.failures += torch.bincount(snapshot["reason"][terminal].long(), minlength=10)
        self.reward_terms += snapshot["reward_terms"].sum(0)*.02
        if "reward_raw" in snapshot:
            self.reward_raw_sum += snapshot["reward_raw"].double().sum(0)
            self.reward_weight_sum += snapshot["reward_weights"].double().sum(0)
            contribution = snapshot["reward_contributions"].double().sum(0)
            self.reward_contribution_sum += contribution
            self.failure_cost += contribution[-1]
            self.reward_detail_samples += family.numel()
        else:
            self.failure_cost -= 100*snapshot["failed"].sum()
        self.reward_sum += rewards.sum()
        self.clipped += (actions.abs() > 1).sum()
        self.failure_count += snapshot["failed"].sum()
        self.count += family.numel()
        if "reached_segments" in snapshot:
            reached = snapshot["reached_segments"][terminal].long()
            self.reached.index_add_(0, family[terminal], reached)
        indices = terminal.nonzero().flatten()
        if indices.numel():
            scalar_names = ("time", "family", "segment", "reason", "failed", "max_drift", "brake_path", "hold_complete", *FLAGS)
            values = {name: snapshot[name][indices].detach().cpu().tolist() for name in scalar_names}
            for name in ("phase", "reached_segments"):
                if name in snapshot:
                    values[name] = snapshot[name][indices].detach().cpu().tolist()
            env_ids = indices.cpu().tolist()
            for offset, env_id in enumerate(env_ids):
                self.terminals.append({"env_id": env_id, "rollout_step": self.rollout_step,
                                       **{name: value[offset] for name, value in values.items()},
                                       **((episodes or {}).get(env_id, {}))})
        if len(self.command_samples) < 2:
            self.command_samples.append({name: snapshot[name][0].detach().cpu().tolist() for name in ("time", "request", "cmd", "vel", "yaw_rate")})

    def summary(self):
        return {"samples": self.samples.cpu().tolist(), "starts": self.starts.cpu().tolist(),
                "completes": self.completes.cpu().tolist(), "segment_steps": self.segment_steps.cpu().tolist(),
                "reached_terminal_segments": self.reached.cpu().tolist(), "failure_reasons": self.failures.cpu().tolist(),
                "reward_terms_sum": dict(zip(REWARD_NAMES, self.reward_terms.cpu().tolist())),
                "reward_sum": float(self.reward_sum), "failure_cost_sum": float(self.failure_cost),
                "reward_details": {name: {"raw_sum": float(self.reward_raw_sum[index]),
                                          "signed_weight_sum": float(self.reward_weight_sum[index]),
                                          "contribution_sum": float(self.reward_contribution_sum[index]),
                                          "samples": self.reward_detail_samples,
                                          "unit": "event_cost" if name == "failure" else "reward_rate"}
                                   for index, name in enumerate(REWARD_TERMS)},
                "clipped_actions": int(self.clipped), "transitions": self.count,
                "command_samples": self.command_samples}


def merge_summaries(summaries):
    result = {}
    for key in ("samples", "starts", "completes", "segment_steps", "reached_terminal_segments", "failure_reasons"):
        result[key] = torch.tensor([item[key] for item in summaries]).sum(0).tolist()
    for key in ("reward_sum", "failure_cost_sum", "clipped_actions", "transitions"):
        result[key] = sum(item[key] for item in summaries)
    result["reward_terms_sum"] = {name: sum(item["reward_terms_sum"][name] for item in summaries) for name in REWARD_NAMES}
    result["raw_action_clip_fraction"] = result["clipped_actions"]/max(1, 14*result["transitions"])
    result["joint_later_samples"] = sum(result["segment_steps"][3][4:])
    result["family_names"] = FAMILY_NAMES
    result["command_samples_rank0"] = summaries[0]["command_samples"]
    result["reward_per_transition"] = result["reward_sum"]/max(1, result["transitions"])
    result["reward_mean"] = result["reward_per_transition"]
    result["reward_terms_per_transition"] = {name: value/max(1, result["transitions"]) for name, value in result["reward_terms_sum"].items()}
    result["reward_details"] = {}
    for name in REWARD_TERMS:
        details = [item.get("reward_details", {}).get(name) for item in summaries]
        details = [item for item in details if item is not None]
        count = sum(item["samples"] for item in details)
        if count:
            item = {key.removesuffix("_sum")+"_mean": sum(value[key] for value in details)/count
                    for key in ("raw_sum", "signed_weight_sum", "contribution_sum")}
            item.update(samples=count, unit="event_cost" if name == "failure" else "reward_rate")
            item["reward_per_transition"] = item["contribution_mean"]*(1 if name == "failure" else .02)
            result["reward_details"][name] = item
    return result


def snapshot_episodes(env):
    snapshot = env.extras.get("locomotion")
    if snapshot is None:
        raise ValueError("reset-before-snapshot terminal data unavailable")
    return {name: value.detach().clone() for name, value in snapshot.items()}
