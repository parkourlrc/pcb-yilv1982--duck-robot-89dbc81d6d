"""仅用于交互回放的配置；训练配置和观测/动作契约保持原样。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import mujoco
import torch

from mjlab_duck.env_cfg import DuckVelocityCommand, DuckVelocityCommandCfg, duck_walk_env_cfg

TRAINING_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CHECKPOINT = (
    TRAINING_DIR / "logs/rsl_rl/duck_walk/2026-10-19_15-02-25/model_9999.pt"
)


class PlaybackVelocityCommand(DuckVelocityCommand):
    """固定用户选择的前后速度；reset/定时重采样不覆盖该值。"""

    def __init__(self, cfg, env):
        super().__init__(cfg, env)
        self.manual_vx = float(cfg.initial_vx)
        self.set_velocity(self.manual_vx)

    def set_velocity(self, value: float) -> None:
        if not -0.2 <= value <= 0.2:
            raise ValueError("当前策略的前后速度范围为 -0.2 至 0.2 m/s")
        self.manual_vx = float(value)
        self._cmd[:, 0] = self.manual_vx
        self._cmd[:, 1] = 0.0

    def _resample_command(self, env_ids: torch.Tensor) -> None:
        self._cmd[env_ids, 0] = self.manual_vx
        self._cmd[env_ids, 1] = 0.0


@dataclass(kw_only=True)
class PlaybackVelocityCommandCfg(DuckVelocityCommandCfg):
    initial_vx: float = 0.0

    def build(self, env) -> PlaybackVelocityCommand:
        return PlaybackVelocityCommand(self, env)


def make_playback_config(*, simple: bool = False, velocity: float = 0.0):
    """只替换视觉源、手动命令和相机；不改控制/物理频率与策略接口。"""
    model_path = TRAINING_DIR / "models" / ("duck_v0.xml" if simple else "duck_visual.xml")
    if not model_path.is_file():
        raise FileNotFoundError(
            f"模型不存在：{model_path}；可用 --simple 查看现有简模。"
        )

    def playback_spec():
        spec = mujoco.MjSpec.from_file(str(model_path))
        # 与训练 _duck_spec 完全相同：由 mjlab 的 IdealPd 创建执行器。
        for actuator in list(spec.actuators):
            spec.delete(actuator)
        return spec

    cfg = duck_walk_env_cfg(num_envs=1, play=True)
    cfg.scene.entities["robot"].spec_fn = playback_spec
    cfg.commands["velocity"] = PlaybackVelocityCommandCfg(
        resampling_time_range=(10.0, 10.0), initial_vx=velocity
    )
    cfg.viewer.distance = 0.65
    cfg.viewer.elevation = -20.0
    cfg.viewer.azimuth = 135.0
    cfg.viewer.lookat = (0.0, 0.0, 0.12)
    cfg.viewer.max_extra_envs = 0
    return cfg, model_path
