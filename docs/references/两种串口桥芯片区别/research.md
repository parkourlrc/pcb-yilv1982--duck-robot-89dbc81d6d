# FT232H 与 FT232RL 区别调研（2026-10-14）

## 日期与问题

- 日期：2026-10-14
- 问题：FTDI 的 FT232H 与 FT232RL 有什么区别；在什么场景下选哪个。
- 背景动机：与本项目 Radxa Zero 3W 串口调试通道（固定 1500000 波特）相关，评估 FTDI 转接板作为替代串口通道时需分清这两颗常见芯片。注意：DAPLink 在 1.5M 下的乱码曾定性为 USB 全速带宽硬限，**该定性已于 2026-10-14 勘误**（[调试器连接故障定性](../调试器连接故障定性/research.md)：150KB/s 仅占全速 USB 有效吞吐约 15%，带宽不是瓶颈；真因是克隆固件无硬件 FIFO/DMA，实时性跟不上 6.67µs/字节）。
- 范围：仅规格对比与公开资料整理（属"原理图或厂商规格"级证据），**非本机实测**。

## 来源

- FT232H 官方数据手册：<https://ftdichip.com/wp-content/uploads/2020/07/DS_FT232H.pdf>（新版路径示例：<https://ftdichip.com/wp-content/uploads/2024/09/DS_FT232H.pdf>）
- FT232R 官方数据手册：<https://ftdichip.com/wp-content/uploads/2020/08/DS_FT232R.pdf>
- Adafruit FT232H Breakout 指南（UART 与 MPSSE 二选一、MPSSE 时钟 ~450 Hz–30 MHz）：<https://learn.adafruit.com/adafruit-ft232h-breakout/serial-uart>、<https://learn.adafruit.com/adafruit-ft232h-breakout/spi>
- pyftdi 文档（FT232H 单通道、时钟最高 30 MHz、SPI 主机 + 基础 JTAG 主机）：<https://eblot.github.io/pyftdi>
- 检索日期：2026-10-14；以上均为公开网页，未下载手册全文逐页核对，关键数字已与多来源交叉。

## 对比（厂商规格，未在本机验证）

| 项目 | FT232RL | FT232H |
|---|---|---|
| USB 速度 | USB 2.0 Full Speed（12 Mbps） | USB 2.0 Hi-Speed（480 Mbps） |
| 接口模式 | 仅 UART；另有异步/同步 bit-bang 与 CBUS 位控 | UART 或并行 FIFO（245 模式）二选一；另有 MPSSE 硬件引擎 |
| 最高 UART 波特率 | 300 baud – 3 Mbaud | 最高 12 Mbaud |
| SPI / I2C / JTAG | 无硬件引擎，只能软件位控模拟（速率与稳定性有限，不适合 JTAG） | MPSSE 引擎原生支持，SPI 时钟与 JTAG TCK 最高 30 MHz；I2C 常用 100k/400k（pyftdi/OpenOCD 等支持） |
| 片上资源 | 集成 1024-bit EEPROM（VID/PID/序列号/CBUS 配置）与振荡器，免晶振 | 同样集成 EEPROM 与振荡器，外围极少 |
| IO 电平 | 内部 3.3V LDO，VCCIO 选 5V/3.3V（接口 1.8–5V） | VCCIO 1.8–5.25V 可调 |
| 封装 | SSOP-28（RL）/ QFN-32（RQ） | SSOP-28 / QFN-32 |
| 典型用途 | USB 串口线、MCU 下载口、低速系统 console | JTAG/SWD 调试探针、SPI Flash 读写、FPGA 配置、I2C 调试工具、高速串口 |
| 模块价位与渠道 | 便宜、量大；杂牌假芯片（克隆 FT232R）泛滥 | 较贵，以 Adafruit 等正规模块为主 |

注意：FT232H 的 UART 模式与 MPSSE 模式**同一时刻只能用一个**（Adafruit 明确说明）；需要双通道（如一路 UART + 一路 JTAG 同时用）看 FT2232H，四通道看 FT4232H。

## 与本项目的关联

- Radxa Zero 3W console 固定 1500000 波特（约 150 KB/s 有效载荷；本节 2026-10-16 按勘误后机制改写）：
  - **FT232RL**：1.5M 在其 3M 标称范围内；带宽不是瓶颈（150KB/s 仅占全速 USB 约 15%），且 FT232R 有硬件缓冲，原理上可承受；实际风险主要在**市售假芯片泛滥**、杂牌模块质量参差。
  - **FT232H**：余量更大（1.5M 为 12M 标称的 1/8 + 480 Mbps 高速 USB），且有硬件 FIFO 与成熟 FTDI USB 栈，对 1.5M 启动突发余量充分（对照克隆 DAPLink 固件路径的实时性短板）；还可兼任 pyftdi/OpenOCD 的 SPI/I2C/JTAG 主机工具。
- 结论对采购的指向（2026-10-16 勘误后依据）：FT232H 优先的理由是**余量更大 + 工具能力**，而非"全速 USB 必然丢字节"。已实际购入 FT232H 转接板（接线与使用见 [串口桥接瑞莎调试口](../串口桥接瑞莎调试口/research.md)）。

## 结论

- 一句话：**FT232RL 是全速 USB 的纯 USB 转 UART 桥；FT232H 是高速 USB 的 UART/FIFO + MPSSE 多协议工具（SPI/I2C/JTAG，时钟至 30 MHz）**。两者封装和"USB 转串口"的基本定位相似，USB 速度、波特率上限和协议引擎能力是三处根本差异。

## 验证状态与限制

- 本页全部为厂商规格与公开资料整理，本机无 FT232H/FT232RL 实测数据。
- **勘误（2026-10-16）**：初版"全速 USB 高波特率易丢字节"的说法继承了 daplink 专题勘误前的旧定性。按勘误后结论，DAPLink 乱码根因是克隆固件实时性，不是全速 USB 接口本身；FT232R 类真品有硬件缓冲，未见 1.5M 必然丢字节的依据。
- 未核验当前市售模块价格、真伪与具体渠道；如启动采购需另建采购调研并更新 BOM.md。

## 下一步（可选）

- 若决定为串口通道采购 FT232H 模块：建采购专题，核对 USB-C/Mini 接口、3.3V 电平、EEPROM 已配置版本，并更新 [BOM.md](../../../BOM.md)。

## 附：JTAG 概念速记（2026-10-14 追加，原理级通识，非本机实测）

- **是什么**：Joint Test Action Group 制定的边界扫描/调试接口标准（IEEE 1149.1）。芯片内部有一条移位寄存器链（TAP），可从外部移位读写，多颗芯片可在板上串成一条链（daisy-chain）。
- **线序**：4 根——TCK（时钟）、TMS（模式控制）、TDI（数据入）、TDO（数据出），可选 TRST（复位）。
- **三大用途**：
  1. 边界扫描（原始用途）：不跑程序、不用探针即可检查 PCB 焊接短路/断路，产测常用；
  2. 调试 MCU/CPU（现最常用）：暂停/单步 CPU、读写内存与寄存器、硬件断点——J-Link、OpenOCD 等调试器的底层通道；
  3. 烧录：FPGA 配置加载、SPI Flash 读写、经调试口给 MCU flash 编程。
- **与 UART 的区别**：UART 是系统运行时对外的通信口（console/日志）；JTAG 是绕过系统、直接访问芯片内部的控制口。用途不重叠。
- **与本项目的对应**：
  - 本机 DAPLink 克隆（CMSIS-DAP）就是把 USB 命令转成 JTAG/SWD 时序去烧 IMU 板（见 [flash/README.md](../../../flash/README.md)），该角色已在位；
  - IMU 板上 ARM Cortex-M 日常用 JTAG 的 2 线精简版 **SWD**（SWDIO/SWCLK），DAPLink 两种均支持；
  - 因此 FT232H 的 MPSSE 虽也能做 JTAG/SPI 工具（OpenOCD/pyftdi），但**采购 FT232H 的理由是高速串口通道，不是补 JTAG 能力**。
- 来源：IEEE 1149.1 标准通识与上文 FTDI/pyftdi 资料；未另行逐条网络核验，如后续涉及实际 JTAG 接线再补专项调研。
