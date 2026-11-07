"""自建 DuckWalk mjlab 环境（GPU 物理）——本项目自设计，非上游任务配置。

迁移自 CPU 版 DuckStandEnv（v0.8 终版语义）：
- 观测 48 维：projected_gravity(3)+joint_pos_rel(14)+joint_vel_rel(14)+last_action(14)
  + [vx_cmd, vx_actual](2) + generated_commands(2)。相位/EMA 不迁（v0.8/v0.9 已证无效/有害）。
- 命令：自写 VelocityCommand（25% 零档 + U(-0.2,0.2)，回合重采样）。
- 奖励：vel_track 2.0 / upright 1.0 / height 1.0 / joint_home 0.1 / action_rate -0.5 / alive 0.25。
- 终止：倾角(|g_xy|>0.9) + 高度(<0.6×HOME) + time_out。
- 事件：reset 扰动（关节±0.015rad/姿态）+ 推扰（1–4N 水平脉冲，内置速度式推）。
执行器：IdealPd（stiffness 25/damping 2/effort 0.94 + BAM armature/摩擦）。
"""

from __future__ import annotations

import json
from pathlib import Path

import mujoco
import torch

from mjlab.actuator import IdealPdActuatorCfg
from mjlab.entity import Entity, EntityArticulationInfoCfg, EntityCfg
from mjlab.envs import ManagerBasedRlEnv, ManagerBasedRlEnvCfg
from mjlab.envs.mdp import (
    generated_commands,
    joint_pos_rel,
    joint_vel_rel,
    last_action,
    projected_gravity,
    push_by_setting_velocity,
    reset_joints_by_offset,
    root_height_below_minimum,
    time_out,
)
from mjlab.envs.mdp.actions import JointPositionActionCfg
from mjlab.managers.command_manager import CommandTerm, CommandTermCfg
from mjlab.managers.event_manager import EventTermCfg
from mjlab.managers.observation_manager import (
    ObservationGroupCfg,
    ObservationTermCfg,
)
from mjlab.managers.reward_manager import RewardTermCfg
from mjlab.managers.scene_entity_config import SceneEntityCfg
from mjlab.managers.termination_manager import TerminationTermCfg
from mjlab.scene import SceneCfg
from mjlab.sim import MujocoCfg, SimulationCfg
from mjlab.terrains import TerrainEntityCfg

_DIR = Path(__file__).resolve().parents[1]
XML = _DIR / "models" / "duck_v0.xml"
HOME = json.loads((_DIR / "params" / "home_pose.json").read_text(encoding="utf-8"))["joint_pos"]

JOINT_ORDER = [
    "left_hip_yaw", "left_hip_roll", "left_hip_pitch", "left_knee", "left_ankle",
    "neck_pitch", "head_pitch", "head_yaw", "head_roll",
    "right_hip_yaw", "right_hip_roll", "right_hip_pitch", "right_knee", "right_ankle",
]
Z_HOME = 0.1182  # HOME 贴地高度（参数表派生值）


def _duck_spec():
    spec = mujoco.MjSpec.from_file(str(XML))
    for act in list(spec.actuators):
        spec.delete(act)
    return spec


# ---------- 命令（自写：25% 零档 + U(-0.2,0.2)） ----------

class DuckVelocityCommand(CommandTerm):
    """自写一维速度命令：25% 零档 + U(-0.2,0.2)，回合重采样。"""

    def __init__(self, cfg, env):
        super().__init__(cfg, env)
        self._cmd = torch.zeros(self.num_envs, 2, device=self.device)

    @property
    def command(self) -> torch.Tensor:
        return self._cmd

    def _resample_command(self, env_ids: torch.Tensor) -> None:
        zero = torch.rand(len(env_ids), device=self.device) < 0.25
        u = torch.empty(len(env_ids), device=self.device).uniform_(-0.2, 0.2)
        self._cmd[env_ids, 0] = torch.where(zero, torch.zeros_like(u), u)
        self._cmd[env_ids, 1] = 0.0

    def _update_command(self) -> None:
        pass

    def _update_metrics(self) -> None:
        pass


class DuckVelocityCommandCfg(CommandTermCfg):
    resampling_time_range: tuple[float, float] = (10.0, 10.0)

    def build(self, env) -> DuckVelocityCommand:
        return DuckVelocityCommand(self, env)


# ---------- 自写观测 ----------

def duck_vx_obs(env: ManagerBasedRlEnv, asset_cfg: SceneEntityCfg) -> torch.Tensor:
    """[vx_cmd, vx_world] → 机体系前向速度。"""
    asset: Entity = env.scene[asset_cfg.name]
    vx = asset.data.root_link_lin_vel_b[:, 0]
    cmd = env.command_manager.get_term("velocity").command[:, 0]
    return torch.stack([cmd, vx], dim=-1)


# ---------- 自写奖励 ----------

def _home_tensor(env, asset_cfg):
    asset: Entity = env.scene[asset_cfg.name]
    home = torch.tensor([HOME[n] for n in JOINT_ORDER], device=env.device)
    return asset, home


def duck_upright(env, asset_cfg) -> torch.Tensor:
    asset: Entity = env.scene[asset_cfg.name]
    g = asset.data.projected_gravity_b
    return -g[:, 2]


def duck_height(env, asset_cfg) -> torch.Tensor:
    asset: Entity = env.scene[asset_cfg.name]
    z = asset.data.root_link_pos_w[:, 2]
    return torch.exp(-((z - Z_HOME) / 0.05) ** 2)


def duck_joint_home(env, asset_cfg) -> torch.Tensor:
    asset, home = _home_tensor(env, asset_cfg)
    q = asset.data.joint_pos[:, asset_cfg.joint_ids]
    return torch.exp(-torch.mean((q - home) ** 2, dim=-1) / 0.25)


def duck_vel_track(env, asset_cfg) -> torch.Tensor:
    asset: Entity = env.scene[asset_cfg.name]
    cmd = env.command_manager.get_term("velocity").command[:, 0]
    vx = asset.data.root_link_lin_vel_b[:, 0]
    return torch.exp(-((vx - cmd) / 0.25) ** 2)


# ---------- 自写终止 ----------

def duck_bad_orientation(env, asset_cfg, threshold: float = 0.9) -> torch.Tensor:
    asset: Entity = env.scene[asset_cfg.name]
    g = asset.data.projected_gravity_b
    return torch.norm(g[:, :2], dim=-1) > threshold


# ---------- 环境装配 ----------

def duck_walk_env_cfg(num_envs: int = 4096, play: bool = False) -> ManagerBasedRlEnvCfg:
    joints = SceneEntityCfg("robot", joint_names=(r".*",))
    robot = EntityCfg(
        spec_fn=_duck_spec,
        articulation=EntityArticulationInfoCfg(
            actuators=(IdealPdActuatorCfg(
                target_names_expr=(r".*",),
                stiffness=25.0, damping=2.0, effort_limit=0.94,
                armature=0.00178, frictionloss=0.0158,
            ),),
        ),
    )

    obs_terms = {
        "gravity": ObservationTermCfg(func=projected_gravity, params={"asset_cfg": joints}),
        "joint_pos": ObservationTermCfg(func=joint_pos_rel, params={"asset_cfg": joints}),
        "joint_vel": ObservationTermCfg(func=joint_vel_rel, params={"asset_cfg": joints}),
        "last_action": ObservationTermCfg(func=last_action),
        "vx": ObservationTermCfg(func=duck_vx_obs, params={"asset_cfg": joints}),
        "command": ObservationTermCfg(func=generated_commands, params={"command_name": "velocity"}),
    }
    events = {
        "reset_joints": EventTermCfg(
            func=reset_joints_by_offset,
            mode="reset",
            params={
                "asset_cfg": joints,
                "position_range": (-0.015, 0.015),
                "velocity_range": (0.0, 0.0),
            },
        ),
        "push": EventTermCfg(
            func=push_by_setting_velocity,
            mode="interval",
            interval_range_s=(1.0, 4.0),
            params={
                "asset_cfg": SceneEntityCfg("robot", body_names=("trunk_base",)),
                "velocity_range": {"x": (-1.2, 1.2), "y": (-1.2, 1.2)},
            },
        ),
    }
    rewards = {
        "vel_track": RewardTermCfg(func=duck_vel_track, weight=2.0, params={"asset_cfg": joints}),
        "upright": RewardTermCfg(func=duck_upright, weight=1.0, params={"asset_cfg": joints}),
        "height": RewardTermCfg(func=duck_height, weight=1.0, params={"asset_cfg": joints}),
        "joint_home": RewardTermCfg(func=duck_joint_home, weight=0.1, params={"asset_cfg": joints}),
    }
    terminations = {
        "bad_orientation": TerminationTermCfg(
            func=duck_bad_orientation, params={"asset_cfg": joints}),
        "low_height": TerminationTermCfg(
            func=root_height_below_minimum,
            params={"asset_cfg": joints, "minimum_height": 0.6 * Z_HOME},
        ),
        "time_out": TerminationTermCfg(func=time_out, time_out=True),
    }

    return ManagerBasedRlEnvCfg(
        scene=SceneCfg(
            terrain=TerrainEntityCfg(terrain_type="plane"),
            entities={"robot": robot},
            num_envs=num_envs, env_spacing=2.0,
        ),
        observations={"actor": ObservationGroupCfg(dict(obs_terms)),
                      "critic": ObservationGroupCfg(dict(obs_terms))},
        actions={"joints": JointPositionActionCfg(
            entity_name="robot", actuator_names=(r".*",), scale=0.5)},
        commands={"velocity": DuckVelocityCommandCfg(resampling_time_range=(10.0, 10.0))},
        events={} if play else events,
        rewards=rewards,
        terminations=terminations,
        sim=SimulationCfg(mujoco=MujocoCfg(timestep=0.002)),
        decimation=10,
        episode_length_s=10.0,
    )
