# 机器人训练两条行业路线调研：真机训练 vs sim2real

- 日期：2026-10-15
- 问题与范围：用户提问"当前机器人公司有两条路线——真机训练与 sim2real，两者区别是什么、具体怎么做"。本文为概念与行业现状梳理，作为 C 线动作训练的背景知识，不改变任何已确认的路线、采购或训练决定。
- 性质：领域通识 + 网络来源摘要 + 本项目已有文档交叉引用。无本机实验、无硬件操作。公司案例均来自公开报道/官网/论文（外部证据，未逐篇核验原文），不能写成对任何公司当前做法的断言。

## 一、结论（先答后证）

1. **一句话区别**：sim2real 是"在仿真里训练、真机只做部署验证"，核心资产是仿真模型 + 奖励函数；真机训练是"训练信号直接来自真实机器人"，核心资产是大规模真机数据（多为遥操作演示）。前者解决"怎么动"（运动控制），后者解决"做什么、怎么做任务"（操作与语义）。
2. **sim2real 具体做法**：建仿真模型 → 定义观测/动作/手工奖励 → GPU 大规模并行 PPO → 域随机化补偿模型误差 → teacher-student 处理特权信息 → 导出小网络零样本上真机，必要时 real2sim 回修。
3. **真机训练具体做法**：两条子路线——(a) 遥操作采集"图像+指令 → 动作"配对数据，模仿学习训练 ACT/Diffusion Policy/VLA，部署后数据飞轮闭环；(b) 真机强化学习（多为仿真预训练 + 真机微调，因真机采样慢、损坏风险高，纯真机 RL 少见）。
4. **分化的根本原因是任务类型**：locomotion（步态/平衡，本体感知主导，奖励好写，仿真够准）几乎全走 sim2real；manipulation（抓取/操作，接触丰富、视觉主导，奖励难写，仿真 gap 大）以真机数据 + 模仿学习为主。
5. **2025-2026 趋势是融合**：分层架构——上层 VLA"大脑"（1-10 Hz，真机数据模仿学习）+ 下层 RL"小脑"策略（50 Hz+，sim2real）；以及 sim 预训练 → 真机 RL 微调、真机数据回填仿真（real2sim）闭环。

## 二、两条路线的具体 pipeline

### 2.1 sim2real（仿真强化学习 → 真机迁移）

| 步骤 | 做什么 | 关键点 |
|---|---|---|
| 1. 建仿真模型 | URDF/MJCF 描述几何、质量/质心/惯量、关节限位；执行器建模（延迟、摩擦、PD 增益，如 BAM 执行器模型） | 模型越准 gap 越小；本项目 C 线"只借物理参数、自建模型"对应此步 |
| 2. 定义任务接口 | 观测 = IMU + 关节角/角速度 + 指令 + 动作历史；动作 = 关节位置目标；奖励 = 速度跟踪、姿态平稳、能耗、动作平滑等手工加权 | 奖励设计是主要人力成本；critic 可看仿真真值（特权信息） |
| 3. 大规模并行训练 | Isaac Gym/Lab、MuJoCo MJX/mjlab 等，GPU 上数千环境并行跑 PPO | 数据近乎免费，几小时可出策略 |
| 4. 域随机化 | 随机质量/摩擦/电机强度/延迟/传感器噪声/推扰 | 让策略对模型误差鲁棒，是弥合 sim gap 的主要手段 |
| 5. teacher-student 蒸馏 | critic 用真值训练，actor 只用真机可得的观测（如 base_lin_vel 只给 critic） | 保证部署侧观测一致 |
| 6. 迁移与回修 | 导出小网络（ONNX/MLP）机载高频推理；效果差则把实测滞后/质量/摩擦回填仿真重训（real2sim 闭环） | microduck 全链路即此路线缩影 |

### 2.2 真机训练（真机数据为主）

子路线 (a)：遥操作 + 模仿学习（主流，VLA 路线）：

1. 建数据采集线：VR 手柄、主从臂（ALOHA 类）、动捕或穿戴设备遥操作真机；Tesla 曾以时薪雇人专职遥操采集 Optimus 演示数据。
2. 采集配对数据：多相机图像 + 语言指令 + 人的动作，规模化到数千~数万小时；国内多家公司建集中式数据采集站。
3. 训练：行为克隆（ACT）、Diffusion Policy，或 VLA（VLM 主干 + 动作头；RT-2、OpenVLA、π0、Figure Helix 等），无手工奖励。
4. 数据飞轮：部署 → 收集失败案例 → 补采/修正 → 再训练。

子路线 (b)：真机 RL——直接在真机上探索学习，或（更常见）仿真预训练 + 真机小步微调（如 TRI 的真机扩散策略 RL 微调、Physical Intelligence 的真机持续学习）。受限于采样速度和安全，纯真机 RL 规模有限。

## 三、对比与代表案例（外部来源，未核验）

| 维度 | sim2real RL | 真机训练（模仿学习/VLA 为主） |
|---|---|---|
| 数据来源 | 仿真自生成，近乎免费 | 真机遥操作/人类视频，贵且慢 |
| 核心资产 | 仿真模型 + 奖励函数 | 真机数据集 + 大模型 |
| 典型任务 | 步态、平衡、全身运动（locomotion） | 抓取、操作、语言条件任务（manipulation） |
| 控制频率/网络 | 50 Hz+，小 MLP（0.1-10M 参数） | 1-10 Hz，数十亿参数 VLA |
| 主要风险 | sim gap（接触/摩擦/延迟建模误差） | 数据采集成本、真机安全与损耗 |
| 泛化方式 | 换任务要重写奖励重训 | 语言条件化，跨任务泛化靠数据规模 |
| 代表 | 宇树平台上的 RL locomotion 研究（Isaac 生态）、ETH/ANYmal teacher-student 范式、microduck | Tesla Optimus（付费遥操+视频+车队学习）、Figure Helix（人类运动先验+VLA）、Physical Intelligence π 系列、国内数据采集站模式 |

趋势佐证（2025-2026 公开讨论）：行业共识转向混合——遥操作/模仿学习负责灵巧与任务理解，sim2real RL 负责运动控制与规模化；Figure Helix 02 亦被报道同时使用人类运动数据与 20 万仿真环境训练。

## 四、与本项目的关系

- 本项目（microduck C 线）走的正是 **sim2real locomotion 路线的最小缩影**：mjlab/MuJoCo 仿真 PPO → ~0.2M 参数 MLP → ONNX → 机载 50 Hz 推理，详见 [runtime 策略模型调研](../运行时策略模型调研/research.md)（其第四节 MLP vs VLA 对比表即两条路线在网络层的投影）。
- C 线训练步骤第 6.1 节自建仿真工程六步与第 6.2 节十阶段（含第 10 步"实机结果回修仿真"）分别对应上表 pipeline 的建模/训练步与 real2sim 回修步，见 [C 线动作训练研究](../动作训练软件研究/research.md)。
- 本项目当前**没有也不需要 VLA**：任务由手柄/上层接口给定，感知闭环依赖本体感知——即只做两条路线中的"小脑"部分。

## 五、来源

外部（搜索摘要，未逐篇核对原文）：

- Figure Helix 官方页：<https://www.figure.ai/news/helix>
- Tesla Optimus 遥操作招聘与数据护城河报道：<https://avala.ai/news/tesla-optimus-hiring-humanoid-robot-data>
- Tesla Optimus 学习管线综述（2026-05）：<https://theroboticlife.com/tesla-optimus-gen-3-learning>
- Sim-to-Real Humanoid Locomotion in 15 Minutes（arXiv 2512.01996，Unitree G1/Booster T1）：<https://arxiv.org/html/2512.01996v1>
- Sim-to-Real Humanoid Locomotion 综述：<https://www.emergentmind.com/topics/sim-to-real-humanoid-locomotion>
- 模仿学习指南（ACT/Diffusion Policy/VLA、遥操作采集）：<https://www.roboticscenter.ai/guides/imitation-learning>
- NVIDIA Isaac Lab 遥操作+模仿学习接口：<https://isaac-sim.github.io/IsaacLab/main/source/overview/imitation-learning/teleop_imitation.html>
- "How to avoid the teleoperation trap"（The Robot Report, 2026-07）：<https://www.therobotreport.com/how-to-avoid-teleoperation-trap-robotics-development>
- TWIST 遥操作全身模仿（2025）：<https://par.nsf.gov/servlets/purl/10633387>

本地交叉引用：

- [运行时策略模型调研/research.md](../运行时策略模型调研/research.md)：MLP 策略 vs VLA 的结构/训练/频率对比（本文路线之争的网络层投影）。
- [动作训练软件研究/research.md](../动作训练软件研究/research.md)：C 线自建仿真训练六步与十阶段（sim2real pipeline 的本项目落地计划）。
- [乐鑫芯片跑多层感知机/research.md](../乐鑫芯片跑多层感知机/research.md)：小型 MLP 步态策略机载部署的社区实证。

## 六、验证状态、限制与下一步

- 已验证：两条路线的技术 pipeline 为领域通识，且与本项目上游训练库（mjlab + PPO + 域随机化 + BAM 执行器）的本地源码证据一致。
- 限制：公司案例全部来自搜索摘要与公开报道，未核对一手论文/财报；各公司路线随时演变，"某公司走某路线"不应作为采购或技术决策的唯一依据；本文不构成投资或选型建议。
- 下一步：无行动要求；若未来 C 线考虑上层任务接口（如语音/视觉指令），再评估是否引入 VLA 类分层架构。
