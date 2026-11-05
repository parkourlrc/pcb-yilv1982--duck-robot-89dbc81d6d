# C 线自建仿真模型物理参数表（v0）

- 日期：2026-10-15。配套执行记录见 [research.md](./research.md) 第 6 节与 [工程 README](../../../training/README.md)。
- 用途：`training/` 自建 real2sim2real 工程的**全部借鉴数值**及溯源。机器人整机未装配，本表全部为**上游公开参数**，无任何本机实测。
- 边界：只提取数值，不复制/加载上游模型文件、网格、任务配置或训练代码（2026-10-15 用户确认）。

## 1. 来源与许可

| 编号 | 内容 | 来源 | 版本/许可 |
|---|---|---|---|
| S1 | 连杆质量/质心/惯量、关节安装位形（pos/quat/axis）、关节限位、动作关节顺序 | [robot_walk.xml](../../../references/microduck-replica/software/training/src/mjlab_microduck/robot/microduck/robot_walk.xml)（Pollen Microduck 官方 CAD，onshape-to-robot 导出） | 经 fanhao375/microduck_rl `d9e1926c` 引入；网格 CC BY-NC-SA，本文仅取数值 |
| S2 | HD-1910 执行器 BAM M6 辨识参数 | [1910_m6.json](../../../references/microduck-replica/software/training/src/mjlab_microduck/robot/hd1910/1910_m6.json) | LuwuDynamics/xgoduck_rl `326d77a1`，Apache-2.0，SHA-256 `ef2d51ad…afceb` |
| S3 | HOME 站姿（STAND2） | [microduck_constants.py](../../../references/microduck-replica/software/training/src/mjlab_microduck/robot/microduck_constants.py) 73–97 行 | 同 S1 引入链 |
| S4 | HD-1910-C001 厂商规格 | [规格书](../../../references/microduck-replica/tools/FeeTech_HD1910M_Servo/HD-1910-C001串型规格书20260907.pdf)：4–8.4 V，减速比 1:320，堵转 15 kg·cm @7.4 V（≈1.47 N·m） | 飞特原件（联系方式已由上游抹除） |

**适用性声明**：S1 质量惯量为 **XL330 版 Microduck**（含 NP-F970 电池、Pi Zero 2W 等电气件的 CAD 质量）；本机 C 线为 HD-1910 舵机 + Radxa Zero 3W + NP-F550，质量分布不同。上游 HD-1910 任务同样"保留 Microduck 几何/质量惯量、只换执行器"，本 v0 沿用同一近似口径并显式标注，实物称重复核属未来 real2sim 校准项（research.md 6.2 第 3/10 步）。

## 2. 单位与坐标约定

- 长度 m、质量 kg、惯量 kg·m²、角度 rad；四元数 **wxyz**。
- body `pos/quat` 相对**父 body** 坐标系；`trunk_base` 相对世界（初始位形）。
- 关节全部为铰链，`axis="0 0 1"`，即轴向为**所在 body 的局部 z 轴**；关节中心=body 原点（joint pos 未偏置）。
- 运动学级联：`X_body(q) = X_parent · X_static(pos,quat) · X_joint(q)`。
- 惯性 `fullinertia=(Ixx,Iyy,Izz,Ixy,Ixz,Iyz)` 在 body 局部系、**绕质心**表达；质心 `pos` 亦为局部系。
- 自由度：freejoint(7) + 14 铰链 = nq 21；**14 个位置执行器**（无嘴/下颌关节——上游步行树即无，C 线第 15 舵机映射暂缓）。

## 3. 连杆质量与惯量（S1）

| body | 父级 | 质量(kg) | 质心(局部,m) | fullinertia (Ixx Iyy Izz Ixy Ixz Iyz, kg·m²) |
|---|---|---|---|---|
| trunk_base | world | 0.199224 | -0.02263 -2.708e-05 0.002801 | 1.240e-04 1.459e-04 1.154e-04 7.2e-08 -2.1e-05 1.3e-07 |
| yaw2roll | trunk_base | 0.0230406 | -8.8e-11 0.0009941 0.01689 | 4.20e-06 3.42e-06 2.33e-06 -0 -0 -5.1e-08 |
| hip_l | yaw2roll | 0.00618934 | 0.01482 1.6e-08 -0.0083 | 8.61e-07 1.16e-06 6.52e-07 1e-12 3.9e-07 -1e-12 |
| upper_leg_left | hip_l | 0.0482067 | 0.006766 0.02288 0.01345 | 1.69e-05 1.04e-05 1.98e-05 -4.4e-06 2.3e-07 3.9e-07 |
| leg | upper_leg_left | 0.0215844 | -1.5e-10 0.03189 -0.009535 | 5.25e-06 2.16e-06 4.34e-06 -1e-12 0 7.7e-07 |
| ankle_left | leg | 0.0300246 | -0.006157 -0.01375 -0.01566 | 5.92e-06 1.12e-05 7.74e-06 -2.1e-07 8.2e-08 5.7e-08 |
| neck | trunk_base | 0.0368414 | 0 -0.025 0.01417 | 1.73e-05 3.13e-06 1.64e-05 0 0 0 |
| neck_pitch | neck | 0.00572 | -6.5e-09 0.01166 -0.0145 | 1.09e-06 9.67e-07 5.12e-07 0 0 0 |
| yaw_roll_motion | neck_pitch | 0.0486 | -0.0001667 -0.00501 0.01781 | 6.98e-06 8.10e-06 9.58e-06 3.2e-07 -3.5e-08 3.4e-07 |
| jaw_soft(头部) | yaw_roll_motion | 0.188766 | 0.004605 0.0012 -0.03248 | 3.21e-04 2.54e-04 1.50e-04 -6.3e-07 6.6e-06 4.2e-06 |
| bearing_roll | trunk_base | 0.0230406 | -8.8e-11 0.0009941 0.01689 | 4.20e-06 3.42e-06 2.33e-06 -0 -0 -5.1e-08 |
| hip_l_2 | bearing_roll | 0.00618934 | 0.01482 1.6e-08 -0.0083 | 8.61e-07 1.16e-06 6.52e-07 1e-12 3.9e-07 -1e-12 |
| upper_leg_right | hip_l_2 | 0.0482067 | -0.006766 0.02288 0.01345 | 1.69e-05 1.04e-05 1.98e-05 4.4e-06 -2.3e-07 3.9e-07 |
| leg_2 | upper_leg_right | 0.0215844 | -0.03189 -1.5e-10 -0.009535 | 2.16e-06 5.25e-06 4.34e-06 1e-12 -7.7e-07 0 |
| ankle_right | leg_2 | 0.0300251 | 0.006155 -0.01375 -0.01566 | 5.92e-06 1.12e-05 7.74e-06 2.0e-07 -8.2e-08 5.7e-08 |
| **合计** | | **0.7372** | | |

机器可读完整版（含更多有效位与 HOME 位形下世界坐标）：[training/params/microduck_geometry.json](../../../training/params/microduck_geometry.json)。

## 4. 关节安装位形与限位（S1）

轴向全部为 body 局部 `0 0 1`；下表 pos/quat 为所在 body 相对父级的静态安装参数。

| 关节 | body | 安装 pos(局部,m) | body quat(wxyz) | 限位(rad) |
|---|---|---|---|---|
| left_hip_yaw | yaw2roll | 0.006 0.0175 -0.005 | 0 -0.7071 -0.7071 -0 | -0.4363 0.5236 |
| left_hip_roll | hip_l | 0 0.0165 0.0125 | 0.7071 -0.7071 -0 -0 | -0.384 0.384 |
| left_hip_pitch | upper_leg_left | 0.025 0 -0.0185 | 0.5 -0.5 0.5 -0.5 | -1.5708 1.5708 |
| left_knee | leg | 0.022 0.03578 -0.004 | 0 0.7071 0.7071 0 | -1.5708 1.5708 |
| left_ankle | ankle_left | 0 0.042 -0.026 | 0 1 -0 0 | -1.5708 1.5708 |
| neck_pitch | neck | 0.026 0.0145 0.03242 | 0 0 0.7071 -0.7071 | -1.5708 1.0472 |
| head_pitch | neck_pitch | 0 -0.05 -0 | 0 1 0 0 | -1.5708 1.5708 |
| head_yaw | yaw_roll_motion | 0 0.01869 -0.0145 | 0 0 -0.7071 -0.7071 | -2.9671 2.9671 |
| head_roll | jaw_soft | -0.0179 0 0.0145 | 0.7071 -0 -0.7071 -0 | -0.4363 0.4363 |
| right_hip_yaw | bearing_roll | 0.006 -0.0175 -0.005 | 0 0.7071 0.7071 0 | -0.5236 0.4363 |
| right_hip_roll | hip_l_2 | 0 0.0165 0.0125 | 0 -0 0.7071 0.7071 | -0.384 0.384 |
| right_hip_pitch | upper_leg_right | 0.025 0 -0.0185 | 0.5 -0.5 0.5 -0.5 | -1.5708 1.5708 |
| right_knee | leg_2 | -0.022 0.03578 -0.004 | 0 1 -0 -0 | -1.5708 1.5708 |
| right_ankle | ankle_right | -0.042 0 -0.026 | 0 -0.7071 -0.7071 0 | -1.5708 1.5708 |

动作关节顺序（上游执行器声明序）：左腿 5（hip_yaw→ankle）、头颈 4（neck_pitch→head_roll）、右腿 5。

HOME 位形下派生几何（用于自建胶囊设计，由 [extract_public_params.py](../../../training/scripts/extract_public_params.py) 级联计算，并与 MuJoCo 加载上游 XML 的结果对拍一致、误差 <1e-6）：大腿（hip_pitch→knee）≈0.042 m、小腿（knee→ankle）≈0.049 m、髋关节间距 0.035×2 m、HOME 屈膝（hip_pitch -0.458 rad）下踝高 ≈0.025 m、躯干初始高度 0.12 m。

**脚底碰撞体（上游 mesh 对照导出）**：HOME 位形、trunk z=0.12 时上游 `*_foot_collision` mesh 世界中心 (0.0068, ±0.0407, 0.0086)（左右镜像对称）、AABB 半尺寸 长 0.0272 × 宽 0.0217 × 厚 0.0068（mesh 局部系旋到世界系后正好轴对齐、底面水平；初始位形脚底离地约 1.8 mm）。此为 v0 脚盒（盒体近似）的数值来源。

## 5. HOME 站姿（S3，STAND2）

| 关节 | 角度(rad) | 关节 | 角度(rad) |
|---|---|---|---|
| left_hip_yaw / right_hip_yaw | 0.0 | neck_pitch | 0.3491 |
| left_hip_roll | -0.0873 | head_pitch | 0.3491 |
| right_hip_roll | 0.0873 | head_yaw | 0.0 |
| left_hip_pitch | -0.4579 | head_roll | 0.0 |
| right_hip_pitch | 0.4579 | left_knee | -0.0049 |
| left_ankle | 0.4530 | right_knee | 0.0049 |
| right_ankle | -0.4530 | | |

上游注释：躯干相对踝轴前移约 5 mm 让质心落在踝轴上方；hip_pitch/ankle 约 ±26°、膝接近伸直。

## 6. 执行器参数

### 6.1 HD-1910 BAM M6 辨识参数（S2，原值）

| 参数 | 值 | 参数 | 值 |
|---|---|---|---|
| kt（力矩常数折算） | 0.6238 | command_delay (s) | 0.006005 |
| R（绕组电阻 Ω） | 4.910 | friction_base (N·m) | 0.01580 |
| armature（转子折算惯量） | 0.0017819 | friction_stribeck | 0.009590 |
| q_offset（辨识偏置 rad） | 0.032748 | friction_viscous | 0.000310 |
| max_velocity (rad/s) | 100（放开斜率限速近似） | load_friction_motor / _external | 0.06851 / 0.15822 |

限制（上游 README 明示）：非本项目辨识；`q_offset` 不等于装配零位；`max_velocity` 非空载转速；`command_delay` 与队列 lag 不可相加；原始辨识电压/固件未知；`actuator:"sts3215"` 是 BAM 实现选择，不代表本机固件同款。

**模型/参数来源链（2026-11-03 补）**：[BAM（Better Actuator Models）](https://github.com/Rhoban/bam)由 Rhoban 维护（Apache-2.0，ICRA 2025 论文），提供执行器模型、**从记录轨迹拟合摩擦参数的辨识流程**，以及已辨识模型库（Dynamixel XL330、Feetech STS3215 等，**不含 HD-1910**）。HD-1910 的 `1910_m6.json` 来自下游 [LuwuDynamics/xgoduck_rl](https://github.com/LuwuDynamics/xgoduck_rl)（Apache-2.0，commit `326d77a1`），其 README 写明执行器用 “HLS1910 BAM model”替代 XL330。作者 kissqy 只做 HD1910 适配：`hd1910_actuator.py` 继承 `FrictionDRBamActuator`、加载该 JSON、设置 vin/延迟/kp 与背隙变体，再在官方 `microduck_rl` 上训练。原始辨识的台架条件（电压/固件/温度）未随文件发布，待确认。

**2026-11-03 补充：飞特官方 HD1910 BAM 已发布**（Gitee `ftservo/ftservo-bam`，Apache-2.0，2026-09-23～30，制造商台架）：`bam/params/feetech_hd1910_7_4V/` m1–m6，m6 的 `actuator` 为 `hd1910`。与本表 S2（Luwu）差异：kt 0.5645 vs 0.6238、R 2.966 vs 4.910、`command_delay` 0.00098 vs 0.0060 s、`friction_base` 0.0120 vs 0.0158、`load_friction_motor` 0.353 vs 0.069、`load_friction_external` 0.043 vs 0.158、`alpha` 4.25 vs 1.52。两者不是同一颗舵机的两种拟合，混用会改变观测-动作对齐和带载力矩预算；重训时优先官方版并保留来源。

**参数含义（BAM 源码 `model.py`/`actuator.py` 核对，2026-11-03）**：

| 参数 | 含义与作用 |
|---|---|
| `kt` | 力矩常数 [N·m/A]，`τ=kt·i`，同时决定反电动势 `kt·ω` |
| `R` | 绕组电阻 [Ω]，`i=(V−kt·ω)/R` |
| `armature` | 转子折算到关节的惯量 |
| `q_offset` | 辨识偏置（rad），**不是装配零位** |
| `command_delay` | 指令传输延迟 [s] |
| `error_gain_ratio` | 固件“位置误差→占空比”的换算比例 |
| `friction_base` | 库仑摩擦（恒定阻力矩）[N·m] |
| `friction_viscous` | 粘滞阻尼（∝速度） |
| `friction_stribeck` | 低速段附加摩擦幅值 |
| `dtheta_stribeck` | Stribeck 特征速度（越小越“陡”） |
| `alpha` | Stribeck 曲线指数 |
| `load_friction_base` | 非分侧负载摩擦系数（m3/m4） |
| `load_friction_motor` / `_external` | 分侧负载摩擦权重：电机侧力矩 vs 外力/重力侧力矩（m5/m6） |
| `load_friction_*_stribeck` | 上述分侧项的“低速附加”部分 |
| `load_friction_*_quad` | 电机力矩与外力矩**反向**时的二次耦合损耗 |
| `max_velocity` | 目标斜率限幅（100≈关闭），不是空载转速 |

控制链：`duty=clip(error_gain·kp·Δq, ±max_pwm)` → `V=duty·vin` → `i=(V−kt·ω)/R` → `τ=kt·i`；摩擦预算 `frictionloss = friction_base + stribeck_coeff·friction_stribeck + 负载项`（`stribeck_coeff=exp(−|ω/dθ|^alpha)`），粘滞项作为阻尼，最终由 MuJoCo 按停止力矩在 ±预算内裁剪。

**怎么确认参数对不对（2026-11-03）**：参数没有绝对真值，只有“在**未参与拟合**的数据上预测得准不准”。可用的判据：

1. **留出验证集**：BAM 的 `--validation_kp` 就是留出一档 P 增益；还应按速度段/负载/方向留出；
2. **独立台架轨迹**：用没参与拟合的阶跃、低速换向、带载、自由下落轨迹回放，比较位置/速度 MAE 与最坏段误差；
3. **物理一致性**：`V/kt` 应与空载转速同量级，`kt·V/R` 应与堵转力矩同量级，R 可由电压阶跃/电流估算，armature 应与转子惯量×减速比² 一致；
4. **残差分析**：误差是否集中在低速（Stribeck 不足）、高速（粘滞/反电势）、带载（负载摩擦）或某方向（分侧项）——有结构说明缺物理项；
5. **敏感性**：每个参数 ±10–20% 扰动，看验证误差变化；几乎不变的方向=不可辨识，应固定或降档；
6. **对比两份参数**：把 Luwu 与飞特官方 m6 都放到**本机自己的**台架数据上回放，比 MAE；不要用它们各自拟合的数据互相比。没有台架时只能用现有机器人日志离线回放，但缺电流/负载，结论有限。

官方值不等于本机正确值（批次、固件、温度、台架不同）；辨识值也不等于错误。只有“你的硬件 + 未参与拟合的数据”能裁决。

### 6.2 v0.1 模型的简化映射（自定；2026-10-15 用户指出动作超速后修正）

执行器为**力矩源（motor）+ 环境内一阶电机模型**：`V_pwm = clip(KV·(q_target−q), ±vin)`，`i = (V_pwm − kt·ω)/R`，`τ = kt·i`，每个物理步（0.002 s）重算。

| v0.1 使用值 | 来源与理由 |
|---|---|
| motor `ctrlrange=±0.94` | S2 电压满幅力矩 `kt·vin/R` @7.4V（规格书 15 kg·cm≈1.47 为 8.4V/辨识口径差异，保留对照） |
| 速度上限 ≈11.9 rad/s @7.4V | 反电动势自然导出 `vin/kt`（S2），60° 用时 88 ms，与飞特标称量级一致；**修复了 v0 position 执行器无速度上限的缺陷**（旧策略实测关节速度达 792 rad/s，修正后 10.9 rad/s） |
| joint `armature=0.00178`、`frictionloss=0.0158` | S2 原值。勘误：v0 生成 XML 的 joint 未引用 default class，两参数此前**实际未生效**，2026-10-15 修正后才真正加载 |
| 固件电压环增益 `KV=200` V/rad | **自选初始值**（小信号刚度 kt·KV/R ≈ 25 N·m/rad，与 v0 的 kp=25 相当），待整定 |
| 延迟/电压 sag/负载相关摩擦/Stribeck | **v0.1 未实现**，完整 BAM 行为留待 v1 |
| 控制周期 50 Hz（timestep 0.002 × decimation 10） | 上游控制周期口径，非本机总线实测 |

对照：上游 XL330 XML 辨识默认为 `kp=0.55, kv=0, forcerange ±0.96, damping 0.053, frictionloss 0.0048, armature 0.0018`（**XL330 参数，C 线不用**，仅记录防混用）；上游 HD-1910 任务用完整 BAM + `kp_fw=5`、电压 7.4–8.0 V、命令延迟 3–6 步。

## 7. 自建 v0 模型的非借鉴部分（自行设计，记录以便迭代）

- 几何：胶囊（端点=关节中心，半径按质量目测 0.006–0.011 m）+ 躯干/头/脚盒（躯干/头盒半尺寸为估算包络；脚盒尺寸取上游 mesh AABB，见第 4 节）；**非 CAD 网格**，仅用于碰撞与可视化。
- IMU site 位置 (-0.021, 0, -0.0147)：取上游 CAD 中 imu site 安装位置数值（S1），属安装参数。
- 地面摩擦 1.0 / condim 3 / 优先脚接触、积分器 implicitfast、自碰撞 exclude 集合：自选。
- keyframe `home` 的 trunk 高度 0.1182 m：由脚本按"HOME 关节角下脚盒底面贴地"计算，非上游数值。

## 8. 局限与下一步

- 质量惯量≠本机（XL330 版 CAD）；HD-1910 更重（15 颗替换后整机质量待称重），仿真站姿/步态特性会偏——学习阶段接受，上机前必须替换为实测。
- 脚盒用轴对齐盒近似上游 sole mesh（AABB 等尺寸），接触形状与真实鞋底不同；躯干/头盒为估算包络、经 exclude 排除与相邻肢体重叠碰撞。
- 上游 14 维接口与 C 线 15 舵机的映射（嘴关节、关节方向、零位）未定，v0 不做部署假设。
- 下一步：跑通 v0 站立训练 → 速度命令任务 → 引入延迟/摩擦完整化（BAM 化）→ 域随机化 → 实物称重/量测替换关键参数。
