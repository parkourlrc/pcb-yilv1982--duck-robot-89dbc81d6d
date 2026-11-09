"""训练与奖励的版本化字段目录；不依赖 GPU 或网页服务。"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import math
from pathlib import Path


REWARD_TERMS = {
    "forward": ("前速跟踪", 1, 3., "posture_gate * exp(-(vx_error / vx_sigma)^2)", "所有命令"),
    "yaw": ("转速跟踪", 1, 3., "posture_gate * exp(-(yaw_error / yaw_sigma)^2)", "非零转向命令"),
    "stand": ("静止保持", 1, 3., "posture_gate * exp(-(speed / stand_sigma)^2) * yaw_zero", "前速和转速命令均为零"),
    "lateral": ("抑制侧移", 1, .5, "auxiliary_gate * exp(-(vy / lateral_sigma)^2)", "所有命令"),
    "straight_yaw": ("直走方向", 1, .5, "auxiliary_gate * yaw_zero", "正前速且零转向"),
    "anchor": ("锚点保持", 1, 1., "auxiliary_gate * exp(-(anchor_distance / anchor_sigma)^2)", "已建立锚点"),
    "posture": ("姿态与高度", 1, .5, "auxiliary_gate * tilt_kernel * height_kernel", "所有命令"),
    "smooth": ("动作平滑", -1, .05, "actual: min(mean(delta_actual^2)/smooth_sigma_squared,1); raw: sum(delta_raw^2)", "所有命令"),
    "late": ("减速/全停超时", -1, .5, "late_indicator", "固定的3秒超时规则"),
    "air": ("足部腾空", 1, 3., "sum(air_min_s < air_time < air_max_s)", "移动命令及已有接触历史"),
    "clearance": ("足底净空", -1, 2., "mean_substep(sum(abs(height-target_height_m)*foot_horizontal_speed))", "移动命令"),
    "swing": ("落地摆动峰值", -1, .25, "sum_landing((peak/target_height_m-1)^2)", "移动命令及有效首次落地"),
    "slip": ("接触滑移", -1, .1, "mean_substep(sum(contact_horizontal_speed_squared))", "移动命令"),
    "failure": ("失败终止代价", -1, 100., "failed_indicator", "固定失败与终止规则"),
}
BASE_NAMES = tuple(REWARD_TERMS)[:9]
FOOT_NAMES = ("air", "clearance", "swing", "slip")
SCALE_FIELDS = {
    "velocity_relative_sigma": ("速度跟踪相对尺度", .25, "比例"),
    "velocity_min_sigma": ("前速跟踪最小尺度", .005, "m/s"),
    "yaw_min_sigma": ("转速跟踪最小尺度", math.pi/180, "rad/s"),
    "yaw_zero_sigma": ("零转速尺度", 3*math.pi/180, "rad/s"),
    "posture_gate_tilt_sigma": ("主奖励姿态门控尺度", 20*math.pi/180, "rad"),
    "posture_gate_height_sigma": ("主奖励高度门控尺度", .03, "m"),
    "stand_sigma": ("静止速度尺度", .01, "m/s"),
    "lateral_sigma": ("侧向速度尺度", .01, "m/s"),
    "anchor_sigma": ("锚点距离尺度", .03, "m"),
    "posture_tilt_sigma": ("姿态奖励倾角尺度", 15*math.pi/180, "rad"),
    "posture_height_sigma": ("姿态奖励高度尺度", .02, "m"),
    "smooth_sigma_squared": ("actual平滑平方尺度", .01, "归一化动作平方"),
    "target_height_m": ("足底目标净空", .01, "m"),
    "air_min_s": ("腾空时间下限", .125, "s"),
    "air_max_s": ("腾空时间上限", .300, "s"),
}
TRAIN_FIELDS = {
    "num_envs": ("全局并行环境数", "integer", 1, None, "执行"),
    "num_steps_per_env": ("每环境采样步数", "integer", 1, None, "执行"),
    "max_updates": ("最大更新轮数", "integer", 1, None, "执行"),
    "save_interval": ("保存间隔", "integer", 1, None, "执行"),
    "eval_interval": ("评估间隔", "integer", 1, None, "执行"),
    "diagnostic_interval": ("诊断间隔", "integer", 1, None, "执行"),
    "seed": ("随机种子", "integer", 0, 4294967295, "执行"),
    "gamma": ("回报折扣gamma", "number", 0, 1, "PPO"),
    "lam": ("优势估计lambda", "number", 0, 1, "PPO"),
    "learning_rate": ("学习率", "number", 0, None, "PPO"),
    "desired_kl": ("目标KL", "number", 0, None, "PPO"),
    "num_learning_epochs": ("优化epoch", "integer", 1, None, "PPO"),
    "num_mini_batches": ("mini-batch数", "integer", 1, None, "PPO"),
    "entropy_coef": ("熵系数", "number", 0, None, "PPO"),
    "value_loss_coef": ("价值损失系数", "number", 0, None, "PPO"),
    "clip_param": ("PPO裁剪系数", "number", 0, 1, "PPO"),
    "max_grad_norm": ("梯度范数上限", "number", 0, None, "PPO"),
    "init_std": ("初始探索标准差", "number", 0, None, "PPO"),
}
STRICT_POSITIVE = {"learning_rate", "desired_kl", "max_grad_norm", "init_std", "clip_param"}
LOCKED = {
    "finite_horizon": True, "init_at_random_ep_len": False, "clip_actions": None,
    "stage1": {"stage": 1, "probabilities": [0., 1., 0., 0., 0.]},
}


def default_rewards():
    return {"schema": 1, "terms": {name: {"enabled": name not in FOOT_NAMES, "weight": info[2]}
            for name, info in REWARD_TERMS.items()},
            "scales": {name: info[1] for name, info in SCALE_FIELDS.items()},
            "smoothing": "actual", "stage_overrides": {}, "schedule": []}


def _number(value, name, minimum=0, maximum=None, strict=False, integer=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name}: finite numeric value required")
    if integer and type(value) is not int:
        raise ValueError(f"{name}: integer required")
    if value < minimum or strict and value == minimum or maximum is not None and value > maximum:
        raise ValueError(f"{name}: value outside allowed range")
    return value


def _reward_values(values, base, prefix="reward_config"):
    if not isinstance(values, dict) or set(values)-{"terms", "scales", "smoothing"}:
        raise ValueError(f"{prefix}: unknown reward fields")
    result = deepcopy(base)
    terms = values.get("terms", {})
    if not isinstance(terms, dict) or set(terms)-set(REWARD_TERMS):
        raise ValueError(f"{prefix}.terms: unknown reward term")
    for name, settings in terms.items():
        if not isinstance(settings, dict) or set(settings)-{"enabled", "weight"}:
            raise ValueError(f"{prefix}.terms.{name}: unknown field")
        current = result["terms"][name]
        if "enabled" in settings:
            if type(settings["enabled"]) is not bool or name == "failure" and not settings["enabled"]:
                raise ValueError(f"{prefix}.terms.{name}.enabled: invalid toggle")
            current["enabled"] = settings["enabled"]
        if "weight" in settings:
            current["weight"] = _number(settings["weight"], name+".weight", strict=name == "failure")
    scales = values.get("scales", {})
    if not isinstance(scales, dict) or set(scales)-set(SCALE_FIELDS):
        raise ValueError(f"{prefix}.scales: unknown reward scale")
    for name, value in scales.items():
        result["scales"][name] = _number(value, name, strict=True)
    if result["scales"]["air_min_s"] >= result["scales"]["air_max_s"]:
        raise ValueError("air_min_s must be smaller than air_max_s")
    if "smoothing" in values:
        if values["smoothing"] not in ("actual", "raw"):
            raise ValueError("unknown smoothing formula")
        result["smoothing"] = values["smoothing"]
    return result


def validate_rewards(values=None):
    values = {} if values is None else values
    if not isinstance(values, dict) or set(values)-set(default_rewards()):
        raise ValueError("reward_config: unknown fields")
    if type(values.get("schema", 1)) is not int or values.get("schema", 1) != 1:
        raise ValueError("unsupported reward schema")
    result = _reward_values({key: value for key, value in values.items() if key in ("terms", "scales", "smoothing")}, default_rewards())
    overrides = values.get("stage_overrides", {})
    if not isinstance(overrides, dict) or set(overrides)-{"1", "2"}:
        raise ValueError("reward stage overrides must use keys 1 and 2")
    for stage, override in overrides.items():
        _reward_values(override, result, "stage_overrides."+stage)
    schedule = values.get("schedule", [])
    if not isinstance(schedule, list):
        raise ValueError("reward schedule must be an ordered list")
    previous = -1
    for node in schedule:
        if not isinstance(node, dict) or set(node) != {"update", "values"}:
            raise ValueError("reward schedule nodes require update and values")
        _number(node["update"], "schedule.update", integer=True)
        if node["update"] <= previous:
            raise ValueError("reward schedule updates must strictly increase")
        previous = node["update"]
    for stage in ("1", "2"):
        current = _reward_values(overrides.get(stage, {}), result)
        for node in schedule:
            current = _reward_values(node["values"], current, "schedule.values")
    result["stage_overrides"] = deepcopy(overrides)
    result["schedule"] = deepcopy(schedule)
    return result


def effective_rewards(config, stage=1, completed_updates=0):
    result = deepcopy(config)
    result = _reward_values(config.get("stage_overrides", {}).get(str(stage), {}), result)
    for node in config.get("schedule", []):
        if node["update"] > completed_updates:
            break
        result = _reward_values(node["values"], result)
    return result


def validate_training(values):
    for name, info in TRAIN_FIELDS.items():
        _number(values[name], name, info[2], info[3], name in STRICT_POSITIVE, info[1] == "integer")
    if values["clip_param"] >= 1:
        raise ValueError("clip_param must be strictly between zero and one")
    for name, expected in LOCKED.items():
        actual = values.get(name)
        if isinstance(expected, bool) and type(actual) is not bool:
            raise ValueError(f"{name}: boolean required")
        if name == "stage1":
            actual = {"stage": actual.stage, "probabilities": list(actual.probabilities)} if hasattr(actual, "stage") else actual
            if isinstance(actual, dict) and set(actual) == {"stage", "probabilities"}:
                actual = {**actual, "probabilities": list(actual["probabilities"])}
        if actual != expected:
            raise ValueError(f"{name}: locked training contract")
    stage2 = values["stage2"]
    stage2 = {"stage": stage2.stage, "probabilities": list(stage2.probabilities)} if hasattr(stage2, "stage") else stage2
    if not isinstance(stage2, dict) or set(stage2) != {"stage", "probabilities"} or stage2["stage"] != 2:
        raise ValueError("stage2 must keep the existing stage identity")
    probabilities = stage2["probabilities"]
    if not isinstance(probabilities, (list, tuple)) or len(probabilities) != 5:
        raise ValueError("stage2 requires five family probabilities")
    for value in probabilities:
        _number(value, "stage2.probabilities", 0, 1)
    if abs(sum(probabilities)-1) > 1e-9:
        raise ValueError("stage2 probabilities must sum to one")


def resolve_config(parameters=None, rewards=None, curriculum=None, base=None):
    from .locomotion_train_cfg import LocomotionTrainConfig
    result = LocomotionTrainConfig().as_dict()
    if base:
        if set(base)-set(result):
            raise ValueError("unknown base training fields")
        result.update(deepcopy(base))
    parameters = parameters or {}
    if not isinstance(parameters, dict) or set(parameters)-set(result):
        raise ValueError("unknown or locked training fields")
    result.update(deepcopy(parameters))
    if rewards is not None:
        result["reward_config"] = deepcopy(rewards)
    if curriculum is not None:
        if not isinstance(curriculum, dict) or set(curriculum)-{"stage1", "stage2"}:
            raise ValueError("unknown curriculum fields")
        result.update(deepcopy(curriculum))
    return LocomotionTrainConfig.from_dict(result).as_dict()


def reward_presets():
    presets = {"baseline": default_rewards()}
    for name in ("gait010", "gait020", "rawramp", "gait010_rawramp"):
        config = default_rewards()
        for term in FOOT_NAMES:
            config["terms"][term]["enabled"] = name != "rawramp"
        config["scales"]["target_height_m"] = .02 if name == "gait020" else .01
        if "rawramp" in name:
            config["smoothing"] = "raw"
            config["schedule"] = [{"update": update, "values": {"terms": {"smooth": {"weight": weight}}}}
                                  for update, weight in ((0, .1), (25, .2), (50, .4), (75, .6), (90, 1.))]
        presets[name] = config
    return presets


def parameter_catalog():
    from .locomotion_train_cfg import LocomotionTrainConfig
    defaults = LocomotionTrainConfig().as_dict()
    fields = [{"key": name, "path": name, "label": info[0], "type": info[1], "group": info[4],
               "unit": "", "default": defaults[name], "min": info[2], "max": info[3],
               "exclusive_min": name in STRICT_POSITIVE, "exclusive_max": name == "clip_param", "locked": False,
               "source": "历史采用配置，非最优范围", "requires_new_experiment": True} for name, info in TRAIN_FIELDS.items()]
    for name, info in REWARD_TERMS.items():
        for setting, kind in (("enabled", "boolean"), ("weight", "number")):
            path = f"reward_config.terms.{name}.{setting}"
            fields.append({"key": path, "path": path, "label": info[0]+("启用" if setting == "enabled" else "幅值"),
                           "type": kind, "group": "奖励", "unit": "事件代价" if name == "failure" else "奖励率系数",
                           "default": defaults["reward_config"]["terms"][name][setting], "min": 0,
                           "exclusive_min": name == "failure", "locked": name == "failure" and setting == "enabled"})
    for name, info in SCALE_FIELDS.items():
        path = "reward_config.scales."+name
        fields.append({"key": path, "path": path, "label": info[0], "type": "number", "group": "奖励尺度", "unit": info[2],
                       "default": info[1], "min": 0, "exclusive_min": True, "locked": False})
    for index, label in enumerate(("原地转向", "直行", "移动转向", "联合动作", "静止")):
        path = f"stage2.probabilities.{index}"
        fields.append({"key": path, "path": path, "label": "阶段二"+label+"比例", "type": "number", "group": "课程",
                       "default": defaults["stage2"]["probabilities"][index], "min": 0, "max": 1, "locked": False})
    fields.append({"key": "reward_config.smoothing", "path": "reward_config.smoothing", "label": "平滑公式", "type": "enum",
                   "group": "奖励", "choices": ["actual", "raw"], "default": "actual", "locked": False})
    return {"schema": 1, "runtime_version": "locomotion-v3", "fields": fields, "defaults": defaults,
            "reward_terms": [{"key": name, "label": info[0], "sign": info[1], "formula": info[3], "gate": info[4],
                              "unit": "event_cost" if name == "failure" else "reward_rate", "implementation_version": "rewards-v1"}
                             for name, info in REWARD_TERMS.items()], "reward_presets": reward_presets(),
            "locked": ["physics", "Kp", "Kd", "HOME", "observation_action_contract", "network", "reset", "termination", "acceptance", "curriculum_gates"]}


config_catalog = parameter_catalog


def transfer_contract(root=None):
    root = Path(root) if root is not None else Path(__file__).resolve().parents[2]
    files = ("training/models/duck_v0.xml", "training/params/home_pose.json",
             "training/mjlab_duck/locomotion_cfg.py", "training/mjlab_duck/locomotion_env.py")
    return {"schema": 1, "physical_and_interface_sources": {
                name: hashlib.sha256((root/name).read_bytes()).hexdigest() for name in files},
            "observation": "61:omega3,gravity3,q14,dq14,raw_previous_action14,command3,reserved10",
            "action": "14:HOME+0.5*clip(raw,-1,1),joint_limits", "normalization": "rank_local",
            "actor": {"hidden_dims": [128, 128], "activation": "elu", "obs_normalization": True,
                      "distribution": "GaussianDistribution", "std_type": "log"}}
