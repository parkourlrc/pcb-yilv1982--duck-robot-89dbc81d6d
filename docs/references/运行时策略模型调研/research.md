# runtime 策略模型调研：是不是 MLP、和 VLA 有什么区别

- 日期：2026-10-13
- 问题与范围：microduck runtime 在真机上加载/执行的策略是什么网络？输入输出是什么？它与 VLA（Vision-Language-Action）模型的本质区别？
- 性质：代码与文档调研，无本机硬件操作。VLA 对比部分为公开通识（RT-2 / OpenVLA / π0 / GR00T 等），未在本项目实验核验。

## 一、结论（先答后证）

1. **是 MLP，且是纯前馈网络**。actor 是一个 3 隐层 MLP：`输入 → 512 → 256 → 128 → 14`，ELU 激活，观测归一化（mean/std）嵌在导出的 ONNX 图内。推理时就是一次矩阵乘堆叠，无卷积、无注意力、无循环状态。
2. **runtime 不是模型，是部署器**。上游 `microduck_runtime` / `robotd`（Rust）以 20 ms（50 Hz）节拍循环：sync_read 总线（IMU 四元数+陀螺仪、15 个舵机的位置/速度/电流）→ 拼观测向量 → ONNX 前向 → 得到关节目标位置 → sync_write `goal_position`。模型本体是训练库导出的 ONNX 文件。
3. **它和 VLA 是两类东西**：这是"脊髓级"底层步态控制器（本体感知→关节目标，50 Hz，RL 训练，~0.2M 参数）；VLA 是"大脑级"任务决策器（图像+语言→动作，1–10 Hz，大规模模仿学习，数十亿参数）。二者在现代分层架构里是互补关系，不是替代关系。详见第四节。

## 二、证据

### 上游训练库（B 线参考，只读）

来源：`references/microduck-replica/software/training/`（上游 `pollen-robotics/microduck_rl` + 复刻项目改动）。

- `README.upstream.md`：策略在 mjlab（MuJoCo Warp）上用 PPO 训练，**50 Hz 控制频率**，导出 ONNX，由 `pollen-robotics/microduck` 仓的 runtime 部署到真机。【上游文档】
- 网络结构（所有任务一致，例 `src/mjlab_microduck/tasks/microduck_roller_slope_env_cfg.py:228-233`）：
  ```python
  hidden_dims=(512, 256, 128)   # actor 与 critic 同结构
  activation="elu", obs_normalization=True
  ```
  `docs/roller_standup_policy_summary.md:81` 同样记录：actor/critic `(512, 256, 128)` elu，`obs_normalization=True`。【代码/文档】
- 观测组成（`microduck_velocity_env_cfg.py`）：关节位置、关节速度、角速度（陀螺仪）、重力投影或原始加速度计、动作历史（`reset_action_history` 事件佐证）、速度指令（twist）、头部/身体姿态指令。actor 侧**刻意删除**了 `base_lin_vel`（只留给 critic 作特权信息）和 `height_scan`（真机没有地形传感器）。**没有图像，没有语言。**【代码】
- 动作：`JointPositionActionCfg`，scale=1.0，输出即 14 个受控关节的位置目标。【代码】

### runtime 侧（飞特适配架构分析，基于上游原型逆向）

来源：`references/microduck-replica/software/飞特适配架构.md` §1.3。

```text
tick (20 ms = 50 Hz)
  read()   sync_read：IMU 板(ID 200) SFLP 四元数+陀螺仪；舵机 present_pwm/current/velocity/position
  decide   观测 → ONNX 策略 → 目标
  write()  sync_write：goal_position ×15
每 1 s 读电压/温度（慢速传感器）
```
单位换算表（位置 2048=0 rad 等）在 `bus.rs`，数值来自原型机 `microduck_runtime`。【上游代码逆向，非本机实测】

### 本机实测（B 线训练冒烟）

来源：`docs/b-training.md`。

- ONNX 导出成功，`onnx.checker` 通过；CPU ORT 验证 shape **`[1,61] → [1,14]`**，图中含 `obs_normalizer._mean`（归一化嵌入图的直接证据）。【本机实测】
- 注意：这是 5 次迭代的冒烟导出，**不是可部署策略**；且 B 线 61 维观测与上游原版 51 维（`roller_standup_policy_summary.md` 提到 51D layout）不兼容，不能互换。

## 三、参数量推算（非实测）

51 或 61 维输入按 `512→256→128→14` 展开：
`51×512 + 512×256 + 256×128 + 128×14 + 偏置 ≈ 0.19 M`（61 维输入约 0.20 M）。
即 **二十万参数量级**，单次前向在 Pi 级 CPU 上为微秒~亚毫秒级。假设：无 LSTM/GRU 隐状态、obs 归一化是逐元素 affine（已由 ONNX 图内 mean 佐证）。

## 四、与 VLA 的区别（概念对比，通识）

| 维度 | 本项目 runtime 的 MLP 策略 | VLA（RT-2 / OpenVLA / π0 / GR00T 等） |
|---|---|---|
| 输入 | 本体感知：关节角/角速度、IMU（重力向量/角速度/四元数）、速度指令、动作历史 | 多视角相机图像 + 自然语言指令（+可选本体感知） |
| 结构 | 3 层 MLP，~0.2M 参数，ELU | VLM 主干（视觉编码器+语言 Transformer，数 B 参数）+ 动作头（离散 token 或 diffusion/flow-matching） |
| 训练 | PPO 强化学习，仿真（域随机化、BAM 执行器模型、背隙仿真），奖励函数设计驱动，sim2real | 大规模真机/仿真演示数据模仿学习为主，一般无手工奖励 |
| 输出 | 14 个关节位置目标，**50 Hz**，直接写舵机寄存器 | 动作块/末端目标/子目标，典型 **1–10 Hz**，频率撑不起双足动态平衡 |
| 任务范围 | 一任务一策略（走、起身、侧翻、轮滑各自独立 checkpoint），零语义理解 | 语言条件化跨任务泛化（"把杯子拿给我"） |
| 部署算力 | Pi 级 CPU，ONNXRuntime | GPU/NPU 或云端 |
| 角色 | 底层全身控制器（"小脑/脊髓"） | 任务级决策器（"大脑"） |

关键点：二者不是竞争关系。现代分层架构（π0、GR00T N1 等）正是 VLA 在上层出目标/指令，RL 训练的快速底层策略在 50 Hz+ 跟踪执行。microduck 目前**没有 VLA**：指令来自手柄/上层接口，"大脑"是任务策略的选择与切换，感知闭环完全依赖本体感知。

## 五、验证状态、限制与下一步

- 已验证：网络结构、观测组成、动作含义、runtime 节拍均有代码/文档直接出处；ONNX shape 与图内归一化有本机实测（B 线冒烟）。
- 限制：上游 `pollen-robotics/microduck` 主仓的 runtime 源码未直接查阅（本仓只有逆向分析文档）；C 线飞特版策略尚不存在，未来若按 HD-1910 重训，结构预计沿用同族 MLP 配置但观测维度可能变化。
- 下一步（无行动要求）：C 线重训时按 `docs/HD-1910训练前数据清单.md` 核对观测/动作维度后再导出部署。

## 关联

- [ESP32 部署可行性调研 20261014](../乐鑫芯片跑多层感知机/research.md)：该 MLP 在 ESP32/S3 上的算力、带宽推算与 XGO-Duck 实证。
- [B 线训练实测](../../../docs/b-training.md)：ONNX 导出与 shape 证据。
- [飞特适配架构](../../../references/microduck-replica/software/飞特适配架构.md)：runtime tick 与总线细节。
- 上游训练库入口：`references/microduck-replica/software/training/README.upstream.md`。
