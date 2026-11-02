# duck-robot

> **11-02 01:08 第二次摔倒日志**：[实测] 主控与两服务持续在线；运动中大量IMU200缺答/陈旧数据，多个舵机也缺答，01:09:47收到网页“停下”关闭策略。没有本次自动关机或网页8秒恢复会话。[推断] 反馈反复中断严重影响起身，底层原因待查。01:11快照策略关闭、扭矩仍开、机身未直立；本轮只读取证。见[第二次事件日志和分析](docs/references/b-feetech-policy-deployment-20261024/walk-fall-second-20261102.md)。

> **行走后停机正在排查（11-01 事件，11-02 取证）**：[实测] 动作期间曾出现 5.7～6.6 V 舵机遥测，随后开始走约 17.45 秒后 Studio 与用户会话停止；[源码核验] 原生低压自动关机默认开启，Studio 缺项提示却称只警告。[推断] 低压关机最吻合，缺故障 boot 系统日志，根因尚未证实。用户重启后两服务已自启、策略及扭矩关闭；本次未改配置或动作。见[日志、配置差异和限制](docs/references/b-feetech-policy-deployment-20261024/walk-crash-investigation-20261101.md)。此前“未动作”仅指部署验收，用户随后已尝试恢复与行走，尚无成功起身验收。

> **躺姿起身入口已部署**：2026-11-01 23:49，按用户“部署”指示安装 `control.47+duck-recovery.1` 及配套Studio，页面按钮已可用，两服务保持自启、六模型已加载、模型与标定等41个文件哈希不变。只读验收结束仍为策略关闭、扭矩确认关闭，未触发起身；[部署记录](docs/references/b-feetech-policy-deployment-20261024/webpad-recovery-deployment-20261101.md)、[交付入口](tools/robotd-recovery/README.md)。最长尝试8秒，姿态恢复后零速度保持；实物起身及承重效果未验证。

> **2026-11-01 网页手柄与模型加载已接通**：[用户确认／实测] 用户已完成正式标定，15 个 `calibrated=true`、`zero_raw=2048`、IMU 已验证，主程序为 `motion/control`。网页手柄无需蓝牙配对；六模型文件哈希一致。经用户确认托稳，仅将 `[policy] enabled` 改为 true 并重启，六模型已加载、五个按键绑定无错误；robotd PID 1567、Studio PID 973 均 active/enabled，部署结束时确认卸力、动态动作开关关闭，未运行站姿或模型动作。首次因助手误读扭矩状态字段触发回退，修正验收后部署通过，原始记录保留。 入口 `http://192.168.1.35:8000/#/pad`；见[模型清单、映射与部署证据](docs/references/b-feetech-policy-deployment-20261024/webpad-models-check-20261101.md)。

> **2026-11-01 Studio 两个站姿入口的零位已对齐**：[实测] 经用户确认托稳后，仅将 robotd 标定文件的 15 个 `zero_raw` 改为 2048，原生 RPC 回读通过；最新 IMU 标定和全部保护保留，robotd/Studio 已恢复 active、网页 HTTP 200，自启保持 enabled。[源码计算] 共同 14 个关节的目标现在一致；此前左膝差 57.66°、右踝差 38.41°。本轮未触发站姿，物理效果待验证；新板已有的 ID 200 缺答仍独立记录。见[原因、部署与验收](docs/references/b-feetech-policy-deployment-20261024/studio-home-target-mismatch-20261101.md)。

> **2026-11-01 当前状态**：[用户确认] 新单 3P 口 IMU 已到货并换上。[实测] 主机通信已回滚为 IMU＋15 舵机同组 SYNC_READ；servo-web 30 秒 296/296 帧舵机完整、IMU 约 9.9 Hz，0 超时/坏校验/错 ID。robotd 已恢复原版；只读验收后已按用户要求切回 robotd/Studio（运行中），servo-web 已停止；此前助手只做过新板只读验收；此前两页站姿零位差已修正，用户已正式写入标定；模型已加载；回滚验收时未动作，用户后续恢复和行走异常见本页最新排障入口。 双口 v0.3 根因排障仍暂缓。见[回滚与验收记录](docs/references/b-feetech-policy-deployment-20261024/restore-mixed-sync-read-20261101.md)。

> **2026-11-01 两端时序代码分析**：[源码核验] robotd 的 2 ms 是 `ppoll` 等待上限，IMU 另有 50 µs 应答及逾期 2 ms 取消规则；两应用都没有显式发送排空／包间静默。原固件协议代码 28 个虚拟时序场景未生成坏 checksum，但未覆盖真实 UART／回切。见[完整代码分析与证据](docs/references/b-feetech-policy-deployment-20261024/imu-robotd-timing-analysis-20261101.md)。

> **2026-11-01 12:31 历史实验，v0.3 问题未修复**：三次原顺序均在起身插值阶段出现坏帧，目标写次数 2／3／2，实收 checksum 为 4C／41／56；先舵机后 IMU 对照仍失败。该次结束恢复单播版、两服务运行；这些是当时状态，现已按上方记录换板并回滚混读。见[原始证据](docs/references/b-feetech-policy-deployment-20261024/research.md)。

> **11:19 排障更新**：53／113 字节目标写包后均捕获 IMU 无应答；写目标后 15 颗扭矩回读变为 1，“卸力时原样写目标”不能视为无动力测试，相关诊断脚本已禁用。用户电源为 7.4 V／限流 3 A；最新数次人工尝试未见限流，显示电流一直低于 1 A，限流假设已降低优先级。两服务已恢复、机器人卸力；后台读取也有超时，物理机理仍待同步取证。

> **2026-11-01 连接与自启**：已补齐 robotd 开机自启，停止并取消旧 servo-web 自启；Studio 保持自启。用户确认托稳后已完成舵机会话交还，10:53 回读主程序在线、15 颗卸力、IMU 数据有效，策略关闭。做 IMU 粗校前须交还舵机会话；离页有舵机保持时主程序会继续暂停。见[当前状态与证据](docs/references/b-feetech-policy-deployment-20261024/research.md)。

> **2026-11-01 标定状态核对**：Studio 已记录 15 颗中位校准，但主程序的舵机标定完成状态仍未写入；最新运行状态已报告 IMU 安装方向验证通过（并非助手独立实物验收）。临时 commissioning 启动项未接入 Studio 标定写入/模式切换约定，需补齐该适配，不能只靠重启或勾选“已完成”。普通舵机会话交还已验证成功，标定写入是另一流程；见[排障记录](docs/references/b-feetech-policy-deployment-20261024/research.md)。

> **2026-10-31：6 个普通足部模型已上传 Radxa，文件 SHA 全部一致。** 目录为 `/home/radxa/duck-policies/hd1910-20261031/`。Python 3.13.18、Studio 和飞特版 robotd 已安装；v0.3 IMU 单播补丁已完成真机只读运行，1500 周期 1497 成功、3 次通信失败，未跑模型动作。Studio 8000 端口可访问。六模型现已导入 Studio，板上无电机推理预检 6/6 通过；按用户要求接入配套动作参数和参考机标定数值，动作保持关闭，本机标定匹配尚未实测。随后经用户支撑确认，robotd 已切为调试模式（约 50 Hz），15 颗舵机卸力已确认；Studio 运行，servo-web 停止。Studio 显示适配已部署，真实网页接口总览和舵机表均为 15/15，位置、电压、温度与 IMU 姿态已有数据；3D 标定关节姿势及部分原生诊断字段仍未接入。另 4 个滑轮模型仍为本地候选。见[模型与控制器记录](docs/references/b-feetech-policy-deployment-20261024/research.md)。用户已确认硬件完成，早期硬件排障保留为历史记录。

> **2026-10-31 历史 IMU 与供电记录**：新 v0.3 双口板已上线，用户确认 3P 直挂 7.4V 正常；补充：DATA/GND 始终接总线；pin4 5V 时主控无法启动，DAPLink 5V 时 IMU PING 不通且只接正极、未接 DAPLink 自身 GND。后者缺明确电源负极回路，前者另查公共 5V/启动条件。**原厂确认 AP2210 VIN/EN 推荐上限 13.2V、绝对最大 15V，旧“只能 5V/7.4V 超限”结论错误**。见[分析与原件](./docs/references/imu-v03-input-voltage-20261031/research.md)和[进度](./PROGRESS.md)。HAT 10-27 损伤与后续恢复使用之间的维修经过未补齐，不据通信恢复声称旧焊盘已修复。

Microduck 小型双足机器人的个人复刻项目。**当前主线为方案 C（社区套件，飞特舵机路线，2026-10-09 定稿）**：选型采购、3D 打印、装配、系统部署与实机验证；训练物理模型、任务与训练入口由本项目自建，借鉴公开物理参数；**2026-10-21 用户同意显示层按来源与许可复用上游精细网格**。显示复用不等于已完成实物对齐；未来真机动作仍以既定安全检查和模型/接口匹配为前提（方案 A 已存档，见下）。

进度流水、硬件到位记录与当前待办见 [PROGRESS.md](./PROGRESS.md)。

**HAT自主设计**：现行Rev A.1已修J502标准针序和C307 DNP钢网，原生检查及kicad-happy同版复审完成；此前电源、codec复位、软件适配与音频路由工作保留。**[用户确认，2026-10-31] 尚未送厂、没有新板实物。** 制造/装配接受与供电条件仍待落实，实际功能留待制造后按[首板草案](./docs/specs/20261028-custom-hat/first-article-a1.md)验证。当前是送审资料，不是投板或上电放行。最新源与包集中在[Rev A.1入口](./hardware/custom_hat/rev_a/README.md)，剩余项见[问题矩阵](./docs/references/hat-simulation-tools-20261029/issue-matrix-20261030.md)；旧Rev A的J502不能按新针序使用。10-30 阶段审查报告未入库，仅保留[清单](./docs/references/hat-simulation-tools-20261029/kicad-happy-review-20261030/manifest.json)。

**项目规则与目录导航：[AGENTS.md](./AGENTS.md)**。协作前先读；调研/图片归档、中文沟通、过期信息清理及自动提交推送按此执行。

## 当前主线：方案 C（飞特路线）

**2026-10-27 HAT 损伤历史记录**：用户为短接 HAT R31 已拆下电阻，反复操作后两侧焊盘脱落；当时要求断电维修。2026-10-31 用户已确认硬件部分完成，本次不继续把旧损伤列为当前阻断；具体维修/替换经过未补齐，原始记录仍见[维修专题](docs/references/pcb-pad-repair-20261027/research.md)。

- **执行机构**：飞特 HD-1910-C001 ×15（总线型，官方 robotd 有飞特补丁）
- **装配与零位校准**：[归中装盘与 CAL 调研](./docs/references/assembly-check-20261017/research.md)记录历史方法。15 颗 ID 已于 2026-10-24 对齐上游；2026-11-01 用户完成本机正式标定，15 个 `zero_raw=2048`、`calibrated=true`，IMU 已验证，详见[标定和模型接入记录](docs/references/b-feetech-policy-deployment-20261024/webpad-models-check-20261101.md)。此前导入的参考机零位已经替换。
- **主控/总线**：microduck HAT（Radxa Zero 3W，UART2）＋**2026-11-01 用户确认已换上的新单 3P 口 IMU**。软件身份为 `06 00 00 00 f2`（原生识别 ft6/legacy），新板厂商/批次未独立核准；servo-web 混合 SYNC_READ 已通过只读验收。新制 v0.3 双口板搁置，旧单口板和更早 v0.3 损伤分别存档。见[版本记录](docs/references/imu-to-dxl-variants-20261009/research.md)及[当前验收](docs/references/b-feetech-policy-deployment-20261024/restore-mixed-sync-read-20261101.md)。
- **旧单口板供电与总线记录（2026-10-27，现已下线）**：用户已尝试 IMU 接 HAT 第二口、中段分叉、左脚掌/左脚踝舵机处，均未消除多节点缺答；已记录梯度在 12→13 颗附近出现变化，更多节点时失败加重。用户确认台供 **7.4V CV、限流 3A、输出约 0.6～0.7A**。**[假设]** 优先核 DATA 上拉与串阻/驱动及边沿余量；用户补测供电均 >7.1V（暂按 IMU 入口理解），持续限流/入口欠压解释降权；板内 3.3V、瞬态和收发方向未隔离。存档 HAT V1.0 R31=1kΩ、官方对应 R33=150Ω，本机 V1.2 实装待核；换位未解决不等于各种拓扑错误率完全相等。见[本轮联合判断](./docs/references/hat-imu-shared-bus-20261027/research.md#node-count-current-20261027)与[实验记录](./docs/references/servo-web-imu-3d-20261024/research.md)。当时用户已下单示波器（2026-11-01 已确认 SDS814X HD 到货并接入 USB，驱动待安装），已断电并断开全部外接线在板测得 R31=100kΩ、R5=51Ω、F1=25Ω；前两项与修订值一致，暂不改这三颗，撤回继续孤立测阻的建议；现按用户决定[先用示波器区分请求、IMU内部响应与回包](./docs/references/hat-imu-shared-bus-20261027/oscilloscope-plan-20261027.md)，尚不能排除 IMU/HAT 的动态通信问题。本轮未操作设备，未决定换阻或改供电。
- **10-27 作者改阻建议（历史）**：[ScrapMeta 建议、圈选件 R31 和公开来源](docs/references/hat-imu-shared-bus-20261027/research.md#author-bug-search-20261027)已保留；该建议早于后续拆除损伤和换板，不作为当前待执行项，未取得改阻成功验收。
- **采购清单**：[BOM.md](./BOM.md)（已重写为 C 线；A 版存档于 [docs/bom-route-a-20260928.md](./docs/bom-route-a-20260928.md)）
- **PCB 打样**：[tools/jlc-order](./tools/jlc-order/README.md) —— 嘉立创开放平台全自动下单（计价→建单→审核→进度跟踪），2026-10-09 已实测下单并审核通过
- **IMU 固件资料**：[flash/README.md](flash/README.md)（当前新单口板使用原出厂固件，未刷写；该目录 v0.3 固件不能用于新板。双口板已搁置，旧单口板损伤保留历史记录。）
- **软件与动作训练**：[自建仿真学习步骤与参数借鉴边界](./docs/references/c-motion-training-20261015/research.md)记录 2026-10-15 起的自建路线：公开物理参数 → 自建物理模型/环境/奖励 → 通用算法训练 → 回放/调参/导出；不复制上游训练任务或整套替换本项目物理模型。2026-10-21 起显示层可按来源许可复用精细网格，现行边界见 [training/](./training/README.md)。2026-10-31 开始[已有策略的真机候选盘点](./docs/references/b-feetech-policy-deployment-20261024/research.md)，现已安装运行端、导入六模型并核清动作参数优先级，参考标定与本机匹配及动作验收待完成；[物理参数表](./docs/references/c-motion-training-20261015/physical-params.md)保留数值溯源。
- **MuJoCo 查看工具（已跑通）**：在仓库根目录运行 `powershell.exe -File .\training\play-mujoco.ps1`，打开程序打印的本地地址（默认 [127.0.0.1:8080](http://127.0.0.1:8080)）。已有精细整机外观、播放/单步/重置、倍率/速度、四视角/跟随与纯碰撞视图；20 s 本机回放实测约 **0.999× 实时率、59.90 Hz 后端场景提交**，浏览器 FPS 未测。用法见 [training](./training/README.md)，截图、性能数据和边界见[实施记录](./docs/references/mujoco-viewer-optimization-20261021/research.md)；显示外观并非本机 C 线精确 CAD。
- 当前工作序列以 [PROGRESS](./PROGRESS.md) 待办与最新记录为准；软件离线准备可与既定硬件步骤并行，不改变硬件安全决定。路线定稿理由与 C 线已知缺口见 PROGRESS「方案方向（2026-10-09）」。

## 并行参考库（只读）

三套开源资料统一存放在 **[references/](./references/README.md)**，各自保持独立目录；本项目自己的调研结论仍放在 `docs/references/`。三套上游参考库**只读参考、不修改、不合并代码、硬件配置或采购清单**（2026-10-09 规则；历史混入的本地修改已提取到 [local-changes/](./local-changes/README.md)）：

| 方案 | 本地入口 | 参考内容 |
| :--- | :--- | :--- |
| A：帆哥教程 | [microduck-build-tutorial](./references/microduck-build-tutorial/README.md) | Pi Zero 2 W / OpenRB / XL330 路线（回退线，基线已存档） |
| B：fanhao375 复刻研究 | [microduck-replica](./references/microduck-replica/README.md) | 机械装配、电控与调试资料；兼论 XL330 与飞特路线 |
| C：jyg9 社区套件 | [microduck-community-kit](./references/microduck-community-kit/README.md) | **主参考**：imu_to_dxl / banana_pcb / dxl_hub 三块板、GD32 固件与升级工具、robotd 飞特补丁、HLS 舵机调试器 |

- 方案 B 遵循其 [LICENSE](./references/microduck-replica/LICENSE) 与 [NOTICE](./references/microduck-replica/NOTICE.md)：不同文件许可不同，不能整目录视为 Apache-2.0 或可商用；其打印 CAD 已迁往上游独立仓 [microduck-replica-cad](https://github.com/fanhao375/microduck-replica-cad)，本地 `cad/`、`print/` 不是完整打印包。
- 方案 C 缺口（`software/microduck_feetech/` 完整源码上游未推送、真机整定值仅可参考等）见 PROGRESS「方案方向」。

## 方案 A 回退线（存档）

A 线（XL330 + OpenRB + Pi Zero 2W）的完整步骤基线（阶段 0-7）、硬件约束（XL330/OpenRB 供电与板级电流限制）、仿真/镜像核查结论与 B 站视频笔记已整体移至 **[docs/route-a-baseline-20260928.md](./docs/route-a-baseline-20260928.md)**。相关入口：

- A 线 BOM 存档：[docs/bom-route-a-20260928.md](./docs/bom-route-a-20260928.md)
- 训练基线说明与验收证据：[docs/a-training.md](./docs/a-training.md)、[docs/a-training-validation.json](./docs/a-training-validation.json)
- 恢复 A 线训练应在**可写工作副本**中重建并核对 [local-changes/microduck-build-tutorial/](./local-changes/microduck-build-tutorial/) 提取件；禁止未经授权回填只读参考库。2026-10-15 已列出运行中的 WSL2 Ubuntu，但旧训练环境是否仍在未查；`export_onnx.py` 等旧路径须逐项核对，见[本轮复查](./docs/references/c-motion-training-20261015/research.md)。

## 致谢

感谢 [AI-FanGe/Microduck-build-tutorial](https://github.com/AI-FanGe/Microduck-build-tutorial)、[Rhoban/microban](https://github.com/Rhoban/microban)、[pollen-robotics/microduck](https://github.com/pollen-robotics/microduck) 及方案 B/C 上游作者的开源工作；各参考库内容以其自带许可为准。

## 市场调研

- **2026-10-10 Microduck漏项修补（现行）：**[开源社区专节](./docs/references/consumer-electronic-toys-market-20261010/research.html#microduck-community)与[X11独立卡](./docs/references/consumer-electronic-toys-market-20261010/product-atlas.html#card-x11)补入官方成品预售、动作／RL架构、教程／板件生态及五仓库公开快照；不把stars或官方排产压力换成销量。现行**234编号＝旧229＋D5；41覆盖＝37消费核心基线＋3邻接＋1开源平台；39图／4视频**，原40卡及38图／4视频保留。完整来源、主会话抽核及未测范围见[补片](./docs/references/consumer-electronic-toys-market-20261010/parts/microduck-market-2026.md)与[质量日志](./docs/references/consumer-electronic-toys-market-20261010/evidence.html#execution-log)；本补录独立审查及主会话QA已通过，版本同步由主会话统一办理。以下229／192／115与40卡数字为此前阶段记录，不再代表现行总数；不改变C线硬件路线。

- 2026-10-10 融资与海外平台增补（此前阶段，以顶部现行补录为准）：[融资×海外平台专节](./docs/references/consumer-electronic-toys-market-20261010/research.html#capital-overseas-2026)与[完整证据／覆盖缺口](./docs/references/consumer-electronic-toys-market-20261010/evidence.html#overseas-sources)已整合；**阶段229编号＝旧192＋C12＋W18＋A7**，含历史纠错、失败与方法，不是229条正向销售证据。18条商品listing观察、7个平台体系不等于18SKU或18次成交；40卡／38图／4视频及原价格保留。下方192／115数字同属此前阶段记录，现行以顶部补录及质量日志为准。

- 2026-10-10（此前阶段，以顶部现行补录为准）：全球消费电子玩具公开资料研究——[研究报告](./docs/references/consumer-electronic-toys-market-20261010/research.html)、[40卡产品图鉴](./docs/references/consumer-electronic-toys-market-20261010/product-atlas.html)、[原30样本与10案例](./docs/references/consumer-electronic-toys-market-20261010/competitors.html)、[证据与质量日志](./docs/references/consumer-electronic-toys-market-20261010/evidence.html)、[媒体来源](./docs/references/consumer-electronic-toys-market-20261010/media/README.md)。2026滚动信号主轴＋软件／硬件使能专节：阶段192编号＝旧115＋T19＋U58（非独立来源数）；40＝原30＋10提名，37核心研究对象＋3邻接，不是40款已售／交付；38图＋4视频仅作研究引用。TECH小修及四组40卡审查修订已落实，最终集成视觉待复核；T110已补原生文本后端与有限正反基准。行业中立，不预设AI或非AI胜出，不改变C线硬件路线。

- 阅读版为可离线打开的 HTML，含章节目录、证据跳转与宽表格；[Markdown 源文件](./docs/references/consumer-electronic-toys-market-20261010/research.md)保留。重新生成：`python scripts/render_toy_market_html.py`；一致性检查：追加 `--check`（依赖 `markdown-it-py`、`Pillow`）。
