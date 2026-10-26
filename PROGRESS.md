# 进度记录

事实性的进度流水：什么时候到了什么、做了什么。核对结论与安全边界见 [README](./README.md) 与 [BOM](./BOM.md)。

## 真机 IMU 读取丢包：诊断分析完成，待实机验证（2026-10-26；无实物操作）

- **现象（用户实测）**：真机环境 robotd 读 IMU（ID 200）**100 次超时约 30 次**，节奏断断续续不成簇；15 颗舵机全部正常零缺失。轻载台架（10-17 ping 200）此前正常，带载真机出现。
- **已排除**：主机侧补丁已知缺陷（BURST_IDLE=2ms / flush 残留——丢后缀必伤尾部舵机，与本现象矛盾）；电压塌陷关断（会成簇 1.5~2s 连续丢，与断续孤立矛盾）；主机解析路径（超时是没收字节，非解析）。
- **当前首选假说**：出厂固件"周期性总线盲区与 50Hz 请求拍频对撞"（100Hz 传感器任务的关中断/主循环应答阻塞 → 盲区中到达的指令丢字节 → 该 tick 不应答；10ms vs 20ms 节拍相位滑动 → 断续对撞；只伤 200 因盲区仅存在于 IMU 板自身接收路径）。次选：echo 窗口边界概率缺陷。
- **验证工作单与判定分支**已落盘 [IMU 固件代码分析专题·验证工作单](./docs/references/imu-fw-v1-code-analysis-20261026/research.md)：V1 日志重看（TELEM_CNT 连续性，零成本）→ V2 间隔扫描（5~200ms 六档，拍频特征判定）→ V3 拆板单测 → V4 换 v1 固件 A/B 对照（烧前先 OpenOCD dump 原厂固件备份，经 H2 SWD 排针，DAPLink 已到货）。**盲区模型若坐实，烧 v1（中断+DMA 应答架构）即治愈**。
- 同轮副产品：v1 固件构建链本机 dry-run 通过（cmake+ninja+xpack-gcc 编出全部镜像，工具链留存 `~/imu-fw-tools/`）；改板设计变更单定稿（5V 档跳线+删 CN2+加 CN3+穿板铜，见 [电源分析专题](./docs/references/imu-jyg9-power-5v-20261026/research.md)）。

## MuJoCo 实时查看工具已跑通（2026-10-21；仅仿真）

- 用户在[优化方案](./docs/references/mujoco-viewer-optimization-20261021/research.md)基础上授权实施，并接受显示层复用上游精细网格。训练物理、任务和策略接口继续自建；来源许可与显示/碰撞隔离须保留，不能将训练网格称为本机精确数字模型。
- 在仓库根目录运行 `powershell.exe -File .\training\play-mujoco.ps1` 即可打开本地工作台：单环境、精细外观、播放/单步/重置、倍率/速度、四相机/跟随、纯碰撞视图与机身位姿。A 回放、B 显示、C 旧入口修复与 D 文档已完成，R 最终独立审查通过；分片明细见专题。网页鼠标施力、录制、关节检查器和显示插值未纳入此次交付。
- 本机 PowerShell → WSL → Chrome 153 headless 的 20 s 精细回放：999 控制步、1198 次场景完成，**0.998991× 实时率、49.94956 Hz 控制、59.89947 Hz 后端提交**，最多 1 个场景任务在途，繁忙时跳过 2 次显示提交，无运行错误。浏览器主要控件实操通过，速度跨 reset 保持 0.05 m/s；修正 mesh 可见性同步后，纯碰撞/精细互切的最终截图经主会话和独立 Reviewer 核看通过。FPS 未测，截图和原始计时已归档，不能写为浏览器稳定 60 FPS。
- 精细模型 70 个外观 geom、38 个原 STL（20.59 MiB），保留原 14 动作/49 观测；Windows MuJoCo 3.16.0 的编译物理数组/原碰撞属性对照通过，初始 qacc 及 100 步 qpos/qvel 对照最大误差为 0，WSL MuJoCo 3.10.0 实际编译回放通过。外观仍有 XL330/NP-F970/Pi Zero 等上游部件，不是本机精确 CAD；未重训、未重评站立/步行质量、未操作实物。
- 原生 native 低速已复现（首次约 0.101×、补测约 0.125×）；WSLg 的 GLFW 图形探针使用 llvmpipe 软件渲染，未认定其为全部低速的唯一原因。首次 PowerShell 退出码 1 未在后续直接捕获 Python 子进程时复现。native 标为实验入口，默认使用已跑通的 viser；证据见 [native 排查](./docs/references/mujoco-viewer-optimization-20261021/native-diagnostics.md)。
- 同日补查上游工具：B 线已有 `servo-web` 0.15.2 整机 3D 网页调试台和源码/模型包/截图，训练框架 mjlab 则有 native/viser 回放界面；修正此前漏查与默认新建 Web 工作台的建议，改为优先评估现有工具。`servo-web --fake` 无重力、状态配置为真机 10 Hz/虚拟 30 Hz，不能当作已解决本机回放卡顿；只读核查已写入同一方案第 2.1 节，未运行或部署工具。
- 同日补查 IMU 显示：servo-web 可把 IMU 三轴姿态施加到整机，并独立显示各关节；当前不跟踪整机 XYZ 平移。六轴传感器不等于完整 6DoF 位姿跟踪；MuJoCo 接入可另传根位置补齐，见方案第 2.2 节。本轮未连接本机 IMU；同时按 `model.json` 勘误上游旧说明，当前网页模型已有合成的嘴部 ID 34 显示关节。

## C 线 15 颗舵机中位校准完成（2026-10-20，用户操作，点检确认）

- 用户完成全部 15 颗"摆直→CAL"校准。点检快照：**15/15 已校准、读数全在 2048 附近且单圈窗内**。OFS 分层：腿部 9 颗 |OFS| ≤ 569（装配工艺好、安全区中心）；头颈 30-34 与 14 号 −1465~−1968（直位对应编码器 100~580 一带，齿位/装配角度所致；CAL 几何保证直位居窗口正中，行程余量充足，不影响使用）。至此**机械组装 + 整链验证 + 位置校准三步全部完成**。
- 下一步：行程检查（每颗从 2048 慢拉上下限，记录结构件干涉时的真实行程）→ 低负载动作 → 带载前回读保护位。**行程结果回填训练**：换算 rad（关节角 = 方向 × (计数−2048) × 2π/4096）更新 `training/params/microduck_geometry.json` 各关节 `range`（现为 CAD 设计值），并顺修 training README 已标错误——动作目标角现用电机 ctrlrange(±0.94 N·m) 裁剪 rad，应改为关节限位裁剪。

## C 线整机机械组装完毕，整链点检通过（2026-10-20，用户确认）

- 用户确认 15 颗舵机 + HAT + 结构件**机械组装完毕**。装配工艺按"通电归中位(2048)扭矩锁定→按孔位对齐装结构件→装完卸力"执行。
- **整链点检（只读）**：15 颗关节 + IMU 200 **全部在线**（板上 :8765 census + ping，错误码 0x00）；全部读数在单圈窗口内（无出窗）；19 号保护位保持出厂（只开过热）。
- **OFS 分布**：头颈 30-34（−1512~−2033）与 14 号左踝（−1812）已有校准值——**待确认是否都在"关节摆直"基准位所做**（若为装配/随手姿势所做，带载前须按流程重做）；左腿 10-13、右腿 20-24 共 9 颗 OFS=0 未校准。
- 当日 30 号实测补充（详见 [assembly-check-20261017](./docs/references/assembly-check-20261017/research.md)）：CAL 以单圈编码器值为基准、产物有界 ±2048 且零位居中；正规流程不存在"输入角度多转一圈"；手掰出窗后先 CAL 再动。板载服务 duck-hls/duck-imuview 因 sudo 非交互不可用改为用户态后台进程运行（systemd 托管待用户板上 `sudo systemctl enable --now` 一次）。
- **下一步**：9 颗未校准关节逐个"摆直→CAL"；复核 6 颗已有 OFS 的基准姿势；行程检查（从 2048 慢拉上下限记录真实行程）；带载动作前回读保护位。
## 舵盘归中与 CAL 必要性复核（2026-10-20；文档调研，无实物操作）

- 更新[装配校准研究](./docs/references/assembly-check-20261017/research.md)，归档厂商 HLS 内存表、SCS 协议原文及来源校验信息。结论：未装盘时先到 2048、选最近齿位、再扶到机械零姿态 CAL，是推荐工艺；不是 CAL 协议前提，没有“大 offset 必烧舵机”的证据。已装好的关节不因偏移绝对值大就一律拆装或盲目驱动旧 2048。
- 撤回旧“唯一明文要求”“脚掌与小腿垂直无依据”“孔位对齐即零位”“试遍 25 档”等判断。保留 10-17 用户确认飞特版件、14 号曾 mid 到 2048 后装配的事实；**仍无本机 CAL 完成记录**。
- 重点操作差异：C 线调试器 CAL 不同步目标，直接开扭矩也不先对齐；校后先确认当前读数约 2048，再在恢复扭矩前对齐目标并回读。未增加台架测试、整机极限扫动或工具修改；各关节零姿态/校准结果仍待实际确认，见[工具索引](./docs/bench-tools.md)。

## C 线 mjlab 首训全面达标（2026-10-19；仿真，无实物）

- 完整 DuckWalk mjlab 环境（命令/推扰/全套奖励/终止）+ rsl_rl PPO 训练入口（mjlab_duck/）全栈跑通；4096 env×10000 迭代 3.4 小时。**验收：速度误差 0.001–0.018（CPU 版的 1/10 以上）、全档存活 95–100%、3N 等效推扰满额率 100%（100/100，门槛 80%）**。19 轮 CPU 归因就此修正：瓶颈是 CPU MuJoCo 接触求解+样本规模，GPU warp 引擎+4096 env 首训即达标。详见[研究记录](./docs/references/c-motion-training-20261015/research.md)。

## C 线 mjlab 路线：GPU 物理管线闭环达成（2026-10-17 晚；仿真，无实物）

- 用户指示切换 mjlab 路线。WSL 装齐 B 线锁定组合（mjlab 1.3.0+mujoco 3.10.0+mujoco-warp 3.8.1+warp 1.12.0，坑：漏声明 scipy、新版 mujoco-warp 3.9.1 接口不兼容）。自建 duck_v0.xml（删 XML 执行器由 IdealPd 接管）+ 自写奖励经 ManagerBasedRlEnv GPU 闭环 smoke 通过：**4096 环境 129,950 env-steps/s**（CPU SubprocVecEnv 的 8.7 倍）。下阶段：完整 DuckWalk 环境+训练入口+验收。详见[研究记录](./docs/references/c-motion-training-20261015/research.md)。

## C 线站立推扰失败复核与旧归因勘误（2026-10-19；只读分析，无重训/实物）

- 新增[失败分析](./docs/references/c-motion-training-20261015/failure-analysis-20261019.md)与[checkpoint 元数据](./docs/references/c-motion-training-20261015/checkpoint-metadata-20261019.json)。v0.3c 历史 3N×0.3s 满额率 50%=恒零，≥80% 未达；优先候选是机身速度观测缺失、EMA 状态晚一拍、raw/filtered 混合惩罚、直接改变动作尺度/滤波续训及缺少课程，因果贡献未做单项对照。
- 撤回“物理不可达、脚被钉住、无 EMA 必败、命令 bug 非根因、架构穷尽、必须数周或 MJX”的旧定论，并逐处更正下方历史记录。23 个 final 含 2 个 smoke；21 个非 smoke 的 num_timesteps 合计 107,311,104，只是现存字段合计，旧“19 轮约 1.35 亿步”无法复核。
- 本轮仅核对源码/Git/已有存档并改文档与注释；未修执行逻辑、未重训、未运行新评估或硬件。当前 49 维接口及未修问题见 [training/README](./training/README.md)。下一步建议先冻结契约、修接口，再做同场景小规模对照。

## C 线 v0.8/v0.9：命令修复、相位与去 EMA 实验（2026-10-19；按 checkpoint/提交时间校正原 10-17 日期）

- 已提交快照的 vx_cmd 采样确曾被注释吞掉，但缺运行快照，不能断言每次运行相同。v0.8 同时修命令与加相位，历史汇总无扰速度档存活 100%、3N 10–15%，不能认定命令 bug 已排除或推扰全档稳定。v0.9 历史无扰存活 0–20%、3N≈0；checkpoint 末 100 训练回合平均 69.62 控制步、满 500 步 0/100，支持该次训练末段失败，不证明 EMA 普遍不可替代。原目标仍未达，详见本轮失败分析。

## 左右腿 ID 映射定案：与上游相反（2026-10-17，部署契约）

- 用户实物装配验证后定案本机映射：**10-14=左腿、20-24=右腿**（上游 `model.rs` 为 left=20-24/right=10-14，两者左右互换）；用户已按新映射完成舵机改号。头颈 30-34、IMU 200、home 角镜像符号（跟随关节名）不变。
- 工具已同步：板上 `~/hls_servo_debugger` 关节表经 [scripts/swap-hls-jointmap.py](./scripts/swap-hls-jointmap.py) 交换并重启生效（:8765 界面 10-14 显示左腿）；参考库未动。
- **契约警示**：将来所有控制软件（robotd 补丁或自研主控、策略部署、仿真-实物关节顺序）必须用本机映射，照抄上游表会左右镜像颠倒。完整表与 A 线视频对照见 [servo-id-mapping](./docs/servo-id-mapping.md)。
- 装配进行中：14 号（本机映射=左踝）已按当时“归中位+孔位对齐”工艺装入脚掌组件；这不代表零位已经校准。**2026-10-20 指导修订**：未装盘且轴未受机构约束时推荐先归中选近齿位，已有装配不一律 mid；按正确机械零姿态 CAL，校后恢复扭矩前确认读数并对齐目标。详见 [assembly-check-20261017](./docs/references/assembly-check-20261017/research.md)。

## 15 颗舵机初始化完成，进入机械组装（2026-10-17）

- 用户经 hls_servo_debugger（板上 :8765）**逐颗完成 15 颗舵机初始化**：出厂 ID 1 → 关节表 10~14 / 20~24 / 30~34（此条早期按上游分配记为左腿 20-24、头颈 30-34、右腿 10-14；**现行本机已换为左腿 10-14、右腿 20-24**，以[本机映射表](./docs/servo-id-mapping.md)为准）。选项按源码分析结论执行：**校准选"不校准只改 ID"**（位置校准留待装机后整体做）、多圈开关保持关（单圈）、19 号电压/过流保护保持关（默认，避免卸力摔机）；工具流程自动写 Kp=32/Kd=0（EEPROM+RAM 双写，规避 robotd 默认 gain=200 的自激振荡雷）。
- **未做整链复验**（用户指示：不串一起测，装好再一起测）。逐颗回读校验由工具初始化流程保证，本机未独立复核；**待装机后整链扫描确认 15+200 全在线**。第一颗"嫌疑坏"舵机（信号脚拖线）单独隔离，未参与初始化与装机。
- 下一步（2026-10-20 修订）：机械组装 → 装后整链确认 → 按对应关节的机械零姿态 CAL → 校后读数确认、目标对齐并回读 → 支撑下低负载动作。未装盘且轴未受机构约束时推荐先归中选近齿位；已装好的不盲点“转到中位”，也不因 offset 大就一律拆装。见[装配与 CAL 调研](./docs/references/assembly-check-20261017/research.md)。

## B5 单舵机 ping 通：ID 1 在线，双真凶定案（2026-10-17 深夜）

- **链路打通**：`ssh radxa` → ttyS2 → HAT 74LVC → 舵机应答，**ID 1 在线、错误码 0x00**（裸诊断 `ff ff 01 02 00 fc` ×3 + 修复后全范围扫描确认）。HAT 驱动正常，前"故障域 HAT"结论勘误作废。
- **IMU 板②挂链末 ping ID 200 在线（错误码 0x00）**——主控+舵机+IMU 三件套总线全部通信正常（2026-10-17 深夜用户串机实测）。深度验收（imu200 13 项）按精简原则暂缓，出问题再查。
- **真凶①：`feetech-ping.py` 的 `checksum_ok()` 公式写错**——正常应答全被判无效，制造长期"无响应"假象；已修复（scripts/ + 板上 ~/feetech-ping.py 同步）。**真凶②：第一颗舵机信号脚异常**（挂线拖总线至 1V，换第二颗后 3.4V 正常，用户实测对比），该舵机换下标记"嫌疑坏"；早期"插舵机起不来"由此解释（异常电平经 HAT 回灌 pin10 锁 U-Boot），"接触不良"归因部分不成立。
- 必要前置：fiq_debugger 修复（见下条）。微雪板验证正常，留作备用主机。排障方法与全程时间线见[排障记录](./docs/references/hat-servo-bus-debug-20261016/research.md)。
- **后续状态**：IMU ID 200 ping 与 15 颗逐颗改号均已于 10-17 完成；当前进入机械装配和[零位校准](./docs/references/assembly-check-20261017/research.md)，坏嫌疑舵机继续隔离，不混入装机批。

## HAT→舵机总线联调排障：Radxa 侧清白，收敛到 HAT 驱动（2026-10-17；结论已被当晚勘误，见上条）

- 舵机扫描全范围 0–253 **0 应答**，经分层隔离：①杜邦接触不良（曾致启动失败，用户修复）；②**fiq_debugger 占用 uart2 已修**——`/etc/kernel/cmdline` 删 `console=ttyFIQ0`+`/etc/default/u-boot` 固定 uart2-m0 overlay+`u-boot-update`，板上有备份；③pinmux 确认 uart2m0-xfer 生效；④**回环 PASS**（pin8↔pin10 短接，36/36 字节）——Radxa 驱动/mux/引脚全正常。**故障域收敛到 HAT 板内 74LVC 半双工驱动**（pin8 空闲 3.16V 正常进板，舵机座 DATA 针仅 1V 且不随发送变化；无 V1.2 图纸不深挖）。
- 附带发现：**pin8/10 短接状态下上电会锁死 U-Boot**（banner 回灌 RX 被当按键输入）——判断"无法启动"时须考虑串口回灌路径；纪律：不在短接状态上电。Radxa 重启后 WiFi 就绪需 1–2 分钟属正常（NM+DHCP），灯亮后等 2 分钟再 ping。
- **下一步**：FE-URT-2（或微雪板 B=USB 模式）绕过 HAT 直连舵机 ping，验证舵机+拿 ID；台架期通信暂走该链路，HAT 驱动问题挂起（待向卖家索取 V1.2 图纸）。详见[排障记录](./docs/references/hat-servo-bus-debug-20261016/research.md)。

## C 线 WSL GPU 大规模训练记录（2026-10-17；历史汇总，归因已勘误）

- 历史记载 WSL CUDA 环境与 512 env 15042 fps、无扰速度档存活 100%、位移 ≤0.02m/s、3N 5–30%。duck_walk_gpu 现存 final 为 12,058,624 步，非原写的 1000 万；原“17 轮约 1.16 亿步”为未完整核准的累计。命令 bug 与 rollout/batch/单环境片段同时变更使对照混杂，撤回“算力不足/命令超极限已证伪”及必须 MJX 的结论。详见[研究记录](./docs/references/c-motion-training-20261015/research.md)。

## C 线行走任务 v0.6 系列三轮（2026-10-17；历史汇总，归因已勘误）

- 历史任务设计为 47 维+速度命令±0.2m/s+scale0.5；三轮各约 800 万步。历史汇总无扰速度档存活 100%、±0.2 档误差约 0.19m/s、3N 5–25%；不能与站立带扰存活率直接比较。已提交快照中训练命令恒 0，不能据此判定算力不足是根因。原“累计 14 轮约 9400 万步”为未完整核准的累计，详见[研究记录](./docs/references/c-motion-training-20261015/research.md)。

## C 线推扰 v0.5 自适应增益记录（2026-10-17 凌晨；历史汇总，归因已勘误）

- 历史记录 v0.5 自适应增益（0.08→0.50、EMA 保留），随机策略活满 10s、约 500 万步后响应 22.4×、无扰 100%，但 3N 50%=基线、4N 从 v0.3c 的 25% 降至 0%；缺逐场原始记录。
- 撤回“脚被钉住/必须换行走/重构路径证伪”归因：模型没有锁脚约束，奖励偏好不等于运动自由度被禁止。原“九轮约 3600 万步”未完整核准；实验环境曾回滚，未保存完整快照，不能直接复现该次环境。

## 测试范围按用户指示大幅精简，进入装机最短路径（2026-10-16）

- **空板 5V 门已通过（2026-10-16 用户实测）**：HAT 空板经背面第 3/4 排焊盘 7.4V/0.3A 限流供电，40P pin2/4 对 GND（pin6）实测 **4.96V**，在 5.0V±0.2V 判定门内。输入侧无持续顶限。
- **Radxa 对插上电成功（2026-10-16 用户确认）**：40P 断电对插，7.4V 供电（限流放宽），Radxa 正常点亮、`ssh radxa` 免密连通。HAT→Radxa 5V 供电链实测可用。下一步：单舵机 `feetech-ping.py scan` → 挂 IMU 板② ping 200。
- **ssh 断连插曲（2026-10-16）**：用户报 radxa 连不上；实测板子 WiFi/IP（192.168.1.35）/sshd 全正常，根因是**本机 ssh 免密配置整套丢失**（config+私钥均不在，10-14 那套去向不明）。当轮重建密钥与别名、paramiko 装回公钥，`ssh radxa` 恢复免密（实测 SSH_OK）。细节与 DHCP 写死 IP 的遗留风险见 [radxa-env-check 2026-10-16 补充](./docs/references/radxa-env-check-20261014/research.md)。板子本次 uptime 16 分钟即中途重启过一次，怀疑与接舵机前后的供电波动有关，舵机上电时注意电流表。
- 用户明确"**非必要的测试都不用做，加快进度，有问题再说**"（延续并强化 2026-10-14 测试价值原则）。现行硬件最短路径：**HAT 空板验 5V（唯一保留实测门，7.4V/0.3A 量 40P pin2/4 = 5.0V±0.2V，防烧 Radxa）→ 断电对插 Radxa ssh → 单舵机 `feetech-ping.py scan` → 挂 IMU 板② ping 200**。A 段断电核对此前已全过（2026-10-11），Radxa 环境已就绪（2026-10-14），故 5V 门过了即可一路联调。
- **降级为"出问题再查"**：8.4V 满电端点、DATA/3.3V 电平核验、MCU 静置观察、IMU 板②分步台架验收（挂链 ping 通即可）、静置/温升记录；**舵机保护位只读回查延至带载动作前**。串口回环本就跳过。
- [HAT 测试单](./docs/hat-v1.2-test.md)现行执行节改写为最短路径表（原分步清单与 A–D 段保留为排查参考）；[IMU 板②验收单](./docs/imu-gd32-bench-test.md)顶部加精简横幅；[AGENTS 规则 7](./AGENTS.md) 追加本轮强化指示。停止条件不变：持续顶限/电压塌陷/反复重启/快速升温立即停。

## C 线推扰训练当时结项记录（2026-10-16 深夜；验收口径已勘误）

- 当时曾在用户未及时回复后按推荐项①记录结项；这不证明用户接受降低原目标。v0.3c 的响应 11.4×、4N 25% vs 0%、无扰 10/10、3 倍初始扰动 5/5 仅保留为历史汇总；原 3N≥80% 未达，不再归因为已证架构极限。当前环境已是 49 维 v0.8，旧策略需匹配环境才能回放。

## C 线推扰 v0.4 斜率限制器失败记录（2026-10-16 深夜；归因已勘误）

- 历史配置同时改 EMA→6rad/s 斜率限制、scale=0.3、log_std 上限并续训；两轮各约 500 万步后文字记载无扰 0%。checkpoint 末 100 训练回合平均 63.95/37.85 步、满 500 步均 0/100。此结果支持各次失败，不证明“任何噪声均失败/3N 不可达”；同一策略均值因 scale 变化而放大 3 倍，滤波改变又影响动态。原“七轮约 2600 万步”未完整核准；详见[研究记录](./docs/references/c-motion-training-20261015/research.md)。

## C 线推扰 v0.3 历史记录：3N 目标未达（2026-10-16；仿真，无实物）

- 当时加入随机 1–3 次×1–4N×0.2–0.4s 推扰，四轮历史约 1100 万步。v0.3c 汇总：响应 11.4×、4N 25% vs 恒零 0%、无扰 10/10；**3N×0.3s 50%=基线，未达 80%**。缺逐场数据，动作响应不等于恢复；旧物理极限推导遗漏地面接触、方向性支撑域并误解 EMA，已撤回。详见[研究记录](./docs/references/c-motion-training-20261015/research.md)与 [training/](./training/README.md)。

## C 线站立策略 v0.2.2：安静站立（2026-10-16；历史汇总，仿真，无实物）

- 历史记录：用户指出 v0.2 乱动，确定性输出每步目标角跳 ±0.03rad@50Hz；加大惩罚后存活 60%，v0.2.2 加 EMA（α=0.25）并修过截断返回值后，记载无扰 10/10、3 倍初始扰动 5/5、|Δa|=0。本轮未复验；EMA 时间常数 69.5ms，不等同固件斜率限制，未验证部署一致性。详见 [training/](./training/README.md)。

## C 线站立策略训练成功记录（2026-10-16；按 checkpoint 时间校正原 10-15 日期；仿真，无实物）

- 用户目标「训练站立动作」达成：v0.2 配置（ACTION_SCALE 0.1 + 初始 std 0.15）100 万步 PPO 后，确定性策略 **10/10 回合活满 10 s**（upright>0.996、z≈HOME），**3 倍扰动下 5/5 活满**。关键诊断：杀伤来自策略输出高频目标抖动而非初始扰动；缩小有效动作尺度后 9 分钟收敛。录像与 checkpoint 存 [training/](./training/README.md)（本地不入库）。仅仿真学习成果，不构成实物行为预测或上机依据；下一步推扰鲁棒性、执行器 BAM 化与速度任务。

## C 线自建训练工程第一轮落地（2026-10-15；全部仿真，无实物操作）
- 按 2026-10-15 确定的"只借物理参数、全部自建"路线，完成六步学习路线第 1–4 步最小闭环，新建 [training/](./training/README.md) 工程：参数提取脚本（只读解析上游 `robot_walk.xml` 15 body/14 关节/总质量 0.7372 kg 与 LuwuDynamics 1910 BAM 参数）→ [物理参数表](./docs/references/c-motion-training-20261015/physical-params.md)（单位/坐标约定/许可全溯源）→ 自建 v0 模型（自写胶囊/盒几何 + 借鉴质量惯量限位，`build_model_v0.py` 生成）→ 自编 gymnasium 站立环境 + SB3 PPO 训练/回放入口。
- **验证**：自写四元数级联与 MuJoCo 加载上游 XML 对拍一致（<1e-6）；v0 模型 HOME 静置 4 s 站稳（关节漂 <0.002 rad）。建模修了三个坑（壳-肢体重叠自碰撞、显式积分数值不稳换 implicitfast、foot site 左右局部系不同构致脚盒错位——脚底改用上游 sole mesh 世界位形对照导出），详见[研究记录第 9 节](./docs/references/c-motion-training-20261015/research.md)。
- **训练未收敛**：两轮各 100 万步 PPO（8 env，CPU ~1900 fps）回合存活停在 ~11 步/500；诊断与下轮迭代方向（终止阈值/动作滤波/站立课程/规模）见 training/README。管线端到端已跑通，策略可加载回放。
- 依赖：Windows 端 uv venv（Python 3.13 + MuJoCo + gymnasium + SB3 + CPU torch）；未动 WSL/CUDA，未触碰任何实物与参考库。
- **执行器 v0.1 限速修正（同日，用户指出录像中动作超速后）**：实测旧执行器下关节速度达 792 rad/s（BAM 推算舵机空载上限 ≈11.9 rad/s）；改为 motor+一阶电机模型（电压环/反电动势）后钳到 10.9 rad/s，阶跃响应与舵机规格量级一致；同时修复 XML joint 未引用 default class 致 armature/frictionloss 此前未生效的生成 bug。静置复测通过，录像已重录。

## C 线动作训练软件研究完成（2026-10-15 初稿阶段；后续训练见上方记录）

- 新增[软件研究与训练步骤](./docs/references/c-motion-training-20261015/research.md)。同日用户进一步明确：**不直接使用已有文件，只借鉴他人的仿真物理参数（例如质量、惯量），自行建立模型与训练工程；暂不对齐实物。** 已撤下此前“现成 HD1910 副本/默认任务”的执行安排，改为参数溯源 → 自建模型/环境/奖励 → 训练与回放。
- B 线已有 HD1910 Flat/Rough 任务和公开 1910 BAM 参数，但仍沿用原 Microduck 的几何/惯量及 14 维动作；不能等同本项目 C 线 15 舵机的已校准模型/部署契约。A/B 短训练是历史资产，不是 C 线验收。
- C 的完整 `software/microduck_feetech/` 在本地及本轮查得公开 main 提交 `923708b6d446f335a9110649cf670f65e29fb2be` 中均缺失；旧补丁仍有 flush/2 ms idle，不能宣称包含 README 后续 50 Hz 修复。上游台架跟随/增益值不是本项目落地行走或整定结果。
- **本轮只读工具清点**：Windows RTX 4080（16376 MiB，驱动 616.92）、uv 0.10.8；WSL2 Ubuntu 已注册且 Running。尚未验证 Ubuntu 内 CUDA/训练依赖/旧 venv，Windows PATH 无 cargo 不代表未安装 Rust；不复用 PATH 中无关工具 Python 环境。
- **初稿阶段尚未训练**：以下仅为当时状态，不代表当前进度；该研究阶段未安装训练环境、未运行训练/play/策略或硬件动作，只纠正历史“现机无 WSL/旧路径一律失效”和 Radxa 环境页内部时序矛盾，没有新增 Radxa 实测。
- 下一步（2026-10-15 同日已部分完成，见上方第一轮落地记录）：物理参数表、自建 v0 模型、最小训练环境与训练入口均已建立；站立策略收敛与执行器 BAM 化是后续迭代。实物校准、舵机映射、runtime 和 Radxa 部署暂缓；不改变供电与未来上机安全边界。

## Radxa Zero 3 软件环境核查（2026-10-14）

- 板子经 `ssh radxa`（密钥免密，别名已入本机 ssh config）远程核查：Python 3.11/pip/git/gcc/make/i2c-tools/numpy 就绪；WiFi 自动连接正常。
- **环境缺口已全部补齐（2026-10-14）**：python3-serial 3.5、cmake 3.25.1 经 apt 装好；**UART2/ttyS2 已通过 overlay `rk3568-uart2-m0` 启用**（M0 mux 即排针 pin8/10，与 HAT A3 实测一致；重启后验证 /dev/ttyS2 存在、serial@fe660000=okay，蓝牙仍独占 ttyS1 不冲突）。extlinux.conf 已写入 fdtoverlays。
- 坑位记录：板子出境网速慢（apt 全量 update 约 20 分钟），须 nohup 后台 + 轮询；pkill -f 会误杀自身 SSH 会话（用 pkill -x）；镜像初始 apt 索引为空必须先 update。
- 家目录有历史误操作残留文件 `~/udo -S -p  sh`（less 帮助页内容），无关功能，待用户确认后删。
- 详见 [环境核查记录](./docs/references/radxa-env-check-20261014/research.md)。同日镜像评估结论：KDE 版无需换小镜像（sddm 已禁用，桌面不驻留，磁盘占用 11%），见 [radxa-system-check-20261014](./docs/references/radxa-system-check-20261014/research.md)。
## 串口调试通道终局：115200 不可行已回退，DAPLink 死而复生但仍不可靠（2026-10-14）

- **方案 A（降 115200）实测不可行，已全部回退**：改 extlinux cmdline、给 getty 加 agetty 115200 override 均改变不了 ttyFIQ0 物理波特率——**Rockchip fiq_debugger 驱动独占调试 UART，忽略 cmdline 波特率与用户态 termios**（1.5M 为其硬配置，改它需动设备树，放弃）。板子已还原出厂一致状态（1500000；extlinux 自 `.bak` 还原、override 目录删除）。曾短暂误报"115200 已完成"，勘误。
- **MOTD 已静音（保留，可逆）**：登录欢迎突发是 DAPLink 挂死触发器；`/etc/motd` 清零 + update-motd.d 两脚本去执行位，备份在板（`/etc/motd.bak`、`/etc/update-motd.d.bak-perms.txt`）。
- **DAPLink 克隆当日死透→复活**：上午 CDC+HID 双死（OpenOCD `CMD_INFO failed`）、拔插换口无效曾判"报废"；后被较长时间断电救回（CDC 与 SWD/HID 均恢复）。**教训：挂死时拔下等 ≥10 秒再插**（短间隔拔插电容未放净、MCU 未真正断电）。SWD 复活=IMU 刷机功能不受影响；CDC 在 1.5M 下仍随机丢字/挂死（串口登录演示：登录成功、uname 干净返回，随后一条命令即双向丢字）。
- **通道分工定案**：交互调试走 **SSH**（radxa/radxa，IP 为 DHCP 用前扫——TCP 22 线程扫描可行；本机代理 TUN 会干扰 SSH 需注意绕开）；串口看控制台/救砖用 `serial-log.py` 抓取（接受丢字）；**可靠串口交互待购适配器**（FT232H 最佳 ~¥60-120；CH340/CP2102 ~¥10 理论也够——克隆问题是固件非带宽）。WiFi=CU_M9pw_5G，当日 IP 192.168.1.35。PuTTY 0.85 已装（`C:\Program Files\PuTTY\`）。
- **勘误（本日）**：①Radxa IP 非固定（DHCP，用户告知）；②1500000 乱码机制早前误算"超 USB 带宽"（差 10 倍），实为 6.67µs 字节间隔超出克隆固件中断响应能力→UART 过载；③"115200 已完成"曾误报（fiq_debugger 假象）。
- 串口调试通道按用户要求改回手动提交，本条目随 2026-10-16 "update" 一并入库。

## DAPLink 克隆"总连不上"故障定性（2026-10-14）

- 把散在各处的现象归成**四种不同的"连不上"**：①仅充电线/口导致不枚举（10-13 实测）；②COM3 被前一个 serial-log 窗口占用——昨晚 23:34 起三连发"连不上"即此（22:25 会话持有 COM3 至 00:07，事后推定高置信）；③克隆固件"假在线"挂死需拔插；④Radxa 控制台无 getty、错过启动窗口后静默，属正常被误判。1500000 波特乱码的机制 2026-10-14 已修正：**不是** USB 带宽不够（150KB/s 仅占全速带宽 ~15%，早前"15Mbit/s"系 10 倍笔误），真因是 6.67µs/字节的到达间隔超出克隆固件中断响应能力导致 UART 过载丢字节，持续过载把固件搞死即③；115200（86.8µs/字节，13 倍裕量）下稳定。
- 枚举成功判据（红灯常亮绿灯闪 + "USB 串行设备 (COMx)"）、对策与证据见[连接排障记录](./docs/references/daplink-connectivity-20261014/research.md)；[flash/README](./flash/README.md) 排障表已互链。仅诊断与落盘，未新增采购。

## Radxa Zero 3W 救活：换 rsdk-b1 镜像重刷成功（2026-10-13 深夜）

- **b6 镜像首启失败根因确诊**：b6 自带 idbloader 的 DDR init（V1.18 typ 23/07/17）与本板 LPDDR4X 颗粒不兼容——串口抓到启动随机挂在 DDR 训练各阶段（banner 后/参数中/读训练后/容量识别后），从未到达 U-Boot。**DDR 硬件无恙**：maskrom 下 v1.10.111 loader「下载Boot」3/3 稳定跑通 DDR init。
- **修复**：换官方最新 **rsdk-b1**（bookworm KDE，2026-07，仅桌面版有 CLI 已停供）`output_512` 镜像 maskrom 全量重刷（Loader v1.10.111 + 镜像 EMMC@0x0 + 强制按地址写），SHA512 校验与官方一致。刷后**正常启动：灯闪、电流 0.6A（挂死态为常亮 0.3A）、HDMI 出画面**（用户确认）。
- **板卡参数**：LPDDR4X、32-bit 总线、双 CS → 推算 **4GB 内存档**；eMMC 容量/颗粒待进系统 `lsblk` 查。
- **过程工具与教训入库**：串口抓取 `tools/serial-log.py`（自动重连+落盘 flush）、并行下载 `tools/parallel-download.sh`；DAPLink（VID C251 克隆）多次"假在线"挂死需拔插，USB 口/线组合须逐一验证；串口接线事故（pin6→RXD/pin8→TXD 对顶致假静默）已勘误；`tools/emmc-flash/` 曾整目录丢失（git 忽略文件），已从官方源重建并留清单。
- **下一步**：进系统配置（账号/WiFi/SSH）→ 验证 rsdk 串口控制台（今 1500000 无输出，配置待查）→ 确认 eMMC 容量 → 接续 [HAT 测试单](./docs/hat-v1.2-test.md) B4（主控 ssh）→ B5（单舵机 ping）。桌面版做机载主控偏重，后续可禁图形自启或评估 Armbian server。
- 详见 [eMMC 线刷记录](./docs/references/emmc-flash-radxa-zero3w-20261013/research.md)（含完整排障链与串口日志存档 `serial-logs/`）。

## 主控 eMMC 线刷成功（2026-10-13，路线 A）

- TF 卡烧录受阻后（自研脚本 ~66MB 确定性失败、Rufus 不识别内置读卡器、1TB 卡假卡嫌疑未排除，见 [SD 烧录记录](./docs/references/sd-flash-radxa-zero3w-20261013/research.md)），用户决定走**路线 A：maskrom 线刷 eMMC**，覆盖前任系统（放弃封存策略）。
- 本机重新下载镜像并验证（SHA512 与官方及另一台机器记录一致）；三件套（DriverAssistant v5.14 / RKDevTool v2.86+v2.96 / rk356x_spl_loader_ddr1056_v1.10.111.bin）来自 dl.radxa.com 官方源，落位 `tools/emmc-flash/`（git 忽略）。
- 排障路径：① DriverInstall.exe 假成功（rockusb.inf 未入库），`pnputil /add-driver` 手动安装才生效；② v2.86 首刷"下载Boot失败"（传输抖动）；③ v2.96 暴露真因——镜像行"存储"列误为 **SPINOR**（板上无此 Flash）→ 切换存储失败；④ 存储列改 **EMMC** 后**全流程成功**（2026-10-13 用户确认）。
- **Radxa Zero 3W 现在板载 Debian Bullseye CLI（b6），从 eMMC 启动**；TF 卡 ~66MB 写入失败留悬案，日后修好可作实验盘（TF 启动优先于 eMMC）。
- 勘误备案：本会话曾误读截图写下一次虚假"成功"（befc480），已在 18b1e7c 撤回；写入成功本身以[线刷记录](./docs/references/emmc-flash-radxa-zero3w-20261013/research.md)（用户确认 + 第 4 次重刷日志）为准。
- **首次开机失败（进行中）**：eMMC 写入确认完整，但上电后灯常亮不闪、micro-HDMI 无信号——maskrom 判别通过（SoC/电源正常），问题锁定从 eMMC 启动过程；此前"显示器无信号"部分系误插 Type-C 口（该口无视频输出），换真 micro-HDMI 后故障仍在。二手 eMMC 坏块在嫌疑列表。
- 定位手段就绪：DAPLink 到手，调试串口 = 排针 8(TX)/9(GND)/10(RX) @1500000；备选实验 = 第二个 Type-C 口插电脑找 ADB。详见[线刷记录](./docs/references/emmc-flash-radxa-zero3w-20261013/research.md)。
- 串口抓取工具备好（2026-10-13）：[tools/serial-log.py](./tools/serial-log.py)（pyserial 3.5 验证，默认 1500000 8N1，落盘专题 `serial-logs/`）+ 双击 `tools/抓Radxa启动日志.bat`；供电可用稳压直流电源（**5.0V 严禁调高**、限流 2A、Type-C 剪线 CC 悬空风险与电脑口回退方案见线刷记录）。待现场接 DAPLink 执行。
- **实验 A 首扫作废 + 供电新线索（2026-10-13 用户实测）**：单线电脑直插下板子**灯亮几下即灭**（电脑口 ≤0.9A 未维持住供电），USB 无枚举是断电必然结果；板子启动电流尖峰超电脑口能力或有过流，待稳压电源电流表区分。

## 电池外置保险必要性复核（2026-10-12）

- 用户要求确认电池接入是否必须另加保险；结论：**外置保险不是一概必需**，若电池内置 BMS/保护的短路与过流切断规格经核实足以保护外部取电线束，可不另装。
- 当前到货 NP-F550 的品牌、准确型号和 BMS 能力仍未登记，故现阶段**不采购保险丝/保险座，也不以电池给整机供电**；先查标签/说明书，若无保护或无法确认，再设计外置正极保险及额定。台架基础测试仍按测试单使用限流电源。
- 更新 [BOM](./BOM.md)、[供电架构](./docs/power-architecture-v2.md)、[HAT 测试单](./docs/hat-v1.2-test.md)与[过流保护方案](./docs/overcurrent-protection.md)。未拆电池、未短路试验、未测 BMS；证据和限制记录见[复核记录](./docs/references/power-review-20261010/research.md#2026-10-12-主保险是否必要)。

## 消费电子玩具：Microduck漏项修补（2026-10-10，现行）

- [X11／G5](./docs/references/consumer-electronic-toys-market-20261010/product-atlas.html#card-x11)已补官方成品预售＋开源社区平台；[主文](./docs/references/consumer-electronic-toys-market-20261010/research.html#microduck-community)承认零售成品取样遗漏，以动作／角色表达、教程、套件支持与AI二次开发候选补齐框架，不重做全市场。
- [D101—D105](./docs/references/consumer-electronic-toys-market-20261010/evidence.html#microduck-sources)为5条新增证据，现行**234编号／41覆盖／39图／4视频**；41＝37消费核心基线＋3邻接＋1开源平台，不是41已售。原229证据、40卡与38图／4视频保留，以下流水中的旧总数为阶段历史。
- 主会话API快照：主仓9,276 stars／1,199 forks；各仓不相加为用户，不换算销量。官方USD399美国预售未含税运；商店称订单多且爬产，新单估计4—6个月，不保圣诞交付，缺订单量／取消率／出货。主会话独立抽核D101范围已登记，未结账或实测。
- 已保存X11官方主视觉900×312小图并view_image核对；程序与4HTML生成检查记质量日志。**本补录的独立内容／范围审查及主会话QA已完成，无必改项**；通过范围见质量日志。本角色未暂存／commit／push，版本同步由主会话统一办理。未改只读参考库，不改变C线供电／采购／训练事实。

## 消费电子玩具：融资与海外平台整合（2026-10-10）

- [主报告专节](./docs/references/consumer-electronic-toys-market-20261010/research.html#capital-overseas-2026)新增融资8行、平台代表12行、关联5行三表；只做资本／渠道与销售证据分层，不生成金额或热度排行榜。
- [统一证据](./docs/references/consumer-electronic-toys-market-20261010/evidence.html#capital-sources)现行**229编号＝旧192＋C12＋W18＋A7**。C12含8主要披露、2限定观察、2历史纠错；W18含11商品、5官方材料／报告线索、1访问记录、1方法；A7为商品观察。18条listing、7平台体系并非18款新产品／成功交易，旧192／115及以下阶段流水原样保留。
- [40卡图鉴](./docs/references/consumer-electronic-toys-market-20261010/product-atlas.html)只补有范围限定的产品／平台深链；原卡数、图片／视频与价格不变。C104补LE270-CN芙崽随行版国内发售的供应方声明，不认证美国.net；C102保留bibo上市6月／开售7月冲突；C112缺来源的公司全称已从分片及正式证据撤回。
- FIN独立9URL审查及SHOP独立11URL审查结果、未覆盖来源、W102／W199主会话方法核查分别写入[质量日志](./docs/references/consumer-electronic-toys-market-20261010/evidence.html#execution-log)；不称全部来源二次核验或资金／销售后台审计。**最终审核与生成检查已完成**：总审无必改项、C112的P2已关闭，程序／视觉QA实数及未测范围见日志；版本同步由主会话办理，不提前记录为已commit／push。

## 消费电子玩具：2026技术使能与40卡整合（2026-10-10）

- [研究报告](./docs/references/consumer-electronic-toys-market-20261010/research.html)保持国庆／近90天线索主轴、618及上半年单列，新增软件／硬件使能如何改变玩法与门槛；区分原型、内容、实时交互、量产、长期服务。T101只支持compaction工程改善；T110补Qwen3.5小模型原生文本后端与有正反项的官方同表基准，不宣称全面提升或具体玩具已采用。
- [40卡图鉴](./docs/references/consumer-electronic-toys-market-20261010/product-atlas.html)：四组各10卡＝原30＋10提名，37消费核心研究对象＋3邻接（F14机构教育、X04成人生产力、X06成人照护），不是40已售／已交付。原[30样本／10案例](./docs/references/consumer-electronic-toys-market-20261010/competitors.html)及旧价格基线保留。
- [正式证据](./docs/references/consumer-electronic-toys-market-20261010/evidence.html)现行**192编号＝旧115＋T19＋U58**，不是独立网站／报告数；旧115条及历史日志保留。T110已依据8个实际读取的官方URL纳入；小尺寸3/2发布、2B默认模式IFEval退步及参数／算力不等条件保留。Eilik税费排除、AIBI发货承诺、Loona暂时免费、51515原App于2026-10-01停止更新／支持已同步现行文，不混入SPIKE 2031承诺。
- [媒体归档](./docs/references/consumer-electronic-toys-market-20261010/media/README.md)与[manifest](./docs/references/consumer-electronic-toys-market-20261010/media/manifest.json)合42记录＝38JPEG＋4视频链接，覆盖40唯一product_id。主会话独立核38图哈希／尺寸／字节通过，总2,360,883 bytes；视频只元数据／部分起始画面，无完整观看或动态实测。素材版权不开放，披露限制不等于获得授权。
- TECH主干通过，两小修按追加授权已同步分片与正式文；PRODUCTS23通过G2/G3的20卡（18图、抽查4源页，其余未复访）。G1/G4审查亦通过，两视频范围／LOVOT阈值小修已镜像；最终集成／浏览器视觉结果已回传通过；总审仅列F04／F15两个主题四处旧附表同步，现已修正，已通过最终定点复核，内容与生成检查完成；版本同步由主会话办理；渲染脚本测试主会话回报27项＝25pass＋2权限skip，集成者不改脚本。
- 主会话最终程序QA已回传：全专题18份Markdown（含历史片）1,201个本地链接、47表列宽检查0错；192证据／40卡集合与媒体校验通过，四HTML --check通过（1,279链接、27表）。这些是四处同步前的检查快照，本次修正后的生成检查另记质量日志。最终浏览器reload确认40卡、36张正文主图及4项导航无横溢，主报告使能锚点跳转和表格可读；另2张证据图在归档，不称file://或打印PDF已测。
- D1—D7重点、行业中立及硬件C线路线保持；真实签收、留存、完整BOM／云成本／儿童场景仍未验收。版本同步由主会话按项目规则处理；以下完整保留原HEAD的上轮2026滚动阶段及更早历史记录。


## 消费电子玩具：转为2026滚动线索主线（2026-10-10）

- [研究报告](./docs/references/consumer-electronic-toys-market-20261010/research.html)摘要先列国庆/9月实际线索，618及上半年单列；近90天明确为7月13日至10月10日。2025与跨年财年移为背景，不再主导机会排序。
- [正式证据](./docs/references/consumer-electronic-toys-market-20261010/evidence.html)新增S01—S08、E01—E11共19条，加原96为**115个编号**，不是独立来源数；[竞品页](./docs/references/consumer-electronic-toys-market-20261010/competitors.html#signals-2026)保留30产品/10案例基线，新增观察不硬计为已验证新品。
- 撤销无屏/ODM默认优先级，保留用户D原则为可证伪假设与韧性要求，允许AI原生玩法但不宣称已证明。儿童、青少年、成人分层；发布/预售/备货/消费者交付/使用/复购独立。
- 落实S03调整后可比基期、玩具业务合计含智能、LOVOT“2万体以上”；DeskMate网页发布日期/修改日期层次已厘清，实际平台事件仍待核；KOTTI到执行者非签收，5月发布日不保证当前能力文案等同原稿。成功/失败与定点独立审查范围见质量日志。
- 本轮检索并归档2026公开资料，完成来源抽查、整合与最终QA；未开展实验、采购或设备测试，不改变C线。版本同步由主会话按项目规则办理。以下原96编号完成记录保留其基线轮次含义。

## 市场调研重要商业判断留存（2026-10-10）

- 追加用户标记重要的[养成反馈、操作节奏、角色表达与离线玩法](./docs/references/consumer-electronic-toys-market-20261010/research.html#play-retention)要点（附录D7），原段增加直达链接。沿用M08日本品类数据，明确不是单品留存/销量或生成式AI增速证据；本轮只记录关注点，不开展实验。

- 用户指出机会建议的详细解释很重要，要求记录。已补入报告[附录 D：重要商业判断与验证方法](./docs/references/consumer-electronic-toys-market-20261010/research.html#decision-notes)，并从执行摘要、第六节直接链接；Markdown 与 HTML 同步。
- 重点保留：玩法先于技术、有限交互/无屏的边界、可复用 ODM 服务、可维修/可降级、分阶段投入，以及静态版/互动版/AI版的对照验证。
- **用户确认的是重点留存，不是选定商业路线或授权投资/实验；例子和验证方法仍属研究解释与待验证假设。** 本轮未新增外部市场数据、未开展用户实验、不改变 C 线硬件任务。

## 市场调研增加 HTML 阅读版（2026-10-10）

- 按用户要求将三份正式文档转换为[研究报告](./docs/references/consumer-electronic-toys-market-20261010/research.html)、[竞品与案例](./docs/references/consumer-electronic-toys-market-20261010/competitors.html)、[证据与方法](./docs/references/consumer-electronic-toys-market-20261010/evidence.html) HTML；Markdown 保留为源文件，研究结论和原始来源不变。
- 增加页间导航、可折叠目录、证据锚点、横向滚动表格、移动端布局与打印样式；样式和脚本内嵌，不依赖 CDN。
- 生成与检查脚本：[render_toy_market_html.py](./scripts/render_toy_market_html.py)。通过正文文本一致性、本地链接/锚点、重复 ID 和离线资源检查，并在浏览器检查桌面/手机布局及跨页证据跳转。

## 全球消费电子玩具公开资料研究完成（2026-10-10）

- 完成截至2026-10-10的[中文研究报告](./docs/references/consumer-electronic-toys-market-20261010/research.md)、[产品与案例对照](./docs/references/consumer-electronic-toys-market-20261010/competitors.md)及[统一证据/质量日志](./docs/references/consumer-electronic-toys-market-20261010/evidence.md)的公开资料集成：30个型号/代际样本（消费核心29、机构教育邻接1）、10个案例、96个M/R/P编号记录；编号数不等于独立报告或全部法规全文核验。
- 内容涵盖规模边界、首购与留存、经营与服务生命周期、假设经济演算、区域合规和多环节机会；来源等级、未知价格/条款及独立审查修订状态均保留在证据日志。
- **未进行访谈、实物测试、采购或企业接洽；不改变C线硬件路线，也不构成接线、上电、下单或产品上市许可。**

## 用户决定：按 v2 推进，先做基础测试（2026-10-10）

- 用户确认继续 v2：电池经取电/保护进入 HAT 一口，另一口连接舵机链与末端 IMU，40P 对插 Radxa；正常整机不加入微雪板和独立稳压板，暂不增加 dxl_hub 或改成独立动力配电。
- 先做[基础检查清单](./docs/hat-v1.2-test.md)：断电核针/极性 → HAT 空板台架 → 主控/IMU → 单舵机 → 整链仅通信 → 支撑下低负载分步动作。此后根据实测问题再决定是否需要进一步分析或改造，不因理论最坏值直接扩展采购。
- 基础测试只能排除明显问题，不等于堵转/全工况安全验证；遇极性或电源网络不明、持续限流、异常压降/重启/发热立即停查。已确认超过额定时不继续试到故障。
- **本轮只记录路线与测试安排，未操作实物、未改变保护参数，未将任何验收项勾为完成。**

## 堵转是否会损坏 HAT：存在性核查（2026-10-10）

- 用户要求先分析实际问题，不先推进配电改造。新增[风险核查](./docs/references/stall-hat-risk-20261010/research.md)，含原厂规格摘录与来源哈希。
- 尚无证据证明本机 HAT 会因一次短促堵转烧坏；按现有图纸舵机大电流走直通铜箔而非 5V/2A 降压输出。连续额定/社区平均值不能单独证明瞬时损坏。
- **新证据**：C001 规格书过流卸载出厂默认关闭；描述是大于 0.5A 持续 2s 后关输出、参数可配且新位置指令清除标志。这是厂商描述，不是本机回读或推荐设置。社区记录与工具也不能保证该保护已开启。
- 下一步先只读核验舵机实际保护位/阈值/延时/模式与 HAT V1.2 路径，再决定是否改配电；没有设置参数、上电、短路或堵转实验，没有新增采购。

## EH 接口与其他配电方案对照（2026-10-10）

- 用户提供的[HAT SERVOS 局部图](./docs/photos/hat-v1.2-servos-closeup-user-20261010.png)已从临时附件原样归档；EH 名称来自存档图，实物品牌/额定待核。
- 核对社区 dxl_hub 的 PCB/README：J3 为两线电源输入，头/左右腿/IMU 分支，未见板载保险；这与本会话最小 HAT 单链意向不同。“不打 HAT”采用独立动力支路+保险的计划，亦非本机实测。
- 新增[配电解释图](./docs/photos/dxl-hub-power-distribution-explained.png)和[对照研究](./docs/references/power-distribution-comparison-20261010/research.md)，含原始资料哈希、PCB 器件/焊盘抽取与在线来源获取失败记录。
- 结论是评估配电/保护，不是新增采购或准许上电；HAT 可继续用于主控供电和数据转换，具体支路额定/接法/接口数量仍须设计验证。

## 过流保护设计说明（2026-10-10）

- 回答用户保护怎么做，新增[过流保护方案](./docs/overcurrent-protection.md)：当时建议正极主保险靠近电池出线，后接直流总开关，并明确保险/PTC/电子保护/BMS 的边界。该“默认加外置保险”的建议已由 2026-10-12 必要性复核收窄：先核验电池内置保护，满足条件即可不另加。
- **保险安数与具体器件未定**：需先核准最弱连接器/导线、正常峰值及动作曲线。HAT 入口约 3A 与整机参考 3–5A 的矛盾不能靠加 5A 保险解决；没有实测、短路/堵转试验或采购。
- BOM 补充待选的直流总开关/断电件；规则导航和供电文档已互链。调研说明同步写入[供电复核记录](./docs/references/power-review-20261010/research.md)。

## HAT 单链接线意向图（2026-10-10）

- 按用户指定的 `hat-v1.2-port-review.png` 底图，生成[接线意向图](./docs/photos/hat-v1.2-wiring-plan.png)与[可复现脚本](./scripts/annotate-hat-wiring.py)：A 口两线进电，B 口接舵机链与末端 IMU，C 排母对插 Radxa。
- 用户描述的功能流程成立：HAT 降压/总线功能通过后可不装微雪板和独立稳压板；取电、适配接头、保护、匹配充电器仍需。
- **没有上电或负载测试**；V1.2 针序和电源路径仍未核验，A 口承担整机电流，EH 约 3A 与常态参考 3–5A 的不匹配必须先解决，不能直接接全机验证。
- [供电方案](./docs/power-architecture-v2.md)、[HAT 验证单](./docs/hat-v1.2-test.md)、BOM 与照片索引已同步；证据与限定见[供电复核记录](./docs/references/power-review-20261010/research.md)。

## 参考资料目录整理（2026-10-10）

- 按用户要求，三个上游参考库统一移入根目录 [references/](./references/README.md)；本项目调研记录仍在 `docs/references/`，历史提取件仍在 `local-changes/`。
- 三个子库内部保持只读、无内容改动；迁移前后 4239 个文件的相对路径、大小及 SHA-256 全部一致。
- 已同步项目规则、导航、引用与辅助脚本路径；原始训练验收证据及导入哈希不改写为新环境事实。
- 详细步骤、验证范围及限制见[目录整理记录](./docs/references/reference-layout-20261010/research.md)。

## 项目规则与本轮资料归档（2026-10-10）

- 新建根目录 [AGENTS.md](./AGENTS.md)：主要目录与文档导航、调研落盘、用户图片归档、硬件标注归档、自动提交并推送、中文沟通及过期信息清理规则；保留只读参考库、UTF-8 BOM 和安全边界。
- 本会话的供电、VBATT、LDO、舵机分支及 HAT V1.2 实物复核已落盘至 [research.md](./docs/references/power-review-20261010/research.md)。**仅资料/照片复核，无本机上电或带载测试。**
- 已登记两张派生图：[IMU LDO 位置](./docs/photos/imu-ldo-location.png)、[HAT 接口复核](./docs/photos/hat-v1.2-port-review.png)，来源和旧图失效状态见[照片索引](./docs/photos/README.md)。
- 供电 v2 与照片索引同步本轮更正：HAT 未识别到独立电池入口，不能直接要求两口分两支；八焊盘对应两组 4Pin 空位；撤回“超级电容”和“软件硬限流兜底”的无依据判断。完整历史文档尚未作全面勘误审计。

## 参考库使用规则（2026-10-09 起）

**`references/microduck-replica/`、`references/microduck-community-kit/`、`references/microduck-build-tutorial/` 是别人的方案，只读参考，不在里面做任何修改。** 自己的进度、笔记、补丁一律放工程根目录（本文件、`docs/`、`local-changes/`）。历史上混入参考库的本地修改已于 2026-10-09 提取到 [local-changes/](./local-changes/) 并把参考库还原为上游原样：

| 参考库 | 上游 | 本地状态 | 校验（2026-10-09，逐文件 SHA256，忽略 CRLF/LF） |
|---|---|---|---|
| microduck-replica | fanhao375/microduck-replica `master` | 固定提交快照 `0f2cff6bd7`（2026-09-28，444 文件，与 README 记录一致） | 还原后与该提交 **0 新增 / 0 缺失 / 0 差异** |
| microduck-build-tutorial | AI-FanGe/Microduck-build-tutorial `main` | 内容等于 2026-10-09 上游 main | 还原后 **0 新增 / 0 缺失 / 0 差异** |
| microduck-community-kit | jyg9/microduck-community-kit `main` | 2026-10-09 zip 下载（无 git 历史） | 上游 zip 原样 + 手动补齐 `.gitmodules` 声明的 GD32F30x_Firmware_Library 子模块内容（参考完整性，非代码改动，是本目录唯一保留的添加） |

## 2026-10-09 硬件到位

用户确认到位（照片 + 口头识别；实物复测未做）：

| 物品 | 数量 | 说明 / 待办 |
|---|---|---|
| 微雪 Waveshare Bus Servo Adapter (A) | 1 | 半双工总线转接板，即 replica《电控采购清单》的「半双工总线转接板」待买项；此前台架一直用 FE-URT-2 顶替。整机走它还是飞线，待测。2026-10-10 照片归档+元件标注（[docs/photos/](./docs/photos/README.md)）：实物 v1.1，输入**直通舵机口不稳压**（HD-1910 台架喂 2S，严禁 12V），跳线 A=UART/B=USB（CH343） |
| 黑色降压模块（XT60 端子） | 1 | 2026-10-10 照片细读（[存档](./docs/photos/README.md)）+ **空载实测**（[操作单](./docs/buck-module-test.md)）：板名 **BUS SERVO POWER SUPPLY V1.3**（By 造物の乐趣，社区自研件，公开无资料，二维码待扫）；丝印 PWR IN 7.2-18V / OUT PWR 5V or 7.4V MAX 6A。**实测**：VCC（3P）12V→6.00V、6.6V→6.00V、6.3V→5.99V——选压桥 **6V 档**、稳压下限 **≈6.3V**（跌落跟随非关机，远好于丝印 7.2V），**2S 最差工况可用**；PWR OUT（2P）全程跟随输入 = **电池直通口**（舵机总线，对上 HD-1910 直挂 7.8-8.1V 用法）。接口分工闭环（~~DC 母座~~系照片误判，实物无此件）。当前方案不使用 VCC 稳压口、无需为 IMU 改焊 5V；模块不再是整机必需件，载流未验证 |
| 绿色 IMU 板 ×2 | 2 | **板①（双 3P 口）= ScrapMeta microduck-diy imu_to_dxl v0.3**（STM32G031，板 32×22mm）。三版来源对比与刷机兼容性查证见 [docs/references/imu-to-dxl-variants-20261009](./docs/references/imu-to-dxl-variants-20261009/research.md)；**飞特固件刷写包已备好**（[flash/](./flash/README.md)：校验过的 0.2.0 HEX + OpenOCD + 一键脚本 + imu200 验收工具），按归档设计拟从总线 VBATT 取电、U3 自降 3.3V；实物料号、输入规格及温升待验证，旧“只能 5V”要求撤回。**板②（单 3P 口）= jyg9 社区成品版**（2026-10-14 照片判别：GD32F303 LQFP48 + 降压前端，[照片存档](./docs/photos/README.md)）：出厂 DXL 2.0 + 飞特双协议免刷、可直接挂总线。**2026-10-26 官方 0.2 BOM/原理图析毕**（[电源分析](./docs/references/imu-jyg9-power-5v-20261026/research.md)）：Buck=ETA2845S2G，**≥6.5V 冷启动 / ≈5.93V 维持（EN 分压设定），5V 必不启动、不损坏**；EH 座针序 1=GND 2=V+ 3=DATA 图纸确认；官方即无 CH340（USB 走 GD32 原生引排针），旧出入关闭；电源正极无保险、反接必烧，断电核针序保留。整机用其一即可，另一块备件 |
| 白色鸭图案 HAT（**实物丝印 V1.2**，2026-10-10 照片更正，此前误记 V1.1） | 1 | **原理图已归档查证**（2026-10-09，[docs/references/microduck-hat-20261006](./docs/references/microduck-hat-20261006/research.md)）：官方 RPI Robot HAT 的嘉立创 EDA 派生版，Radxa Zero 3W（舵机总线 UART2=ttyS2）兼容 Pi Zero 2W，比官方多一颗 BNO085。**2026-10-10 正反面照片归档+元件标注**（[docs/photos/](./docs/photos/README.md)）：实物 V1.2 与存档原理图 V1.0 差异大——**背面多一颗 MCU 类器件（完整型号/功能待核）；正面圆柱电容标记 10 / 50V，不再按超级电容处理**；RS485 座未焊。接线/上电前须索取 V1.2 原理图 |
| 全部舵机 | 待清点 | 型号/数量/出厂 ID 状态待登记。飞特方案按官方关节表应为 HD-1910-C001 ×15（含嘴） |
| 打印件 | 待清点 | 版本/材料/数量待登记；打印模型以上游独立仓库 microduck-replica-cad 为准 |

台架现状：总线调试用 FE-URT-2 + 飞线；转接线是否随本批到货未记录。

**工具与耗材到位（2026-10-09 用户口头确认，实物未复测）**：

| 物品 | 数量 | 说明 / 待办 |
|---|---|---|
| 万用表 | 1 | 解锁「降压模块实测」待办（与直流电源配合） |
| 稳定直流电源 | 1 | 做降压模块输入下限/输出电压扫描；带载表现后续用台架实测 |
| 电烙铁 | 1 | 解锁 IMU 板 J2 焊接、banana_pcb 焊接工序。焊锡/助焊剂已确认有 |
| 电池盒 | 1 | 对应 banana_pcb 取电方案；化学体系/串数/触点形式待登记 |
| 杜邦线 | 若干 | 可走 IMU J2「杜邦线直焊焊盘」路线（替代 BM07B-SRSS-TB 座 + SH1.0 7P 线） |
| 无头电子线 | 若干 | banana_pcb「拆电池焊接出线」备选线材；线径须按 3-5A 核对，具体线规待登记 |

**工具照片存档（2026-10-10 建，同日降压模块正反面入档）**：[docs/photos/](./docs/photos/README.md)——万用表、直流电源、降压模块正反面（含元件标注图）实拍照片已从微信缓存拷入永久保存；后续照片（J2 焊盘、HAT、舵机/打印件清点）同规则补入。

**在途（2026-10-09 用户确认已发货）**：DAPLink SWD 调试器、U6068 插针 ×2、电池。到齐后 IMU 刷机链路（J2 焊接 → DAPLink 烧录 → imu200 验收）与 banana_pcb 装配的硬件缺件清零；电池到货后登记化学体系/串数/触点，与电池盒、降压模块实测结果一起定供电方案。

**原理图档案（2026-10-09 建）**：已确认硬件的设计文件统一存 [docs/schematics/](./docs/schematics/README.md)——IMU 板（ScrapMeta v0.3 的 `.eprj2` 真源工程 + 网表，钉 `main @ aa4c32d`）、HAT（5 页 PDF，图版本 V1.0；实物 2026-10-10 照片确认为 V1.2，目录已更名 `microduck-hat-v1.0-sch`）；微雪转接板与降压模块为成品模块无公开原理图，暂只记规格待补。

**banana_pcb 打板已下单（2026-10-09 用户确认），等板回来。** 到板后手顺：焊 U6068 插针 ×2（未购则先买）→ 打印 `banana_pcb_locker` → 拆电池焊接出线（线径按 3-5A 选）→ 万用表直流档核极性 → 断电机械试装（插针与电池触点配合、locker 保持力）→ 只带主控支路验证 5V。

### 由到货衍生的待办

- [ ] 万用表实测降压模块（[操作单](./docs/buck-module-test.md)）：**2026-10-10 空载扫描已完成**——选压桥 6V 档、实测稳压下限 ≈6.3V（压差 0.3V 跌落跟随，远好于丝印 7.2V）、2S 最差点 6.6V 时输出仍 6.00V，**2S 初判可用**；接口分工闭环（XT60 入 / PWR OUT 直通 / 3P VCC 稳压；"DC 母座"系照片误判，实物无此件）。现行候选不使用稳压口，取消改焊 5V；若仅作直通转接，仍须核验其直通路径及接头载流，空载结果不是整机验收
- [x] 确认 IMU 板是哪一版设计（2026-10-09 用户确认板①：ScrapMeta microduck-diy v0.3；2026-10-14 照片判别板②：jyg9 社区 GD32 成品版，见同专题补充节）
- [ ] IMU 板②（jyg9 GD32 版，免刷）台架验收：按 [docs/imu-gd32-bench-test.md](./docs/imu-gd32-bench-test.md)——断电核针序 → 可调电源 7.4V/0.2A 空板供电 → URT-2 接总线 → `flash/3-验收-imu200.bat` 全 PASS + 晃动验证。**验收通过则整机 IMU 优先用板②，板①刷机降级为备件任务**
- [ ] 按手顺完成 IMU 板①刷机（备件/练手，优先级低于板②验收）：购 SWD 调试器（推荐 DAPLink）→ J2 接线（⚠️ 实物 J2 未焊插座只有焊盘，2026-10-10 看实物标注图确认：焊 BM07B-SRSS-TB 座 + SH1.0 7P 线，或杜邦线直接焊盘）→ 双击 `flash/1-烧录-DAPLink.bat` → 断电重启 → `flash/3-验收-imu200.bat` 全 PASS（详见 [flash/README.md](./flash/README.md)）
- [x] 清点舵机（型号、数量、ID/零位状态）：**ID 部分 2026-10-17 完成**——15 颗逐颗初始化编号（10-14/20-24/30-34，选项与流程见当日条目），型号 HD-1910-C001；零位未完成，按[装配与 CAL 调研](./docs/references/assembly-check-20261017/research.md)逐关节确认基准、校准并在使能前对齐目标；另有一颗"嫌疑坏"（信号脚拖线）隔离未编号。未做整链复验，装机后整链扫描确认
- [ ] 清点打印件（版本、材料、缺件）——随本次机械组装一并登记
- [ ] 微雪转接板上机验证（对比飞线方案）
- [ ] 向板卡来源索取 HAT **V1.2** 原理图或改动说明（存档图为 V1.0；实物差异含 MCU 类器件——2026-10-11 实测丝印 **GD32F3xx**（兆易创新，F303 兼容），照片复核另有圆柱电容 10/50V——图物差异大，见 [docs/photos/](./docs/photos/README.md) HAT 小节）
- [ ] 舵机线 ↔ 板座连接器适配（2026-10-11 实物核对定案，完成远端「逐针核对」待办）：飞特 HD-1910 原线 **AMP2.0-3P（2.0 mm）**，与三块板全不配——HAT 与 imu_to_dxl 同为 JST EH 3P（2.5 mm）、微雪转接板为 5264-3P（2.5 mm，外壳与 EH 不同形）。**方案：台架过渡期用杜邦公母线**——公头针插进 AMP2.0 母壳端子孔、母头套板座针（2.54 兼容 2.5）；⚠️ 脚序须交叉（飞特线端 `1=Signal/2=Vcc/3=GND` ↔ 板座 `1=GND/2=+BATT/3=DATA`），上电前蜂鸣档逐根核对；仅限调 ID/零位/ping 验收，不带载（堵转 1.8A），接触无保持力需胶带固定。**整机前统一换 EH 压接头**（剪 AMP2.0 头 → 压 EH 端子胶壳，15 根一次改完，三板块全兼容）
- [ ] HAT V1.2 与手头主控/外壳的机械与电气适配核对（电气功能确认按 [docs/hat-v1.2-test.md](./docs/hat-v1.2-test.md) 操作单执行：断电通断核对 + 限流上电分步验证）
- [ ] banana_pcb 到板装配与取电验证（焊 U6068 ×2、locker 打印、核极性、断电试装、主控支路验证）

## 2026-10-09 参考库清理（提取 → 还原）

- `references/microduck-replica/调试记录.md`：此前会话把 10-09 到货记录（7 行）写进了上游作者的表格里。用户相关内容已转录到本文件上表；原文件还原为上游版（「手头有的」等小节本来就是上游作者 fanhao375 的库存记录，不是本项目的）。
- `references/microduck-build-tutorial/`：A 训练重建的库内修改（4 个改文件 + 51 个添加文件，清单见 [local-changes/README](./local-changes/README.md)）全部提取，目录还原为上游原样。A 训练的说明与验收记录不受影响：[docs/a-training.md](./docs/a-training.md)、[docs/a-training-validation.json](./docs/a-training-validation.json)。

## 供电架构定稿（2026-10-10）

基于电源板空载实测 + IMU 网表 + HAT 查证记录，整机供电拓扑定稿并建档：docs/power-architecture-v1.md。当天评审证伪其中两处前提（IMU LDO 上限实为 13.2V 非 5.5V；HAT 的 F1 在数据线而非舵机电源路），已修订为现行版 [docs/power-architecture-v2.md](./docs/power-architecture-v2.md)：IMU 直挂总线（混血线与改焊 5V 任务取消）、电源板降为可选转接件、F1 未定项关闭、新增全链无保险与 EH 座分流两个风险项。

## 主文档路线审计（2026-10-10）

逐份检查主要文档中「确定路线（2026-10-09 主参考 C 飞特）之前」的遗留信息，修复如下：

- **根 BOM.md 重写为 C 线现行清单**（核心件/供电充电/线材/结构件/安全边界，按供电架构 v2 口径：IMU 直挂总线、电源板可选、新增 5A 保险采购项）；原 A 线清单（2026-09-28，XL330 + OpenRB + Pi Zero）原样存档 [docs/bom-route-a-20260928.md](./docs/bom-route-a-20260928.md)，仅回退 A 线时使用——其供电安全研究（XL330 6.0V 上限、OpenRB 板级电流限制）仍有效。
- **README.md**：路线状态段更新（主线 = C，指向架构 v2）；「机器人概览」「复刻计划」两节加 A 线基线横幅（原文保留不删——A 训练资产仍有效）。
- **.goal/PROJECT_KNOWLEDGE.md**：IMU 版本行更正（"v1.0 待核"→已确认 v0.3）；「已安装环境与入口」节曾加旧机横幅（截至 2026-10-10 当时记录为无 WSL、旧训练环境不在该机；2026-10-15 已复查 WSL2 Ubuntu Running，旧环境/路径须逐项核对，见本页最新软件研究）。
- **power-architecture-v2.md** 两处残留 "实物 V1.1" 更正为 V1.2（与 PROGRESS/照片一致）。
- 检查过、无需改：docs/a-training.md、docs/b-training.md（明确的 A/B 线训练存档，属历史资产）；flash/、docs/photos/、PROGRESS 本体均为 C 线现行档。
- 审计移交用户的待确认项：① NP-F550 充电器是否已有（BOM 已列）② HAT V1.2 图纸索取（到货待办已列）。

## 方案方向（2026-10-09）

- **主参考 = microduck-community-kit（飞特路线）**：HD-1910-C001 + 官方 robotd 的飞特补丁（`firmware/v1/patches/`）+ imu_to_dxl 总线从站（ID 200，双协议）。与手头硬件（飞特舵机、IMU2DXL 板、微雪半双工转接板）直接对口。
- replica 作为机械/装配/电控采购资料来源；build-tutorial 保留 A 训练基线存档（已提取到 local-changes）与教程对照。
- community-kit 已知缺口，用前留意：
  1. `software/microduck_feetech/` 完整源码**未推送**（README 提及但 main 分支没有；补丁文件在，基线官方 `f0d934e`，但完整树比补丁新三处关键修复——删 `tcdrain`、`BURST_IDLE` 2→4ms、同步上游 10 提交）；
  2. 主控↔舵机总线的物理适配层未开源（三块板只覆盖取电/配电/IMU）——**已由手头 HAT 补上**：板上 74LVC 半双工驱动 + UART2（Radxa `ttyS2`）正是 robotd 飞特补丁期望的总线入口，见 [HAT 查证记录](./docs/references/microduck-hat-20261006/research.md)；
  3. 真机整定值只能参考不能照抄：增益默认 32（200 会自激振荡，5A/74°C）、关节方向实测 −1（与 XL330 相反）、电池满/空电压阈值需复测。

## 工程迁移

2026-10-09 工程从 `E:\Projects\duck-robot` 迁到 `C:\Projects\duck-robot`（全部文件时间戳为迁移当日，无法再据时间戳判断改动，版本核对一律以上游哈希为准）。历史文档/脚本里的 `/mnt/e/`、`E:/` 路径已失效；本次已修根 README 的 3 处链接与 `scripts/a-training.sh` 的 2 处路径，`local-changes/` 里的提取件（export_onnx.py 等）仍含旧路径，复用前需改。

**本机新装工具链（2026-10-09）**：Python 3.13（`%LOCALAPPDATA%\Programs\Python\Python313`，含 pyserial）、OpenOCD 0.12.0（工程内 `flash/tools/`）、嘉立创EDA专业版 3.2.149（`%LOCALAPPDATA%\Programs\lceda-pro`，可开 `.eprj2`）、Git for Windows 2.55（winget 安装于 `C:\Program Files\Git`；`~/.gitconfig` 里失效的本地代理已移除，可直连，user.name/email 已配好）。截至 2026-10-09 当时记录为无 WSL、旧训练环境不在该机；2026-10-15 已复查 WSL2 Ubuntu Running，当前工作区为 E 盘，旧训练环境是否仍在待查，见本页最新软件研究。

## 嘉立创开放平台 API 打通（2026-10-09）

- 应用 **microduck-replica**（AppID 631092845187391489）PCB 业务线 API 已开通；密钥与 RSA 脱敏密钥已配置到 `tools/jlc-order/jlc-order.toml`（gitignore）。
- 之前 doctor 401 的根因：示例配置里的 appid/密钥是**官方文档教学示例值**，示例路径 `/order/v1/createOrder` 也只是签名示例，真实接口路径完全不同。
- 真实路径从控制台→SDK下载的官方 Java SDK jar 提取，14 个已授权 PCB 接口全部对齐进 `api_spec.py` 并探活验证；14 份接口 PDF 文档已下载到 `tools/jlc-order/api-docs/`（gitignore）。
- **计价链路全通**：`python -m jlc_order pcb quote -p examples/banana_pcb.toml` 实测返回真实价格（banana_pcb 39.2×6.8mm 双层 5 片 ≈ **¥55.04**：喷镀 30.04 + 特价 20 + 税 5）。
- 关键报文事实：板长宽在 `stencilLength/stencilWidth` 且单位是 **cm**；层数=`stencilLayer`、数量=`stencilCounts`；计价无需文件。
- **下单未完**：`/pcb/order/create` 需 `pcbFileUrl`+`fileName`（平台无上传接口，文件需先有可访问 URL）+ RSA 加密的 `orderReceive` 收货信息；cli 的 order/quick 命令待实现，字段表见 `api-docs/创建订单接口.pdf`。
- 3D 打印有独立 API（`/3dp-open/order/uploadModelFile`/`submitOrder`，有上传接口），但需在控制台为应用加开 3DP 业务线。

## jlc-order 下单命令实现（2026-10-09 下午）

- 通读《创建订单接口》PDF 后实现完整下单：`pcb order` / `pcb quick`（打包校验→计价→确认→下单）已对齐真实报文，dry-run 全链路验证（含 JOP 签名）。
- 关键结论：官方示例收货信息**明文**提交（RSA 脱敏密钥用于解密响应，不加密请求）；`pcbFileUrl` 可为任意公网 URL（示例用网盘）；`advancePayment=false` 只建单不扣款（默认）。
- 下单信息存 `jlc-order.toml [order]` 段（gitignore）；查询/返单单号=`customerOrderId`（整数）+ `orderType`（examples 样板/batch 小批量）。
- 待用户侧两件事即可真实下单：① gerber zip 托管到公网 URL 填入 `[order].pcb_file_url`；② 填收货人/发票/快递信息。

## banana_pcb 首单 API 下单成功（2026-10-09 下午）

- **订单 customerOrderId 85073604**（生产单 86482706/Y2）：39.2×6.8mm 双层 1.6mm 5 片 FR-4 绿色无铅喷锡全部测试，顺丰电商标快寄付，**¥50.04 待支付**（状态 1=等待嘉立创审核，未自动扣款），去 jlc.com 订单页人工支付。
- 全自动链路首次跑通：KiCad gerber → 百度网盘（官方 MCP stdio 上传）→ 分享链接（SSE `file_sharelink_set`，30 天提取码 jlc8）→ `[order].pcb_file_url` → 计价 → `/pcb/order/create`。
- API 下单踩坑实录（均已写进代码注释/README）：
  1. `charFontColor`（丝印字符颜色）下单必填（计价可省）；
  2. 个人发票必须显式 `invoiceType="personal"`，否则默认 company 报「发票主体与类型不符」；
  3. **`expressType=JYM` API 下单被拒**（报笼统「提交订单错误」），换 `SF_DSBZ_JF` 即过——浪费 4 次尝试才定位；
  4. 同一 pcbFileUrl 短时间重复提交会报「存在重复文件」——解法是换文件名重新上传+新分享链接（`tools/baidu-pan-mcp/run_upload_share.py` + `share_link.py` 一分钟搞定）。
- 百度网盘 MCP 双服务器已配进 `~/.zcode/cli/config.json`（baidu-pan SSE + baidu-pan-upload stdio），个人 token 30 天有效（2026-11-08 前需重新授权）。

## 嘉立创开放平台上传能力调查（2026-10-09）

用户问「API 没有上传功能么」→ 逐一验证各业务 SDK（控制台 SDK下载 逐个提取路径常量）：
- **PCB（已开通 14 接口）**：无上传，下单只能 pcbFileUrl；审核失败重传也只在 jlc.com 网页（askGuest 通道）
- **SMT（已开通）**：54 个类全是 /smtOpenApi/ 元器件邮寄管理+查单，无上传
- **CNC（已开通）**：官方描述即"下载图纸、查单"，无上传
- **云ERP（未开通）**：/open/api/saas/erp/* 进销存单据，无关
- **3DP（审核中）**：唯一有上传的业务线（/3dp-open/order/uploadModelFile），3D 打印专用
- SDK 基础包有 UploadRequest 基类、SDK 文档演示过 UploadFileRequest(orderNo,file)，但无任何业务包实现；控制台自己的 /api/file/fileUpload 仅限控制台内用
- 结论：**PCB 下单文件上传不存在 API 通道**；pcbFileUrl 需"直接下载字节流"的直链（百度分享页→爬虫抓到网页→"压缩包损坏"）；后续自动下单需直链托管方案（GitHub release / 对象存储）
- 附：应用管理页的"已获得/申请中/可申请（86）"是静态标签非页签；业务线状态 SMT、CNC 已开通，3DP、元器件&MRO 审核中

## GitHub 直链实测（2026-10-09，结论：不可行）

- 仓库 duck-robot 已转公开，`raw.githubusercontent.com` 链接本机直连可下载且 md5 一致；
- 但 API 下单实测两种结果：`raw.githubusercontent.com` 域名 → 报「PCB文件资源路径无效」；`github.com/.../raw/...`（302 重定向式）→ 通过校验但 JLC 服务端**同步抓取超时**（客户端 30s/120s 两档均超时，未产生幽灵订单）——嘉立创履约侧网络到海外源基本不可达，「有海外业务」不等于国内工厂的爬虫有海外出口；
- 另确认：下单去重键=文件名+内容哈希（换 fileName 标签可绕「存在重复文件」）；
- 待选替代：Gitee raw 直链（需码云账号）/ 问客服 pcbFileUrl 支持形式 / jlc.com 网页上传（当单急救）。

## 全自动下单链路收官（2026-10-09 15:06）

- **Gitee 镜像方案成功**：duck-robot 已镜像到 gitee.com/yilv1982/duck-robot（双远程 origin=GitHub / gitee=Gitee，推送凭证已存 GCM）；gerber zip 的国内直链 = `https://gitee.com/yilv1982/duck-robot/raw/main/hardware/banana_pcb/production/banana_pcb.zip`（匿名下载 1 秒、md5 一致）。
- **订单 85078132 审核通过**（下单后 26 秒过审，"单片出货，数量:5片"）——JLC 爬虫从 Gitee 抓文件秒下（对比 GitHub 120s 超时）。¥50.04 待支付，19:30 前付款排当晚生产。
- 旧订单 85073604（百度网盘链接"压缩包损坏"那单）停留在审核询问状态，需在 jlc.com 网页取消。
- ** pcbFileUrl 最终结论**：用国内代码托管 raw 直链（Gitee）；网盘分享页（爬虫抓到网页）、海外源（GitHub 超时）都不可行。以后改版重下单流程：改 PCB → 导 gerber → commit+push 两边 → 更新 [order] 的 file_name（避开文件名+哈希去重）→ `pcb order --yes`。


## HAT V1.2 实测开始（2026-10-11）

按 [docs/hat-v1.2-test.md](./docs/hat-v1.2-test.md) 操作单执行，断电通断核对进行中。A1 量点标注图：`docs/photos/hat-v1.2-a1-pinout.jpg`（脚本 `scripts/annotate-hat-a1.py`）。

**A1/A2 已确认（万用表蜂鸣/电阻档，德力西 6000 位）**：

| 项 | 结果 |
|---|---|
| 舵机口针序（两白座，以用户实拍正面照方向） | **下=pin1 GND（与安装孔通✓）、中=pin2 +BATT（与 SERVOS 旁焊盘列第 3 盘直通✓）、上=pin3 DATA（排除法）**——与 V1.0 图一致 |
| pin1↔pin2 | OL 不通 ✓ |
| pin2↔pin3 | 电阻档：一向 OL，反向从 0 缓爬至 386kΩ = 电容充电曲线，非短路 ✓；二极管档单向 0.5V 压降（驱动芯片 ESD 结，正常） |
| SERVOS 旁两竖列焊盘 | 各列最下盘 = GND（与安装孔通）；疑为两舵机口的并联测试盘，一一对应关系待复核 |
| **+BATT 进板口（A2 收尾）** | 背面 8 盘组（用户实拍：40P 排母在上的朝向）：**第 3 排双盘 = +BATT（与 pin2 直通✓）、第 4 排双盘 = GND**；B1 电源线即接此处（红 3 排 / 黑 4 排）；第 1、2 排盘身份已测（2026-10-11 晚用户确认） |
| 上电前短路预检 | 第 3 排 ↔ 第 4 排电阻档复测无短路 ✓（2026-10-11 晚用户确认） |
| 第二座针序 + 两座 pin2 并联 | 复核一致、pin2↔pin2 直通 ✓（2026-10-11 晚用户确认） |
| **A3 排母针序（背面实拍，排母在照片上缘）** | **GND 规律 8/8 全中**：上排左起 4/6/11/14/18（pin34/30/20/14/6）+ 下排左起 1/8/16（pin39/25/9）均与安装孔通 → **pin1 在下排最右，针号从右往左递增，上排偶数脚、下排奇数脚**；关键脚：pin2/4(5V)=上排左起 20/19，pin6=上排 18，pin8/10(UART2)=上排 17/16。标注图 `docs/photos/hat-v1.2-header-pinout.jpg`。注：电感输出侧蜂鸣扫 5V 孔不响系 Q1 理想二极管断电关断所致（V1.0 图可解释），改 GND 反查法定针序 |

| A3 收尾（二极管/电阻档） | 电感输出端↔pin2：1.39V / 0.33V 双向压降（LM5050+Q1+BAT54 复合路径特征，非短路非断路，5V 链待 B2 上电终验）；pin8/pin10 对安装孔 OL ✓ |

| A4 F303（丝印 GD32F3xx，兆易创新 F303 兼容）粗查 | 蜂鸣档从 pin3、pin8、pin10 扫四边 48 脚全不响 → **MCU 不在舵机数据链上（旁观者）** ✓（2026-10-11 晚用户确认） |
| A5 超级电容 | 断电两端电压 ≈0V ✓（2026-10-11 晚用户确认） |

**A 段断电核对已全部通过**（2026-10-11 晚）。

**待续**：B 段限流上电——B1 电源 8.4V/0.3A 红接第 3 排盘、黑接第 4 排盘（接前拍照核对极性）→ B2 空板 5V 判定门（排母 pin2/4 = 5.0V±0.2，电流几十 mA）→ B3 pin3 空闲 ≈3.3V → B4 插 Radxa ssh → B5 单舵机 ping → B6 MCU 干扰静置排除。


## 2026-10-12 到货

| 物品 | 说明 / 待办 |
|---|---|
| **banana_pcb 板** | 嘉立创订单 85078132（5 片）到货。装配手顺（2026-10-09 已定）：焊 U6068 插针 ×2（已到货）→ 打印 `banana_pcb_locker` → 拆电池焊接出线（线径按 3-5A）→ 万用表直流档核极性 → 断电机械试装 → 只带主控支路验证 5V |
| **Radxa Zero 3W** | 到货（二手，板载 eMMC 含前任系统）。**2026-10-13 路线变更：放弃 TF 卡启动（eMMC 封存作废），改 USB maskrom 线刷 eMMC**——工具链 `tools/emmc-flash/`（RKDevTool v2.86/v2.96 + DriverAssitant v5.14 + loader `rk356x_spl_loader_ddr1056_v1.10.111.bin`，git 忽略），镜像 SHA512 已验；驱动经 pnputil 手动安装后 maskrom 连接正常（VID_2207&PID_350A）。刷写进行中：「下载Boot」两次 err=79 后重试已通；13:06–13:08 三次执行卡在 `switch into SPINOR failed`（判读：「强制按地址写」未勾，工具试图切到本板不存在的 SPINOR，官方流程要求勾选）。⚠️ eMMC 已被写入新 IDB 而系统镜像未写入，**现为半新半旧不可启动状态**，必须完成一次完整写入；并行会话记录称「烧录成功」但截至 13:08 磁盘日志无成功写入记录，**结果待用户确认**。详见 [eMMC 线刷记录](./docs/references/emmc-flash-radxa-zero3w-20261013/research.md) 与 [TF 卡烧录记录](./docs/references/sd-flash-radxa-zero3w-20261013/research.md)。烧成后首启前须拔掉 TF 卡（RK3566 启动顺序 TF 优先于 eMMC） |
| **U6068 香蕉头插针 ×2** | 到货。2.5mm 香蕉头 PCB 插针（banana_pcb 电池触点）——用户确认所称「香蕉插头」「电池座」均指此件，更正此前「台架电源接线耗材」误记及重复登记 |
| **DAPLink SWD 调试器** | 到货（用户确认）。IMU 刷机链路硬件齐：J2 焊接（杜邦直焊或 BM07B 座）→ `flash/1-烧录-DAPLink.bat` → 断电重启 → `flash/3-验收-imu200.bat` |
| **2S 电池（NP-F550）** | 到货（用户确认）。待登记：化学体系/串数/触点形式、BMS 能力 |
| **匹配充电器** | 到货（用户确认）。待核对输出规格与 NP-F550（2S 8.4V）匹配后登记 |

在途清单清零（2026-10-09 起在途四项全部到货）。

## 2026-10-16 到货

| 物品 | 说明 / 待办 |
|---|---|
| **EH 端子（簧片）+ 胶壳** | 到货（用户确认）。待核对：端子是否 SEH-001T-P0.6、胶壳是否 EHR 系（卖家常标「EH2.54」，实为 2.5mm 系；对板座 B3B-EH-A 空壳试插分辨）；压线钳是否同单到货。压接步骤与全黑线/交叉脚序纪律见 [EH 采购调研·压线操作](./docs/references/eh-crimp-purchase-20261012/research.md#到货与压线操作2026-10-16) |

采购缺口剩余：直流总开关/断电连接件；EH 端子/胶壳已到货（压线钳状态与型号核对待确认）。外置主保险暂非确定采购项，先查电池内置保护，见本页 2026-10-12 复核记录。
