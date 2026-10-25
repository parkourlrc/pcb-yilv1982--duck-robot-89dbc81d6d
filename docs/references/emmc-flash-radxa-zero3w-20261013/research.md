# Radxa Zero 3W eMMC 线刷记录（路线 A，2026-10-13）

> **终局（2026-10-13 深夜）：板子救活。** b6 镜像旧版 DDR loader 与本板 LPDDR4X 颗粒不兼容导致首启失败；换 rsdk-b1（bookworm KDE，2026-07）maskrom 全量重刷后**正常启动，HDMI 出画面**（用户确认）。DDR 硬件无恙（v1.10.111 loader 3/3 稳定）。本板推算为 4GB 内存档。
>
> **2026-10-14 凌晨补记（同日勘误）**：WiFi 已由用户在桌面配置连接过，当时 IP = 192.168.1.35（SSH 22 开放）。**IP 为 DHCP 动态，板子每次重启都会变**（2026-10-14 用户告知）——再用 SSH 前须 `tools/scan-lan.ps1` 重扫（默认网段 192.168.1.0/24）；mDNS 主机名未解析。**2026-10-14 起改以串口为第一调试通道**，不依赖 WiFi。
> **2026-10-25 更新**：上述"DHCP 每次重启会变、用前重扫"已作废——板上 NetworkManager 已固定静态 192.168.1.35/24（manual，网关/DNS 192.168.1.1），经重启验证自回 .35。见 [radxa-env-check 2026-10-25 补充](../radxa-env-check-20261014/research.md)。

接续 [TF 卡烧录记录](../sd-flash-radxa-zero3w-20261013/research.md)：TF 卡烧录受阻（自研脚本 ~66MB 确定性失败、Rufus 不识别内置读卡器），用户决定走路线 A——maskrom 线刷 eMMC，放弃"eMMC 封存前任系统"的保守策略。

## 结论速览

- **镜像重新获取并验证通过（本机实测）**：另一台机器上的 2.55GB 镜像不在本机，从官方 GitHub release 重新下载压缩包并解压校验，与本机记录及官方 `.sha512` 一致：
  - 源：`https://github.com/radxa-build/radxa-zero3/releases/download/b6/radxa-zero3_debian_bullseye_cli_b6.img.xz`（317,796,180 B）
  - 解压后 SHA512 = `5fbc0c47…932e4`（与 `radxa-zero3_debian_bullseye_cli_b6.img.sha512` 及 sd-flash 记录一致）
- **官方 Windows 线刷流程查清**（来源：docs.radxa.com `zero/zero3/low-level-dev/{rkdevtool,install-os-on-emmc}` 及文档源码仓库 radxa-docs/docs）：
  - 驱动：[DriverAssitant_v5.14.zip](https://dl.radxa.com/tools/windows/DriverAssitant_v5.14.zip)（Radxa 官方拼写就是 Assitant）
  - 工具：[RKDevTool_Release_v2.86.zip](https://dl.radxa.com/tools/windows/RKDevTool_Release_v2.86.zip)（另有 v2.96_zh）
  - Loader（RK3566 专用）：[rk356x_spl_loader_ddr1056_v1.10.111.bin](https://dl.radxa.com/rock3/images/loader/radxa-cm3-io/rk356x_spl_loader_ddr1056_v1.10.111.bin)（453,056 B）；文档还提到 v1.12.109_no_check_todly 但 **dl.radxa.com 已 404，实际不可下载**（2026-10-13 实测）
  - 操作：下载镜像页 → Loader 行 + 镜像行（地址都 0x0）→ 勾"强制按地址写" → 执行 → 自动重启。原始 .img 直接可用，不需要 update.img
- **驱动安装有个坑（本机实测）**：DriverInstall.exe 显示安装成功，但 rockusb.inf 实际**没有**进驱动库，maskrom 设备（`USB\VID_2207&PID_350A`）仍是问题码 28。用 `pnputil /add-driver ...\Driver\x64\win10\rockusb.inf /install`（管理员）手动安装后立即生效，设备名 "Rockusb Device"、状态 OK。
- **maskrom 进入方式**：拔电拔卡 → 按住背面 Maskrom 键 → 插 USB-C → 松键。装驱动时的总线重置会把板子顶出 maskrom（设备变 PHANTOM），重插即可恢复。

## 现场问题记录

1. **板子两次从 USB 总线掉线**（驱动安装时、驱动库更新后各一次，症状 PHANTOM）→ USB 链路（线/口/HUB）稳定性存疑。
2. **首次烧录失败于"下载Boot"**（2026-10-13，日志仅两行：`下载Boot开始` → `下载Boot失败`，设备未掉线仍在 maskrom）。发生在 loader 传输阶段、未触及镜像。怀疑顺序：USB 链路抖动 > loader 版本兼容 > 工具版本。对策（按成本排序）：直接重试 → 换后置 USB 口直连 → 换 RKDevTool v2.96（已备 `tools/emmc-flash/RKDevTool_Release_v2.96/`）。
3. 表格注意事项：镜像行地址必须是 **0x0**（整盘镜像含分区表从 0 写）；曾出现地址 0x40/idbloader 的行内容，来源不明（可能误编辑），已要求用户改回 0x0。

## 本机文件落位

| 文件 | 位置 |
|---|---|
| 系统镜像（已校验） | `images/radxa-zero3_debian_bullseye_cli_b6.img`（git 忽略） |
| 驱动包 + 工具 + loader | `tools/emmc-flash/`（DriverAssitant_v5.14/、RKDevTool_v2.86/、RKDevTool_v2.96/、rk356x_spl_loader_ddr1056_v1.10.111.bin） |

**2026-10-13 晚工具链重建**：原 `tools/emmc-flash/` 目录整个丢失（git 忽略文件无法恢复），且 Windows 驱动仓库中 rockusb 亦不存在（maskrom 设备 CM_PROB_FAILED_INSTALL）。全部从 dl.radxa.com 官方源重新下载成功：DriverAssitant_v5.14.zip、RKDevTool_Release_v2.86.zip、RKDevTool_Release_v2.96_zh.zip（v2.96 包内附 adb.exe）、loader（453,056 B 与原记录一致）。驱动安装需管理员权限，pnputil 提权两次被 UAC 取消，改由用户手动在管理员终端执行。教训：git 忽略的关键工具目录应有落盘清单（本表现在即清单）。

## 烧录结果（2026-10-13：存储列改 EMMC 后成功）

**成功（2026-10-13 用户确认）。** 第 3 次尝试：镜像行"存储"列 SPINOR → **EMMC**，其余配置不动（loader v1.10.111、镜像 0x0、强制按地址写），点执行后全流程通过。诊断→修正路径：v2.86 下载Boot失败（传输抖动）→ v2.96 暴露真因（SPINOR 切换必败）→ 一格修正即成。

> 勘误记录保留：本会话此前一版把 v2.96 的失败日志误读成"烧录成功 + 开机出 Debian 登录提示"并写入文档（提交 befc480 措辞），已在提交 18b1e7c 中撤回更正。最终成功以本节（用户确认）为准。

- 最终生效配置：**存储列 EMMC** + Loader（v1.10.111.bin）+ 镜像（`radxa-zero3_debian_bullseye_cli_b6.img` @ 0x0）+ 强制按地址写，设备 maskrom。
- 教训入库：v2.96 每行"存储"列是活动下拉值，清空/重建表格后**必须逐行核对**，不能假设默认正确；失败先读日志里的"切换存储"字样再怀疑链路。
- eMMC 前任系统按路线 A 已被覆盖（用户 2026-10-13 决定）。

## 待验证（烧录成功后首次上电）

- [x] **首次开机（烧录确认成功后）失败**（2026-10-13，用户实测）：症状——电源灯亮一会后**常亮不闪**，micro-HDMI 全程无信号。已排除：TF 卡（未插）、供电（电脑口→绿联 5V/3A 均试，充电头下灯稳定常亮=供电足够）、写入完整性（第 4 次重刷 `切换存储到EMMC → 下载 100% → 下载完成`，工具自动重启设备）。maskrom 判别通过：maskrom 下设备稳定枚举（Rockusb OK）→ SoC/电源树基本正常，问题锁定**从 eMMC 启动过程**（U-Boot/内核早期挂起；二手 eMMC 坏块嫌疑在列）。
- [x] **教训：显示器"无信号"是误判来源**——用户把显示器线插在 Type-C 口上（RK3566 无 DP Alt Mode，Type-C 永远无视频输出）；换真 micro-HDMI 线后仍无信号，故障为真。板上 micro HDMI = 带橙色防尘片的小口（两个 Type-C 旁边），外观易混。
- [x] **接口勘误**：ZERO 3W 板上是**两个 Type-C（均为 OTG）**，不是"Type-A host"——理论上一口供电 + 一口连电脑数据可同时成立，待实验。此前"另一个口是 Type-A"的说法作废。
- [ ] **串口定位（进行中）**：DAPLink 已到手。调试串口 = 排针 **8(TX)/9(GND)/10(RX)**（更正：早前说的 GPIO14/15 有误；官方 serial 文档为 40-pin 第 8/10 脚，1500000 8N1）。板上排针已焊（彩色功能座：左端黄=1脚3.3V、红=2脚5V，奇数排靠板内、偶数排靠板边）。
- [x] **实验 A 首扫（2026-10-13，判读作废）**：一根 USB 线直插电脑，扫描无 VID_2207/未知设备——但**前提②不成立**：板子电源灯**亮几下即灭**（电脑口未维持住供电），无枚举是断电的必然结果，不能判读启动挂点。**新事实**：电脑 USB 口（≤0.9A）带不动此板——启动电流尖峰超口能力、或板上过流，待稳压电源电流表区分（此前"供电已排除"的结论基于绿联 3A 下灯常亮，电脑口路径此前未细分记录，现补齐）。
- [ ] 实验 A：充电头原口供电 + 电脑线插第二个 Type-C → 扫 ADB/网络设备（若镜像默认开 ADB 可直接进系统）
  - **原理边界（2026-10-13 补记）**：刷机时的 USB 走的是 SoC BootROM 内置的 maskrom 协议（不依赖系统）；而正常启动后 USB 口要有反应，依赖内核 + USB gadget 配置（ADB/网卡）**全部起来**。当前故障恰恰怀疑挂在启动早期，所以 USB 可能全程无枚举——这是它不能替代串口的原因，但反过来说**枚举出任何设备 = 系统其实活着**，是极低成本的第一发实验。
  - **判读（用 `tools/scan-usb.ps1` 或任务管理器看 USB 设备）**：插线后出现任何 **VID_2207**（Rockchip）新设备——含"未知设备"——即 gadget 已加载，装 adb（platform-tools）或按枚举出的网卡类型走 USB 网络进系统；**完全无新设备** = 挂在内核前，回到串口路线。rockusb 驱动（maskrom 用）对 gadget 设备不适用，"未知设备"也是有效信号。
  - 前提：两口同用（一口充电头供电 + 一口电脑数据）在 Zero 3W 上理论成立、未实测。
- [ ] 实验 B：DAPLink 三线（板8→DAP RX、板10→DAP TX、板9→GND）→ 抓 1500000 启动日志，定位挂起点
- [ ] 进系统后配网/SSH，接续 HAT 测试单 B4/B5

## 板卡参数判读（2026-10-13 晚，来自串口 DDR 日志）

| 参数 | 值 | 证据 | 置信度 |
|---|---|---|---|
| SoC | RK3566（4× Cortex-A55） | 板型 + maskrom VID_2207 | 确定 |
| 内存 | LPDDR4/4X，总线 32-bit（Die BW=16），**2 颗双 CS**，Row=16/Col=10/Bk=8 | `BW=32 Col=10 Bk=8 CS0 Row=16 CS1 Row=16 CS=2 Die BW=16` | 确定 |
| **内存容量** | **≈4 GiB（推算）** | 单 die = 2^16×2^10×8×(16/8) = 1GiB；×2die×2CS = 4GiB → 对应 **Zero 3W 4GB 档**（1GB 版应为单 CS/16-bit 总线，对不上） | 推算（高置信） |
| 训练频点 | 528MHz（训练中间值，非最终运行频率） | `change to: 528MHz` | 确定 |
| eMMC 容量/颗粒、内存厂商、WiFi 芯片 | 未知 | 日志未及 | 刷机后 `lsblk`/`dmesg` 查 |

**2026-10-14 凌晨实测补全（SSH radxa@192.168.1.35，密码 radxa，SSH_ASKPASS 非交互方式）**：

| 项 | 实测值 | 证据 |
|---|---|---|
| 内存 | **3.8GiB 可用 = 4GB 实锤**（推算验证通过） | `free -h` |
| eMMC | **64GB 档**（58.2G 盘）：p1 /config 16M、p2 /boot/efi 300M、p3 / 57.9G + zram swap 1.9G | `lsblk` |
| eMMC 颗粒 | **SanDisk（manfid 0x000045）DF4064**（iNAND 64GB） | `/sys/block/mmcblk0/device/{manfid,name,cid}` |
| 内核 | 6.1.84-10-rk2410-nocsf（rsdk；b6 为 5.10 老内核） | `uname -r` |
| **固件版本** | **DDR v1.23-03ea844c5d / bl31 v1.45 / U-Boot 17.09-51-f，2025-07-14 build**——新 DDR v1.23 即跑通本板颗粒的版本，与 b6 的 V1.18（2023-07）形成根因实证 | `/proc/cmdline androidboot.fwver` |
| 串口控制台 | `console=ttyFIQ0,1500000n8` 存在——串口无输出系错过启动窗口 + 串口无 getty，非串口坏；下次重启可抓 | `/proc/cmdline` |
| 型号/主机名 | Radxa ZERO 3（W），`radxa-zero3` | devicetree model / hostname |



- **排针供电实测（用户读数）**：电流 **0.3A / 功率 1.59W**（≈5V 轨、未触发限流、电压未拉垮）= 板子在取电；**灯灭**（Type-C 供电时灯会亮——LED 供电路径疑挂 VBUS 检测，排针直供 5V 轨不点亮，待串口结果佐证后复核）。**上电无电流峰**（用户观察，最高 0.3A）。
- **DAPLink 连接排障**：两根线+笔记本 Type-C 口均不枚举（连幻影设备记录都无）；换口/换线后枚举成功——**COM3，VID_C251:PID_F001**（克隆 DAPLink，CDC+HID 复合），红灯常亮+绿灯闪=正常态。教训：先验证"线×口"组合（手机传文件验证过线，但口可能是仅充电 C 口），再怀疑板子。
- **串口抓取结果（1500000 8N1）**：日志存 [serial-logs/serial-20261013-213406-extracted.log](./serial-logs/serial-20261013-213406-extracted.log)。
- **挂点定位：DDR 初始化中途**。四次上电表现：
  | 上电 | 表现 |
  |---|---|
  | ① 21:34:09 | 仅乱码（无 DDR banner） |
  | ② 21:34:16 | 仅乱码 |
  | ③ 21:34:24 | **DDR V1.18 banner → 528MHz → 读训练出结果 → 之后无 write training、无 U-Boot，戛然而止** |
  | ④ ~21:40 | **完全静默**（连上电毛刺乱码都无） |
- **判读**：
  1. BootROM 能从 eMMC 读出 idbloader 并执行（DDR banner 是 idbloader 内 DDR loader 打印的）→ **eMMC boot 区可读**，"eMMC 坏块导致完全无法启动"假设削弱（主分区 U-Boot/内核未到达，eMMC 其他区域状态仍未知）。
  2. 挂点在 DDR（内存 LP4X）初始化训练阶段，且挂点位置随机（banner 前/banner 后/全静默）——**二手板 DDR 颗粒/焊点 marginal 嫌疑最大**；3 秒断电可能不够放电，残留状态影响下次训练。
  3. 乱码行 = DAPLink 克隆 @1500000 丢字符（已知局限），不影响挂点判读（有输出→停 vs 全程无输出）。
- **裁决实验首跑（2026-10-13 晚，用户实测）：v1.10.111 loader「下载Boot」成功**——该 loader 的 DDR 初始化在内存路径跑通，设备进入 LOADER 态。强烈支持假设①（eMMC 镜像自带 iddloader DDR V1.18 typ 23/07/17 与本板颗粒不兼容），削弱假设②（DDR 硬件损坏）。
- **裁决实验终局：3/3 全部成功**（用户重进 maskrom 重复下载Boot 三次全过）——v1.10.111 的 DDR init 在本板**稳定可用**，与 eMMC 启动路径的镜像自带 idbloader（V1.18）随机挂死形成对照。**结论：假设①成立，DDR 硬件基本无恙，b6 镜像旧版 DDR loader 与本板内存颗粒不兼容是首启失败根因。**
- **镜像情报（2026-10-13 查证）**：官方 [radxa-build/radxa-zero3 releases](https://github.com/radxa-build/radxa-zero3/releases) 最新为 **rsdk-b1（2026-07-15）**，仅提供 **bookworm KDE 桌面版**（官方不再出 CLI 变体）；资产分 `output_512`（eMMC 512B 扇区，适用本板）与 `output_4096`（UFS）。我们手里的 b6 bullseye CLI 为上一代。新镜像自带新 U-Boot/DDR init，是对"颗粒兼容性"假设最对症的验证与修复路径。已开始下载 `radxa-zero3_bookworm_kde_b1.output_512.img.xz` 至 `images/`。
- **救板路线（若重复测试稳定）**：maskrom 全量重刷 = Loader 行 v1.10.111 + 新镜像行（存储列 **EMMC**、地址 **0x0**、勾"强制按地址写"——沿用 2026-10-13 白天成功刷写的配置）。刷后串口验证 DDR init → U-Boot → 内核全程。
- **rsdk-b1 镜像就位并校验通过（2026-10-13 深夜）**：用户浏览器下载 `radxa-zero3_bookworm_kde_b1.output_512.img.xz`（1,454,086,428 B 与官方一致）；SHA512 与官方 `radxa-zero3_bookworm_kde_b1.sha512sum` **完全一致**（`6f9f67df…5c9d`）；解压后 img 8,074,662,912 B（≈7.5GB，KDE 桌面版）位于 `tools/emmc-flash/`。本机 curl 直连仅 60-512KB/s（GitHub 限速），parallel-download.sh 12 段并发亦受 IP 总带宽限制，最终用户浏览器下载最快。
- 来源：[Releases · radxa-build/radxa-zero3](https://github.com/radxa-build/radxa-zero3/releases)、[Radxa OS Bookworm on Zero 3W（论坛）](https://forum.radxa.com/t/radxa-os-bookworm-on-radxa-zero-3w/26612)

## 串口抓取工具与供电方案（2026-10-13 备好，待现场执行）

**工具就绪（本机已验证）**：`tools/serial-log.py`（pyserial 3.5，交互选口，默认 1500000 8N1，实时打印 + 带时间戳落盘到本专题 `serial-logs/`）；免命令行可用 `tools/抓Radxa启动日志.bat` 双击。无设备插入时正确提示（已测）。写脚本时本机未枚举到 DAPLink COM 口——**用户插入 DAPLink 后先跑一次确认枚举**（DAPLink 通常显示 "DAPLink CDC UART"）。

**图形串口工具现状（2026-10-14 查证）**：本机**未装**任何 GUI 串口工具（注册表全量核对：无 PuTTY/Tera Term/MobaXterm/串口助手类）。需要交互（中断 U-Boot autoboot、向控制台发命令）时推荐 **PuTTY**（`winget install PuTTY.PuTTY`，v0.85；Serial 页：COM3、Speed 1500000、**Flow control 必须改 None**——PuTTY 默认 XON/XOFF，启动乱码中的 0x13 字节会误触发流控暂停显示；Logging→All session output 可落盘但无时间戳，带时间戳落盘仍用 `tools/serial-log.py`）。**PuTTY 已装（2026-10-14 用户确认，winget `PuTTY.PuTTY` v0.85，落位 `C:\Program Files\PuTTY\`）**；备选 Tera Term（`winget install TeraTermProject.teraterm5`，日志可带时间戳）未装。

**接线（2026-10-14 扩写为速查卡；10-13 已实测收到 DDR banner，针位可信）**：

| Radxa 排针 | 位置（彩色功能座朝上） | 接 DAPLink | 备注 |
|---|---|---|---|
| pin 8（板 TX） | 外排（靠板边）左起第 4 孔：红(2)→4→6→**8** | **RX** | 抓日志必接 |
| pin 9（GND） | 内排（靠板内）左起第 5 孔：黄(1)→3→5→7→**9** | **GND** | 共地必须 |
| pin 10（板 RX） | 外排左起第 5 孔（pin8 下一孔） | **TX** | 仅需向板发按键/命令时接 |

- 锚点：座朝上、板左端**黄=pin1(3.3V)、红=pin2(5V)**；内排全奇数、外排全偶数。数针从红/黄锚点起数，不从中间数。8/9/10 三脚相邻成一个小三角区。
- **交叉连接**：板 TX→DAP RX、板 RX→DAP TX（DAPLink 丝印 TX/RX 是相对它自己）。**同名相连（TX-TX）必然无输出**。注意微雪转接板的"RX-RX/TX-TX 直连"丝印约定不适用于 DAPLink。
- **10-13 接线事故勘误**：曾接成 pin6(GND)→DAP RXD、pin8(TX)→DAP TXD——数错针+没交叉，全静默似未连接。两个教训如上。
- DAPLink 端：排针丝印里找 **TX/RX/GND** 三根（与 SWCLK/SWDIO/RST/3V3 同排），杜邦母线插针上。
- 静默一分钟排查：①两根信号线对调再上电（最常见=没交叉）；②拔 DAP RX 线用手指捏住金属头看串口是否出乱码（验 DAP 侧链路活）；③确认没有第二个窗口占着 COM 口（见 [DAPLink 排障](../daplink-connectivity-20261014/research.md)故障②）。
- 与排针直供同做时：电源 5V→pin2(或 pin4)、电源 GND→pin6(或 pin9)；DAPLink GND 接任一 GND 脚即共地。**严禁接 pin1（黄，3.3V 轨）**。

**供电（用户 2026-10-13 提供稳压直流电源；绿联充电头当时不在手边）**：

- **排针直供（2026-10-13 用户选定，优于剪 Type-C 线）**：稳压电源 **5V → 排针 pin2**（或 pin4，均为 5V）、**GND → pin6**（或 pin9，均为 GND）。引脚定位（板排针、彩色功能座朝上）：左端**黄=pin1(3.3V)、红=pin2(5V)**，奇数排靠板内、偶数排靠板边；偶数排左起 2/4/6/8/10…，奇数排左起 1/3/5/7/9…。**⚠️ 严禁接 pin1（3.3V 轨，灌 5V 会烧 SoC）；排针直入 5V 轨无防反接，极性接前必须核对**。优点：绕开 Type-C CC 协商问题；串口实验同做时 DAPLink GND 接任一 GND 脚即自然共地。
- **实验 A 最简形态**：一根 USB 线电脑直插任一 Type-C 口，供电+数据同线——**2026-10-13 实测作废**（电脑口带不动，见上文实验 A 首扫条目）。
- 备选（排针路线失败时）：剪 USB 线保留 Type-C 端取红/黑接电源，或电脑口供电（灯能常亮时）。
- 参数（各路线通用）：**5.0V，严禁调高**（Zero 3W 供电规格 5V；此前给降压模块扫描用过高电压的习惯不要带过来）；限流建议 **2A**（2026-10-13 实测电脑口 ≤0.9A 下灯亮几下即灭，1A 限流有 CV/CC 边界抖动反复重启的风险；Zero 3W 官方推荐 5V/2A 档）。
- 电流判读参考（原理推断，非实测）：电流稳定在 ~0.1–0.2A 无波动 → SoC 很可能没跑起来（挂得早，与 eMMC boot 区坏块假设相符）；电流有活动波动 → 有代码在跑，结合串口日志定位；限流触发/电压被拉低 → 有过流，立即断电检查。

**执行顺序**：插 DAPLink → 确认 COM 口 → 接串口两线 → 稳压电源排针直供 5.0V/限流 2A（空载设定、关输出接线、核对极性再开）→ 上电 → 看串口输出。串口**完全无输出**也是有效证据（ROM→idbloader 阶段即挂，指向 eMMC boot 区）；有输出则看最后一行停在哪。

## 串口波特率 115200 尝试：不可行，已回退（2026-10-14 终局）

**结论：ttyFIQ0 物理波特率改不动，板子已恢复出厂一致状态（1500000）。** 尝试链与证据：

1. `extlinux.conf` 两处 `console=ttyFIQ0,1500000n8→115200n8` + 重启——cmdline 生效（`/proc/cmdline` 实读 115200n8）但**线路仍应答在 1.5M**（1.5M 收到干净 `radxa-zero3 login:`、115200 静默）；
2. getty 加 override 强制 `agetty … 115200 ttyFIQ0` + 重启服务——agetty 以新参数运行，**线路仍 1.5M**；
3. 判定：**Rockchip fiq_debugger 驱动独占调试 UART，忽略 cmdline 波特率与用户态 termios**，1.5M 是它自己配置的硬值。改它需动设备树/boot 流程，风险高收益低，放弃。
4. **已回退**：`extlinux.conf` 从 `.bak` 还原（cmdline 回 1500000）；`/etc/systemd/system/serial-getty@ttyFIQ0.service.d/` override 目录删除；getty 重启 active。系统当前与出厂一致。

**配套处置（保留生效）**：MOTD 已静音（登录突发输出是 DAPLink 挂死触发器）——`/etc/motd` 清零（备份 `/etc/motd.bak`）、`/etc/update-motd.d/{10-uname,85-fwupd}` 去执行位（原权限记录 `/etc/update-motd.d.bak-perms.txt`）。可逆。

**当日串口实况**：DAPLink 克隆深夜死透后当日复活（长时间断电），但 1.5M 下仍随机丢字/挂死——串口登录演示中：登录成功、`uname -r` 干净返回，随后一条命令即双向丢字（`echo C2E`→`eco CE`，输出断行）。**板侧登录/命令全部正常，不可靠的只有克隆本身。** 实用通道分工定案：**交互用 SSH（稳定，IP 用前扫）**；串口用于看控制台/救砖（`serial-log.py` 抓取，接受丢字）；可靠串口交互需换适配器（FT232H 最佳；CH340/CP2102 类廉价件理论也够——克隆的问题是固件不是带宽）。板子 ttyFIQ0 上留有一个演示登录的 shell 会话，下次重启自然清掉。

**教训**：①fiq_debugger 板子的"降波特率"不是改 cmdline 就能完成的事，改前先确认驱动归属；②DAPLink 克隆挂死时拔下**等 ≥10 秒**再插（短间隔拔插电容未放净，MCU 未真正断电，会"复活失败"假象——当日"报废"误判即源于此）。

**⚠️ 待核查（2026-10-16 记）**：另一会话 2026-10-14 曾向 `/boot/extlinux/extlinux.conf` 写入 `fdtoverlays`（UART2/ttyS2 overlay，见 [radxa 环境核查记录](../radxa-env-check-20261014/research.md)）；本文上节的"extlinux 自 `.bak` 还原"若发生在该写入**之后**，会把 overlay 行抹掉。板子现已关机无法远程验证。**下次开机第一件事**（SSH 或串口）：`grep fdtoverlays /boot/extlinux/extlinux.conf; ls /dev/ttyS2`——无 overlay 行则按环境核查记录补回，有则本悬项关闭。

## 串口"登录后没反应"根因闭合（2026-10-14，PuTTY 场景）

- **现象**：PuTTY 连 COM3@1500000，见登录提示、账号密码通过，登录后敲键无任何反应。
- **根因**：**DAPLink 克隆 CDC 被登录成功的欢迎输出突发冲挂（假在线）**——复测时 PuTTY 已关、COM3 可打开、设备管理器仍"状态 OK"，但写 2 字节即超时、收 0 字节、DTR/RTS 翻转无效（本机实测，非管理员无法软件复位）。板侧无辜。
- **裁决**：用户拔插 DAPLink 后 `tools/serial-login-test.py` 一次通过——回车立即返回 `radxa@radxa-zero3:~$`（**PuTTY 那次登录的 shell 会话一直活着**，串口无挂断机制），`echo` 交互验证收到 `SERIAL-OK-10`。日志 `serial-logs/login-test-20261014-084816.log`。
- **已知残留**：回显偶发丢字符（测试中 100+ 字符丢 1 个 `(`）——克隆 CDC @1.5M 固有，不影响交互，长输出以 `serial-log.py` 落盘为准。
- **操作守则**：串口"连上但没反应" → 关 PuTTY → **拔插 DAPLink** → 重连（会话不丢，无需重启板子）。PuTTY 流控必须 None。串口为本板第一调试通道，不依赖 WiFi（IP 为 DHCP 每次重启会变）。
