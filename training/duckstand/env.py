"""duck v0.8 速度命令与相位任务：历史站立任务的扩展，保留推扰。

3N×0.3s 满额率≥80% 尚未达到；旧“站立物理不可达”归因已于 2026-10-19 撤回，
见 docs/references/动作训练软件研究/failure-analysis-20261019.md。
观测 49 维：重力方向(3) + 关节角(14) + 关节速度(14) + 动作状态(14) + [vx_cmd, vx_actual]
+ [sin(φ), cos(φ)]（步态相位）。
v0.8 同时修复命令采样并引入相位辅助，不是单项因果对照。相位 φ 随时间循环，
频率随速度命令；当前奖励在前半周期偏好右脚腾空、后半周期偏好左脚腾空。
已知待修：动作状态观测晚一拍、目标角误用 motor 力矩范围裁剪、reset 未重置相位。
本轮只勘误注释，执行逻辑保持原状；旧45/47维策略不能直接用于当前环境。

不使用上游观测/奖励配置；接口定义见 training/README.md。
"""

from __future__ import annotations

import json
from pathlib import Path

import gymnasium as gym
import mujoco
import numpy as np

TRAIN = Path(__file__).resolve().parents[1]
MODEL_XML = TRAIN / "models" / "duck_v0.xml"
HOME_JSON = TRAIN / "params" / "home_pose.json"

CONTROL_HZ = 50.0
DECIMATION = 10  # × timestep 0.002s
# v0.6 起实验使用较大 scale；相同策略均值的目标偏移会随 scale 改变。
# EMA 的收益与代价尚未通过固定其他条件的对照隔离。
ACTION_SCALE = 0.5

# 速度命令（起步仅前后向，小速度段）
CMD_VX_RANGE = (-0.2, 0.2)   # m/s；v0.8 修复：reset 的命令采样行曾误入注释致 vx_cmd 恒 0
GAIT_FREQ_BASE = 0.8         # Hz，站立档相位频率
GAIT_FREQ_GAIN = 4.0         # Hz/(m/s)，步频随 |vx_cmd| 抬升
W_PHASE_FOOT = 2.0
CMD_ZERO_PROB = 0.15         # v0.6b：降低站立档占比，强化速度学习
# v0.2.2 起对目标指令做 EMA；50Hz、alpha=0.25 时等效时间常数 69.5ms，
# 100ms 阶跃响应约76.3%，不是纯延迟，也不等同固件斜率限制。
# v0.9 去 EMA 的一次失败不能证明所有无 EMA 配置都不可学；尚无部署一致性验证。
ACTION_EMA_ALPHA = 0.25
EPISODE_SECONDS = 10.0

# v0.3 推扰事件：训练中随机对躯干施加水平脉冲力，逼策略学会主动恢复。
# 历史8方向初标定：1N 100%、2N 62%、3N 12%、≥4N 0%；与正式20场景不是同一测试集。
# 当前1–4N随机分布未做渐进课程。设 PUSH_COUNT_RANGE=(0,0) 可整体关闭；
# interact.py 手推时置 env.push_enabled=False，避免覆写用户施加的力。
PUSH_COUNT_RANGE = (1, 3)          # 每回合推扰次数
PUSH_FORCE_RANGE = (1.0, 4.0)      # 力幅 N（水平）
PUSH_DURATION_RANGE = (0.2, 0.4)   # 持续 s
PUSH_FIRST_TIME_RANGE = (1.0, 8.0) # 首次时刻 s（留出站稳时间）
PUSH_INTERVAL_RANGE = (1.0, 3.0)   # 相邻推扰间隔 s

# 执行器一阶电机模型（参数来源 training/params/hd1910_bam_m6.json，LuwuDynamics 公开辨识）：
#   V_pwm = clip(KV·(q_target−q), ±vin)；i = (V_pwm − kt·ω)/R；τ = kt·i → motor ctrl。
#   电压饱和段空载速度被反电动势钳在 vin/kt ≈ 11.9 rad/s @7.4V；力矩饱和 kt·vin/R ≈ 0.94 N·m。
#   KV 为自选固件增益（小信号刚度 kt·KV/R ≈ 25 N·m/rad，与 v0 的 kp=25 相当），待整定。
MOTOR_KT = 0.6237611235393989
MOTOR_R = 4.910191564179625
MOTOR_VIN = 7.4
FIRMWARE_KV = 200.0  # V/rad

# 奖励权重（自选初始值；迭代时一次只改一项）
# v0.2.1：抖动诊断显示确定性策略每步 |Δa|≈0.32（目标角每步跳 ±0.03 rad、
# 关节每步摆 2.7°@50Hz），而旧平滑惩罚每步仅 ~0.005 分、占总奖励 <0.2%，
# 策略无动力收敛到"静止站"。加大 action_rate/mag 惩罚逼出安静站立。
# v0.3c 当时降低 joint_home/action_mag，意图减少对恢复动作的抑制；因果贡献未隔离。
# action_rate 当前比较 raw action 与上一 filtered action，不是相邻 raw/filtered 差分。
# alpha=0.25 时其平方项等于相邻 filtered 差分平方的16倍；惩罚语义待明确。
W_UPRIGHT = 1.0
W_HEIGHT = 1.0
W_JOINT_HOME = 0.1
W_ACTION_RATE = -0.5
W_ACTION_MAG = -0.01
W_VEL_TRACK = 4.0  # v0.6b：2.0 下学成'安全赖着不动'，加码逼出步态
W_FEET_AIR = 1.0   # v0.6c：脚腾空奖励（诱导抬脚迈步），每脚 0.5×min(air,0.4s)/0.4
W_ALIVE = 0.25     # v0.6c：从 0.5 降权，削弱'苟着不动'收益

Z_HOME_TOL = 0.05     # 高度奖励宽度（m）
TILT_TERMINATE = 0.9  # |重力水平分量| 超过此值判摔（cos 倾角 < ~0.44）


class DuckStandEnv(gym.Env):
    """MuJoCo 后端；qpos 布局 = freejoint(7) + 14 关节（XML 声明序）。"""

    metadata = {"render_modes": ["human", "rgb_array"], "render_fps": int(CONTROL_HZ)}

    def __init__(self, render_mode: str | None = None):
        self.render_mode = render_mode
        self.model = mujoco.MjModel.from_xml_path(str(MODEL_XML))
        self.data = mujoco.MjData(self.model)

        self.nq = self.model.nq
        self.nu = self.model.nu
        assert self.nu == 14 and self.nq == 21, f"模型维度异常: nq={self.nq} nu={self.nu}"

        home = json.loads(HOME_JSON.read_text(encoding="utf-8"))["joint_pos"]
        self.act_names = [
            mujoco.mj_id2name(self.model, mujoco.mjtObj.mjOBJ_ACTUATOR, i)
            for i in range(self.nu)
        ]
        self.home_q = np.array([home[n] for n in self.act_names], dtype=np.float64)
        self.qpos_addr = np.array([self.model.jnt_qposadr[i] for i in range(1, self.model.njnt)])
        self.ctrlrange = self.model.actuator_ctrlrange.copy()
        self.z_home = self.model.key_qpos[0][2]

        self.obs_dim = 3 + 14 + 14 + 14 + 2 + 2
        self._vx_cmd = 0.0
        self._phase = 0.0  # 步态相位 [0, 2π)
        self._air_time = np.zeros(2)  # [left, right] 脚离地累计秒数
        self.observation_space = gym.spaces.Box(-np.inf, np.inf, (self.obs_dim,), np.float64)
        self.action_space = gym.spaces.Box(-1.0, 1.0, (self.nu,), np.float64)

        self._last_action = np.zeros(self.nu)
        self._action_filtered = np.zeros(self.nu)
        self._step_count = 0
        self._renderer = None
        self._viewer = None
        # 推扰：施加对象为躯干；实例开关供交互模式关闭（False 时 step 不触碰 xfrc_applied）
        self.push_enabled = True
        self._trunk_bid = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_BODY, "trunk_base")
        self._push_schedule = []  # [(start_step, end_step, fx, fy), ...] 控制步计数

    def _sample_push_schedule(self):
        """按 PUSH_* 常量抽样本回合推扰时刻表（力水平方向随机）。"""
        rng = self.np_random
        n = int(rng.integers(PUSH_COUNT_RANGE[0], PUSH_COUNT_RANGE[1] + 1))
        schedule = []
        t = rng.uniform(*PUSH_FIRST_TIME_RANGE)
        for _ in range(n):
            start = int(t * CONTROL_HZ)
            dur = int(rng.uniform(*PUSH_DURATION_RANGE) * CONTROL_HZ)
            angle = rng.uniform(0, 2 * np.pi)
            mag = rng.uniform(*PUSH_FORCE_RANGE)
            schedule.append((start, start + dur, mag * np.cos(angle), mag * np.sin(angle)))
            t += rng.uniform(*PUSH_DURATION_RANGE) + rng.uniform(*PUSH_INTERVAL_RANGE)
        return schedule

    def _apply_push(self):
        """按时刻表写入/清除躯干外力，返回当前力幅（N）。"""
        active = 0.0
        for start, end, fx, fy in self._push_schedule:
            if start <= self._step_count < end:
                self.data.xfrc_applied[self._trunk_bid, :3] = (fx, fy, 0.0)
                active = float(np.hypot(fx, fy))
                return active
        self.data.xfrc_applied[self._trunk_bid, :3] = 0.0
        return active

    def _motor_torque(self, q_target: np.ndarray) -> np.ndarray:
        """一阶电机模型：固件电压环 + 反电动势限速，返回关节力矩。"""
        q = self.data.qpos[self.qpos_addr]
        dq = self.data.qvel[6:]
        v_pwm = np.clip(FIRMWARE_KV * (q_target - q), -MOTOR_VIN, MOTOR_VIN)
        current = (v_pwm - MOTOR_KT * dq) / MOTOR_R
        return MOTOR_KT * current

    # ---------- 观测 ----------

    def _gravity_body(self) -> np.ndarray:
        """重力方向在机体坐标系的单位向量（直立时 ≈ (0,0,-1)）。"""
        q = self.data.qpos[3:7]
        rot = np.zeros(9)
        mujoco.mju_quat2Mat(rot, q)
        rot = rot.reshape(3, 3)
        g_world = np.array([0.0, 0.0, -1.0])
        return rot.T @ g_world

    def _get_obs(self) -> np.ndarray:
        q_rel = self.data.qpos[self.qpos_addr] - self.home_q
        dq = self.data.qvel[6:]
        return np.concatenate([self._gravity_body(), q_rel, dq, self._last_action,
                               [self._vx_cmd, self.data.qvel[0]],
                               [np.sin(self._phase), np.cos(self._phase)]]).astype(np.float64)

    # ---------- 回合流程 ----------

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        mujoco.mj_resetData(self.model, self.data)
        self.data.qpos[:] = self.model.key_qpos[0]
        self.data.qvel[:] = 0.0

        rng = self.np_random
        self.data.qpos[self.qpos_addr] += rng.uniform(-0.015, 0.015, self.nu)
        self.data.qpos[2] += rng.uniform(-0.005, 0.005)
        self.data.qpos[3:7] = self._tilt_quat(rng.uniform(0.0, 0.04))
        self.data.qvel[2] = rng.uniform(-0.03, 0.03)

        self._last_action = np.zeros(self.nu)
        self._action_filtered = np.zeros(self.nu)
        self._step_count = 0
        self._vx_cmd = 0.0
        self._air_time = np.zeros(2)  # [left, right] 脚离地累计秒数
        self._vx_cmd = 0.0 if rng.random() < CMD_ZERO_PROB else rng.uniform(*CMD_VX_RANGE)
        self._push_schedule = self._sample_push_schedule() if self.push_enabled else []
        self.data.xfrc_applied[:] = 0.0
        self.data.ctrl[:] = 0.0  # motor ctrl = 关节力矩
        mujoco.mj_forward(self.model, self.data)
        return self._get_obs(), {}

    def _tilt_quat(self, angle: float) -> np.ndarray:
        """绕随机水平轴倾斜 angle 的四元数（wxyz）。"""
        rng = self.np_random
        axis = np.array([rng.uniform(-1, 1), rng.uniform(-1, 1), 0.0])
        axis /= np.linalg.norm(axis) + 1e-9
        quat = np.zeros(4)
        mujoco.mju_axisAngle2Quat(quat, axis, angle)
        return quat

    def step(self, action):
        gait_freq = GAIT_FREQ_BASE + GAIT_FREQ_GAIN * abs(self._vx_cmd)
        self._phase = (self._phase + 2 * np.pi * gait_freq / CONTROL_HZ) % (2 * np.pi)
        action = np.clip(action, -1.0, 1.0)
        self._action_filtered = (ACTION_EMA_ALPHA * action
                                 + (1.0 - ACTION_EMA_ALPHA) * self._action_filtered)
        target = np.clip(self.home_q + ACTION_SCALE * self._action_filtered,
                         self.ctrlrange[:, 0], self.ctrlrange[:, 1])
        prev_action = self._last_action.copy()

        push_force = self._apply_push() if self.push_enabled else 0.0
        for _ in range(DECIMATION):
            # 每个物理步重算力矩（固件环频率高于控制频率的近似）
            self.data.ctrl[:] = self._motor_torque(target)
            mujoco.mj_step(self.model, self.data)

        obs = self._get_obs()
        g = self._gravity_body()
        z = self.data.qpos[2]

        upright = -g[2]                        # 直立=1
        height = float(np.exp(-((z - self.z_home) / Z_HOME_TOL) ** 2))
        joint_home = float(np.exp(-np.mean((self.data.qpos[self.qpos_addr] - self.home_q) ** 2) / 0.25))
        action_rate = float(np.mean((action - prev_action) ** 2))
        action_mag = float(np.mean(action ** 2))
        vx = self.data.qvel[0]
        vel_track = float(np.exp(-((vx - self._vx_cmd) / 0.25) ** 2))

        # 脚触地检测（geom 名匹配），更新腾空计时
        grounded = [False, False]
        for i in range(self.data.ncon):
            for j, fname in enumerate(("left_foot_collision", "right_foot_collision")):
                for gid in (self.data.contact[i].geom1, self.data.contact[i].geom2):
                    if mujoco.mj_id2name(self.model, mujoco.mjtObj.mjOBJ_GEOM, gid) == fname:
                        grounded[j] = True
        dt_ctrl = 1.0 / CONTROL_HZ
        self._air_time = np.where(grounded, 0.0, self._air_time + dt_ctrl)
        feet_air = float(np.mean(np.minimum(self._air_time, 0.4) / 0.4))
        # 相位-抬脚耦合：当前实现前半周期偏好右脚腾空、后半周期偏好左脚腾空
        left_window = 0.0 if self._phase < np.pi else 1.0
        phase_foot = (float(not grounded[0]) * left_window
                      + float(not grounded[1]) * (1.0 - left_window))

        reward = (W_UPRIGHT * upright + W_HEIGHT * height
                  + W_JOINT_HOME * joint_home + W_ACTION_RATE * action_rate
                  + W_ACTION_MAG * action_mag + W_VEL_TRACK * vel_track
                  + W_FEET_AIR * feet_air + W_PHASE_FOOT * phase_foot + W_ALIVE)

        terminated = bool(np.linalg.norm(g[:2]) > TILT_TERMINATE or z < self.z_home * 0.6)
        if terminated:
            self.data.xfrc_applied[:] = 0.0  # 摔倒后不再施力
        truncated = self._step_count >= int(EPISODE_SECONDS * CONTROL_HZ)
        self._step_count += 1
        self._last_action = self._action_filtered.copy()

        if self.render_mode == "human":
            self.render()
        return obs, float(reward), terminated, truncated, {
            "upright": upright, "height": height, "z": z, "push_force": push_force,
            "vx": vx, "vx_cmd": self._vx_cmd}

    # ---------- 渲染 ----------

    def render(self):
        if self.render_mode == "rgb_array":
            if self._renderer is None:
                self._renderer = mujoco.Renderer(self.model, 480, 640)
            self._renderer.update_scene(self.data)
            return self._renderer.render()
        if self._viewer is None:
            from mujoco import viewer as mujoco_viewer
            self._viewer = mujoco_viewer.launch_passive(self.model, self.data)
        if self._viewer.is_running():
            self._viewer.sync()
        return None

    def close(self):
        if self._renderer is not None:
            self._renderer.close()
        if self._viewer is not None:
            self._viewer.close()
