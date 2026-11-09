"""从原基线创建固定物理层的足部奖励/渐进平滑实验。"""
import argparse
import hashlib
import json
from pathlib import Path
from prepare import PRESETS, prepare, replace

GAIT_PRESETS = {
    "gait010": {"feet_enabled": True, "target_height_m": .01, "raw_ramp": False},
    "gait020": {"feet_enabled": True, "target_height_m": .02, "raw_ramp": False},
    "rawramp": {"feet_enabled": False, "target_height_m": .01, "raw_ramp": True},
    "gait010_rawramp": {"feet_enabled": True, "target_height_m": .01, "raw_ramp": True},
}


def prepare_gait(source, destination, preset, seed=42):
    PRESETS[preset] = {"alpha": 1., "smooth_weight": .05, "damping": 2., "gait": GAIT_PRESETS[preset]}
    prepare(source, destination, preset, seed)
    frozen = destination/"frozen"
    env = frozen/"training/mjlab_duck/locomotion_env.py"
    replace(env, 'AMPLITUDE = json.loads((ROOT / "experiments/amplitude/variant.json").read_text())',
            'AMPLITUDE = json.loads((ROOT / "experiments/amplitude/variant.json").read_text())\n'
            'from experiments.amplitude.gait import sample as gait_sample, reward as gait_reward')
    fields = ('        self.gait_air = zeros(2); self.gait_peak = zeros(2)\n'
              '        self.gait_seen = zeros(2, dtype=torch.bool); self.gait_contact = zeros(2, dtype=torch.bool)\n'
              '        self.gait_height = zeros(2); self.gait_reward_terms = zeros(4)\n'
              '        self.gait_landing_cost = zeros(); self.gait_landing_count = zeros()\n'
              '        self.gait_clearance_cost = zeros(); self.gait_slip_cost = zeros(); self.gait_samples = zeros()')
    replace(env, '        self.rp_square_sum = zeros(2)', '        self.rp_square_sum = zeros(2)\n'+fields)
    replace(env, '        self.filtered = torch.zeros_like(self.raw)',
            '        self.filtered = torch.zeros_like(self.raw)\n        self.gait_previous_raw = torch.zeros_like(self.raw)')
    replace(env, '        self.filtered[ids] = 0', '        self.filtered[ids] = 0\n        self.gait_previous_raw[ids] = 0')
    replace(env, '        self.raw.copy_(torch.nan_to_num(actions, nan=0., posinf=0., neginf=0.))',
            '        self.gait_previous_raw.copy_(self.raw)\n        self.raw.copy_(torch.nan_to_num(actions, nan=0., posinf=0., neginf=0.))')
    replace(env, '    if env._sim_step_counter % env.cfg.decimation == 0:',
            '    env._gait_height = AMPLITUDE["gait"]["target_height_m"]\n'
            '    gait_sample(env, valid, ground0, ground1)\n'
            '    if env._sim_step_counter % env.cfg.decimation == 0:')
    replace(env, '    result = env.locomotion.reward(action.actual, action.previous)',
            '    result = env.locomotion.reward(action.actual, action.previous)\n    result = gait_reward(env, AMPLITUDE)')
    replace(env, '    env.extras["locomotion"] = {name: getattr(env.locomotion, name).clone() for name in names}',
            '    env.extras["locomotion"] = {name: getattr(env.locomotion, name).clone() for name in names}\n'
            '    env.extras["locomotion"]["gait_reward_terms"] = env.locomotion.gait_reward_terms.clone()')
    train = frozen/"training/mjlab_duck/train_locomotion.py"
    replace(train, '                logger.write(record)',
            '                from experiments.amplitude.gait import take_log\n'
            '                record["gait"] = take_log(env.unwrapped)\n                logger.write(record)')
    diagnostic = frozen/"training/experiments/amplitude/diagnose.py"
    replace(diagnostic, '"qpos","reward_terms")}', '"qpos","reward_terms","gait_reward_terms")}')
    replace(diagnostic, '"reward_terms":state.reward_terms[0]}',
            '"reward_terms":state.reward_terms[0],"gait_reward_terms":state.gait_reward_terms[0]}')
    for rel in ("training/models/duck_v0.xml", "training/params/home_pose.json"):
        if (source/rel).read_bytes() != (frozen/rel).read_bytes():
            raise ValueError("Physical source changed: "+rel)
    cfg_text = (frozen/"training/mjlab_duck/locomotion_cfg.py").read_text(encoding="utf-8")
    if cfg_text != (source/"training/mjlab_duck/locomotion_cfg.py").read_text(encoding="utf-8").replace(
            '    ROOT, HOME, Z_HOME, JOINT_ORDER,', '    AMPLITUDE, ROOT, HOME, Z_HOME, JOINT_ORDER,').replace(
            'stiffness=25., damping=2., effort_limit=.94,', 'stiffness=25., damping=AMPLITUDE["damping"], effort_limit=.94,'):
        raise ValueError("Unexpected environment/physics configuration delta")
    for path in (frozen/"training").rglob("*.py"):
        compile(path.read_text(encoding="utf-8"), str(path), "exec")
    record = json.loads((destination/"preparation.json").read_text())
    record.update(gait_recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  physical_files_unchanged=True, scope="reward and read-only instrumentation only")
    (destination/"preparation.json").write_text(json.dumps(record,indent=2)+"\n")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--destination", type=Path, required=True)
    p.add_argument("--preset", choices=GAIT_PRESETS, required=True)
    p.add_argument("--seed", type=int, default=42)
    a = p.parse_args()
    prepare_gait(a.source, a.destination, a.preset, a.seed)
