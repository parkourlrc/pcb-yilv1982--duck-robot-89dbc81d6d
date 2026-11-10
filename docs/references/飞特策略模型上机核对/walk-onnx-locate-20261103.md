# 以"向前走"为例：行为到模型 ONNX 的定位

日期：2026-11-03。问题：拿"向前走"这一行为为例，找出其对应的模型 ONNX 文件位置与本机可得性。

## 结论

- **[实测·11-01 板侧快照]** "向前走"不是独立模型，由 `walk` 槽承载：**行走、零速保持与倒地恢复联合策略**（`Mjlab-VelStand-Rough-Backlash-MicroDuck`）。网页操作次序为"站起来"→"开始走"→摇杆/键盘速度输入，速度命令进入已加载的 walk 策略推理，不存在单独的"前进模型"。
- **[实测·11-01 板侧快照]** 文件本体在 Radxa 主控（192.168.1.35）两处：
  - 运行目录：`/home/radxa/studio-dev/state/models/316b92cd3d4f42babda055a804e73b03/policy.onnx`
  - 原始备份：`/home/radxa/duck-policies/hd1910-20261031/`
  - SHA256：`1cbf8730eadd75a5704332c9f3c10f60bfa9412135b907831c9dbd731ce1795f`
- **[实测·11-01 板侧快照]** 模型接口登记（来自同目录 sidecar，非重新推理验证）：`input_dim=61`、`output_dim=14`、obs 归一化 `baked_in_onnx`；命令空间 `head_pose`(4 维) + `body_pose`(6 维)；训练来源 iteration 9599 / step 230376。
- **[实测·本轮检索]** 本机仓库内**没有**该 onnx 副本：`tools/`、`docs/`、`training/`（排除 .venv）下无任何该 SHA 对应文件；`references/` 下的 ONNX 全部为 A/B 线产物（A 线 `walk.onnx`、B 线 velocity 训练导出），与 C 线真机模型不可混用。
- **[实测·本轮]** 主控 192.168.1.35 SSH 22 端口超时（2026-11-03 尝试，BatchMode），当前不可达，无法本轮拉取文件或核对在板 SHA。

## 下一步（待主控开机联网后）

1. `ssh radxa@192.168.1.35 "sha256sum /home/radxa/studio-dev/state/models/316b92cd3d4f42babda055a804e73b03/policy.onnx"` 核对与 11-01 登记 SHA 一致。
2. 用 `scp` 拉取 `policy.onnx`（连同 `deployment-contract.json`、`deployment-runtime.json` 等 sidecar）到本仓库模型存档目录，登记 SHA 与来源，再在本机做输入/输出结构分析（61 维观测布局、14 维输出到关节的映射）。
3. 注意 61 维中"向前走"速度指令的具体占位尚未从 sidecar 直接读出，需结合 robotd 源码观测打包逻辑确认，本轮未下结论。

## 任务名解读：`Mjlab-VelStand-Rough-Backlash-MicroDuck`（2026-11-03 追加）

训练任务本体在 B 线参考库同源工程中有完整注册与定义：

- **[推断·多项吻合]** 任务注册行（`references/microduck-replica/software/training/src/mjlab_microduck/tasks/__init__.py:264`）：`("Mjlab-VelStand-Rough-Backlash-MicroDuck", make_microduck_velstand_env_cfg, {"rough": True}, MicroduckVelStandRlCfg, _BL_ALLCOL)`。即：**velstand 环境 + 粗糙地形（rough）+ 背隙机器人变体（Backlash）**。与板侧 sidecar 的 `experiment=velstand`、`num_steps_per_env=24`、`source_iteration=9599` 吻合；且 9599 × 24 = 230,376 与 sidecar `training_step` 逐位一致。上游 `official_0151` 引擎代码与本地 B 线副本是否逐字一致未逐字节核验。
- **任务结构**（`microduck_velstand_env_cfg.py` 模块 docstring 与代码）：
  - Walk 层 = 逐字复用 velocity recipe（速度跟踪/air_time/原地转/DR），rough=True 为粗糙地形；
  - 机器人 = 全碰撞 standup XML（躯干/头壳保留接触，可物理躺地），Backlash 变体为每舵机 ±1° 齿隙 + encoder-through-backlash 反馈（`tasks/backlash.py`），观测/动作维度不变（61/14）；
  - Recovery 层 = tilt>40° 门控的恢复奖励（upright_progress / height_progress / com_upward_velocity）、fallen_tax、recovery_success 赏金（恢复完成 = tilt<25° 且 z>0.09 m）；
  - 课程三阶段：0–500 iter 先干净行走（fell_over 70° 终止）→ 500+ 摔倒不终止改为恢复训练（8 s 超时回收）→ 1500+ 俯卧初始化爬坡至 45%。
- **RL 配置**（`MicroduckVelStandRlCfg`）：rsl_rl PPO，actor/critic 均 (512,256,128) ELU MLP，观测归一化（导出烘焙进 ONNX，与 `obs_normalizer=baked_in_onnx` 一致），adaptive LR（1e-3，desired_kl 0.01），num_steps_per_env=24，max_iterations 20000（实际 9599 导出）。
- **执行器物理**（[c-motion-training 专题已核](https://gitee.com/yilv1982/duck-robot-training/blob/main/docs/references/动作训练软件研究/research.md)）：HD1910 = BAM M6 电压控制律 + 库仑/Stribeck/负载相关摩擦 + 摩擦/电压/压降/延迟域随机化，参数 `hd1910_m6.json` 来自 LuwuDynamics/xgoduck_rl；baseline "HD1910 / BAM M6 · 官方骨架 820g"。
- **勘误说明**：`model-inventory-20261031.json` 中 `policy_path`（`training/logs/b-feetech-walk-20261024/...`）是**板侧相对路径**，本机 `training/` 下无此目录，不改变上文"本机无副本"结论。

## 来源

| 来源 | 用途 |
|---|---|
| [六模型核对 2026-11-01](webpad-models-check-20261101.md) | walk 槽定义、板侧路径、操作次序 |
| [模型快照 JSON](webpad-models-snapshot-20261101.json) | `models[0]` sidecar 全文：SHA256、input/output_dim、commands、训练来源 |
| [模型清单 2026-10-31](model-inventory-20261031.json) | checkpoint 来源路径、task、source_iteration、declared_robot |
| B 线参考库 `mjlab_microduck`（只读） | 任务注册 `tasks/__init__.py:103-116,245-264`；env 定义 `tasks/microduck_velstand_env_cfg.py`；背隙 `tasks/backlash.py`；上游关系 `README.upstream.md` |
| 本轮检索 | 全仓库 `*.onnx` 枚举与归属排除；SSH 连通性测试（失败，超时） |
