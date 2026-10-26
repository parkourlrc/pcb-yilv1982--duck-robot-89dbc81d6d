# imu_to_dxl 三版来源对比查证记录

查证日期：2026-10-09。用户问：[ScrapMeta/microduck-diy](https://github.com/ScrapMeta/microduck-diy/tree/main/imu_to_dxl) 的 `imu_to_dxl` 是不是飞特版。本次只读远端资料。

## 结论

**ScrapMeta 的 imu_to_dxl 不是飞特版，是 Dynamixel 2.0 专用版。**

证据（README 契约表 + 固件目录树，2026-10-09 读取）：

- README「契约」表明确：协议 **Dynamixel 2.0**、ID 200、1 Mbps、控制环读地址 **124**、12 字节块（陀螺 i16×3 + 四元数 half-float）——对齐官方 `duck-control` 的 `sync_read` 契约（XL330/官方路线）。
- 固件源文件只有 `dxl_slave.c` / `dxl_crc.c`（DXL Protocol 2.0 CRC-16），**无任何飞特 SCS/STS/HLS 实现**。
- 硬件 v0.3（真源 `imu_to_dxl_ref_2026-08-30_18-59-47.eprj2`，嘉立创EDA专业版工程）：STM32G031F8P6 + LSM6DSV16X（SPI + SFLP），USART2 + SN74LVC1G125 半双工，双 B3B-EH 3P 座 + BM07 7P 调试座，AP2210K-3.3 LDO。MIT 许可。

## 三版对比（回答"哪版是飞特的"）

| | ScrapMeta/microduck-diy | fanhao375/microduck-replica | jyg9/microduck-community-kit |
|---|---|---|---|
| MCU | STM32G031F8P6（TSSOP20） | STM32G031F8P6（TSSOP20） | **GD32F303CC（LQFP48）** |
| IMU | LSM6DSV16X（SPI+SFLP） | LSM6DSV16X | LSM6DSV16X |
| 总线协议 | **仅 Dynamixel 2.0**（ID 200 @124） | 固件 **0.2.0（2026-09-22）起换成飞特 SCS/STS**；其采购清单注明硬件不改、固件分支即可双协议 | **双协议自动识别**（DXL 2.0 @124 + 飞特 @56 的 15 字节契约块），带 A/B 槽 bootloader 和总线在线升级 |
| 板卡形态 | 自绘 v0.3，调试走 BM07 7P + ST-Link/OpenOCD | 自绘 45×22mm 双层；交互式 BOM 在仓库 hardware/ | **成品有售**（作者淘宝店，见其 README）；板上带 CH340 调试口 |
| 遥测布局 | @124 12B（官方契约）；20B 诊断为"自约定" | 见其 firmware/ | @124 20B / 飞特 @56 15B 契约块 + @128 20B 诊断（与 15 颗舵机同一次 sync_read） |

## 对手头绿板（丝印 IMU2DXL v1.0）的判别建议

版本号线索：ScrapMeta 现行 v0.3、replica 为自绘 v0.x，都不叫 v1.0；**"v1.0" 更像商业化成品版（jyg9 店铺）的编号**，但仅为推测。实物判别方法（按可靠度排序）：

1. **看主控封装**：GD32F303CC 是 LQFP48（四边 48 脚），STM32G031F8P6 是 TSSOP20（20 脚细体）——一眼可辨。GD32 ⇒ jyg9 版（飞特可用、双协议）；STM32 ⇒ ScrapMeta/replica 血统。
2. **找 CH340/USB**：jyg9 版板上有 CH340 调试串口；另两版没有（ScrapMeta 用 7P 调试座）。
3. **问购买渠道**：jyg9 淘宝店订单可直接确认。
4. 若是 STM32G031 板：硬件同样能挂飞特总线（半双工 TTL 物理层一致），但**必须刷 replica 的 0.2.0+ 飞特固件**；ScrapMeta 固件只应答 DXL 2.0，飞特版的 robotd（读 @56/15B）认不了它。若是 jyg9 的 GD32 板：直接兼容 C 路线（含其 upgrade.py 在线升级工具链）。

## 刷机兼容性：ScrapMeta 板能不能刷 replica 的飞特固件（2026-10-09 补查）

**能刷，引脚不用改。** 两板同源（replica 的固件底子来自"同学写的底子，PR #32"，文件结构与 ScrapMeta 高度相似），引脚映射逐脚对得上：

| 功能 | ScrapMeta v0.3（md_config.h） | replica 板（接线表） | 兼容性 |
|---|---|---|---|
| IMU INT1 | PA0 | PA0（U1.7） | ✅ |
| 总线方向 OE# | PA1（固件 GPIO 翻，`0=TX 1=RX`） | PA1 = **USART2 硬件 DE**（`CR3.DEP=1`，U1.8） | ✅ 同一网络功能——replica 固件把 PA1 配成硬件 DE 后照样驱动 ScrapMeta 的 1G125 OE#，时序还更好 |
| 总线 TX / RX | PA2 / PA3（USART2） | PA2 / PA3（USART2） | ✅ |
| SPI CS/SCK/MISO/MOSI | PA4–PA7 | PA4–PA7 | ✅ |
| 调试串口 | PA11 / PA12（USART1） | PA11 / PA12（重映射 PA9/10） | ✅ |
| SWD | PA13 / PA14 | PA13 / PA14 | ✅ |
| IMU INT2 | 未引出 | PB0/PA8（U1.15） | ⚠ replica 固件若启用了 INT2 的 EXTI，ScrapMeta 板上此脚悬空——刷前核对 |
| RX_EN（回显抑制） | 无 | PB7（上拉，可选） | ✅ 固件写 PB7 在 ScrapMeta 板上是无害空操作 |

前端的唯一拓扑差异：replica 用 SN74LVC**2G**241 双缓冲（发+收，收常开），ScrapMeta 用单颗 1G**125**（只缓冲发，收直连）。replica 固件本就按"接收常开、发时按长度丢弃回显"设计，在 ScrapMeta 的直连 RX 上同样成立。

**刷录路径**：
- 预编译 HEX 在本地：`references/microduck-replica/hardware/imu_to_dxl/firmware/Build/imu_to_dxl.hex`（0.2.0，飞特）——不用装 Keil。
- SWD 接 ScrapMeta 的 J2（BM07 7P）：2=SWCLK、3=SWDIO、4=GND、7=NRST（1=+3V3 参考），用 ST-Link + OpenOCD（ScrapMeta 仓库自带 `flash_openocd.sh`，把目标换成 replica 的 HEX 即可）。
- **G0 空片坑**（replica 实测记录）：第一次烧完软件复位可能停在 ST bootloader——**断电重上电一次**即好。
- 契约对齐：replica 0.2.0 = 飞特 SCS/STS、ID 200、**@56 的 15 字节块**，与 HD-1910（HLS 家族）的 present 块布局及 robotd 飞特补丁的 sync_read 兼容。

**成熟度警告**：replica 固件**尚未上过真总线**（其 README/协议文档明写"真总线待实测"；2026-09-22 只验证到 IMU 采样与模拟总线 `imu200.py check`）。真机验证过（15×HD-1910 + 50Hz 环路 + 在线升级）的只有 jyg9 的 **GD32** 固件——但那是另一颗 MCU，**不能**刷进 STM32G031 板。如果手头绿板是 jyg9 的 GD32 板，也不需要刷：出厂即双协议（含飞特），用它的 `upgrade.py` + `.ipkg` 走总线升级。

## 关联

- 手头板照片与到货记录：根 `PROGRESS.md` 2026-10-09 硬件到位表。
- HAT（Radxa 版）查证：`../microduck-hat-20261006/research.md`。
- 电池/banana_pcb 调研（其中 §4 也提过 ScrapMeta 仓库）：`../microduck-battery-20261008/research.md`。

## 2026-10-14 补充：用户第二块 IMU 板确认为 jyg9 GD32 社区版

用户提供第二块板（**单个 3P 座**）正反面照片（存 `docs/photos/imu-board-b-20261014-a.jpg` / `-b.jpg`），照片判别：

- 主控 **LQFP48 + GigaDevice GD32F303 丝印** ⇒ jyg9 / community-kit 血统（排除 STM32G031 的 ScrapMeta/replica 血统）。
- 正面有电感 + 二极管 + SOIC-8 降压前端，与社区库 `hardware/imu_to_dxl/README.md` 标称**供电 6~24V、效率 >90%** 一致；该输入规格仅属于板②，使用前仍核实实物针序。**2026-10-25 清除旧指导**：“两板都可直挂总线”缺少板①实物器件和工作额定闭环，不再有效；板①按 [flash/README](../../../flash/README.md) 的供电红线执行，不能把板②的 6~24V 或旧 13.2V 说法套给板①。
- 出厂双协议自动识别（DXL 2.0 @124 + 飞特 @56），**不需要刷固件**；升级走总线 `upgrade.py`。
- ⚠️ 差异待确认：本板照片**未见 CH340/USB 调试座**（上文表格称 jyg9 版带 CH340），调试口形式以实物/卖家资料为准。
- 接线前仍需核对 3P 座针序（照片推断为 JST EH，1=GND 2=V+ 3=DATA，见 `docs/photos/board-servo-socket-pinout.png`），未核针序不上电。

**两块 IMU 板身份记录**：双口板 = ScrapMeta v0.3 / STM32G031（历史板①，2026-10-25 测量短接致损，不再列可用备件，见 [PROGRESS](../../../PROGRESS.md)；匹配固件和供电限制按 `flash/README.md`）；单口板 = jyg9 GD32 社区成品版（历史板②，当前使用，ID 200）。**用户 10-25 晚口头“板一”指单口板，确认此前出问题的也是它，烧损的是另一块双口板；本次没有换 IMU，后续按单口/双口区分。** 17:47 回读镜像 **1.5.1 / CRC32 0xD9CA0DEF / 槽 A**；18:18 旧接法已捕获请求 CRC 错误，具体环节未隔离。10-25 晚单口板刚移至 HAT 第二个 3P 口，用户测该口三针电压无问题，完整交错复测仍仅 2/360 成功。现行接法见[配电记录 §10](../power-distribution-comparison-20261010/research.md#hat-port2-20261025)，数据见[换口记录](../servo-web-imu-3d-20261024/research.md#hat-port2-20261025)。单口成品板照片/对应设计未见 LED，源码 PB5 指示灯只适用于开发板，勿要求它必须亮灯。

**2026-10-25 公开包核验补充**：已从 GitHub 官方 release 取得 1.5.1 槽 A 包，payload CRC32 为 `0x84C0963A`，与本机自报 `0xD9CA0DEF` 不同；仅说明构建来源未匹配，不能据此判定 Flash 损坏，也不能保证公开源码与本机二进制逐行一致。包、SHA256、官方 URL、源码比对及失败重试均见[二进制/源码证据](../servo-web-imu-3d-20261024/upstream-binary-source-check-20261025.json)。本轮没有刷写；上游 1.6.0 明确为 FT6 特殊协议、与 1.5.x 不兼容，不能作为直接升级。

## 2026-10-26 勘误与补强：jyg9 板官方 BOM/原理图已析

后续专题 [jyg9 电源分析（2026-10-26）](../imu-jyg9-power-5v-20261026/research.md) 直接解析了社区库内 jyg9 官方 KiCad 工程，修正/精确化本页两处：

1. **"带 CH340"说法与官方图纸不符**：0.2 版 BOM 无 CH340；USB 调试走 GD32 原生 USB（PA11/PA12）引到 H3 排针。上文 2026-10-14 记录的"照片未见 CH340 出入"由此关闭。
2. **"6~24V"下限的机理**：Buck = ETA2845S2G（芯片本体 5~38V），但板级 EN 分压（R3 100K/R4 30K → 0.231×VBATT，EN 阈值 1.5V）设定 **冷启动 ≈6.5V、维持 ≈5.93V——5V 供电必不启动**（不损坏）。EH 座针序 1=GND 2=V+ 3=DATA 获图纸级确认。
3. **"带 CH340"误读彻底闭环 + 固件路径修正**（同日追加）：v1 固件 README"调试口是 CH340 的 ttyUSB*"指**台架外接 CH340 适配器**，板上从无 CH340。且 `firmware/v1` 为完整开源复刻固件（build.sh + bootloader + A/B slot，真机验证过），与 0.2_10p 硬件引脚级吻合——自产板可烧 v1，见[电源分析专题追加 3](../imu-jyg9-power-5v-20261026/research.md)。
