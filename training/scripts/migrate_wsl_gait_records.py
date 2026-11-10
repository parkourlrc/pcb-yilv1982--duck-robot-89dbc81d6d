"""将 2026-11-07/08 双足正式重试显式迁入统一训练记录。

脚本只处理固定的四个、已经完成源码合同与 rank0 校验的 WSL 运行目录。
它复制冻结源码、检查点和运行证据到 training/artifacts/runs/，再生成
training/records/<run_id>.json。原始 /root/duck-training-runs 目录不会删除。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / "training/artifacts"
RUNS = ARTIFACTS / "runs"
RECORDS = ROOT / "training/records"
WSL_ROOT = "/root/duck-training-runs"
DEFAULT_DISTRIBUTION = "Ubuntu-24.04"
RUN_IDS = (
    "amplitude-20261107-gait010-s42-r1",
    "amplitude-20261107-gait020-s42-r1",
    "amplitude-20261107-rawramp-s42-r1",
    "amplitude-20261107-gait010_rawramp-s42-r1",
)
LABELS = {
    "amplitude-20261107-gait010-s42-r1": "gait010",
    "amplitude-20261107-gait020-s42-r1": "gait020",
    "amplitude-20261107-rawramp-s42-r1": "rawramp",
    "amplitude-20261107-gait010_rawramp-s42-r1": "gait010_rawramp",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def wsl(distribution: str, command: str) -> None:
    argv = ["wsl.exe"]
    if distribution:
        argv += ["-d", distribution]
    argv += ["--exec", "bash", "-lc", command]
    result = subprocess.run(argv, text=True, capture_output=True)
    if result.returncode:
        detail = (result.stderr or result.stdout or "WSL命令失败").strip()
        raise RuntimeError(detail)


def wsl_path(distribution: str, path: Path) -> str:
    argv = ["wsl.exe"]
    if distribution:
        argv += ["-d", distribution]
    argv += ["--exec", "wslpath", "-a", "-u", str(path.resolve())]
    result = subprocess.run(argv, text=True, capture_output=True, check=True)
    return result.stdout.strip()


def validate_manifest(path: Path) -> dict:
    manifest = read_json(path)
    if manifest.get("schema") != 1 or manifest.get("complete") is not True:
        raise ValueError(f"检查点清单不完整: {path}")
    rank_files = manifest.get("rank_files")
    if manifest.get("world_size") != 1 or set(rank_files or {}) != {"0"}:
        raise ValueError(f"检查点 rank 结构不支持: {path}")
    entry = rank_files["0"]
    candidate = (path.parent / entry["path"]).resolve()
    if candidate.parent != path.parent.resolve() or not candidate.is_file():
        raise ValueError(f"rank0 文件缺失: {path}")
    actual = sha256(candidate)
    if actual != entry.get("sha256"):
        raise ValueError(f"rank0 SHA 不匹配: {path}")
    return manifest


def copy_from_wsl(run_id: str, destination: Path, distribution: str) -> None:
    source = f"{WSL_ROOT}/{run_id}"
    target = wsl_path(distribution, destination)
    command = (
        f"set -e; rm -rf {shell_quote(target)}; "
        f"mkdir -p {shell_quote(target + '/history')} {shell_quote(target + '/project')}; "
        f"test -d {shell_quote(source)}; "
        f"tar --exclude=frozen --exclude='*.pyc' -C {shell_quote(source)} -cf - . | "
        f"tar -C {shell_quote(target + '/history')} -xf -; "
        f"tar --exclude='*.pyc' -C {shell_quote(source + '/frozen')} -cf - . | "
        f"tar -C {shell_quote(target + '/project')} -xf -"
    )
    wsl(distribution, command)


def shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\\''") + "'"


def build_workflow(run_id: str, config: dict, source_hashes: dict, imported_utc: str) -> dict:
    evidence = [
        "docs/specs/20261107-步幅参数优化/spec.md",
        "docs/references/自主训练平台/足部奖励百轮对照-20261107.md",
    ]
    names = ("策略需求", "任务定义与验收标准", "训练环境组装", "训练方案", "执行训练", "独立评估与回放", "策略交付")
    statuses = ("reused", "reused", "completed", "completed", "completed", "completed", "pending")
    steps = []
    for number, (name, status) in enumerate(zip(names, statuses), 1):
        steps.append({
            "number": number,
            "name": name,
            "status": status,
            "inputs": [{"run_id": run_id, "source": "WSL历史训练输出"}] if number <= 4 else [],
            "outputs": [{"evidence": evidence}] if number in (1, 2, 6) else [],
            "evidence": evidence if number in (1, 2, 6) else [],
        })
    return {
        "task_id": "locomotion",
        "task_version": "historical",
        "current_step": 7,
        "steps": steps,
        "budget": {
            "source": "run/result.json",
            "validated_utc": imported_utc,
            "config": config,
        },
        "source_run_id": run_id,
        "migration": "explicit historical migration; no new training executed",
        "source_hashes": source_hashes,
    }


def migrate(run_id: str, distribution: str, force: bool) -> dict:
    destination = RUNS / run_id
    record_path = RECORDS / f"{run_id}.json"
    if destination.exists() or record_path.exists():
        if not force:
            raise RuntimeError(f"目标已存在，使用 --force 才覆盖: {run_id}")
        if destination.exists():
            shutil.rmtree(destination)
        record_path.unlink(missing_ok=True)

    staging = RUNS / f".{run_id}.importing"
    if staging.exists():
        shutil.rmtree(staging)
    staging.parent.mkdir(parents=True, exist_ok=True)
    copy_from_wsl(run_id, staging, distribution)

    history = staging / "history"
    runtime = staging / "project"
    run_data = read_json(history / "run/run.json")
    config = read_json(history / "config.json")
    result = read_json(history / "run/result.json")
    source_hashes = run_data.get("source_sha256")
    if not isinstance(source_hashes, dict) or not source_hashes:
        raise ValueError(f"缺少冻结源码合同: {run_id}")
    mismatches = [name for name, expected in source_hashes.items()
                  if not (runtime / name).is_file() or sha256(runtime / name) != expected]
    if mismatches:
        raise ValueError(f"冻结源码 SHA 不匹配 {run_id}: {mismatches[:3]}")

    manifests = sorted((history / "run/checkpoints").glob("*/manifest.json"))
    if not manifests:
        raise ValueError(f"没有检查点: {run_id}")
    checkpoint_rows = []
    final_manifest = None
    for manifest_path in manifests:
        manifest = validate_manifest(manifest_path)
        checkpoint_id = f"{run_id}-{manifest_path.parent.name}"
        row = {
            "checkpoint_id": checkpoint_id,
            "model_iteration": manifest.get("iter"),
            "stage": manifest.get("stage"),
            "integrity": "complete",
            "replayable": True,
            "resumable": bool(manifest.get("resumable", True)),
            "consumed_transitions": manifest.get("consumed_transitions"),
        }
        checkpoint_rows.append(row)
        if manifest_path.parent.name.startswith("final_"):
            final_manifest = (manifest_path, manifest, checkpoint_id)
    if final_manifest is None:
        raise ValueError(f"没有 final 检查点: {run_id}")

    imported_utc = datetime.now(timezone.utc).isoformat()
    max_transitions = result.get("max_transitions") or config.get("num_envs", 0) * config.get("num_steps_per_env", 0) * config.get("max_updates", 0)
    consumed = result.get("consumed_transitions") or final_manifest[1].get("consumed_transitions")
    budget = {
        "consumed_transitions": consumed,
        "remaining_transitions": max(0, max_transitions - consumed) if consumed is not None and max_transitions is not None else 0,
        "max_transitions": max_transitions,
        "transitions_per_update": config.get("num_envs", 0) * config.get("num_steps_per_env", 0),
    }
    workflow = build_workflow(run_id, config, source_hashes, imported_utc)
    label = LABELS[run_id]
    run = {
        "run_id": run_id,
        "experiment_id": final_manifest[1].get("experiment_id", run_id),
        "parent_run_id": None,
        "parent_checkpoint_id": None,
        "task_id": "locomotion",
        "task_version": "historical",
        "name": f"足部奖励对照 · {label} · seed42 · 100更新",
        "managed": False,
        "read_only": True,
        "state": "completed" if result.get("status") == "budget_exhausted" else "unknown",
        "completion_reason": result.get("status"),
        "connection": {"state": "offline_archive", "last_seen_utc": None},
        "stage": final_manifest[1].get("stage"),
        "model_iteration": final_manifest[1].get("iter"),
        "budget": budget,
        "execution": {"mode": "historical_wsl", "node_ids": [], "world_size": 1},
        "config": config,
        "created_utc": run_data.get("created_utc"),
        "elapsed_s": result.get("wall_seconds_including_evaluation_and_checkpoint"),
        "eta_s": None,
        "latest_checkpoint_id": final_manifest[2],
        "failure": None,
        "capabilities": {
            "stop": {"allowed": False, "reasons": ["历史归档"]},
            "replay": {"allowed": True, "reasons": []},
            "scratch": {"allowed": False, "reasons": ["历史迁移未登记可复用的任务合同"]},
            "warm": {"allowed": False, "reasons": ["未核验物理/接口/迁移 transfer 合同"]},
            "resume": {"allowed": False, "reasons": ["原100轮预算已耗尽；续训需新预算和新流程记录"]},
        },
        "workflow": workflow,
        "provenance": {"kind": "wsl_historical_training", "source": f"{WSL_ROOT}/{run_id}", "imported_utc": imported_utc},
        "_directory": str((destination / "history" / "run").resolve()),
        "_runtime_root": str((destination / "project").resolve()),
        "_warm_compatible": False,
    }
    write_json(runtime / "source-manifest.json", source_hashes)
    documents = staging / "record-documents"
    documents.mkdir(parents=True, exist_ok=True)
    for source in (
        ROOT / "docs/references/自主训练平台/足部奖励百轮对照-20261107.md",
        ROOT / "docs/specs/20261107-步幅参数优化/spec.md",
    ):
        if source.is_file():
            shutil.copy2(source, documents / source.name)
    staging.rename(destination)

    # Archive helper writes the durable dashboard cache and a fixed artifact manifest.
    sys.path.insert(0, str(ROOT / "training"))
    from dashboard.archive import Archive
    archive = Archive(ROOT, ARTIFACTS)
    archive.save(run)
    archive.seal(run)

    record = {
        "schema": 1,
        "record_kind": "training-run",
        "producer": "training-process-history-migration",
        "documented_utc": imported_utc,
        "run_id": run_id,
        "name": run["name"],
        "task_id": run["task_id"],
        "task_version": run["task_version"],
        "state": run["state"],
        "created_utc": run["created_utc"],
        "config": config,
        "budget": budget,
        "result": {
            "completion_reason": result.get("status"),
            "failure": None,
            "elapsed_s": run["elapsed_s"],
            "model_iteration": run["model_iteration"],
            "stage": run["stage"],
        },
        "workflow": workflow,
        "artifact_reference": f"training/artifacts/runs/{run_id}",
        "source": run["provenance"],
        "capabilities": run["capabilities"],
        "checkpoints": checkpoint_rows,
        "behavior_acceptance": "not_inferred_from_training_completion; dev9四组均0/9",
    }
    write_json(record_path, record)
    return {"run_id": run_id, "record": str(record_path), "checkpoints": len(checkpoint_rows), "source_files": len(source_hashes)}


def main() -> None:
    parser = argparse.ArgumentParser(description="迁移四组双足 WSL 历史训练到 training/records")
    parser.add_argument("--distribution", default=DEFAULT_DISTRIBUTION)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    RECORDS.mkdir(parents=True, exist_ok=True)
    results = [migrate(run_id, args.distribution, args.force) for run_id in RUN_IDS]
    print(json.dumps({"migrated": results, "raw_sources_preserved": True}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
