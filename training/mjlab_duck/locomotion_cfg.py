"""独立联合环境装配；runner/任务注册留第④步。"""
from __future__ import annotations

import mujoco
from mjlab.actuator import IdealPdActuatorCfg
from mjlab.entity import EntityArticulationInfoCfg, EntityCfg
from mjlab.envs import ManagerBasedRlEnvCfg
from mjlab.envs.mdp import reset_joints_by_offset, time_out
from mjlab.managers.event_manager import EventTermCfg
from mjlab.managers.metrics_manager import MetricsTermCfg
from mjlab.managers.observation_manager import ObservationGroupCfg, ObservationTermCfg
from mjlab.managers.reward_manager import RewardTermCfg
from mjlab.managers.scene_entity_config import SceneEntityCfg
from mjlab.managers.termination_manager import TerminationTermCfg
from mjlab.scene import SceneCfg
from mjlab.sim import MujocoCfg, SimulationCfg
from .locomotion_env import (
    ROOT, HOME, Z_HOME, JOINT_ORDER, LocomotionCommandCfg, OrderedActionCfg,
    observation, measure_substep, failure, trajectory_finished, reward_rate,
    failure_cost_rate, metric, STAGE_PROBABILITIES, FAMILY_PROBABILITIES,
)


def robot_spec():
    spec = mujoco.MjSpec.from_file(str(ROOT / "models/duck_v0.xml"))
    for actuator in list(spec.actuators):
        spec.delete(actuator)
    return spec


def locomotion_env_cfg(num_envs=4, *, evaluation=False, seed=0, stage=0, probabilities=None):
    if stage not in (0, 1, 2):
        raise ValueError("Unknown locomotion curriculum stage")
    expected = STAGE_PROBABILITIES.get(stage, FAMILY_PROBABILITIES)
    if probabilities is not None and stage != 2 and tuple(probabilities) != expected:
        raise ValueError("Curriculum probabilities differ from the confirmed stage")
    robot = EntityCfg(
        spec_fn=robot_spec,
        init_state=EntityCfg.InitialStateCfg(pos=(0., 0., Z_HOME), joint_pos=dict(HOME)),
        articulation=EntityArticulationInfoCfg(actuators=(IdealPdActuatorCfg(
            target_names_expr=JOINT_ORDER, stiffness=25., damping=2., effort_limit=.94,
            armature=.00178, frictionloss=.0158,
        ),)),
    )
    metrics = {"substep_max_drift": MetricsTermCfg(func=measure_substep, per_substep=True, reduce="last")}
    for name in ("max_drift", "brake_path", "anchor_time", "max_tilt", "min_height", "strict_drift", "strict_stop", "strict_path", "strict_full_stop", "strict_hold", "hold_complete", "reason"):
        metrics[name] = MetricsTermCfg(func=metric, params={"name": name}, reduce="last")
    return ManagerBasedRlEnvCfg(
        scene=SceneCfg(entities={"robot": robot}, num_envs=num_envs, env_spacing=2.),
        observations={key: ObservationGroupCfg({"contract": ObservationTermCfg(func=observation)}) for key in ("actor", "critic")},
        actions={"joints": OrderedActionCfg(entity_name="robot")},
        commands={"velocity": LocomotionCommandCfg(resampling_time_range=(150., 150.), strict=evaluation,
                                                   stage=stage, probabilities=probabilities if probabilities is not None else STAGE_PROBABILITIES.get(stage, FAMILY_PROBABILITIES))},
        events={"reset_joints": EventTermCfg(func=reset_joints_by_offset, mode="reset", params={
            "asset_cfg": SceneEntityCfg("robot", joint_names=JOINT_ORDER),
            "position_range": (-.005, .005), "velocity_range": (0., 0.),
        })},
        rewards={"task": RewardTermCfg(func=reward_rate, weight=1.), "failure": RewardTermCfg(func=failure_cost_rate, weight=1.)},
        terminations={"failure": TerminationTermCfg(func=failure),
                      "trajectory_end": TerminationTermCfg(func=trajectory_finished, time_out=True),
                      "time_limit": TerminationTermCfg(func=time_out, time_out=True)},
        metrics=metrics, sim=SimulationCfg(mujoco=MujocoCfg(timestep=.002, integrator="implicitfast"), njmax=256, nconmax=128),
        decimation=10, episode_length_s=150., auto_reset=not evaluation, seed=seed,
    )
