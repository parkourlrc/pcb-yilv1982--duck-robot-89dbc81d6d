"""建立唯一训练文档目录并清理不可恢复的平台历史副本。

原始 docs/specs、docs/references 和 training/logs 只作为迁移输入；运行后的
dashboard 不再扫描这些目录。脚本只删除 training/artifacts/runs 下的缓存。
"""
from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

TRAINING_ROOT = Path(__file__).resolve().parents[1]
if str(TRAINING_ROOT) not in sys.path:
    sys.path.insert(0, str(TRAINING_ROOT))

from dashboard.history import checkpoint_info
from dashboard.registry import file_hash


ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / "training/artifacts"
RUNS = ARTIFACTS / "runs"
RECORDS = ROOT / "training/records"


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def frozen_sources_match(history: Path, source: Path) -> bool:
    """Require the run's recorded source contract to match the saved snapshot."""
    run = history / "run.json"
    if not run.is_file():
        return False
    data = json.loads(run.read_text(encoding="utf-8"))
    expected = data.get("source_sha256")
    if not isinstance(expected, dict) or not expected:
        return False
    return all((source / name).is_file() and file_hash(source / name) == digest for name, digest in expected.items())


def migrate(run_root: Path) -> dict | None:
    dashboard_path = run_root / "dashboard-run.json"
    history = run_root / "history"
    if not dashboard_path.is_file() or not history.is_dir():
        return None
    run = json.loads(dashboard_path.read_text(encoding="utf-8"))
    source = history / "sources"
    required = (
        source / "training/mjlab_duck/train_locomotion.py",
        source / "training/mjlab_duck/locomotion_env.py",
        source / "training/models/duck_v0.xml",
    )
    checkpoints = []
    for manifest in history.rglob("manifest.json"):
        item = checkpoint_info(manifest, run_root.name, run_root.name + "-" + manifest.parent.name)
        if item and item["replayable"]:
            checkpoints.append(item)
    if (not all(path.is_file() for path in required) or not checkpoints or
            not frozen_sources_match(history, source)):
        return None

    project = run_root / "project"
    if project.exists():
        shutil.rmtree(project)
    shutil.copytree(source, project)
    source_manifest = {}
    for path in project.rglob("*"):
        if path.is_file() and "__pycache__" not in path.parts:
            source_manifest[path.relative_to(project).as_posix()] = file_hash(path)
    write_json(project / "source-manifest.json", source_manifest)
    run["_runtime_root"] = str(project)
    run["_record_origin"] = "historical-training-output"
    run["capabilities"] = {
        "replay": {"allowed": True, "reasons": []},
        "scratch": {"allowed": False, "reasons": ["历史运行缺少经流程登记的任务合同"]},
        "warm": {"allowed": False, "reasons": ["未核验物理/接口/迁移合同"]},
        "resume": {"allowed": False, "reasons": ["缺少原节点和预算账本"]},
    }
    write_json(dashboard_path, run)
    record = {
        "schema": 1,
        "record_kind": "training-run",
        "producer": "training-process",
        "documented_utc": datetime.now(timezone.utc).isoformat(),
        "run_id": run_root.name,
        "name": run.get("name"),
        "task_id": run.get("task_id"),
        "task_version": run.get("task_version"),
        "state": run.get("state"),
        "created_utc": run.get("created_utc"),
        "config": run.get("config", {}),
        "budget": run.get("budget", {}),
        "result": {key: run.get(key) for key in ("completion_reason", "failure", "elapsed_s", "model_iteration", "stage")},
        "artifact_reference": f"training/artifacts/runs/{run_root.name}",
        "source": run.get("provenance", {}),
        "capabilities": run["capabilities"],
        "checkpoints": [{key: item[key] for key in ("checkpoint_id", "model_iteration", "stage", "integrity", "replayable")} for item in checkpoints],
        "behavior_acceptance": "not_inferred_from_training_completion",
    }
    write_json(RECORDS / f"{run_root.name}.json", record)
    return {"run_id": run_root.name, "source": run.get("provenance", {}).get("source"), "kept": True, "reason": "有冻结源码快照和可验证rank0检查点"}


def main() -> None:
    RECORDS.mkdir(parents=True, exist_ok=True)
    kept = []
    ledger_path = RECORDS / "cleanup-20261109.json"
    previous = json.loads(ledger_path.read_text(encoding="utf-8")) if ledger_path.is_file() else {}
    removed = list(previous.get("removed", []))
    removed_ids = {item.get("run_id") for item in removed}
    for run_root in sorted(RUNS.iterdir() if RUNS.is_dir() else []):
        if not run_root.is_dir():
            continue
        # Explicit historical migrations (for example the WSL gait records)
        # already have a canonical training document and a different archive
        # layout. Keep them under the records contract; do not treat them as
        # unregistered platform copies on a later cleanup run.
        existing_record = RECORDS / f"{run_root.name}.json"
        existing_data = json.loads(existing_record.read_text(encoding="utf-8")) if existing_record.is_file() else {}
        if existing_data.get("record_kind") == "training-run" and existing_data.get("producer") == "training-process-history-migration":
            kept.append({"run_id": run_root.name, "source": existing_data.get("source", {}).get("source"), "kept": True,
                         "reason": "已按显式历史迁移流程登记，保留统一档案"})
            continue
        result = migrate(run_root)
        if result:
            kept.append(result)
            continue
        if run_root.name not in removed_ids:
            removed.append({"run_id": run_root.name, "reason": "没有同时具备冻结源码哈希合同和可验证rank0检查点"})
            removed_ids.add(run_root.name)
        (RECORDS / f"{run_root.name}.json").unlink(missing_ok=True)
        shutil.rmtree(run_root)
    ledger = {
        "schema": 1,
        "record_kind": "maintenance",
        "producer": "cleanup_training_records.py",
        "cleaned_utc": datetime.now(timezone.utc).isoformat(),
        "kept": kept,
        "removed": removed,
        "raw_sources_preserved": True,
        "scope": "仅 training/artifacts/runs 平台副本；未删除 docs 或 training/logs 原始材料",
    }
    kept_ids = {item["run_id"] for item in kept}
    for document in RECORDS.glob("*.json"):
        if document.stem == ledger_path.stem:
            continue
        data = json.loads(document.read_text(encoding="utf-8"))
        if data.get("record_kind") == "training-run" and document.stem not in kept_ids:
            document.unlink()
    write_json(ledger_path, ledger)
    (ARTIFACTS / "history-inventory.json").unlink(missing_ok=True)
    print(json.dumps({"kept": len(kept), "removed": len(removed), "record_dir": str(RECORDS)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
