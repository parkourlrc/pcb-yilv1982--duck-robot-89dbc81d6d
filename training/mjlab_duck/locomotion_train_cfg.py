"""已确认的两阶段训练配置；旧测速入口保持独立。"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import math
from typing import Any

from .experiment_config import default_rewards, validate_rewards, validate_training


@dataclass(frozen=True)
class CurriculumConfig:
    stage: int = 1
    probabilities: tuple[float, ...] = (0., 1., 0., 0., 0.)

    def __post_init__(self):
        if type(self.stage) is not int or self.stage not in (1, 2):
            raise ValueError("stage must be 1 or 2")
        if len(self.probabilities) != 5 or any(isinstance(value, bool) or not math.isfinite(value) or value < 0 for value in self.probabilities) or abs(sum(self.probabilities)-1) > 1e-9:
            raise ValueError("five nonnegative probabilities summing to one are required")


STAGE1 = CurriculumConfig(1, (0., 1., 0., 0., 0.))
STAGE2 = CurriculumConfig(2, (.20, .30, .30, .15, .05))


@dataclass(frozen=True)
class LocomotionTrainConfig:
    num_envs: int = 4096
    num_steps_per_env: int = 64
    max_updates: int = 1000
    save_interval: int = 100
    eval_interval: int | None = None
    diagnostic_interval: int = 200
    seed: int = 42
    gamma: float = .995
    lam: float = .95
    learning_rate: float = 3e-4
    desired_kl: float = .01
    num_learning_epochs: int = 5
    num_mini_batches: int = 4
    entropy_coef: float = .005
    value_loss_coef: float = 1.
    clip_param: float = .2
    max_grad_norm: float = 1.
    init_std: float = .30
    finite_horizon: bool = True
    init_at_random_ep_len: bool = False
    clip_actions: Any = None
    stage1: CurriculumConfig = STAGE1
    stage2: CurriculumConfig = STAGE2
    reward_config: dict = field(default_factory=default_rewards)

    def __post_init__(self):
        if self.eval_interval is None:
            object.__setattr__(self, "eval_interval", self.save_interval)
        for name in ("num_envs", "num_steps_per_env", "max_updates", "save_interval", "eval_interval", "diagnostic_interval", "num_mini_batches"):
            if type(getattr(self, name)) is not int or getattr(self, name) < 1:
                raise ValueError(f"{name} must be positive")
        if not self.finite_horizon or self.init_at_random_ep_len or self.clip_actions is not None:
            raise ValueError("finite horizon, HOME starts and raw action history are required")
        validate_training(asdict(self))
        object.__setattr__(self, "reward_config", validate_rewards(self.reward_config))

    @property
    def global_transitions_per_update(self):
        return self.num_envs*self.num_steps_per_env

    @property
    def max_transitions(self):
        return self.global_transitions_per_update*self.max_updates

    def as_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, values):
        values = dict(values)
        for name in ("stage1", "stage2"):
            if isinstance(values.get(name), dict):
                item = values[name]
                values[name] = CurriculumConfig(item["stage"], tuple(item["probabilities"]))
        return cls(**values)


def ppo_config(cfg: LocomotionTrainConfig | None = None):
    from mjlab.rl import RslRlModelCfg, RslRlOnPolicyRunnerCfg, RslRlPpoAlgorithmCfg

    cfg = cfg or LocomotionTrainConfig()
    result = asdict(RslRlOnPolicyRunnerCfg(
        actor=RslRlModelCfg(hidden_dims=(128, 128), activation="elu", obs_normalization=True,
                            distribution_cfg={"class_name": "GaussianDistribution", "init_std": cfg.init_std, "std_type": "log"}),
        critic=RslRlModelCfg(hidden_dims=(128, 128), activation="elu", obs_normalization=True),
        algorithm=RslRlPpoAlgorithmCfg(
            learning_rate=cfg.learning_rate, schedule="adaptive", desired_kl=cfg.desired_kl,
            num_learning_epochs=cfg.num_learning_epochs, num_mini_batches=cfg.num_mini_batches,
            gamma=cfg.gamma, lam=cfg.lam, entropy_coef=cfg.entropy_coef,
            max_grad_norm=cfg.max_grad_norm, value_loss_coef=cfg.value_loss_coef,
            use_clipped_value_loss=True, clip_param=cfg.clip_param,
            normalize_advantage_per_mini_batch=False, optimizer="adam"),
        num_steps_per_env=cfg.num_steps_per_env, max_iterations=cfg.max_updates,
        save_interval=cfg.save_interval, seed=cfg.seed,
        obs_groups={"actor": ("actor",), "critic": ("critic",)},
        logger="tensorboard", upload_model=False, clip_actions=None,
        experiment_name="duck_locomotion"))
    result["check_for_nan"] = True
    result["is_finite_horizon"] = True
    return result
