#!/usr/bin/env python3
"""duck 当前速度命令与相位任务的训练入口（SB3 PPO）。

用法（在 training/ 下）：
    .venv/Scripts/python.exe train.py --steps 200000
checkpoint 与日志写入 training/checkpoints/。
"""

from __future__ import annotations

import argparse
from pathlib import Path

from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback, CallbackList, CheckpointCallback
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.vec_env import DummyVecEnv, SubprocVecEnv

from duckstand.env import DuckStandEnv


def make_env():
    from stable_baselines3.common.monitor import Monitor
    return Monitor(DuckStandEnv())


class LogStdCap(BaseCallback):
    def __init__(self, cap: float):
        super().__init__()
        self.cap = cap

    def _on_step(self) -> bool:
        return True

    def on_rollout_start(self):
        self.model.policy.log_std.data.clamp_(max=self.cap)


def main():
    raise SystemExit("此历史训练入口已停用。请在训练平台登记任务与预算后使用版本化训练入口；历史策略可继续查看和回放。")
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=200_000)
    ap.add_argument("--envs", type=int, default=8)
    ap.add_argument("--continue-from", type=str, default=None, help="续训的 checkpoint 路径")
    ap.add_argument("--run-name", type=str, default="duck_stand_v0")
    ap.add_argument("--log-std", type=float, default=None,
                    help="续训时覆盖策略初始 log_std（如 -3.0），压低探索噪声")
    ap.add_argument("--log-std-cap", type=float, default=None,
                    help="每轮 rollout 开始时钳制 log_std 上限（如 -2.66≈std 0.07），"
                         "作为探索噪声控制项；其失败因果贡献尚未隔离")
    args = ap.parse_args()

    out_dir = Path(__file__).parent / "checkpoints" / args.run_name
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.envs >= 32:
        # Linux/WSL 大规模并行：fork 模式，make_env 模块级可 pickle
        venv = SubprocVecEnv([make_env for _ in range(args.envs)], start_method="fork")
    else:
        venv = DummyVecEnv([lambda: Monitor(DuckStandEnv()) for _ in range(args.envs)])

    n_steps = 128 if args.envs >= 32 else 512  # 大并行时缩小单环境 rollout
    if args.continue_from:
        model = PPO.load(args.continue_from, env=venv)
        if args.log_std is not None:
            model.policy.log_std.data.fill_(args.log_std)
            print(f"续训: {args.continue_from} (log_std 覆盖为 {args.log_std})")
        else:
            print(f"续训: {args.continue_from}")
    else:
        model = PPO(
            "MlpPolicy", venv,
            # 当前初始化 std=exp(-1)≈0.368；旧站立配置为 log_std=-1.9、scale=0.1。
            # 初始化字段不等于训练后std；更改scale/EMA续训也不保留原控制行为。
            policy_kwargs=dict(net_arch=[128, 128], log_std_init=-1.0),
            n_steps=n_steps, batch_size=4096, n_epochs=5,
            learning_rate=3e-4, gamma=0.99, gae_lambda=0.95,
            ent_coef=0.0, verbose=1,
            device="auto",
        )

    ckpt_cb = CheckpointCallback(save_freq=20_000, save_path=str(out_dir), name_prefix="ckpt")
    callbacks = [ckpt_cb]
    if args.log_std_cap is not None:
        callbacks.append(LogStdCap(args.log_std_cap))
    model.learn(total_timesteps=args.steps, callback=CallbackList(callbacks))
    model.save(out_dir / "final")
    print(f"已保存: {out_dir / 'final'}.zip")


if __name__ == "__main__":
    main()
