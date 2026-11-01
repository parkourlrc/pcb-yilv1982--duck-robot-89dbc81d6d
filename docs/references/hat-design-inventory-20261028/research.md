# HAT 设计盘点与首版需求依据

日期：2026-10-28。范围：本项目三个只读参考目录及此前归档的官方/社区 HAT 工程。回答“有哪些 HAT 设计、提供什么功能”，为 KiCad 自设计整理需求；不修改电路、不下单、不实测。

## 结论与证据等级

- **[原始工程核对]** 可区分三类设计来源：Pollen 官方 C1/D1；社区 Radxa 适配 V1.0 原理图；kissqy HAT REVA 两层工程。C1/D1 是同一官方系列的两个修订，不是两套无关架构。
- **[待确认]** 用户白色 HAT V1.2 的完整工程仍未取得，不能用社区 V1.0、官方 C1/D1 或 kissqy 替代其实际网表。V1.0 来源沿用用户供图记录，不凭卖家线索另行认定作者。
- **[本地目录核对]** community-kit 的 hardware 只有 banana_pcb、dxl_hub、imu_to_dxl；未发现独立 HAT 工程。replica 引用官方 HAT，不视为又一套独立设计。build-tutorial 走 Pi Zero 2 W + OpenRB-150，非 C 线 HAT 设计。
- **[建议]** 用户已有 KiCad，优先把文件齐全的官方 C1 作为可追溯的功能参考；结合社区 Radxa 信号映射与 kissqy 精简思路形成自己的需求。尚未批准任何版本作为最终电路基线。

## 设计与交付资料

| 来源/固定版本 | 本地已有资料 | 可核功能 | 边界 |
|---|---|---|---|
| Pollen C1，88d51faf7f5fcc845d2e3b42d4f05ebb98b963b9 | KiCad 9 工程、层级原理图、四层 PCB、Gerber/钻孔、BOM、坐标、PCB PDF | 40P 主控接口、5V 降压、理想二极管电路/掉电检测、TTL 与 RS485 舵机接口、音频编解码/功放/麦克风、BMI088、4 个 I2C 扩展座、EEPROM 预留 | EEPROM 在 C1 BOM 标 DNP；原图 TODO 包含核对 Radxa 兼容性，不是直接适配本机的已验证成品 |
| Pollen D1，6de86283297e4c49a9da8312cd3395ab83c437e3 | PCB 源文件、PCB PDF、装配图 | PCB 器件字段确认 AP63205、LM5050-1、TLV320AIC3104、PAM8406、3P/4P 舵机座；板载 IMU 值为 LSM6DSV16XTR | 本地未配齐该提交层级原理图与生产三件套；不得把 C1 BOM 直接配 D1 PCB。不是声称当前最新版本 |
| 社区 Microduck-Hat-for-Radxa-Zero V1.0，用户 10-09 供图 | 5 页原理图 PDF；文档日期 09-03 至 09-20 | Radxa 40P 信号映射、5V 降压/掉电检测、BMI088、4 个传感器扩展座、TTL 3P×2、RS485 4P×2、音频编解码/功放/麦克风、EEPROM 电路 | 无该版可编辑 PCB；与实物 V1.2 未逐网对应。第 3 页也有 BNO085 符号，本轮未核其连线及贴装，不能写成两颗 IMU 均工作 |
| kissqy HAT REVA，7c5fba929e668aab4fa86f608fb7586c0e9718b2 | 10-07 EH2.5、10-15 AMP2.0 两份 EDA 专业版 .epro2，含原理图与 PCB | 作者文档/BOM：两层板、5V 降压、理想二极管电路、TTL 3P×2、音频/麦克风、一个 ToF/Qwiic 扩展座；10-15 版改接口并增 LED | 非 KiCad 原生工程；原版 HAT BOM 未列 BMI088/RS485 芯片，外置躯干 IMU 为另一块板；硬件许可尚未核定。长期运行是上游报告，不是本机实测 |

## 功能怎样理解

### 供电

C1 的 power.kicad_sch 有 AP63205 固定 5V 降压、LM5050-1/MOS 电路及 Switch off detection。这些描述分别是功能块，不代表具备整机过流保护、完整反接保护、充电或 UPS 能力，也不是本机负载额定。新板电池范围、5V 预算、入口/铜箔/接插件载流和 USB 倒灌边界需独立核算。

特别核对：C1 目录虽有 pwr_supply_charge.kicad_sch，但主入口只引用 main，main 只引用 audio/power/sensors/dynamixel。该充电图不在当前主工程层级中，C1 BOM 也不含其 CN3302/HY2120；不能把 USB-C 充电记为 C1 HAT 已提供功能。

### 总线

C1 有 3P TTL 与 4P RS485 两种物理接口；它们不能仅凭插座数量算成四路独立 UART。社区 V1.0 两个 3P 口同网，已在既有研究核对。新板需求应先写“两个插座、一条共享总线”；如果希望分离 IMU 与舵机为两路独立总线，则是新增需求，须核主控 UART、软件和走线。

HAT 提供电气收发接口；飞特与 Dynamixel 的报文支持仍取决于主控软件和从机协议。保留数据串阻/保护元件的调试位置是候选建议，不能因某作者 R33=0Ω 就把本机 R31 故障归因或最终阻值写死。

### 音频、传感器与 IMU

- C1 BOM：U2 TLV320AIC3104 编解码、U1 PAM8406 功放、MK1 模拟 MEMS 麦克风；社区 V1.0 第 5 页与 kissqy 文档也有相应音频模块。软件驱动和音频管脚适配另需确认。
- I2C/Qwiic 扩展座可接外围模块；提供 ToF 插座不等于板载测距传感器。社区 V1.0 扩展座中有 UART4 复用标注，最终信号映射须逐网核。
- 官方 C1 的 BMI088 是 HAT 本体位置的 IMU；D1 PCB 改为 LSM6DSV16XTR。它们不能不经坐标、安装位置和软件核对就替代躯干 IMU。
- 相机不列入这些 HAT 已核功能；本项目相机走主控相机接口，不因头部装有 HAT 就算 HAT 自带相机。

## 来源与定位

1. [官方归档说明](../../schematics/pollen-hat-pcb-reference/README.md)：固定提交、文件齐备度、Apache-2.0 与 3D 模型缺口。
2. [C1 原理图入口](../../schematics/pollen-hat-pcb-reference/c1-88d51fa/elec_RPI_Robot_HAT.kicad_sch)：约 523 行 Radxa TODO、13175 行 main 引用；main.kicad_sch 7335/7388/7441/7494 行子页引用；同目录各功能子页及 C1 BOM 核器件。
3. [D1 PCB](../../schematics/pollen-hat-pcb-reference/elec_RPI_Robot_HAT.kicad_pcb)：rev D1；约 18057 行 U11 Value=LSM6DSV16XTR。功能盘点仅到器件/接口层，未完成 D1 全网差异审计。
4. [社区 V1.0 PDF](../../schematics/microduck-hat-v1.0-sch/SCH_Microduck-Hat-for-Radxa-Zero_2026-10-06.pdf)：第 1 页主控，第 2 页电源，第 3 页传感器，第 4 页舵机，第 5 页音频；本轮使用 PyMuPDF 提取内容，未新做视觉逐网复核。
5. [kissqy 工程归档](../../schematics/kissqy-hat-reva-reference/README.md)、[README 快照](../hat-imu-shared-bus-20261027/pcb-search/kissqy-readme.md) §工程表/完整位号 BOM、[时间线](../hat-imu-shared-bus-20261027/pcb-search/kissqy-HAT-TIMELINE.md)：J5 ToF、J13/J14 TTL、U1/U2 音频、U9/U10 电源；10-15 工程容器已有核对记录，本轮未在 EDA 中导出完整网表。
6. [community-kit README](../../../references/microduck-community-kit/README.md) 及 hardware 目录；[replica README](../../../references/microduck-replica/README.md) §硬件开源说明；[build-tutorial README](../../../references/microduck-build-tutorial/README.md) §电源接线。只读上游中的历史概括不覆盖本项目现行证据。
7. 原始上游地址： https://github.com/pollen-robotics/elec_RPI_Robot_HAT 、https://github.com/kissqy/Microduck-kissqy 。本轮 web open/search 未返回可引用内容，因此依赖已归档固定版本，不宣称重新核验了在线最新状态。

## 限制、失败与下一步

本轮未跑 ERC/DRC，因未产生电路变更；未启动 KiCad、未核本机软件版本、未核库存/报价。PowerShell 不支持 shell brace expansion，首次多文件搜索失败，随后改目录配 glob 完成层级引用检索；另一次路径通配调用失败，不据失败输出作结论。

需求草案见 [spec](../../specs/20261028-custom-hat/spec.md)。用户确认功能范围后，再进入资料确认与修改方案阶段。既有 IMU 丢包的机理仍待验证，新板不作为已验证修复。

<a id="rs485-eeprom"></a>
## 头部 IMU 确认与 RS485 / EEPROM 用途（2026-10-28 追加）

- **[用户确认]** 新板需要头部 IMU，已更新 spec R06。传感器型号、安装坐标和驱动未定；不删除外置躯干 IMU。
- **[原理图] RS485**：官方 C1 dynamixel.kicad_sch 的收发器和 4P 座提供差分接口（电源、地、A/B 两根数据线），供相应 RS485 舵机/设备使用。现有 TTL 3P 是电源、地、单根 DATA；两种物理接口不能直接互插。RS485 收发器本身不转换飞特/Dynamixel 等报文协议。该功能不是头部 IMU 的默认依赖，IMU 接口须按所选器件决定。
- **[用户确认]** 用户已明确首版不需要 RS485；此前“尚未确认取舍”仅为历史过程，不能继续作为现行待确认项。
- **[原理图/官方文档] 识别 EEPROM**：非易失的小容量存储器，HAT 场景主要保存板卡厂商/产品等身份和配置数据，让支持该机制的主控识别扩展板。树莓派旧 HAT 数据格式定义 vendor info、GPIO map、device-tree blob 等数据项；不能把这份旧格式当作所有新标准或 Radxa 的默认行为。
- 官方原文：https://raw.githubusercontent.com/raspberrypi/hats/master/eeprom-format.md ，本轮通过 Invoke-WebRequest 取得，定位 EEPROM Structure、Atom Types、Vendor info atom。该原文自身标为 preliminary；本轮只用它解释传统 HAT EEPROM 的用途，不核定新板符合 HAT/HAT+ 认证。
- C1 main.kicad_sch 标 HAT Identification/I2C 0x50，生产 BOM U4 标 DNP-CAT24C32HU4。因此是可选预留，不是 HAT 所有功能工作的强制条件。不是存 Linux 系统、运动策略或主程序的主存储器。
- **[用户确认]** 用户已明确首版不需要识别 EEPROM；本机 Radxa 镜像自动读取能力仍未核验，但该问题不再阻塞首版，因为首版省略该器件。此前“尚未确认取舍”仅为历史过程。

## 设计方案核验补充（2026-10-28）

- **[官方文档]** Radxa ZERO 3W/3E 具有 4-lane、22-pin、0.5 mm pitch MIPI CSI；针序包含 D0–D3、CLK、I2C2、CAMERAB_PDN_L、CIF_CLKOUT、3V3。官方列出的已支持摄像头包括 Raspberry Pi Camera V1.3（OV5647）、V2（IMX219）和 Radxa Camera 8M（IMX219）。来源：<https://docs.radxa.com/en/zero/zero3/hardware-design/hardware-interface>、<https://docs.radxa.com/en/zero/zero3/accessories/camera>；2026-10-28 通过 `Invoke-WebRequest` 获取页面正文。
- **[官方文档]** 40P 的 UART2_M0 位于 8/10，默认作为 U-Boot/调试串口，官方不建议直接当普通 UART；这与本机现有 HAT 使用背景存在冲突，方案必须先核对关闭 console/启动日志或改用其他 UART，不能把 8/10 直接写成已验证普通串口。
- **[厂商页面]** LCDwiki 的 3.5inch IPS SPI Module ST7796 页面列出无触摸 SKU MSP3525、320×480、4-wire SPI、5 V 输入、背光约 95 mA、14P 0.5 mm FPC；该物是带控制板的模块，不能当裸 LCD 针序。来源：<https://www.lcdwiki.com/3.5inch_IPS_SPI_Module_ST7796>，页面修订 2025-05-19；不等于本机已购或已验证驱动。
- **[环境事实]** 主会话注册表记录本机 KiCad 10.0.7，安装目录 `C:/Users/yilv/AppData/Local/Programs/KiCad/10.0`；本轮未启动 KiCad、未打开工程、未运行 ERC/DRC。
- 联网限制：web 检索仍无返回；EEPROM 原文通过 shell 直接读取成功。本轮未操作任何硬件，未运行功能测试。
