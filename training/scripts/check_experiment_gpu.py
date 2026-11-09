"""执行已登记的96转换工具验收；不作为策略行为训练。"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root, records, output = args.root.resolve(), args.records.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    snapshot = output/"frozen"
    paths = list((root/"training/mjlab_duck").glob("*.py"))
    paths += list((root/"training/models").glob("*.xml"))+list((root/"training/params").glob("*.json"))
    paths += [root/"training/experiment_archive.py"]
    for source in paths:
        destination = snapshot/source.relative_to(root)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    for name in ("scratch-config.json", "scratch-workflow.json", "warm-config.json", "warm-workflow.json", "validation-budget.json"):
        shutil.copy2(records/name, output/name)
    results = {}
    source_manifest = None
    for mode in ("scratch", "resume", "warm"):
        config_name = "warm" if mode == "warm" else "scratch"
        command = [sys.executable, "-m", "mjlab_duck.train_locomotion", "--config", str(output/f"{config_name}-config.json"),
                   "--workflow-record", str(output/f"{config_name}-workflow.json"), "--output", str(output/mode),
                   "--experiment-dir", str(output/("warm-experiment" if mode == "warm" else "scratch-experiment")),
                   "--check-mode", "--max-new-updates", "1", "--run-id", "archive-check-"+mode]
        if mode == "resume":
            command += ["--resume-manifest", source_manifest]
        elif mode == "warm":
            command += ["--warm-start-manifest", source_manifest]
        print(json.dumps({"phase": "starting", "mode": mode, "command": command}), flush=True)
        with (output/f"{mode}.log").open("w", encoding="utf-8") as log:
            code = subprocess.call(command, cwd=snapshot/"training", stdout=log, stderr=subprocess.STDOUT)
        if code:
            print(json.dumps({"phase": "failed", "mode": mode, "exit_code": code}), flush=True)
            raise SystemExit(code)
        results[mode] = json.loads((output/mode/"result.json").read_text())
        if mode == "scratch":
            source_manifest = results[mode]["checkpoint_manifest"]
        print(json.dumps({"phase": "completed", "mode": mode, "result": results[mode]}), flush=True)
    import torch

    def payload(manifest):
        manifest = Path(manifest)
        data = json.loads(manifest.read_text())
        return torch.load(manifest.parent/data["rank_files"]["0"]["path"], map_location="cpu", weights_only=False)

    source = payload(source_manifest)
    warm_start = payload(next((output/"warm/checkpoints").glob("start_*/manifest.json")))
    scratch_start = payload(next((output/"scratch/checkpoints").glob("start_*/manifest.json")))
    assert results["scratch"]["consumed_transitions"] == 32
    assert results["resume"]["consumed_transitions"] == 64
    assert results["warm"]["consumed_transitions"] == 32
    assert warm_start["state"]["model_iteration"] == 0 and warm_start["stage"] == 1
    assert not warm_start["optimizer_state_dict"]["state"]
    for name, tensor in warm_start["actor_state_dict"].items():
        expected = scratch_start["actor_state_dict"][name] if name.startswith("distribution.") else source["actor_state_dict"][name]
        assert torch.equal(tensor, expected), name
    for name, tensor in warm_start["critic_state_dict"].items():
        assert torch.equal(tensor, scratch_start["critic_state_dict"][name]), name
    result = {"status": "passed", "training_transitions": 96, "runs": results,
              "warm_actor_normalizer_inherited": True, "warm_critic_optimizer_exploration_reset": True,
              "resume_budget_preserved": True, "behavior_acceptance": "not_tested"}
    (output/"verification.json").write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
