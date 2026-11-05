# ESP32 能否跑 microduck 的 MLP 策略

- 日期：2026-10-14
- 问题与范围：microduck 的 ~0.2M 参数 MLP 策略（`61→512→256→128→14`，50 Hz）能否在 ESP32（经典款 / S3）上实时推理并顺带承担总线循环？性能、内存、带宽定量推算 + 业界实证。
- 性质：桌面调研与纸面推算，无本机实测。结论不改变当前 C 线主控选型。

## 一、结论（先答后证）

1. **纯推理角度：能，且余量充足**。单次前向约 19.8 万次乘加（0.4 MFLOP），50 Hz 持续算力需求约 20 MFLOPS——对 240 MHz 的 ESP32 是轻负载。真正的约束是**权重存储带宽**，不是算力。
2. **约束与对策**：float32 权重约 773 KB，超出 ESP32 片内 SRAM（经典 520 KB / S3 512 KB），50 Hz 从外部存储流式读取需 ~39 MB/s，经典 ESP32 的 QSPI flash/PSRAM 实际带宽撑不住；**int8 量化后约 193 KB，可整体放进片内 SRAM，单次推理 1 ms 量级，毫无压力**。结论：经典 ESP32 必须 int8；ESP32-S3 有 int8 向量指令（ESP-NN/TFLite-Micro/ESP-DL），怎么跑都行。
3. **最有分量的实证：LuwuDynamics XGO-Duck**（Microduck 的官方衍生品，同为 15 个飞特 1910 舵机、同样的 ID 布局 10-14/20-24/30-34）。它的选择是**双芯片分工**：Linux 主机（Arduino UNO Q 的 Qualcomm 侧）用 ONNX Runtime 单线程跑 50 Hz 策略，STM32 跑 100 Hz 舵机/IMU 总线环。注意：**他们 MCU 明明就在 100 Hz 稳定跑总线，却仍把推理留在 Linux 侧**——说明难点不在算力，而在 ONNX 直接可用、换模型不重刷固件、带 Web UI 的迭代便利。
4. **对本项目的含义**：C 线现有 Linux 主控（robotd，Rust/ONNX）已覆盖此需求；ESP32 是"未来极简整机/独立步态协处理器"的可选实验路线，不是当前路线的变更。

## 二、定量推算（非实测，公式与假设如下）

模型：`61→512→256→128→14`，ELU，obs 归一化已嵌入图内（见 [runtime 策略模型调研](../运行时策略模型调研/research.md)）。

| 量 | 计算 | 结果 |
|---|---|---|
| 参数量 | 61×512+512×256+256×128+128×14+偏置 910 | ≈ 197,774 ≈ 0.198M |
| 单次乘加 | 同上 | ≈ 0.198M MAC |
| 单次浮点 | ×2 | ≈ 0.40 MFLOP |
| 50 Hz 持续算力 | ×50 | ≈ 20 MFLOPS |
| float32 权重体积 | ×4 B | ≈ 773 KB（> 片内 SRAM） |
| int8 权重体积 | ×1 B | ≈ 193 KB（可入片内 SRAM） |
| float32 带宽需求 | 773 KB×50 | ≈ 38.6 MB/s |
| int8 带宽需求 | 193 KB×50 | ≈ 9.6 MB/s |

推理耗时估算（假设：矩阵-向量乘访存受限）：
- 经典 ESP32 @240 MHz，int8 标量乘加按 1–2 周期/MAC → 0.8–1.6M 周期 ≈ **1.7–3.3 ms**，20 ms 节拍内富余。
- ESP32-S3 @240 MHz，int8 向量指令（ESP-NN）→ **<1 ms**。
- 经典 ESP32，float32 权重走 QSPI flash/PSRAM（实际 ~20–30 MB/s）→ 26–39 ms，**50 Hz 下不可行**；这也是"必须 int8"的原因。

总线时序估算（1 Mbps 半双工，return delay 0，参照 [飞特适配架构](../../../../references/microduck-replica/software/飞特适配架构.md) 的 DXL 帧构成）：sync_read 16 器件×(帧头+12 B 数据) ≈ 2.5–3.5 ms；sync_write 15×4 B ≈ 0.8–1 ms；合计 ≈ 3.5–4.5 ms，占 20 ms 节拍的 1/4 以内。**旁证：XGO-Duck 的 STM32 以 100 Hz（10 ms 周期）跑同类总线环**，比我们需要的更紧。

## 三、业界实证

### LuwuDynamics XGO-Duck（同型机器人，最直接参照）【上游公开资料】

- 硬件仓 `github.com/LuwuDynamics/xgoduck_hardware`：Arduino UNO Q（"Linux host for policy inference and web UI; STM32 MCU for servo and sensor communication"）+ 15 个飞特 1910 串行舵机（10 腿 + 4 颈头 + 1 嘴），IMU 为 QMI8658A；策略输出 14 关节目标，嘴舵机单独控制——与 microduck 完全同构。
- 运行时仓 `github.com/LuwuDynamics/xgoduck_runtime_arduino`：**Linux 50 Hz ONNX →（80 B duck_command）→ STM32 100 Hz 总线环**，MCU 以 100 Hz 发布 240 B `duck_state` 快照，50 Hz 线程读最新一帧；MCU 不等 Linux，迟到周期直接跳过；舵机位置饱和到编码器 0–4095 并拒绝非有限目标。
- 训练仓 `github.com/LuwuDynamics/xgoduck_rl`：PPO/mjlab 训练，ONNX 导出（归一化入图），执行器为 HLS1910 BAM 模型（`1910_m6.json`）——本仓 B 线训练引用的正是这套参数（见 `README.upstream.md`）。

### 其他佐证【公开通识级】

- 乐鑫官方支持 TFLite-Micro（含 int8 量化）跑在 ESP32/S3 上：[ESP32 如何运行 TensorFlow 模型](https://www.espressif.com/zh-hans/news/ESP32_meet_Tensorflow)。
- 社区共识：小型 MLP 步态策略可用 TFLite-Micro 或手写 C 推理跑在 ESP32 上（四足爱好者常做）；更重的模型建议主机推理流式下发——[NVIDIA 开发者论坛讨论](https://forums.developer.nvidia.com/t/is-it-actually-possible-to-sim2real-from-isaacgym-anymal-enviroment-to-a-quadruped/245091)。
- 芯片规格依据：[ESP32-S3 Datasheet](https://docs.espressif.com/esp32-s3_datasheet_en.pdf)（512 KB SRAM、LX7 240 MHz、向量指令）；经典 ESP32 520 KB SRAM 为通识规格。

## 四、如果真要在 ESP32 上部署，路线

1. **量化导出**：ONNX → TFLite（int8 PTQ）→ TFLite-Micro（S3 有 ESP-NN 优化内核）；或用训练仿真 dump 一批观测作代表性数据集做激活量化。RL 策略对量化有一定敏感性，**必须先在仿真里用量化后的推理复跑验收**（sim2quantized-sim），过了再上真机。
2. **手写导出**（对 4 层 MLP 很现实）：把权重和归一化 mean/std 直接 dump 成 C 数组，前向 ~200 行 C，ELU 用 `expf` 或查表。无任何依赖，最省心，爱好者四足项目常用做法。
3. **runtime 重写**：robotd 是 Rust/Linux，ESP32 上要重写 20 ms 节拍循环（ESP-IDF C++，或 esp-rs，但 ONNX 生态不可用）；舵机替换 adoption、寄存器纠偏、health 工具、免重刷换模型等便利全部丢失。
4. **收益**：成本 ~￥20-40、瞬时启动、mW-级待机（相对 Linux 主控）、自带 Wi-Fi/BLE 遥控链路。

## 五、验证状态、限制与下一步

- 已验证（外部证据）：XGO-Duck 的 50 Hz ONNX + 100 Hz MCU 总线架构、同舵机同 ID 布局；乐鑫 TFLM 官方支持。
- 未验证（纸面推算）：本文所有耗时/带宽数字均为公式估算，未在本机 ESP32 上实测；int8 量化对本策略的精度影响未评估。
- 不改变现行路线：C 线主控已到位（eMMC 线刷已完成），ESP32 仅作为未来"极简整机"或"独立步态协处理器"的备选记录在案。

## 关联

- [runtime 策略模型调研 20261013](../运行时策略模型调研/research.md)：MLP 结构、观测组成、50 Hz 节拍出处。
- [B 线训练实测](../../../b-training.md)：ONNX `[1,61]→[1,14]` 与图内归一化证据。
- [飞特适配架构](../../../../references/microduck-replica/software/飞特适配架构.md)：20 ms tick 与总线帧构成。
- 上游参照：`LuwuDynamics/xgoduck_hardware`、`xgoduck_runtime_arduino`、`xgoduck_rl`（GitHub，只读外部仓库）。
