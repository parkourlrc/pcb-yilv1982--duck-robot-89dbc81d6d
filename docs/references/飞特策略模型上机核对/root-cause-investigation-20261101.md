# 站姿坏帧根因定位与修复任务

## 现行决定：搁置 v0.3，新单口板已换装并恢复混读（2026-11-01）

**[用户确认／此前搁置原因]** 小焊盘探测操作难度过高；用户现有 DAPLink 接法还缺 7P 连接线，因此决定先把双口 v0.3 板放一边，购买同款单 3P 口 IMU 尝试。这里记录的是用户当前工具条件，不据此断言所有 SWD 接法都必须使用完整 7P 线。示波器、飞线、DAPLink 定位均暂缓，以下原计划及已完成实验保留为历史证据，不再作为当前必做前置项。

**[用户口述／状态更新]** 用户确认之前那块单 3P 口板此前可用，后来自己弄坏了一颗电阻，板子现已损坏。按项目既有身份索引指向 jyg9 GD32 单口板；损坏的电阻位号、发生时间和实物照片未提供，不猜为 R31/R5/F1，也不与 HAT R31 焊盘损伤混同。2026-10-25/27 缺答日志保留，损伤与各次历史故障的时间关系未核实；本轮未重新测旧板，不能据此将历史所有缺答定为同一根因。

**当前替换状态**：[用户确认] 新单 3P 口 IMU 已到货并换上。[实测] 主机通信已回滚为 IMU＋15 舵机同组 SYNC_READ；servo-web 30 秒 296/296 帧舵机完整、IMU 约 9.9 Hz，0 超时/坏校验/错 ID。robotd 已恢复原版；只读验收后已按用户要求切回 robotd/Studio（运行中），servo-web 已停止；此前助手只做过新板只读验收；用户现反馈舵机页站姿能站住、IMU 页角度异常，模型仍未运行。 新板只读结果不代表 v0.3 根因已定位，见[独立回滚验收](restore-mixed-sync-read-20261101.md)。

**下一步边界**：身份读取和 servo-web 混读已完成；本次此前助手只做过新板只读验收；用户现反馈舵机页站姿能站住、IMU 页角度异常，模型仍未运行。后续动作须结合当时支撑、安装方向与标定状态，沿用原校验及故障卸力，不能把只读通过当作动作验收。

原始采购意向见[用户决定记录](single-port-replacement-decision-20261101.json)，仅保留历史。当时文档更新未访问真机；随后用户确认换板并授权回滚，已完成[主机回滚及只读采集](restore-mixed-sync-read-20261101.md)。暂停的 v0.3 根因任务没有恢复。

日期：2026-11-01。目标为用户明确设置的“根本原因并解决问题”，当前未完成。验收须能解释并消除原生 robotd 起身时的 IMU 通信失败，在既有校验与卸力保护下通过对应真机站姿验证；服务在线、只读通过或一次动作成功均不能单独视为完成。

## 授权及现状

- 用户本轮确认“已固定，可做短时对照”。后续必要的短时动作仍通过原生 robotd；不调用旧的直接目标写实验，不改变标定、模型或保护位。
- 13:24:36–13:24:46 本机只读审计：robotd PID 2046、原单播版 SHA `9f9fa71723339b80f97d7be065dec04855bb0d31a3ed7c5978e8605c22db3e5b`；串口 `/dev/ttyS2` 唯一持有者为 robotd fd 11，commissioning/ready/off；10 秒内失败累计保持 118。
- 内核为 `6.1.84-10-rk2410-nocsf`，`dw-apb-uart`，UART 时钟 sysfs 报 16 MHz、FIFO 64；`/proc/tty/driver/serial` 只有历史 `oe:1`，该窗口无增量。这些是驱动记录，不是电气波形，也不能排除未被硬件置错标志的字节损坏。
- Windows 当前未枚举到 CMSIS-DAP／ST-Link／USB 串口设备；尚未连接 SWD、读取芯片 Flash 或取得 IMU TX 引脚波形。未据此假定用户没有调试器或示波器。
- 审计原始记录：[root-cause-live-audit-20261101.json](root-cause-live-audit-20261101.json)，[脚本](root-cause-live-audit-20261101.py)。

## 只读固定数据对照

[实测] 13:28 起，确认卸力后短暂停 Studio 和 robotd，由独占 Python 采集器只发 READ／SYNC_READ；发送包装层拒绝其他指令。每条件 1000 周期，目标周期 20 ms，所有条件结束逐颗回读扭矩 0，恢复两服务及原参数。

固定数据来源为当前归档 0.2.0 `control_table.c`：寄存器 71–123 是全零的 53 字节，正常应答共 59 字节。它不使用动态传感器值。此采集器不是 robotd，不可把其调度和判错直接等同原生。

| 条件 | IMU 请求数 | 采集器报失败 | 坏 checksum | 有效固定帧数据异常 | 固件取消增量 |
|---|---:|---:|---:|---:|---:|
| 动态 56/15，IMU 先 | 1000 | 2 | 0 | 不适用 | 1 |
| 固定 71/53，IMU 先 | 1000 | 2 | 0 | 0 | 2 |
| 固定 71/53，舵机先 | 999 | 2 | 0 | 0 | 1 |
| 固定 71/53，舵机先，间隔 500 µs | 998 | 1 | 0 | 0 | 1 |

**采集器限制／勘误**：复用的历史 `collect` 仅在读取循环判断 deadline；可能在舵机事务返回超过 20 ms 后仍发送 IMU READ。第三组 index 604 就是这种情况：舵机完整读取耗时 23.106 ms，随后 IMU 只写入并耗时 210 µs，未进入正常等待。因此该条不能算作 IMU 节点缺答，原始数据保留不改写；原生 robotd 的 send 会检查剩余预算。其余失败主要为零字节，一条仅在约 20.7 ms 时取得 `FF`。本次没有将该采集器用于动作或放宽原生判据。

[实测] 固件取消计数总增量 5，第一组 RX ring overflow +14，最后一组 UART errors +14；不与某个失败一一绑定。所有组累计未出现完整坏 checksum 帧。

[推断] 当前窗口表明卸力下可有“无完整答复／取消／采集超期”，但没有重现此前起身中的坏帧；不据 2 对 1 次失败宣称 500 µs 间隔有效，不将两个现象强行归为同一根因。

原始记录：[root-cause-fixed-read-20261101.json](root-cause-fixed-read-20261101.json)，[一次性采集脚本](root-cause-fixed-read-20261101.py)。

## 原生控制节奏对照：10 Hz 仍复现坏帧

用户已确认固定和短时对照。使用原 robotd 二进制、原生 `hold-home`（3000 ms、15 个方向 −1），仅将实验配置的 `control.hz` 临时从 50 改为 10；仍使用 20 ms 遥测截止、原校验与故障卸力。仅执行一次，原生采集器最长等待 6 秒后 relax，逐颗回读卸力。100 ms 周期还会改变动作步距和故障检测频次，不能把它当成只改一个 UART 空闲时间，更不作为生产修复。

配置写入 `/run/robotd-root-cause-hz10-20261101.toml`；独立 `/run/systemd/system/robotd.service.d/zzzzzz-root-cause-hz10-20261101.conf` 只用于实验启动。结束删除本实验两文件、重新加载并恢复 50 Hz，两服务及生产配置 SHA 均核对。实现见 [一次性运行脚本](root-cause-native-hz10-20261101.py)。

[实测] 13:32:48 执行这一次原生 `hold-home`，实读 target_hz=10；预载后只发送一次插值目标，下一 IMU READ 收到 21 字节坏帧：

```text
FF FF C8 11 00 FD FF CA FE 63 00 5F B0 0E B2 18 3A 7C 08 00 5E
按实收前 20 字节计算应有 checksum=5A，实收=5E。
```

- 上一目标 `write` 返回至失败 READ 的 `write` 起点：**91.277 ms**。
- READ 起点至 `read` 开始：1.044 ms；该 `read` 耗时 0.106 ms，完整返回为 **1.150 ms**。
- 原生捕获共 13 次 IMU READ，其中 12 次有效、1 次上述坏帧；12 组舵机遥测完整有效。
- 固件 `cancelled_replies / receive_timeouts / rx_overflows / uart_errors / tx_timeouts / tx_busy_drops` 均无增量。主控 `/proc/tty/driver/serial` 的 `fe:8 / oe:1` 前后不变；这是累计驱动标志，不等于线路所有字节正确。
- 原生报 timeout 并卸力，15 颗寄存器 40 均为 0。结束已恢复 target_hz=50、commissioning/ready/off；生产配置 SHA 不变、运行覆盖文件已删除。

[推断] 单纯将控制频率从 50 降至 10 Hz 并未消除本次坏帧。91 ms 的主机间隔进一步降低“上一目标尚未发完、下一请求过紧”这一解释，但不能替代 UART 物理波形；应转向同步取得 MCU TX、外部 DATA 与主控接收的数据，避免再靠任意加等待推定根因。

证据：[部署与恢复](root-cause-native-hz10-deployment-20261101.json)、[原生 RPC／前后回读](root-cause-native-hz10-20261101.json)、[原始 syscall](root-cause-native-hz10-20261101.log)、[离线解析](root-cause-native-hz10-20261101-summary.json)。

## 暂缓方案：示波器发送端取证（已由上述替换决定取代）

[用户确认／USB 实测] 示波器为鼎阳 SDS814X HD，用户已通过 USB 接入电脑；2026-11-01 13:49 Windows 枚举名称为 `SDS814XHD`，VID/PID 为 `F4EC:1017`。13:49 设备曾报 Code 28；13:59 已恢复 PnP 正常，暂停前仍在安装 VISA 组件，尚未取得 `*IDN?` 应答或波形。详情见下节。没有把 USB 枚举成功等同于仪器通信成功；用户随后明确探头尚未连接。

拟先同步比较 v0.3 的 USART2_TX（PA2／U6 输入）与连接器 DATA（R6 外侧）；条件允许再加 OE#（PA1）和 HAT 的 UART_RX。J2 的 TX 是 USART1 调试日志，不是这次需要比较的 USART2 总线发送信号。使用匹配 v0.3 的原理图及实物丝印核对测点，不套用此前单口 GD32 板位号。

解码目标为 1 Mbps、8N1、空闲高。具体探头倍率、采样率、存储与触发设置待按用户机型确认；以同一包的 TX／DATA／主机原始字节比较为判据，区分“源头已错”“输出／线路变坏”“主控接收后变坏”，不由单通道截图直接下结论。

### USB 连接核对（2026-11-01）

- **[实测]** Windows 11 `10.0.26200` 已发现仪器，设备 ID 为 `USB\VID_F4EC&PID_1017\SDS08A0QA12396`，兼容类为 `FE/03/01`；ProblemCode=28，ProblemStatus=`0xC0000490`，未报告驱动服务或 INF。原始记录见 [USB PnP 记录](siglent-usb-pnp-20261101.json)。序列号来自 USB 枚举，尚未用 SCPI 交叉核对。
- **[厂商文档]** Microsoft 的 Code 28 文档解释为驱动未安装，`0xC0000490` 为未找到兼容驱动；[归档正文](sources/siglent-usb-20261101/windows-code28.md)，来源 `https://learn.microsoft.com/en-us/windows-hardware/drivers/install/cm-prob-failed-install`。
- **[实测／官方来源]** 已从 NI 官方站取得 NI-VISA 2026 Q4 在线安装器（26.8，9,002,792 字节），SHA256 与官网发布值一致，Authenticode 校验有效，签名者 National Instruments Corporation。Windows 11 位于官网支持列表。安装器留在本机临时目录，不纳入版本库；路径、下载地址与哈希见 [安装器记录](siglent-ni-visa-installer-20261101.json)。官网页面归档见 [NI-VISA 下载页](sources/siglent-usb-20261101/ni-visa.html)。该记录是安装前的下载核验，实际执行状态见下条，不据下载页推定安装成功。
- **[用户确认／执行中]** 用户回复“继续安装并验证连接”，已于 13:53:38 启动官方安装器并请求 UAC，随后确认安装进程 PID 43820 及 MSI 正在运行；使用静默安装、接受许可及禁止自动重启参数。结果见 [安装执行记录](siglent-ni-visa-install-run-20261101.json)。只有安装退出、PnP 恢复及查询成功才算连接验收；探头未核对前不发起动作。
- **[官方手册核验]** 已取得 SDS800X HD 对应 EN11G 编程手册，印刷 p18 将本系列列为支持型号，p19 要求 USB 连接使用 NI-VISA，p22 说明 USB 驱动安装，p30 定义 `*IDN?` 返回厂家／型号／序列号／固件版本。原件、页码、官网地址和哈希见 [来源清单](siglent-usb-sources-20261101.json)。[只查询脚本](siglent-usb-query-20261101.py) 仅匹配此 VID/PID 和序列号；默认只查身份，`--state` 才附加手册定义的通道和采集参数查询。Python 依赖放独立临时 venv（PyVISA 1.16.2），不修改工程运行依赖。
- **边界**：没有更改示波器采集设置、刷示波器固件或追加真机动作。Code 28 是电脑与示波器之间的驱动问题，不能解释此前 robotd 的 IMU 坏帧。
- **安装中检查**：13:59 USB PnP 已变为 `OK / USBTestAndMeasurementDevice`；此时 NI 安装仍在运行，提前执行一次身份查询得到 `VI_ERROR_LIBRARY_NFOUND`，尚未发出 `*IDN?`，原件见 [首次查询记录](siglent-idn-20261101.json)。这次失败不能解释为仪器不应答，需等运行库安装结束再验收。

### v0.3 生产焊盘测点图

[图纸／生产数据核验] 已依据本项目下单 Gerber 内 `FlyingProbeTesting.json` 制作 [测点图](imu-v03-probe-map-20261101.png)，并打开核对文字、测点及箭头。来源和哈希见 [坐标清单](imu-v03-probe-map-source-20261101.json)，生成脚本为 `scripts/render-v03-probe-map-20261101.py`，已登记照片索引。

- A=U6-2，USART2_TX；B=R6-1（元件面顶视右端），外部 DXL_BUS。
- C=R6-2（左端），芯片侧 DXL_DATA；D=R3-2，OE#；G=U6-3 或经确认的公共 GND。
- 图以 J2 在上、J1/J3 在下，元件面顶视、不镜像；焊盘坐标来自生产导出，未画铜线、焊锡，不是实物测量。必须核对实际新制板朝向与丝印后断电固定探头；所有示波器地夹只接公共 GND，避免相邻小焊盘短接。J2-5 是 USART1 日志 TX，不能代替测点 A。
- **[用户确认]** 探头尚未接机器人，用户询问接法。已展示图并说明：机器人断电后，探头拨 ×10；CH1=A、CH2=B、CH3=C、CH4=D；地夹接已确认的 J1/J3 GND 或公共地引线，不将粗地夹夹到 U6 小脚，不接 DATA/3V3/VBATT。接好后再配置采集和观察卸力通信，尚未授权或执行边接探头边启动动作。示波器自身保护接地保留，用户手册印刷 p2/PDF12 要求仪器保护接地。

### 小焊盘的实际固定方法（2026-11-01，替代直接挂探头的接法）

用户指出 R3/R6/U6 太小，无法直接固定接头。前述图是电气测点定位，不能解释为把大探钩直接挂到小元件上。当前根因目标由用户暂停，本次只回答固定方法并记录，不恢复动作、采集或驱动安装后的验证。

**[生产网表核验]** 重查同一 Gerber 的 `FlyingProbeTesting.json`：外部 DATA 可用 J1-3 或 J3-3（DXL_BUS），GND 可用 J1-1 或 J3-1；均为通孔接口焊盘。USART2_TX 仅列 U2-9 与 U6-2，无已引出的连接器测点；OE# 列 R3-2/U6-1/U2-8；芯片侧 DXL_DATA 列 R4-2/R6-2/U6-4/U2-10。原始筛选见 [同网测点清单](imu-v03-probe-alternatives-20261101.json)。脚号来自网表，不从插合面猜左右。

**[建议／未实物验证]** 为减少小焊点操作，第一轮可先用 CH1=U6-2 TX、CH2=J1-3 或 J3-3 DATA 的两通道接法；CH3/CH4 保留为进一步区分串阻两端和 OE# 时添加。这能比较 TX 与外部总线数据，但不能代替四通道对所有中间段的同步观测。

1. 整机断电并断开仍可能给板供电的调试连接；固定板子，在放大观察下操作。
2. 小焊点用约 0.1–0.2 mm 的细绝缘飞线短距离引出；1–2 cm 是本次布置起点，不是厂家规定长度或已验证带宽指标。只在导线两端去绝缘，先给导线端预上锡、焊点加少量助焊剂，快速连接到已有焊点，不反复长时间加热或拖动元件。
3. 导线绝缘段在附近用绝缘胶带固定，焊点到固定处保留一点松弛；另一端露出少量导体供探钩夹住，不能让裸端碰到相邻节点。探头本体和粗电缆另用支架或胶带固定到台面/夹具，小焊点不承担其重量和拉力。
4. DATA/GND 优先从已核对的较大接口焊盘或匹配插头转接线取得；信号引线和地回路都尽量短且靠近。观察快速边沿/振铃时需复核探测附件自身影响，不能把长引线引起的波形变化直接判为板故障。
5. 放大检查无焊锡桥、无裸线搭接；没有细焊条件时先观察大接口 DATA，内部 TX 用能稳定定位的探针支架，或交由有细焊经验的人引出，不手持四个探头做动作测试。拆除时先释放外部固定、熔化焊锡后取线，不生拉。

**外部依据与适用边界**：已取得并读取 Tektronix《Socket Cables and Solder Tip Kits Instructions》071-2538-00，其 General recommendations 明确焊接端不能承受探头重量，须另行固定以释放焊点应力，Procedure 要求引线尽量短。已取得并读取 Keysight《Probe soldering guidelines for Keysight InfiniiMax probes》5992-3350EN：p1 说明短线及焊接连接，p2–3 说明细烙铁头、助焊剂及控制热量，p9 的 Strain relief 说明胶带等机械固定方法。这些是专业探头的一般机械/测量依据，不代表附件适配本机鼎阳被动探头，也不是推荐购买对应产品。上述线径和长度为本次布置建议，非引用厂家数值。原件和下载结果见 [来源清单](sources/probe-fixing-20261101/sources.json)。

- 尝试读取 Tektronix Probing Tips 网页返回 HTTP 403，未将该页文字或 Figure 14 作为本轮已核验证据： https://www.tek.com/en/documents/application-note/probing-tips-high-performance-design-and-measurement
- https://download.tek.com/manual/071253800web.pdf
- https://prc.keysight.com/Content/PDF_Files/5992-3350EN.pdf
- web.run 本轮搜索／打开均未返回正文，以上 PDF 通过官方 HTTPS 直接取得；pypdf 报缺少 fontTools 的字体解析提示，本文引用段落已可读，未因此声称完成 PDF 视觉验收。

尚未焊线、接探头或取得实物固定照片；本轮无真机操作，修改保留工作区，未提交。

## 工具失败与记录边界

- 直接以 radxa 读 `/proc/tty/driver/serial` 被拒，`sudo -n` 未授权；改用用户此前提供的管理员凭据执行只读采集，凭据不写入脚本或证据文件。
- web 检索 STM32G031 USART errata 和 Rockchip UART 未返回可核验正文，尚无外部勘误依据。
- `Build/imu_to_dxl.map` 及误写的 `duck-control/src/params.rs` 不存在；参数源码实际位于 `robotd-params/src/lib.rs`，10 Hz 在其 1–1000 Hz 有效范围内；缺失文件未被伪称检查。
- 未修改三个只读参考库，未 commit／push。原始现场故障尚未解决。
- [最后只读核对](root-cause-final-read-20261101.json)：robotd 原版 SHA 一致，target_hz=50、commissioning/ready/off；robotd PID 2304、Studio PID 2311，均 active/enabled；实验 override 不存在。重启后后台累计已有 15 次通信失败，不能把服务恢复写成通信修复。四份新实验远端原始文件与本地 SHA 全部相同。
