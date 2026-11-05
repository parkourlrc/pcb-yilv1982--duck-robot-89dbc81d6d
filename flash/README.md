# 刷机指南：把飞特固件烧进 ScrapMeta imu_to_dxl 板

> **2026-11-01 当前板型边界**：用户已换上新单 3P 口 IMU，保持原出厂固件；已恢复主机混读并通过 servo-web 只读验收，见[记录](../docs/references/飞特策略模型上机核对/restore-mixed-sync-read-20261101.md)。本目录 STM32 v0.3 固件不能用于新单口板，v0.3 排障暂缓。

> **🚨 2026-10-25 事故记录（当晚更正归因）**：一块 v0.3 备件在机器人 7.4V 分支上测量电压时
> **表笔短接致损**（用户确认）。**"7.4V 过压直接烧毁"不成立为定论**。
> 错误的“5.5V 输入上限”已于 2026-10-31 依据原厂手册撤回：VIN/EN 推荐上限 13.2V、绝对最大 15V。
> 7.4V 没有超出该 LDO 推荐范围；不再要求因这个错误上限另建 5V 支路。见[电气复核](../docs/references/惯性单元输入电压复核/research.md)。
> 若仅 LDO 损坏可换料修复（AP2210K-3.3）。

目标板：**ScrapMeta `microduck-diy` imu_to_dxl v0.3**（32×22mm，丝印 `imu-to-dxl v0.3`，STM32G031F8P6 + LSM6DSV16X）——2026-10-09 用户确认手上绿板即此板。

要刷的固件：**replica 0.2.0 飞特版**（ID 200、@56 15 字节块、SCS/STS 协议）。预编译 HEX 已复制到本目录并通过作者公布的 SHA-256 校验（镜像 0x08000000 起 10,724 字节，`66bc7c53…938e`）。

> 引脚兼容性已逐脚核实（详见 `../docs/references/惯性单元三版来源对比/research.md`）：两板 PA0/PA1/PA2/PA3/PA4-7/PA11/PA12/PA13/PA14 功能一一对应；固件未用 INT2（ScrapMeta 板悬空无风险）；PB7 回显抑制脚在 ScrapMeta 板上是无害空操作。

---

## 供电与接口边界（2026-10-31 原厂复核）

- 设计 LDO 为 **AP2210K-3.3TRG1**：VIN/EN 推荐上限 13.2V、绝对最大 15V；3.3V 输出版本在 4.3–13.2V 测试线性调整率，5V 和 7.4V 均可作为输入。推荐范围与绝对最大值不是同一概念。
- 下文保留 **5V 台架刷机示例**，不是强制电压限制。新板 5V 下曾刷机成功；DAPLink 5V 那次只接正极、未接 DAPLink 自身 GND；pin4 那次则为主控启动不了，须分开分析，不能把刷机成功当作通信成功。独立供电必须使电源自身负极与 IMU/总线 GND 连通。
- **7.4V/8.4V 没有超过这颗 LDO 的推荐输入范围**；实物料号、温升和瞬态仍须与设计区分，不能由芯片范围宣称整板允许接到 13.2V。电源只进 J1/J3 的 VBATT；不进 DATA/J2-3V3，不把独立 5V 与总线电源经并联的 J1/J3 并接。单口 GD32 板使用另一套电源设计，不套用本结论。

---

## 第 0 步：清点（你需要有什么）

| 物品 | 说明 | 没有？ |
|---|---|---|
| SWD 调试器 | **首选 CMSIS-DAP/DAPLink**（免驱）；ST-Link V2 也行（要装驱动，见排障） | 淘宝 ¥10–25 搜 "DAPLink" 或 "ST-Link V2" |
| SH1.0 7P 端子线 / BM07B 插座 | **2026-10-31 新 PCB+SMT 板 J2 已贴装**；旧板曾仅有焊盘。以下方案仅适用于未贴座的板：方案 A：焊上 BM07B-SRSS-TB 座（约 ¥1-2）再插 SH1.0 7P 线（¥3，可复用）；方案 B：杜邦母对母线剪一头直接焊到 J2 焊盘（零采购，刷完剪掉） | 淘宝搜 "BM07B-SRSS-TB" / "SH1.0 7P 插头线" |
| 5V 电源 | USB 线（剪一头露出 +5V/GND）或面包板电源 | 现成的 USB 充电线即可 |
| 杜邦线母对母 | 4–6 根 | — |
| 万用表 | 核电压用 | — |

软件已全部备好（本目录）：OpenOCD 0.12.0、一键脚本、验收工具 imu200、Python 3.13 + pyserial（已装在 `C:\Users\elvis\AppData\Local\Programs\Python\Python313`）。**不需要装 Keil、不需要 ST 软件。**

## 第 1 步：接线（你做）

板子 **J2**（7P 调试座，板上丝印从 1 脚起：`3V3 / CLK / DIO / GND / TX / RX / RST`。2026-10-31 新板已贴 J2，可用匹配 SH 1.0 线；仅旧板未贴座时才考虑焊线或补座）：

| J2 脚 | 丝印 | 接 DAPLink | 接 ST-Link V2 |
|---|---|---|---|
| 1 | 3V3 | **VTref**（电平参考，必接） | 3.3V 脚（作参考） |
| 2 | CLK | SWCLK | SWCLK |
| 3 | DIO | SWDIO | SWDIO |
| 4 | GND | GND | GND |
| 7 | RST | 可不接（连不上再接 NRST） | 同左 |
| 5/6 | TX/RX | 不接（验收阶段可选，见第 4 步） | 同左 |

板子供电（**J1**，EH 3P 总线座，丝印 GND/VBATT/DATA；J1/J3 并联插哪个都行）：

```
USB 5V  +  → J1-2 (VBATT)
USB 5V  −  → J1-1 (GND)
```

> 先用万用表确认你剪的 USB 线空载 5V 左右再接。接好后板上应有 3.3V（可用万用表量 J2-1 对 GND）。

**接好后的状态：DAPLink 插电脑 USB + 板子 5V 供电。**

## 第 2 步：烧录（你做，双击即可）

1. 双击 **`1-烧录-DAPLink.bat`**（ST-Link 用户用 `1-烧录-STLink.bat`）。
2. 看到这两行就是成功：
   ```
   ** Programming Started **
   ** Programming Finished **
   ** Verified OK **        ← 关键行
   ```
3. **给板子断电、再上电**（G0 芯片第一次烧写后的已知行为：软复位可能停在 ST 引导程序，断电重启一次即正常运行）。

脚本内容（其实就一条命令，出错时可直接看）：`openocd -f interface/cmsis-dap.cfg -c "adapter speed 200" -f target/stm32g0x.cfg -c init -c "reset halt" -c "program imu_to_dxl-0.2.0-feetech.hex verify" -c "reset run" -c shutdown`

## 第 3 步：接上总线（你做）

用 URT-2（或微雪转接板）做主机，跟板子对话：

```
URT-2 / 微雪适配器 TTL 总线三线 ──→ 板子 J1：
   GND  → J1-1 (GND)
   DATA → J1-3 (DATA)
   （VBATT 不从 URT-2 取，板子继续用自己的 USB 5V，共地即可）
```

URT-2 插电脑 USB，双击 **`2-查COM口.bat`** 找到它的 COM 号。

## 第 4 步：验收（你做，双击）

双击 **`3-验收-imu200.bat`**，输入 COM 号。它按主控真实代码的判据跑 **13 项检查**（ID 200 在线、@56 读 15 字节、四元数范数、陀螺量程、采样计数递增、不冻结、sync_read 时延……），全 PASS = 主控会认。

日志自动落在 `tools\imu200\logs\`（含原始收发十六进制），有问题把日志发我。

可选加分项：把 J2-5（TX）接任意 USB-TTL 的 RX（115200），能看到 replica 固件的调试日志。

## 排障

| 症状 | 处理 |
|---|---|
| DAPLink 方式报 `no CMSIS-DAP device found` | 换 USB 线/口（有些线只充电）；设备管理器看有没有 HID 设备。本机这颗克隆的完整故障定性（不枚举/口被占/假在线/静默误判）见 [DAPLink 连接排障](../docs/references/调试器连接故障定性/research.md) |
| ST-Link 报 `libusb_open() failed` / 找不到 | ST-Link 需要 WinUSB 驱动：装 [Zadig](https://zadig.akeo.ie/) → Options→List All Devices → 选 ST-Link → 目标驱动选 **WinUSB** → Replace Driver（约 30 秒）。换回 ST 官方软件时需重装 ST 驱动 |
| 连上但 `target halted` 报错/读不到 IDCODE | 检查 SWDIO/SWCLK 有没有接反；把 J2-7 (RST) 也接到调试器 NRST；脚本已用低速 200kHz，仍不行降到 100（编辑 bat） |
| `Programming Finished` 但 `Verified` 报错 | 重新烧一次；再不行把 bat 里 `verify` 后加 `reset halt` 前多等——一般不出现 |
| 验收某项 FAIL | 把 `tools\imu200\logs\` 最新日志发我，逐条判 |

## 文件清单

| 文件 | 说明 |
|---|---|
| `imu_to_dxl-0.2.0-feetech.hex` | 待刷固件（已过 SHA-256 校验；来源 replica 仓库 Build/，参考库只读所以复制出来） |
| `verify_hex.py` | 重跑完整性校验：`python verify_hex.py` |
| `1-烧录-DAPLink.bat` / `1-烧录-STLink.bat` | 一键烧录（program + verify + reset run） |
| `2-查COM口.bat` | 列串口 |
| `3-验收-imu200.bat` | 总线 13 项验收 |
| `tools/xpack-openocd-0.12.0-7/` | OpenOCD（xpack 构建，内置 stm32g0x 支持，无需器件包） |
| `tools/imu200/` + `software/servo-web/` | 验收工具（来自 replica 仓库，复制出来用；`imu200.py demo` 可离线自测） |

## 边界（诚实清单）

- replica 0.2.0 固件**作者自述"真总线和舵机尚未实测"**（其主机测试与模拟总线验收全过，2026-09-22 已烧进其开发板工作正常）。本板刷完后 `imu200 check` 全 PASS 才算第一步验收；DE 释放时序、绝对 T_resp 等需逻辑分析仪的项可后置。
- 刷机会覆盖板上原有固件（ScrapMeta 的 DXL 2.0 版，如预刷过）；想刷回去：源码在参考库 `microduck-diy`（上游仓库），ScrapMeta 自带 `make g031` 构建与烧录脚本。
- 固件不写 Option Bytes、不写配置进 Flash（作者文档声明），刷写动作可逆、无 brick 风险（SWD 始终在）。
