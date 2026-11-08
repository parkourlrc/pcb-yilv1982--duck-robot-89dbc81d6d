"""将已冻结基线复制为独立单因素实验；不改现行训练源文件。"""
from pathlib import Path
import argparse
import hashlib
import json
import shutil

PRESETS = {
    "baseline": {"alpha": 1., "smooth_weight": .05, "damping": 2.},
    "ema025": {"alpha": .25, "smooth_weight": .05, "damping": 2.},
    "ema050": {"alpha": .5, "smooth_weight": .05, "damping": 2.},
    "smooth020": {"alpha": 1., "smooth_weight": .2, "damping": 2.},
    "kd100": {"alpha": 1., "smooth_weight": .05, "damping": 1.},
}


def replace(path, old, new):
    source = path.read_text(encoding="utf-8")
    if source.count(old) != 1:
        raise ValueError(f"expected one exact source anchor in {path}: {old!r}")
    path.write_text(source.replace(old, new), encoding="utf-8", newline="\n")


def prepare(source, destination, preset, seed):
    # 2026-11-07用户明确：Kd属于固定执行器参数，不纳入步幅调参。
    if PRESETS[preset]["damping"] != 2.:
        raise ValueError("Kd changes are disabled by the current user instruction; use damping=2")
    if destination.exists():
        raise FileExistsError(destination)
    # 输入只能为原冻结基线，拒绝对已经修改的副本再次叠加补丁。
    source_manifest = json.loads((source.parent / "run/run.json").read_text())
    for name, expected in source_manifest["source_sha256"].items():
        if hashlib.sha256((source/name).read_bytes()).hexdigest() != expected:
            raise ValueError(f"baseline source changed: {name}")
    destination.mkdir(parents=True)
    frozen = destination / "frozen"
    shutil.copytree(source, frozen, ignore=shutil.ignore_patterns("__pycache__", "MUJOCO_LOG.TXT"))
    package = frozen / "training/experiments/amplitude"
    package.mkdir(parents=True, exist_ok=True)
    for script in Path(__file__).parent.glob("*.py"):
        shutil.copy2(script, package/script.name)
    variant = {"schema": 1, "preset": preset, **PRESETS[preset],
               "clip_stop_fraction": .5, "clip_stop_updates": 5,
               "observation": "original raw previous action; EMA memory is not additionally observed"}
    (package/"variant.json").write_text(json.dumps(variant, indent=2)+"\n")
    env = frozen/"training/mjlab_duck/locomotion_env.py"
    replace(env, 'ROOT = Path(__file__).resolve().parents[1]',
            'ROOT = Path(__file__).resolve().parents[1]\nAMPLITUDE = json.loads((ROOT / "experiments/amplitude/variant.json").read_text())')
    replace(env, 'self.raw = torch.zeros(self.num_envs, 14, device=self.device)',
            'self.raw = torch.zeros(self.num_envs, 14, device=self.device)\n        self.filtered = torch.zeros_like(self.raw)')
    replace(env, 'self.target[ids] = self.home', 'self.target[ids] = self.home\n        self.filtered[ids] = 0')
    target = 'self.target = (self.home+.5*self.raw.clamp(-1, 1)).clamp(limits[..., 0], limits[..., 1])'
    replace(env, target,
            'if AMPLITUDE["alpha"] == 1.:\n            '+target+'\n'
            '        else:\n'
            '            self.filtered.mul_(1-AMPLITUDE["alpha"]).add_(self.raw.clamp(-1, 1), alpha=AMPLITUDE["alpha"])\n'
            '            self.target = (self.home+.5*self.filtered).clamp(limits[..., 0], limits[..., 1])')
    replace(env, '-.05*((actual-previous).square().mean(-1)/.01).clamp_max(1)',
            '-AMPLITUDE["smooth_weight"]*((actual-previous).square().mean(-1)/.01).clamp_max(1)')
    cfg = frozen/"training/mjlab_duck/locomotion_cfg.py"
    replace(cfg, '    ROOT, HOME, Z_HOME, JOINT_ORDER,', '    AMPLITUDE, ROOT, HOME, Z_HOME, JOINT_ORDER,')
    replace(cfg, 'stiffness=25., damping=2., effort_limit=.94,',
            'stiffness=25., damping=AMPLITUDE["damping"], effort_limit=.94,')
    checkpoint = frozen/"training/mjlab_duck/locomotion_checkpoint.py"
    replace(checkpoint, '"action": "14:HOME+0.5*clip(raw,-1,1),joint_limits", "normalization": "rank_local",',
            '"action": "14:HOME+0.5*EMA(clip(raw,-1,1),alpha='+str(variant['alpha'])+'),joint_limits", '
            '"amplitude": json.loads((ROOT/"training/experiments/amplitude/variant.json").read_text()), "normalization": "rank_local",')
    extras = sorted(str(p.relative_to(frozen)).replace("\\", "/") for p in package.iterdir() if p.suffix in (".py", ".json"))
    replace(checkpoint, '\n\ndef sha_file(path):', '\nCONTRACT_FILES += '+repr(tuple(extras))+'\n\ndef sha_file(path):')
    train = frozen/"training/mjlab_duck/train_locomotion.py"
    replace(train, '        new_updates = 0', '        new_updates = 0\n        amplitude_clip_streak = 0')
    replace(train, '                logger.write(record)',
            '                logger.write(record)\n'
            '                amplitude_clip_streak = amplitude_clip_streak+1 if global_stats["raw_action_clip_fraction"] > .5 else 0\n'
            '                if amplitude_clip_streak >= 5:\n'
            '                    atomic_json(output_dir/"amplitude_stop.json", {"reason": "five_updates_raw_clip_above_50pct", "iteration": state.model_iteration})\n'
            '                    stop_file.touch()')
    config = {"num_envs": 4096, "num_steps_per_env": 64, "max_updates": 100,
              "save_interval": 100, "eval_interval": 100, "diagnostic_interval": 100, "seed": seed}
    (destination/"config.json").write_text(json.dumps(config, indent=2)+"\n")
    for script in (frozen/"training").rglob("*.py"):
        compile(script.read_text(encoding="utf-8"), str(script), "exec")
    record = {"baseline_sources": source_manifest["source_sha256"], "variant": variant,
              "seed": seed, "recipe_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "frozen": str(frozen), "budget_transitions": 26214400}
    (destination/"preparation.json").write_text(json.dumps(record, indent=2)+"\n")
    print(json.dumps(record), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--preset", choices=PRESETS, required=True)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    prepare(args.source, args.destination, args.preset, args.seed)
