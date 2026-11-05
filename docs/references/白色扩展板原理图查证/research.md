# Microduck-Hat-for-Radxa-Zero 原理图查证记录

查证日期：2026-10-09。用户提供 PDF（文件名 `SCH_Microduck-Hat-for-Radza-Zero_2026-10-06.pdf`，528,943 bytes，5 页），为 2026-10-06 导出的原理图。原件存于本目录，文本提取见 `extracted-text.txt`。本次只做静态读图，未接触实物板、未上电。

> **历史记录，2026-10-27 已勘误**：原图 V1.0、本机 V1.2；F1 在 DATA 而非 +BATT，TTL_TXEN 为 TX 自动换向。当前双口缺答判断以[共总线原理图复核](../扩展板双口惯性缺答复核/research.md)为准，原 PDF 保留不改。

## 结论

这块板（用户手上的白色鸭图案板，PCB 丝印 **V1.2**（2026-10-10 照片更正））是一份**社区在嘉立创 EDA 里改绘的 RPI Robot HAT 派生品**，不是官方板：

- **来源可溯**：第 1 页完整保留了官方 `elec_RPI_Robot_HAT` 的标题栏、修订历史（"[fixed] Acc. is at 0x19 I2C address"、"[update] Dynamixel_dir is based on Tx" 等）和设计者缩写（SN/EB/SNEB）——即从 [pollen-robotics/elec_RPI_Robot_HAT](https://github.com/pollen-robotics/elec_RPI_Robot_HAT)（Apache-2.0，KiCad 9）复制改绘。图页署名"Microduck-Hat"，原理图版本 **V1.0**（创建 2026-09-03，各页更新至 2026-09-20）。
- **目标主控是 Radxa Zero 3W，同时兼容 Pi Zero 2W**：40-pin 排母 J1 的网络名双标注（`RADXA ZERO 3W` 与 `RASPI ZERO 2W` 两列 mux 名），有中文改动注记"**I2C5改到29，31**"。
- **舵机总线走 UART2_M0（IO0_D0/D1）** —— Radxa Zero 3W 上即 `/dev/ttyS2`，与官方 robotd（含飞特补丁）的 `bus.port` **正好一致**；Pi 侧对应 IO14/15（UART0）。`TTL_TXEN` 由 Q2/R16/R17 根据 TX 电平生成，控制 TTL 收发缓冲；0Ω 的 R21/R32 属 RS485 接收/方向选路，不能混为一谈。
- **比官方板多了一颗 BNO085（U14，28 脚）**：官方板的 U11 BMI088 是"贴了但软件不用"（dormant）；本板 BMI088（U3）保留之外又加了 BNO085，I2C 地址 0x18 的 TLV320 音频codec、Qwiic 座等与官方一致。

## 逐页要点

| 页 | 图页名 | 内容 |
|---|---|---|
| 1 | （官方页改绘） | 40-pin 排母 J1（2x20 SMD）、HAT EEPROM U16 BL24C32A（地址由 A0-A2 设置）、Pi/Radxa 双标注 GPIO 映射、官方修订历史；GPIO14/15=舵机 UART，GPIO2/3=IMU+音频+Qwiic I2C，GPIO6=关机检测，GPIO22=IMU_IT |
| 2 | Power | U1 **AP63205WU-7** 降压（+BATT→+5V，L1 6.8µH，22µF×2 输出）——与官方 U9 同型；U2 **LM5050-1** 理想二极管控制器 + Q1 SI2312；D1 BAT54SW；软开关 G1/S2；**关机检测**：R2 10k/100Ω 分压 + D2 3.3V 稳压管 → `PWR_DET/IO3_A1` |
| 3 | Sensor | U3 **BMI088**（acc 0x19 / gyr 0x68，R3-R6 0Ω 选路）+ U14 **BNO085**（本板新增）；CN1-CN4 = **BM04B-SRSS-TB**（JST SH 1.0mm 4P，Qwiic/Stemma）×4，各带 10k 上拉（挂 I2C3/I2C4/I2C5/UART4 网络名） |
| 4 | Servo | 半双工 TTL 驱动三件套与官方同构：U4 SN74LVC1G125 + U7 74LVC1G08 + U5 SN74LVC1G126（方向由 TX 自动生成）；U6 **SIT3088EEUA** RS485 收发器（`SERVO_DIR`）；**TTL 舵机口 CN11/CN12 = B3B-EH-A（JST EH 3P）**，两口 DATA 共经 R31=1 kΩ 与 F1（PRG18BB101MB1RB），D3 从两者间节点对地；+BATT 直连两口，100nF×4 为逻辑芯片去耦；RS485 口 U8/U9 = B4B-EH-A（JST EH 4P） |
| 5 | Audio | U10 TLV320AIC3104 codec（0x18，12MHz OSC1）+ U11 XC6206P182 1.8V LDO + U12 PAM8406DR 功放；喇叭座 H1（2.54mm 1P×2）；CN5/CN6/CN9/CN10 = ZX-MX1.25-2PLT 4P（麦克风/扩展）；BLM15 磁珠若干 |

## 对本项目（飞特路线）的意义

1. **补上了 community-kit 的已知缺口 #2**（主控↔舵机总线物理适配未开源）：本板的 74LVC 半双工驱动 + UART2_M0（ttyS2）正是官方 robotd 飞特补丁期望的总线入口。TTL 物理层对 Dynamixel 2.0 与飞特 SCS/HLS 是同一条（半双工单线 TTL），方向自动生成对两家协议通用。
2. **供电链闭环**：+BATT →（本板 AP63205 出 +5V 给主控；舵机口直出 +BATT）。与 banana_pcb 取电 → 配电的链路可衔接；舵机侧仍是电池直挂（飞特 HD-1910 真机 7.8-8.1V 的用法）。
3. **IMU 路线两用**：走 A 线（教程 Python 栈）时可用板上 BNO085（I2C）；走 C 线（robotd 飞特）时姿态来自 imu_to_dxl 总线从站（ID 200），板上 BMI088/BNO085 与官方 BMI088 一样处于不用状态。
4. **舵机口是 JST EH 3P（图纸）**：飞特 C001 厂商资料写 AMP2.0-3P，与旧 5264 记录不同。按实际批次与插合视角核针序，不能靠试插判断兼容；见[10-10 复核](../供电与扩展板实物复核/research.md)。

## 未确认项 / 风险

- **原理图 V1.0 vs 实物 PCB V1.2**：2026-10-10 照片更正版本；未取得 V1.2 差异表、PCB 或贴装 BOM。
- 板卡设计者与来源未确认（推测来自 replica 社区/微信群生态，嘉立创 EDA 绘制）；若自行改板再发布，注意官方 HAT 部分 Apache-2.0 的署名保留（本图标题栏保留了官方设计者缩写，做法正确）。
- `TTL_TXEN` 在存档 V1.0 图中用途已核为 TX 自动换向；V1.2 是否一致、对应串阻实际值仍待核。
- AP63205 额定 2A，与官方相同：**5V 只给主控，不能当舵机动力**；F1 自恢复保险的具体保持电流值未查手册。
- 最初分析仅用 pypdf 文本提取，曾误判 F1 电源路径。2026-10-27 已核第 4 页实际连线并修正上文；其他历史页未全部重新审计，V1.2 对应关系不可由旧图推定。

## 本目录文件

- `SCH_Microduck-Hat-for-Radxa-Zero_2026-10-06.pdf` — 原件（来自 `C:\迅雷下载\`，2026-10-06 导出）
- `extracted-text.txt` — pypdf 全文提取（5 页）
- `research.md` — 本记录
