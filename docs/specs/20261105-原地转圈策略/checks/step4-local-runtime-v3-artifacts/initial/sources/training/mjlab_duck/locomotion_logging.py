"""只使用 reset 前快照的分族日志与覆盖统计。"""
from __future__ import annotations

import json
from pathlib import Path

import torch

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

    def collect(self, snapshot, dones, actions, rewards):
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
                self.terminals.append({"env_id": env_id, **{name: value[offset] for name, value in values.items()}})
        if len(self.command_samples) < 2:
            self.command_samples.append({name: snapshot[name][0].detach().cpu().tolist() for name in ("time", "request", "cmd", "vel", "yaw_rate")})

    def summary(self):
        return {"samples": self.samples.cpu().tolist(), "starts": self.starts.cpu().tolist(),
                "completes": self.completes.cpu().tolist(), "segment_steps": self.segment_steps.cpu().tolist(),
                "reached_terminal_segments": self.reached.cpu().tolist(), "failure_reasons": self.failures.cpu().tolist(),
                "reward_terms_sum": dict(zip(REWARD_NAMES, self.reward_terms.cpu().tolist())),
                "reward_sum": float(self.reward_sum), "failure_cost_sum": -100*float(self.failure_count),
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
    return result


def snapshot_episodes(env):
    snapshot = env.extras.get("locomotion")
    if snapshot is None:
        raise ValueError("reset-before-snapshot terminal data unavailable")
    return {name: value.detach().clone() for name, value in snapshot.items()}
