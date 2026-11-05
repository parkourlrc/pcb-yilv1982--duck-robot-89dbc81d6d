# imu_to_dxl 三版来源对比查证记录

> **2026-11-02 用户确认（来源）**：当前这台单 3P 口 IMU 是 [kissqy/Microduck-kissqy](https://github.com/kissqy/Microduck-kissqy/tree/main/hardware) 的 `imu_to_dxl RevA V1`（STM32G031F8P6 + LSM6DSV16X，FT6 固件），与在用 HAT 同源。此前按 LQFP48 GD32F303 照片把“单口板”判为 jyg9 社区版，对应的是更早一块历史板；当前板以用户确认为准，封装/丝印仍待新照片核对。见[kissqy 参考工程](../../schematics/kissqy-hat-reva-reference/README.md)。

> **2026-11-01 状态更新 [用户确认／实测]**：新单 3P 口板已换上，软件身份 `06 00 00 00 f2` / ft6/legacy；恢复混合 SYNC_READ 与原状态判据后，servo-web 30 秒 0 超时/坏校验，15 舵机及姿态可读。新板厂商/固件批次未独立核准，不能套用旧 GD32 kitbits。双口 v0.3 先搁置；旧单口电阻损伤、旧 v0.3 短接损伤与 HAT 损伤分别存档。见[当前回滚验收](../飞特策略模型上机核对/restore-mixed-sync-read-20261101.md)。下文按各历史日期理解。

> **2026-10-31 当前板更新与电压勘误**：新制 v0.3 双口板已上线，单口 GD32 板下线；10-25 损伤的是旧 v0.3 板。AP2210 原厂确认 VIN/EN 推荐上限 13.2V、绝对最大 15V，撤回“仅 5V”限制；用户确认两路 5V 接法失败、7.4V 直挂正常，原因尚未唯一分离。见[电气复核](../惯性单元输入电压复核/research.md)。下文早期实物状态按各自日期理解。

查证日期：2026-10-09。用户问：[ScrapMeta/microduck-diy](https://github.com/ScrapMeta/microduck-diy/tree/main/imu_to_dxl) 的 `imu_to_dxl` 是不是飞特版。本次只读远端资料。

> **2026-10-26 单口 GD32 板工程入口**：已核实存在 KiCad 9 工程、原理图、PCB 布局及生产文件；见[本轮文件核对](#single-port-pcb-20261026)。本地布局标 `imu2dxl 0.2 / 2026/9/27`，不把设计同源等同实物每处修订一致；也不把本地快照称为上游最新版。
> **调试口补充**：这份设计有 H3 USB 下载焊盘、H1 UART 日志焊盘、H2 SWD 焊盘，没有 USB 插座或 CH340；不能将“未见 USB 座”写成“没有 USB 引出/只能从总线调试”。用途和供电边界见[接口核对](#usb-debug-20261026)。

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
| 板卡形态 | 自绘 v0.3，调试走 BM07 7P + ST-Link/OpenOCD | 自绘 45×22mm 双层；交互式 BOM 在仓库 hardware/ | **成品有售**；本机单 3P GD32 板未见 CH340/USB 插座；设计预留 H1 UART、H2 SWD、H3 USB 下载焊盘，有 KiCad 源文件 |
| 遥测布局 | @124 12B（官方契约）；20B 诊断为"自约定" | 见其 firmware/ | @124 20B / 飞特 @56 15B 契约块 + @128 20B 诊断（与 15 颗舵机同一次 sync_read） |

## 对手头绿板（丝印 IMU2DXL v1.0）的判别建议

版本号线索：ScrapMeta 现行 v0.3、replica 为自绘 v0.x，都不叫 v1.0；**"v1.0" 更像商业化成品版（jyg9 店铺）的编号**，但仅为推测。实物判别方法（按可靠度排序）：

1. **看主控封装**：GD32F303CC 是 LQFP48（四边 48 脚），STM32G031F8P6 是 TSSOP20（20 脚细体）——一眼可辨。GD32 ⇒ jyg9 版（飞特可用、双协议）；STM32 ⇒ ScrapMeta/replica 血统。
2. **核对接口与实物版本**：本机单口 GD32 成品板未见 CH340/USB 插座，但设计有 USB 下载和 UART/SWD 焊盘，不能以“应当带 CH340”作为该板判据；ScrapMeta 双口板另有 7P 调试座。
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
- HAT（Radxa 版）查证：`../白色扩展板原理图查证/research.md`。
- 电池/banana_pcb 调研（其中 §4 也提过 ScrapMeta 仓库）：`../电池取电结构查证/research.md`。

## 2026-10-14 补充：用户第二块 IMU 板确认为 jyg9 GD32 社区版

用户提供第二块板（**单个 3P 座**）正反面照片（存 `docs/photos/imu-board-b-20261014-a.jpg` / `-b.jpg`），照片判别：

- 主控 **LQFP48 + GigaDevice GD32F303 丝印** ⇒ jyg9 / community-kit 血统（排除 STM32G031 的 ScrapMeta/replica 血统）。
- 正面有电感 + 二极管 + SOIC-8 降压前端，与社区库 `hardware/imu_to_dxl/README.md` 标称**供电 6~24V、效率 >90%** 一致；该输入规格仅属于板②，使用前仍核实实物针序。**2026-10-25 清除旧指导**：“两板都可直挂总线”缺少板①实物器件和工作额定闭环，不再有效；2026-10-31 原厂复核已确认 AP2210 的 13.2V 推荐上限，撤回后来误写的“仅 5V”限制，见 [flash/README](../../../flash/README.md)；不能把板②的 6~24V 套给 v0.3，也不把 LDO 额定当作整板全工况验收。
- 出厂双协议自动识别（DXL 2.0 @124 + 飞特 @56），**不需要刷固件**；升级走总线 `upgrade.py`。
- 本板照片**未见 CH340/USB 插座**；旧表“必有 CH340”已撤回。2026-10-26 设计核对补齐 H1 UART/H2 SWD/H3 USB 下载焊盘，详见[接口记录](#usb-debug-20261026)，实物对应仍待核。
- 接线前仍需核对 3P 座针序（照片推断为 JST EH，1=GND 2=V+ 3=DATA，见 `docs/photos/board-servo-socket-pinout.png`），未核针序不上电。

**两块 IMU 板身份记录**：双口板 = ScrapMeta v0.3 / STM32G031（历史板①，2026-10-25 测量短接致损，不再列可用备件，见 [PROGRESS](../../../PROGRESS.md)；匹配固件和供电限制按 `flash/README.md`）；单口板 = jyg9 GD32 社区成品版（历史板②，该历史窗口使用，2026-10-31 已下线，ID 200）。**用户 10-25 晚口头“板一”指单口板，确认此前出问题的也是它，烧损的是另一块双口板；本次没有换 IMU，后续按单口/双口区分。** 17:47 回读镜像 **1.5.1 / CRC32 0xD9CA0DEF / 槽 A**；18:18 旧接法已捕获请求 CRC 错误，具体环节未隔离。10-25 晚曾移至 HAT 第二口，用户测电压无问题，交错复测 2/360；随后已脱离 HAT，22:39 曾接微雪 COM4、外部 7.4V。微雪首轮实际仅 USB，补电后仍全无字节；22:51 用户又拔下 IMU、同口换接舵机，独立舵机同样无字节，微雪尚未证明正常，不能据此判 IMU 损坏。现行条件见[舵机对照](../舵机网页工具惯性显示/research.md#waveshare-servo-ping-20261025)，历史数据见[换口记录](../舵机网页工具惯性显示/research.md#hat-port2-20261025)。单口成品板照片/对应设计未见 LED，源码 PB5 指示灯只适用于开发板，勿要求它必须亮灯。

**2026-10-25 公开包核验补充**：已从 GitHub 官方 release 取得 1.5.1 槽 A 包，payload CRC32 为 `0x84C0963A`，与本机自报 `0xD9CA0DEF` 不同；仅说明构建来源未匹配，不能据此判定 Flash 损坏，也不能保证公开源码与本机二进制逐行一致。包、SHA256、官方 URL、源码比对及失败重试均见[二进制/源码证据](../舵机网页工具惯性显示/upstream-binary-source-check-20261025.json)。本轮没有刷写；上游 1.6.0 明确为 FT6 特殊协议、与 1.5.x 不兼容，不能作为直接升级。

## 2026-10-26 勘误与补强：jyg9 板官方 BOM/原理图已析

后续专题 [jyg9 电源分析（2026-10-26）](../单口惯性单元五伏供电/research.md) 直接解析了社区库内 jyg9 官方 KiCad 工程，修正/精确化本页两处：

1. **"带 CH340"说法与官方图纸不符**：0.2 版 BOM 无 CH340；USB 调试走 GD32 原生 USB（PA11/PA12）引到 H3 排针。上文 2026-10-14 记录的"照片未见 CH340 出入"由此关闭。
2. **"6~24V"下限的机理**：Buck = ETA2845S2G（芯片本体 5~38V），但板级 EN 分压（R3 100K/R4 30K → 0.231×VBATT，EN 阈值 1.5V）设定 **冷启动 ≈6.5V、维持 ≈5.93V——5V 供电必不启动**（不损坏）。EH 座针序 1=GND 2=V+ 3=DATA 获图纸级确认。
3. **"带 CH340"误读彻底闭环 + 固件路径修正**（同日追加）：v1 固件 README"调试口是 CH340 的 ttyUSB*"指**台架外接 CH340 适配器**，板上从无 CH340。且 `firmware/v1` 为完整开源复刻固件（build.sh + bootloader + A/B slot，真机验证过），与 0.2_10p 硬件引脚级吻合——自产板可烧 v1，见[电源分析专题追加 3](../单口惯性单元五伏供电/research.md)。

<a id="single-port-pcb-20261026"></a>

## 2026-10-26：当前单口 GD32 板是否有 PCB 工程

**有，jyg9 / microduck-community-kit 已公开 KiCad 设计，本地参考快照也保存了实际工程文件。** 本次用户问工程是否存在，范围为只读核对来源、文件类型和设计身份，不打开保存参考工程、不运行硬件、不代为生产下单。

| 用途 | 本地文件 |
|---|---|
| KiCad 项目入口 | [imu_to_dxl.kicad_pro](../../../references/microduck-community-kit/hardware/imu_to_dxl/imu_to_dxl.kicad_pro) |
| 单板 PCB 布局 | [imu_to_dxl.kicad_pcb](../../../references/microduck-community-kit/hardware/imu_to_dxl/imu_to_dxl.kicad_pcb) |
| 原理图 | [imu_to_dxl.kicad_sch](../../../references/microduck-community-kit/hardware/imu_to_dxl/imu_to_dxl.kicad_sch) |
| 拼板布局 | [imu_to_dxl_10p.kicad_pcb](../../../references/microduck-community-kit/hardware/imu_to_dxl/imu_to_dxl_10p.kicad_pcb)；未独立验算实际生产拼板数量 |
| 已有生产资料 | [production/](../../../references/microduck-community-kit/hardware/imu_to_dxl/production/)：Gerber ZIP、bom.csv、positions.csv、designators.csv、netlist.ipc |

- **文件直接证据**：README 写使用 KiCad 9；原理图/PCB 头部均为 `generator_version "9.0"`。单板 PCB 丝印为 `imu2dxl 0.2 / 2026/9/27`，元件属性 U2=GD32F303CCT6、U3=LSM6DSV16XTR、U1=ETA2845S2G_C22362741、U4/U5=74LVC 接收/发送缓冲。这是 GD32 路线设计，不是双口 ScrapMeta `.eprj2`。元件属性是设计证据，不自动证明实物贴装完全相同。
- **来源**：[上游目录](https://github.com/jyg9/microduck-community-kit/tree/main/hardware/imu_to_dxl)，GitHub Contents API `https://api.github.com/repos/jyg9/microduck-community-kit/contents/hardware/imu_to_dxl` 于本日直接 HTTPS 读取成功，列有项目/PCB/原理图/拼板及 production。网页工具打开目录返回空正文，API 结果已另存，不伪称网页工具提供正文。
- **版本边界**：本地文件由 duck-robot 仓库跟踪，`git -C` 得到的 e44859a 是本项目迁移提交，不能充当上游硬件修订。将本地文本 CRLF 归一化为 LF 后计算 Git blob SHA1，项目/原理图/两份布局均与本日上游 listing 的 blob 不同，不能仅用换行解释差异；未下载覆盖、未断言变化内容。本地额外 `_10p.kicad_pro` 不在本日远端列表，不作为上游当前文件保证。
- **实物对应**：现有用户照片/芯片身份支持单口 GD32 社区成品路线，但未将实物背面丝印、批次、器件代换和所有走线与本地 0.2 或远端版本逐项匹配。所以“有工程”成立，“恰好是这块实物的完全相同修订”仍待核对。使用源文件可继续分析电源、DATA 收发和固件引脚，但不能直接据此定位当前故障。
- **许可文件**：目录附 `LICENCE.txt`，标题为 CERN Open Hardware Licence Version 2 - Permissive（CERN-OHL-P v2）；只记录文件标题，本轮不作法律解释或发布操作。
- **落盘与验证**：[源文件清单、SHA256、远端列表及 blob 对比](./pcb-source-check-20261026.json)。本轮只读源码/文件头、未运行 KiCad GUI/DRC/ERC、未导出或验收 Gerber，也未修改三个只读参考库。同步原理图索引和 PROGRESS，纠正本页残留“单口板必有 CH340”的旧指引；新链接与空白检查后留工作区，不 commit/push。

<a id="usb-debug-20261026"></a>

## 2026-10-26：USB 下载与 UART/SWD 调试接口

**结论：本地 0.2 设计有 USB 下载信号引出（H3），但没有 USB 插座或 USB 转串口芯片；调试日志走另一个 H1 UART，SWD 走 H2。** 用户问的是设计是否有 USB 调试口，应区分下载接口、电气引出与当前固件能否通过 USB 枚举/输出日志，不可只因成品照片没有 USB 座就回答“没有 USB”。

### 设计证据与逻辑针号

直接解析 `hardware/imu_to_dxl/imu_to_dxl.kicad_pcb` 的 KiCad S 表达式，保留每个焊盘的 net/pinfunction；[结果及源文件 SHA256](./usb-debug-design-check-20261026.json)。以下是**文件中的逻辑焊盘号，不是从实物某方向数针的接线图**，没有验证手上实物逐网一致。

| 接口 | 设计用途 | 图中连接 |
|---|---|---|
| H3，`microduck:pad-4` | USB 下载引出 | 1=GND，2=USB_DP，3=USB_DM，4=+BATT；DP 经 R18 51Ω 到 U2 PA12，DM 经 R17 51Ω 到 PA11 |
| H1，`microduck:pad-4` | UART 调试日志 | 1=+3.3V，2=GND，3 经 R10 51Ω 到 DEBUG_RX/PB7，4 经 R11 51Ω 到 DEBUG_TX/PB6 |
| H2，`microduck:pad-5` | SWD | 1 经 R14 1kΩ 到 NRST，2=+3.3V，3=GND，4 经 R13 51Ω 到 SWDIO/PA13，5 经 R12 51Ω 到 SWDCLK/PA14 |

- 原理图 `imu_to_dxl.kicad_sch:5006/5016/5046` 有 `SWD`、`USB Download`、`USB Download Switch` 文字；H3/H1/H2 实例分别位于 8533/12874/14173 行。H3 是 pad-4 焊盘封装，不是 USB-C/Micro-USB 座。
- USB_DP/DM 引到 GD32 本体，不经过 CH340；U1–U6 器件清单没有 USB 转串口桥。PCB 中 R33 跳线连接 BOOT0 与 +3.3V，R19 下拉 BOOT0；仅记录结构，不改跳线、不声称特定启动模式已实测。
- **供电注意**：H3-4 是直接接板卡电池轨的 +BATT，不能当成已隔离 USB VBUS。当前 7.4V 台架场景下，不能将该脚与电脑 USB 5V 直接并接。USB-only 电压是否满足板卡降压启动、MCU USB 下载模式/主机驱动是否可用均未验证，不提供直接飞线试接操作。

### 对排查的用途与限制

- `firmware/v1/README.md:188–195` 明确 H1 物理引脚和 PB6/PB7；`src/board.h:58–60,311,357–360` 定义 UART 调试默认启用、115200、USART0/PB6/PB7。可据此把 **H1 接外部 USB 转 TTL 串口读日志**列为排查候选，数据不经过微雪单线舵机接口；外部适配器和实物焊盘需匹配 3.3V 电平。
- “USB 下载焊盘”不等于“当前固件已实现 USB CDC 调试串口”，本轮没有拿到本机 USB 枚举或下载成功证据。本机镜像指纹与公开构建未匹配，源码默认日志打开也不能保证当前板一定输出日志。
- H2 是芯片调试/烧录通道，不是能直接插电脑 USB 的端口。没有运行 SWD、刷机、改固件或启用镜像总线，也不声称这次已通过日志定位故障。
- 已撤回台架验收单“没有调试日志可看、判别全靠总线侧”，同步照片索引与进度。没有新用户照片或新标注图；旧照片不因设计推导升级为已核实针序。

### 来源与验证状态

源文件为上节已指纹归档的本地 KiCad 快照，上游入口 `https://github.com/jyg9/microduck-community-kit/blob/main/hardware/imu_to_dxl/imu_to_dxl.kicad_sch`；本次网页工具打开仍返回空正文，设计结论依据本地原始文件及固件说明。未将上一轮远端 main 列表误当与本地逐行相同。S 表达式解析成功，关键引脚由封装 pad 与 MCU pinfunction、串阻网络交叉核对；未验证实际走线连通性/实物版本，未执行硬件试验。研究与派生 JSON 留工作区，未 commit/push。
