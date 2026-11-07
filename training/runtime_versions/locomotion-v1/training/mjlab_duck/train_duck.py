#!/usr/bin/env python3
"""自建 DuckWalk mjlab 任务训练入口（GPU 物理 + rsl_rl PPO）。

用法（WSL training/ 下）：
    .venv-wsl/bin/python mjlab_duck/train_duck.py [mjlab train 参数]
回放使用独立入口：.venv-wsl/bin/python play_mujoco.py
任务注册后转交 mjlab.scripts.train（与上游同一 CLI，但任务为本项目自建）。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mjlab.rl import (  # noqa: E402
    RslRlModelCfg,
    RslRlOnPolicyRunnerCfg,
    RslRlPpoAlgorithmCfg,
)
from mjlab.tasks.registry import register_mjlab_task  # noqa: E402

from mjlab_duck.env_cfg import duck_walk_env_cfg  # noqa: E402

TASK_ID = "Duck-Walk-Flat-v1"


def duck_rl_cfg() -> RslRlOnPolicyRunnerCfg:
    return RslRlOnPolicyRunnerCfg(
        actor=RslRlModelCfg(
            hidden_dims=(128, 128), activation="elu", obs_normalization=True,
            distribution_cfg={"class_name": "GaussianDistribution",
                              "init_std": 1.0, "std_type": "scalar"},
        ),
        critic=RslRlModelCfg(
            hidden_dims=(128, 128), activation="elu", obs_normalization=True,
        ),
        algorithm=RslRlPpoAlgorithmCfg(
            learning_rate=3e-4, schedule="adaptive", desired_kl=0.01,
            num_learning_epochs=5, num_mini_batches=4,
            gamma=0.99, lam=0.95, entropy_coef=0.0,
        ),
        experiment_name="duck_walk",
        logger="tensorboard",
        upload_model=False,
        save_interval=50,
        num_steps_per_env=24,
        max_iterations=10_000,
    )


register_mjlab_task(
    task_id=TASK_ID,
    env_cfg=duck_walk_env_cfg(),
    play_env_cfg=duck_walk_env_cfg(play=True),
    rl_cfg=duck_rl_cfg(),
)


def main():
    import os
    os.environ.setdefault("PYTHONUTF8", "1")
    # rsl_rl 的代码快照功能对 /mnt 下含非 UTF-8 文件名的路径会崩（surrogate 编码错误）；
    # 快照仅用于 wandb 归档，本地 tensorboard 训练直接禁用。
    import rsl_rl.utils.logger as _rlog
    _rlog.Logger._store_code_state = lambda self, *a, **k: []
    from mjlab.scripts import train as mjlab_train
    sys.argv = ["train", TASK_ID] + sys.argv[1:]
    mjlab_train.main()


if __name__ == "__main__":
    main()
