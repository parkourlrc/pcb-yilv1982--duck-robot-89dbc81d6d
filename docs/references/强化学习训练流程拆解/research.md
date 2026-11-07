# 以 VelStand 为例：mjlab 任务训练全流程拆解

日期：2026-11-03。问题：以真机 walk 模型的训练任务 `Mjlab-VelStand-Rough-Backlash-MicroDuck` 为例，详细说明一个 RL 任务从物理建模到部署是怎么训练出来的。

证据等级说明：本流程拆解基于 B 线参考库 `references/microduck-replica/software/training/`（只读，Apache-2.0，pollen-robotics/microduck_rl 的同源副本）的源码阅读 **[源码核验]**，与板侧模型 sidecar 登记（`webpad-models-snapshot-20261101.json`、`model-inventory-20261031.json`）**[实测·板侧登记]** 交叉印证；本机**未运行**任何训练，上游 `official_0151` 引擎与本地副本是否逐字一致未逐字节核验。B 线工程是真机六模型的同源训练框架（任务注册名、velstand 实验名、24 步/迭代、9599×24=230376 步均吻合）。

## 0. 前置条件

- Python ≥3.12 且 <3.13（BAM `better-actuator-models` 钉死上限）、CUDA GPU（训练走 MuJoCo Warp GPU 并行）、`uv` 包管理。
- 核心依赖（`pyproject.toml`）：`mjlab==1.3.0`、`warp-lang==1.12.0`、`better-actuator-models`（BAM 执行器）、`torch==2.9.1`、`onnxruntime`、`rsl_rl`（mjlab 内带）。
- `uv sync` 安装；ARM 盒子首拉约 2 GB CUDA wheel，需 `UV_HTTP_TIMEOUT=600`。
- 无 GPU 时可 `--hf-jobs` 提交 Hugging Face Jobs 云训。

## 1. 物理层：机器人与执行器（real2sim 的"real"）

任务训练的输入不是抽象 gym，而是三件物理资产（都在 `src/mjlab_microduck/robot/`）：

- **MJCF 骨架**：VelStand/StandUp 用**全碰撞 standup XML**——躯干/头壳保留碰撞几何，机器人能物理躺倒撑地起身（普通行走任务用的是去掉躯干碰撞的 walk XML）。Backlash 变体 XML 在 14 个舵机关节串入 ±1°（合计 2°）齿轮间隙，且编码器反馈"透过背隙"（`tasks/backlash.py`），观测/动作维度不变。
- **执行器模型**：HD1910 用 BAM M6——电压控制律 + 反电动势 + 库仑/Stribeck/负载相关摩擦，参数 `hd1910_m6.json`（kt=0.6238、R=4.910、armature=0.00178 等，来源 LuwuDynamics/xgoduck_rl）。适配器 `Hd1910Actuator` 继承 `FrictionDRBamActuator`。
- **域随机化（DR）**：电压环 `vin_range=(7.4, 8.0)`、压降增益 0–0.2、指令延迟 3–6 步、`kp_fw=5.0`、摩擦参数域随机化；观测噪声与延迟（如角速度延迟 0–1 步、Uniose ±0.03）。

baseline 声明"HD1910 / BAM M6 · 官方骨架 820g"，`training_firmware_p=5.0`（与真机固件位置增益一致，见 c-motion-training 专题）。

## 2. 环境定义（env cfg）：任务的核心工作量

VelStand 的写法是**"复用已验证底座 + 叠加恢复层"**（`tasks/microduck_velstand_env_cfg.py`，162 行起 `make_microduck_velstand_env_cfg(rough=True)`）：

1. **底座**：`make_microduck_velocity_env_cfg(rough=True)` 逐字复用——速度命令跟踪奖励、air_time、原地转分桶、固定命令范围、全部 DR/噪声/观测、粗糙地形（rough）。这是"已证明能走"的 recipe，不重写。
2. **换机器人**：`cfg.scene.entities = MICRODUCK_STANDUP_ROBOT_CFG`（全碰撞版，Backlash 任务再换成 `MICRODUCK_BACKLASH_ROBOT_CFG`）。
3. **恢复奖励层**（全部门控在 tilt>40°，保证干净行走时贡献恰为零）：
   - `upright_progress`（势函数 Δcos tilt：起身得分、摔倒扣分、保持零分——防"躺着刷分"）；
   - `height_progress`（势函数 Δz，ceiling 0.115 m，补 crouch→stand 最后一里）；
   - `com_upward_velocity`（重量课程 0→2.0）；
   - `fallen_tax`（趴下税 -0.5，带迟滞释放：tilt<25° 且 z>0.09 才停税）；
   - `recovery_success`（一次性赏金 +10，恢复完成=tilt<25° 且 z>0.09）；
   - `joint_torque_rate_l2`（-2e-3，惩罚力矩变化量，抑抖不挡翻身）。
4. **事件**：`random_prone_init`（reset 时按概率俯卧/仰卧/半蹲初始化，z 固定 0.05–0.09 m 贴地，修复过 0.20 m 自由落体 bug）。
5. **终止**：`fallen_too_long`（z<0.08 或 tilt>40° 持续 8 s 回收）；`fell_over` 由课程从 70° 逐步放开到 π。
6. **课程三阶段**（`CurriculumTermCfg`，按 PPO 迭代数触发）：
   - Phase 1（0–500 iter）：`fell_over` 70° 终止活跃 → 先学干净行走；
   - Phase 2（500+）：摔倒不再终止，变成恢复训练数据；
   - Phase 3（800+ crouch 切片 / 1500+ prone 爬坡至 45%）：恢复经济（tax+bounty）1200 iter 才开——留出"免费自然摔倒窗口"，否则学出 crouch-freeze 局部最优（run-3/6 教训）。

**观测 61 维**（按部署合同顺序）：3 机体角速度 + 3 重力投影 + 14 相对 HOME 的关节位置 + 14 关节速度 + 14 上一步原始策略输出 + 3 速度命令 + 4 头颈姿态命令 + 6 躯干姿态命令 = 61。**动作 14 维**（4 头颈 + 10 腿），action scale 1.0，部署阶段为"归位+缩放后的关节位置目标"。

2026-11-05 勘误 **[归档合同／源码核验]**：原文将3维速度命令误写成加速度计，现已替换。依据[板侧快照](../飞特策略模型上机核对/webpad-models-snapshot-20261101.json)的 `models[0].sidecars["deployment-contract.json"].text` 解码后的 `observations.terms` 和 `onnx_metadata.observation_names`，该 walk 使用 `projected_gravity`，没有额外 `raw_accelerometer` 输入；3维 `command` 指向 `twist`。逐项含义见[平台接口核对](../自主训练平台/research.md)。本次未重新连接主控或采集动作数据。

### 2.5 状态判定与奖惩实现（`tasks/mdp.py`，2026-11-03 补充）

所有"摔倒/趴下/起来了"状态只用**两个物理量**定义，不引入额外状态机：

- **倾角 tilt**：躯干局部 Z 轴在世界系的 z 分量，`cos(tilt) = 1 − 2(qx² + qy²)`，直接从四元数取（`_fallen_mask`，mdp.py:507–524）；
- **躯干高度 z**：`root_link_pos_w[2] − 地形原点 z`（相对高度，NaN 按 0 处理）。

**三个状态定义**（velstand 实际数值）：

| 状态 | 判定 | 出处 |
|---|---|---|
| FALLEN（摔倒/趴下，奖励门控用） | **仅 tilt > 40°**；通用 `_fallen_mask` 支持"z<阈值 OR tilt>阈值"，但 velstand 调用传 `gate_z_below=0.0` 把 z 条件关掉 | mdp.py:507，env REWARD_GATE_TILT_DEG |
| RECOVERED/UP（起来了） | tilt < 25° **且** z > 0.09 m（0.09 取在真实站立包络 z≈0.084–0.096 内、高于坐 0.07/趴 0.05；旧值 0.105 不可达导致深蹲停车） | mdp.py:646–680，RECOVERED_UP_* |
| fallen_too_long（回收，终止器用） | (z < 0.08 OR tilt > 40°) **持续 ≥ 8 s** → 终止回收；终止器保留 z 条件（坐着 z≈0.07 也要被回收，而非被奖励） | mdp.py:936–960 |

**奖惩项与状态的关系**（env cfg 权重 × mdp 实现）：

| 项 | 状态门控 | 行为 |
|---|---|---|
| `upright_progress` (×5.0) | 无门控，全程 | 势函数 Δcos(tilt)：每步朝直立变化 +、朝摔倒 −、**保持任何姿态 0**；回合重置帧清差分防假 delta |
| `height_progress` (×30) | 无门控，全程 | 势函数 Δmin(z, 0.115)：蹲→站最后一里的密集梯度；跳得更高不多给 |
| `com_upward_velocity` (×2.0，1200 iter 后) | tilt > 40°（z 门关闭） | clamp(vz, 0, cap)，只在摔倒后为正；防步态下蹲-弹跳刷分 |
| `fallen_tax` (×−0.5，1200 iter 后) | **迟滞**：tilt>40° 武装 → tilt<25° 且 z>0.09 解除 | 每步 −0.5；40° 以下深蹲不是免费休息站 |
| `recovery_success` (×+10，1200 iter 后) | 真摔（tilt>40° 累计 ≥0.5 s）后某帧达到 UP | 一次性 +10；触发即解除武装，门限振荡不重复给 |
| `feet_air_time`（步态项，继承 velocity） | **反门控**：tilt > 40° 清零 | 躺着有节奏蹬腿不给步态分（run 教训："躺着抖腿"刷 air_time） |
| `joint_torque_rate_l2` (×−2e-3) | 无门控 | 惩罚力矩**变化量**，抑抖不挡爆发式翻身 |

**设计原则**（docstring 明文，run-1..7 失败换来的）：

1. **惩罚门控在坏状态是安全的；正奖励门控在坏状态必被刷分**——趴下税可以门控；被门控的正奖励先后被坐着、躺平、头三脚架（run-4）刷过，最终改为势函数 + 迟滞。
2. **奖励门控只用 tilt 不用 z**：坐姿 z≈0.07 且直立，加 z 门等于奖励坐下刷分；tilt>40° 从任何舒适姿态都够不着，真摔才开门。
3. **势函数 shaping**（引 Ng et al. policy-invariant）：保持/振荡净收益 0，任何状态无法刷，只加速学习不造新最优。
4. **迟滞**（armed→released）防门限振荡刷分，并把"门下深蹲"继续计税逼出完整站立。

## 3. 注册任务

`tasks/__init__.py` 用 `register_mjlab_task(task_id=..., env_cfg=..., play_env_cfg=..., rl_cfg=..., runner_cls=...)` 注册。task_id 命名规则 `Mjlab-<家族>-<Flat|Rough>-[Backlash-]MicroDuck`。Backlash 变体不逐个手写，而由 `_BACKLASH_TASKS` 派生表批量注册（同一 make 函数换机器人 cfg）。包通过 entry point `[project.entry-points."mjlab.tasks"] mjlab_microduck = "mjlab_microduck.tasks"` 自动被 `uv run list-envs` 发现。

## 4. RL 配置（rl cfg）

`MicroduckVelStandRlCfg = RslRlOnPolicyRunnerCfg(...)`：actor/critic 均 (512, 256, 128) ELU MLP；`obs_normalization=True`（运行均值方差归一化，导出时烘焙进 ONNX）；PPO：clip 0.2、entropy 0.01、lr 1e-3 adaptive（desired_kl 0.01）、gamma 0.99、lam 0.95、5 epochs、4 mini-batches；`num_steps_per_env=24`、`save_interval=250`、`max_iterations=20000`；wandb 项目 `mjlab_microduck`、experiment 名 `velstand`。

## 5. 训练与迭代

命令（README Quickstart 原文，换成 VelStand 任务）：

```bash
uv run train Mjlab-VelStand-Rough-Backlash-MicroDuck --env.scene.num-envs 4096
# 断点续训
uv run train <task> --agent.run-name resume --agent.load-checkpoint model_9599.pt --agent.resume True
```

4096 并行环境约 1–2 h 出可用步态（velocity 任务的经验值）。真机 walk 模型对应 checkpoint：`logs/rsl_rl/velstand/2026-10-07_00-14-46_.../model_9599.pt`（上游 official_0151 引擎训练，未跑满 20000，9599 迭代 = 230,376 步导出）。

**奖励迭代是主要工作量**：velstand 文件 docstring 完整记录了 run-1→run-7 的教训链（坐着刷分→头三脚架 farming→crouch-freeze→prone 崩溃→…），每次失败模式对应一条可检查的设计规则（正向奖励门控在坏状态会被刷分；势函数项不可刷；课程排布决定数据分布）。要复刻这类任务，预期同样要按 eval 结果多轮改奖励/课程。

## 6. 回放验证

- `uv run play <task> --wandb-run-path <entity/project/run_id>`：viewer 里看策略。
- `uv run scripts/infer_policy.py --walking walk.onnx ...`：CPU MuJoCo + 键盘驱动，排练部署时"共享 61 维观测契约下策略热切换"的真实运行时行为，支持 `--save-csv`/`--record` 做 sim2real 对比。

## 7. 导出与部署

- `uv run scripts/export.py <task> --wandb-run-path <...>`：加载 checkpoint，`runner.export_policy_to_onnx()` 导出——观测归一化（EmpiricalNormalization）**自动烘焙进计算图**，ONNX 即 `actor(normalizer(obs))`；`attach_metadata_to_onnx` 附加元数据。
- 上游再打包为 `models/<sha256 前 24 位>/` 目录：`policy.onnx` + sidecar（`manifest.json`、`deployment-contract.json`（61/14 维、动作滤波、关节序）、`deployment-runtime.json`（训练来源、命令范围）、`deployment-execution.json`（action_scale、lowpass）、`model-info.json`）。
- 部署：目录上传板侧 Studio（本机路径 `/home/radxa/studio-dev/state/models/<目录 ID>/`），robotd 按 toml 槽位（walk/sitstand/...）加载，50 Hz 推理。

## 8. 本项目视角的边界

- B 线参考库只读：上述流程是**参考读物**，不能在其内跑训练或改动。
- 本项目自建训练在 `training/`（"从零学习"路线，2026-10-15 用户确认）：物理参数表→自建 MJCF（`build_model_v0.py`）→自建任务环境（`duckstand/`）→自建训练入口；已跑通 mjlab rsl_rl 训练（`duck_walk` model_9999.pt）与精细显示回放。要练 VelStand 类任务，应在本工程内自写等价 env（借鉴公开参数与上述设计模式），不复制上游任务代码。
- `training/logs/` 下 10-24 下载的外部 HD1910 包（含真机六模型同源件）是外部产物，不是自建训练结果。
- 本文档拆解未在本机执行任何训练命令；引用数值以源码与板侧登记为准。

## 来源

| 来源 | 用途 |
|---|---|
| `references/microduck-replica/software/training/`（只读） | `pyproject.toml`（依赖/入口）；`tasks/__init__.py`（注册与派生表）；`tasks/microduck_velstand_env_cfg.py`（env/rl cfg 全文与 run-1..7 教训）；`tasks/backlash.py`；`scripts/export.py`（导出与归一化烘焙）；`README.upstream.md`（Quickstart 命令、任务表） |
| [模型快照 2026-11-01](../飞特策略模型上机核对/webpad-models-snapshot-20261101.json) / [模型清单 2026-10-31](../飞特策略模型上机核对/model-inventory-20261031.json) | checkpoint 路径、9599 迭代、sidecar 结构 |
| [c-motion-training 专题](../动作训练软件研究/research.md) | BAM M6 参数溯源、执行器适配、training_firmware_p |
| [training/README.md](../../../training/README.md) | 本项目自建工程现状与边界 |
