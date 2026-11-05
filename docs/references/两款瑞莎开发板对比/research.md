# Radxa Cubie A7Z 与 Zero 3W 对比调研

- 日期：2026-10-14
- 问题与范围：用户询问瑞莎 Cubie A7Z（全志 A733）与项目当前主控 Radxa Zero 3W（瑞芯微 RK3566）的区别，评估是否影响 C 线主控选型。
- 验证状态：全部来自厂商文档与第三方报道，**非本机实测**；A7Z 未采购、未上机。

## 来源

- Radxa 官方文档 Cubie A7Z：https://docs.radxa.com/cubie/a7z （英文版 https://docs.radxa.com/en/cubie/a7z）
- Radxa 官方文档 ZERO 3：https://docs.radxa.com/zero/zero3
- LinuxLinks 功耗实测（2025-11）：https://www.linuxlinks.com/radxa-cubie-a7z-single-board-computer-running-linux-power-consumption/
- Hackster 报道（2026-10-10）：https://www.hackster.io/news/radxa-targets-cost-conscious-edge-ai-projects-with-the-compact-radxa-cubie-a7z-131ac9f35921
- 湖南大学嵌入式实验室 Zero 3W 介绍：https://esnl.hnu.edu.cn/info/1005/2716.htm

## 规格对比（厂商规格）

| 项目 | Zero 3W | Cubie A7Z |
|---|---|---|
| SoC | 瑞芯微 RK3566 | 全志 A733 |
| CPU | 4× Cortex-A55 @1.6GHz | 2× Cortex-A76 @2.0GHz + 6× Cortex-A55 @1.8GHz |
| 协处理器 | 无 | 玄铁 E902 RISC-V @200MHz |
| GPU | Mali-G52-2EE | Imagination BXM-4-64 MC1（OpenGL ES 3.2 / Vulkan 1.3 / OpenCL 3.0） |
| NPU | 0.8 TOPS INT8 | 3 TOPS INT8 |
| 内存 | 1/2/4/8GB LPDDR4 | 1/2/4/8/16GB LPDDR4/4x |
| 板载存储 | 可选 eMMC 5.1（最高 64GB） | 可选 UFS（最高 1TB） |
| 扩展总线 | 无 PCIe | PCIe 3.0 x1 FPC（可接 NVMe SSD / AI 加速卡） |
| 显示 | Micro HDMI 1080p60 | Micro HDMI 4K60 + USB-C 3.0 DP Alt 双屏 |
| 摄像头 | 1× 4-lane MIPI CSI（22Pin 0.5mm） | 1× 4-lane 或 2× 2-lane MIPI CSI |
| 无线 | Wi-Fi 6 + BT 5.4 | Wi-Fi 6 + BT 5.4 |
| 供电 | USB-C 5V/2A，GPIO Pin 2/4 可供电 | USB-C 5V，GPIO Pin 2/4 可供电 |
| 尺寸 | 65×30mm | 65×30mm |
| GPIO | 40Pin（最多 5 UART / 1 SPI / 2 I2C / 6 PWM） | 40Pin（PWM/UART/SPI/I2C，具体复用待核） |
| 空闲功耗 | 未实测（RK3566 平台一般更低） | 实测约 2.2W（无头）–2.9W（LinuxLinks 数据） |

## 结论

1. A7Z 与 Zero 3W **同外形、同 40Pin 排针、同 5V USB-C 供电**，物理层面大概率可直接对插 HAT。
2. **不是软件平替**：SoC 换厂商后，内核设备树、GPIO 引脚复用定义、串口设备名、NPU 工具链全部不同。社区套件（`references/microduck-community-kit/`）的 robotd 与飞特补丁是围绕 RK3566 + Debian 验证的，换板需要重新适配。
3. 全志 A733 的 NPU 工具链成熟度不及瑞芯微 RKNN，3 TOPS 短期难以利用。
4. 功耗上升（空闲 2.2–2.9W）对 NP-F550 电池续航不利，若考虑换板需实测整机功耗。
5. **当前不换板**：现阶段任务是舵机控制 + IMU 融合 + HAT 验证，Zero 3W 性能够用；A7Z 的吸引力在 16GB 内存、PCIe NVMe 和视觉推理，属于未来扩展选项。

## 未验证 / 待确认

- A7Z 40Pin 引脚复用表与 Zero 3W 的逐脚对应关系（需查 A7Z 原理图/pinmux 文档）。
- A7Z 上 Debian 镜像的成熟度与社区支持程度。
- HAT V1.2 与 A7Z 的电气/机械兼容（仅外形推断，未核对）。
- A7Z 带载功耗与整机续航影响。
