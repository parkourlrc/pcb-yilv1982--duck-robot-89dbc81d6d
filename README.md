# duck-robot

Microduck 小型双足机器人的个人复刻项目。**当前主线为方案 C（社区套件，飞特舵机路线，2026-10-09 定稿）**：选型采购、3D 打印、装配、系统部署与实机验证；训练物理模型、任务与训练入口由本项目自建，借鉴公开物理参数；**2026-10-21 用户同意显示层按来源与许可复用上游精细网格**。显示复用不等于已完成实物对齐；未来真机动作仍以既定安全检查和模型/接口匹配为前提（方案 A 已存档，见下）。

进度流水、硬件到位记录与当前待办见 [PROGRESS.md](./PROGRESS.md)。

**项目规则与目录导航：[AGENTS.md](./AGENTS.md)**。协作前先读；调研/图片归档、中文沟通、过期信息清理及自动提交推送按此执行。

## 当前主线：方案 C（飞特路线）

- **执行机构**：飞特 HD-1910-C001 ×15（总线型，官方 robotd 有飞特补丁）
- **装配与零位校准**：[归中装盘与 CAL 调研](./docs/references/assembly-check-20261017/research.md)（2026-10-20）：未装盘时推荐先到 2048、选近齿位，再按机械零姿态 CAL；这不是 CAL 协议前提。15 颗 ID 已完成并于 **2026-10-24 改号对齐上游**（[本机映射](./docs/servo-id-mapping.md)：20–24 左腿、10–14 右腿、30=neck_pitch、31=head_pitch）；零位仍待校准，校后恢复扭矩前须确认读数并对齐目标。
- **主控/总线**：microduck HAT（Radxa Zero 3W，板载 74LVC 半双工驱动接 UART2）+ 当前使用单口 IMU：jyg9 / community-kit GD32F303 单 3P 成品版（ID 200，历史文档板②）；ScrapMeta v0.3 双口板（历史板①）于 2026-10-25 测量短接致损，不再列可用备件。用户本轮口头“板一”指单口板，后续按接口数量区分。板型见[版本记录](./docs/references/imu-to-dxl-variants-20261009/research.md)，通信见[IMU 调研](./docs/references/servo-web-imu-3d-20261024/research.md)。
- **供电与总线现状（2026-10-25 晚）**：同一块单口 IMU 已由用户移至 HAT 第二个 3P 口，用户测量该口三针电压无问题；换口后 IMU 仍严重缺答，舵机 15/15 在线。两腿原外部焊接分叉、电源入口及头部支路是否同时改变未完整描述，当前不以旧图代替实物。旧[单链接线图](./docs/photos/hat-v1.2-wiring-plan.png)仅历史意向；当前口述、复测与限制见[配电对照研究 §10](./docs/references/power-distribution-comparison-20261010/research.md#hat-port2-20261025)。**路线决定不等于实物接法完成载流验收**。
- **采购清单**：[BOM.md](./BOM.md)（已重写为 C 线；A 版存档于 [docs/bom-route-a-20260928.md](./docs/bom-route-a-20260928.md)）
- **PCB 打样**：[tools/jlc-order](./tools/jlc-order/README.md) —— 嘉立创开放平台全自动下单（计价→建单→审核→进度跟踪），2026-10-09 已实测下单并审核通过
- **IMU 备件刷机入口**：[flash/README.md](./flash/README.md)（仅板① ScrapMeta 备件需按对应飞特固件处理；当前板②无需刷机即可使用）
- **软件与动作训练**：[自建仿真学习步骤与参数借鉴边界](./docs/references/c-motion-training-20261015/research.md)记录 2026-10-15 起的自建路线：公开物理参数 → 自建物理模型/环境/奖励 → 通用算法训练 → 回放/调参/导出；不复制上游训练任务或整套替换本项目物理模型。2026-10-21 起显示层可按来源许可复用精细网格，现行边界见 [training/](./training/README.md)。实物对齐与机载 runtime 暂缓；[物理参数表](./docs/references/c-motion-training-20261015/physical-params.md)保留数值溯源。
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
