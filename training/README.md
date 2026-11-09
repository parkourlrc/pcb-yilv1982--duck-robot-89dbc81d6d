# C 线自建 real2sim2real 学习工程

> **2026-11-09 训练档案与复训实施**：工作台新增任务/实验/运行档案、历史分级导入、67个参数与奖励字段目录、阶段配方、从零重训和接权重训练；物理与接口锁定。最小GPU验收scratch/续训/warm合计96转换通过，策略行为未验收；见[任务及验证记录](../docs/specs/20261109-训练档案与复训/spec.md)和[工作台使用说明](dashboard/README.md)。

> **训练流程强制要求（2026-11-09 用户指示）**：所有新训、续训、重训、调参、对照实验及包含训练更新的短跑/测速，均须走[已确认的训练流程](../docs/specs/20261105-自主训练平台/spec.md)，执行[项目规则第10条](../AGENTS.md#10-所有训练必须走训练流程2026-11-09-用户指示)。启动前明确任务、步骤、输入、配置、预算及验收标准；逐步验证并记录结果。已有有效确认和验证可复用，输入变化时返回受影响步骤。

> **2026-11-08 足部奖励四组百轮完成**：[完整结果、对照图与视频](../docs/references/自主训练平台/足部奖励百轮对照-20261107.md)。固定Kp25/Kd2及物理层，20mm组在2/3场景形成有效迈步，左右膝周期中位幅度约15.3°/10.8°；第三场静止，四组dev9均0/9，尚未解决稳定直走。训练/评估/视频全部结束，未追加种子复核；后续航向约束仅为待确认提案。

> **2026-11-07 Kd试验已停止**：按用户最新指示固定物理参数；四组Kd变化运行已保存退出，组合排队取消，alpha0.1/Kd2尚未启动。昨天与今天基线均为自选IdealPD，并未使用飞特官方完整BAM；[参数来源核对](../docs/references/自主训练平台/训练物理参数来源核对-20261107.md)区分已采用设计值、公开近似参数和本机标定。步幅仍未达标，原训练源未改。

> **2026-11-07 本机百轮基线完成**：现有 v2 冻结源码、RTX 5090 Laptop 单卡、4096 环境、64 步、seed 42 完成 100 更新，dev9 无跌倒但 0/9 行为通过，小摆幅仍在。新权重镜像 `training/logs/amplitude-baseline-20261107/`，WSL 完整运行 `/root/duck-training-runs/amplitude-20261107-baseline/`；[结果、50 fps 视频及数据](../docs/references/自主训练平台/本机百轮步幅基线-20261107.md)。训练实现未改，后续调参方案见[步幅优化 spec](../docs/specs/20261107-步幅参数优化/spec.md)。下方“第二轮未开始”仅描述 11-06 当时状态。

> **2026-11-07 本机环境登记**：RTX 5090 Laptop 24 GB / Ubuntu-24.04 WSL2，Python 3.12.3、torch 2.13.0+cu129、mjlab 1.3.0；GPU 仿真与小规模 PPO 更新通过。Windows 工作台已安装，local 节点与任务可用；运行 `powershell -File training/start-dashboard.ps1`，访问 `http://127.0.0.1:8766`。解释器、依赖修复、换行修复、启动及原始证据见[本机训练环境](../docs/references/本机训练环境/research.md)。下面 RTX 4080 / CUDA 13.0 为另一机器的历史记录，不适用于本机。

> **第⑤步网页回放外观来源（2026-11-06）**：用户指定Studio模型，不用MuJoCo简模。已按部署固定提交恢复[模型及加载源码](../software/studio/model-source-2026103101/README.md)，来源哈希已核验，可进行本地适配；当前板侧是否有额外修改未重新在线比对，不阻塞设计。见[需求](../docs/specs/20261106-训练可视化工具/spec.md)与[来源记录](../docs/specs/20261106-训练可视化工具/studio-model-source.md)。

> **2026-11-06 第⑤步训练可视化工具验收完成**：[修改方案](../docs/specs/20261106-训练可视化工具/implementation-plan.md)已实现，使用[训练工作台入口](dashboard/README.md)，默认8766。[实测] 三模式新建/停止/恢复/预算退出合计576转换通过；旧模型23秒回放、四窗、刷新接回及关闭释放通过；重启后983帧历史曲线恢复、Windows/WSL/Spark资源卡及WSL持久JSONL通过。结果及四截图见[最终验收](../docs/specs/20261106-训练可视化工具/checks/final-browser-check.json)与[实施记录](../docs/specs/20261106-训练可视化工具/implementation-record.md)。这是工具验收，不宣称策略行为达标；未提交。

> **2026-11-06 失败诊断完成**：动作分布与确定性输出越界证据、两段回放和下一版稳定化建议见[诊断记录](../docs/specs/20261105-原地转圈策略/step5-diagnosis.md)。训练实现未改，第二轮未开始；建议参数和预算尚待用户确认。

> **2026-11-06 第⑤步首轮执行结束，行为未达标**：双Spark完成1000更新、262144000转换后预算耗尽正常退出；10次dev9均0/9，仍阶段一，未进入转向或full96。详见[第⑤步记录](../docs/specs/20261105-原地转圈策略/step5-training-run.md)。没有自动重训或增加预算；下方第④步“未开始”为历史状态。模型未部署。

> **2026-11-06 第④步完成**：已按确认参数实现双Spark（spark1＋spark2）、全局4096环境、rollout64、两阶段合计1000更新的训练入口、课程、评估、预算和保存恢复，见[实施记录](../docs/specs/20261105-原地转圈策略/step4-implementation.md)。本地必要检查、最终双Spark64/4096环境2＋1更新与完整恢复通过，源码SHA一致、独立审查通过。第⑤步正式训练未开始，策略行为尚未达标。后文64环境/2000轮仅为历史预算对照。

> **模型清单：** 外部候选与自训产物的来源、哈希和验证状态见 [MODELS.md](MODELS.md)。

> **2026-10-31 模型库存补充**：用户确认硬件完成，工程已有策略及真机候选见[模型盘点](../docs/references/飞特策略模型上机核对/research.md)。本目录 `logs/` 另存 10-24 下载的外部 HD1910 包（6 个普通足部动作、4 个滑轮动作）；它们不是下文自建训练的产物。自建 `model_9999.pt` 仍在，历史 CPU/SB3 `checkpoints/` 当前工作区未找到；本轮未运行策略或连接真机。

> **同日后续部署**：六个普通足部模型已复制至 `radxa-zero3:/home/radxa/duck-policies/hd1910-20261031/`，SHA 6/6 一致。Studio/Python 3.13/robotd 已安装，v0.3 单播补丁已在真机只读运行（1500 周期、1497 成功、3 次通信失败）；六模型随后已导入 Studio 并通过板上无电机前向预检，按用户指示接入配套动作参数和参考标定数值；本机标定匹配未实测、动作保持关闭。自建训练产物的下述使用边界不变；详情见同一专题。

本工程沿用 2026-10-15 用户确认的“从零学习”路线：**借鉴公开物理参数（质量、惯量、安装位形等），物理模型、任务环境、训练入口由本项目自行编写**；不复制上游任务、训练脚本或策略权重。**2026-10-21 用户授权显示层按来源许可复用上游精细网格、材质及挂接变换**，替代此前绝对“不加载上游网格”的限制；显示层不参与碰撞，不改变质量/惯量、关节或策略接口。MuJoCo、mjlab、stable-baselines3 与 rsl_rl 作为通用基础工具使用。

上游数值的全部溯源见[物理参数表](../docs/references/动作训练软件研究/physical-params.md)；路线与阶段计划见[训练软件研究](../docs/references/动作训练软件研究/research.md)第 6 节。

**MuJoCo 查看工具（已跑通）**：[2026-10-21 实施与验收记录](../docs/references/物理仿真查看工具优化/research.md)。WSL mjlab 单环境回放已接入精细显示层和现有 viser/native viewer；20 s 本机精细模型回放测得约 **0.999× 实时率、49.95 Hz 控制、59.90 Hz 后端场景提交**。浏览器主要操作已检查，浏览器 FPS 未测；旧 CPU/SB3 入口另已修复启动和等待问题。

**工具选择**：本次采用 mjlab 现有 viser/native 回放能力。B 线 [servo-web 整机 3D 网页调试台](../references/microduck-replica/tools/servo-web/README.md)保留为舵机/IMU 工具参考；其 `--fake` 无重力，不是本次 MuJoCo 回放入口，也未在本次接入实物。

## 目录

**当前联合训练入口**：优先使用[网页工作台](dashboard/README.md)冻结任务与源码。从冻结源码的本目录也可运行`python -m mjlab_duck.train_locomotion --config CONFIG.json --output RUN_DIR --experiment-dir EXP_DIR`，支持单rank或双节点各一rank；每次使用新`--output`，续训显式指定`--resume-manifest`并复用原账本及合同。课程决定待执行的中间`evaluated`点只供推理，续训选择final/stage2兼容点。具体协议见[运行时协议](dashboard/runtime_protocol.md)，验收状态见上述实施记录。

**历史短测速证据**：独立`scripts/benchmark_locomotion.py`完成RTX4080、单Spark及双Spark同全局4096样本的2预热＋3计时短跑，见[比较记录](../docs/references/自主训练平台/Spark与本地训练比较.md)。后续[256/1024/4096环境扫描](../docs/specs/20261105-原地转圈策略/benchmark-scale-runbook.md)采用2预热＋5计时，单Spark补跑加载双机相同env文件；4096下双/单吞吐约1.629×。测速不保存正式策略，不替代新入口恢复检查或行为验收。

**2026-11-05 联合环境及后续扩展**：用户确认第③步方案后新增 `mjlab_duck/locomotion_env.py`、`locomotion_cfg.py`，保持61维actor/critic和14维关节目标，覆盖只前进、减速、弧线、原地转和停止。最短检查入口 `scripts/check_locomotion_env.py --output <结果.json>`（使用既有WSL `.venv-wsl/bin/python`）；见[方案](../docs/specs/20261105-原地转圈策略/environment-plan.md)和[第③步结构检查](../docs/specs/20261105-原地转圈策略/environment-runtime-check.json)。第④步新增版本化课程、逐子步验收统计和reset前终态快照；GPU回归通过不代表策略动作达标。正式入口直接构建runner；未导出或部署。每步`extras["locomotion"]`提供命令、实际速度、固定锚点、失败与奖励分项。

| 路径 | 内容 |
|---|---|
| `dashboard/` / `start-dashboard.ps1` | 第⑤步网页工作台、独立控制服务与Windows启动器；实际验收见工作台README |
| `tasks/locomotion.json` / `runtime_versions/locomotion-v1/` | 现行任务描述及来源SHA；旧运行兼容推理冻结来源 |
| `params/` | 机器可读参数表（由 `scripts/extract_public_params.py` 只读提取生成） |
| `scripts/extract_public_params.py` | 从参考库只读解析上游公开参数（含自写四元数级联，已与 MuJoCo 内核对拍一致，误差 <1e-6） |
| `scripts/build_model_v0.py` | 从参数表生成 `models/duck_v0.xml`（几何为自建胶囊/盒，端点=关节中心） |
| `models/duck_v0.xml` | 自建 v0 模型（生成物，勿手改——改脚本再生成） |
| `scripts/build_visual_model.py` / `models/duck_visual.xml` | 在自建骨架上挂接精细外观；地面 group 0、70 个显示 geom 为 group 2、15 个原碰撞体为 group 3 |
| `models/visual/` | 38 个 STL 与材质/变换清单；来源、许可和 SHA-256 见 [SOURCE.md](models/visual/SOURCE.md)、[manifest.json](models/visual/manifest.json) |
| `play_mujoco.py` / `play-mujoco.ps1` | WSL mjlab 单环境回放与 Windows 启动入口，默认本地 viser、可选 native |
| `mjlab_duck/playback.py` / `mjlab_duck/viewer.py` | 回放配置、性能记录与界面扩展；训练入口仍使用原 `duck_v0.xml` |
| `duckstand/env.py` | 自编 gymnasium 环境：当前为 v0.8 速度命令与相位任务；历史站立策略接口不同 |
| `train.py` / `play.py` / `interact.py` | 旧 CPU/SB3 训练与回放；回放必须显式指定兼容的 SB3 checkpoint |

## 历史回放环境（RTX 4080，2026-10-21 现场核查）

WSL Python 3.12.3、mjlab 1.3.0、MuJoCo 3.10.0、torch 2.14.1+cu130、Viser 1.1.1、rsl-rl 5.0.1；RTX 4080 的 CUDA 可用。默认 checkpoint 固定为 `training/logs/rsl_rl/duck_walk/2026-10-19_15-02-25/model_9999.pt`，不自动挑选其他策略；它保留在本机日志目录，不随版本库分发。历史 SB3 `.zip` 不用于此入口。

## 打开当前 MuJoCo 工作台

在仓库根目录的 PowerShell 运行：

```powershell
powershell.exe -File .\training\play-mujoco.ps1
```

打开终端打印的地址，默认 [http://127.0.0.1:8080](http://127.0.0.1:8080)。启动器使用已有 `training/.venv-wsl`，仅绑定本机地址；环境在其他 WSL 发行版时可加 `-Distro`。第一次启动会初始化模型与 GPU 内核，运行计时从初始化完成后开始。WSL 内也可在 `training/` 下运行 `.venv-wsl/bin/python play_mujoco.py`。

| PowerShell 参数 | Python 参数 | 用途 |
|---|---|---|
| `-Viewer native` | `--viewer native` | 原生实验入口；本机 WSLg 图形探针使用 llvmpipe 软件渲染，回放仅约 0.10–0.125×，日常使用默认 viser |
| `-Simple` | `--simple` | 切回原始碰撞简模，便于对照 |
| `-Checkpoint <路径>` | `--checkpoint <路径>` | 指定与本项目 mjlab 任务兼容的 `.pt`；不改变观测/动作契约 |
| `-Velocity 0.1` | `--velocity 0.1` | 初始前后速度，范围 −0.2 至 0.2 m/s；默认 0 |
| `-Duration 20` | `--duration 20` | 初始化后运行指定墙钟秒数并退出，含暂停时间 |
| `-Metrics <路径>` | `--metrics <路径>` | 退出时保存后端计时 JSON；不是录屏或浏览器 FPS |
| `-Port 8081` | `--port 8081` | 改本地网页端口，以实际打印地址为准 |

PowerShell 的 checkpoint/metrics 路径支持从当前工作目录解析的 Windows 相对/绝对路径，也支持以 `/` 开头的 WSL 路径。示例：

```powershell
powershell.exe -File .\training\play-mujoco.ps1 -Duration 20 -Metrics .\training\logs\viewer-metrics.json
```

网页将常用操作放在“播放与速度”“视角与模型”：暂停/继续、单步（运行时先暂停）、重置、退出，0.5×/1×/2×倍率，前后速度及归零，斜前/正面/侧面/俯视，跟随开关及“仅显示碰撞体”（隐藏外壳）。“实时状态”显示机身 XYZ、横滚/俯仰/偏航与实际速度；高级 mjlab 诊断默认折叠。鼠标拖动旋转相机、滚轮缩放；网页“退出”或终端 Ctrl+C 关闭回放。

精细模型使用 Pollen Robotics 的上游外观（38 个 STL，20.59 MiB），包含 XL330、NP-F970、Pi Zero 等原版部件，**不代表本机 HD-1910-C001 的精确外壳/装配 CAD**；模型许可与署名见 [SOURCE.md](models/visual/SOURCE.md)。物理属性对照及 100 步轨迹一致性已通过；只改善显示，没有重训或接入实物。

本轮没有实现 Viser 鼠标施力、录制、专门的关节检查器或显示插值，也没有测量浏览器 FPS 或重新评价策略的站立/步行质量。画面忠实显示仿真产生的前倾/位移；后端状态提交 Hz 不能代替浏览器 FPS。原生窗口低速已复现，首次启动器退出码 1 在后续直接捕获 Python 子进程时未复现，未改系统图形设置；详细证据见[实施记录](../docs/references/物理仿真查看工具优化/research.md)与 [native 排查](../docs/references/物理仿真查看工具优化/native-diagnostics.md)。

## 旧 CPU/SB3 环境

```bash
cd training
uv venv .venv --python 3.13
uv pip install mujoco gymnasium stable-baselines3 torch   # Windows pypi torch 为 CPU 版
```

## 旧 CPU/SB3 用法

```bash
python scripts/extract_public_params.py   # 只读提取参数（参数库变动时重跑）
python scripts/build_model_v0.py          # 重新生成模型
.venv/Scripts/python.exe train.py --steps 1000000 --envs 8  # 当前49维任务的新训练，不是旧站立任务
.venv/Scripts/python.exe play.py path/to/current_sb3_checkpoint.zip
.venv/Scripts/python.exe interact.py path/to/current_sb3_checkpoint.zip
```

**checkpoint 兼容性**：当前 49 维环境不能直接回放或续训历史 45 维站立、47 维行走策略。`play.py`、`interact.py` 已移除不兼容的旧默认文件，要求显式路径，并在开窗前检查观测/动作形状；mjlab checkpoint 提示改用 `play_mujoco.py`。维数匹配仍不代表观测语义、scale、EMA 和奖励一致；旧存档缺完整环境快照。本轮未运行上述 CPU 训练/回放命令。

**推扰（v0.3 起加入）**：`DuckStandEnv` 默认每回合随机对躯干施加 1–3 次水平脉冲力（1–4 N × 0.2–0.4 s，首次 ≥1 s）；此分布固定，尚非由易到难的课程。`env.push_enabled=False` 可关闭（`interact.py` 已默认关闭以免覆写手推的力）；`info["push_force"]` 暴露当前力幅。历史初标定的恒零 2N=62%、3N=12% 来自 8 方向；正式 `eval_push.py` 为 5 时刻×4 方向、全 seed=0 的 20 个 3N 场景，历史恒零汇总为 50%，两组不能直接对比。随机推扰满额 35% 也只是另一条件下的历史汇总。

**旧 CPU 交互工具**（`interact.py`）：在策略/环境契约匹配后，可在 viewer 窗口**双击身体选中 → Ctrl+左键拖动**手工施加外力；摔倒 1s 自动重置，等待期间继续同步窗口。两入口按绝对 deadline 等待，过度落后时重锚时钟，不积压追帧或改变物理步；`play.py` 在检查窗口前显式创建 viewer。历史推扰记录未在本轮复验；忽略地面接触的冲量换算不能当作机身实际速度。

## CPU/SB3 当前接口（2026-10-19，源码基线 bf9a977；仅仿真）

- **观测 49 维**：机体系重力方向(3) + 相对 HOME 关节角(14, rad) + 关节速度(14, rad/s) + 动作状态(14) + `[vx_cmd, vx_actual]`(2) + `[sin(phase), cos(phase)]`(2)。动作状态因 `step()` 更新顺序晚一拍；机身角速度与侧向速度仍未观测。
- **动作 14 维** ∈ [-1,1]：先 EMA（α=0.25），再 `q_target = HOME + 0.5 × filtered_action`；一阶电机模型输出 motor 力矩。当前错误地用 motor `ctrlrange=±0.94 N·m` 裁剪目标角 rad，尚未修为关节角限位；不能宣称此接口已经正确或可部署。
- **关节顺序**（上游执行器声明序）：`left_hip_yaw, left_hip_roll, left_hip_pitch, left_knee, left_ankle, neck_pitch, head_pitch, head_yaw, head_roll, right_hip_yaw, right_hip_roll, right_hip_pitch, right_knee, right_ankle`。
- 控制周期 50 Hz（timestep 0.002 × decimation 10）；回合 10 s。
- 当前奖励：upright=1、height=1、joint_home=0.1、action_rate=−0.5、action_mag=−0.01、vel_track=4、feet_air=1、phase_foot=2、alive=0.25；`action_rate` 实际比较当前 raw action 与上一 filtered action。终止：重力水平分量范数 >0.9 或躯干高度 <0.6×HOME。
- 历史 v0.3c 站立是 45 维、scale=0.1；v0.6/v0.7 为 47 维，v0.8 起 49 维。当前 PPO 新建策略为普通 MLP `[128,128]`、`log_std_init=-1.0`，没有观测历史；旧站立 checkpoint 的初始化字段为 −1.9，不能混用说明。

## 自建与借鉴边界（v0）

| 借鉴数值（有溯源） | 自建内容 |
|---|---|
| 连杆质量/质心/惯量（Pollen CAD，XL330 版） | 胶囊/盒简化几何及尺寸 |
| 关节安装 pos/quat/axis/限位（同 CAD） | 执行器增益（历史 v0 的 kp=25/kv=2、当前电压环 KV=200 自选）、场景、地面 |
| HOME 站姿（上游 STAND2） | 观测/奖励/终止/重置设计 |
| HD-1910 BAM 电机参数（kt/R/armature/摩擦）、速度/力矩上限 | 执行器固件电压环增益 KV（自选）、训练入口与超参 |
| 脚底碰撞体 HOME 世界位形与 AABB 尺寸（上游 mesh 对照导出） | 自碰撞 exclude 集合、IMU site 之外的 site/camera |

## 当前状态与已知差距

- **2026-10-19 失败复核**：[原因分析与证据](../docs/references/动作训练软件研究/failure-analysis-20261019.md)。优先候选为机身速度观测缺失、EMA 状态晚一拍、raw/filtered 混合惩罚、动作尺度/滤波同时变更与缺少课程；因果贡献尚未单项验证。撤回“物理不可达、脚被钉住、无 EMA 必败、架构穷尽、必须数周或 MJX”的旧定论。本轮只做静态核查和文档勘误，未修执行逻辑或重训。
- **站立推扰历史结果**：v0.3c 的 3N×0.3s 满额率 50%=恒零基线，原 ≥80% 目标未达；响应 11.4×、4N 25% vs 0%、无扰 10/10 与每步 |Δa|=0.0041 都是缺逐场原始数据的历史汇总，不能作为普遍恢复已通过的证明。v0.2.2 的无扰 10/10、3 倍初始扰动 5/5、|Δa|=0.000 同属历史记录。
- **v0.4/v0.4b、v0.9 崩溃证据**：现存 checkpoint 末 100 训练回合平均长度分别为 63.95/37.85/69.62 控制步，满 500 步均 0/100；这支持各次训练末段失败，不是新评估，也不能推广到所有无 EMA 配置。v0.4/v0.5 实验环境未完整存档。
- **v0.8/v0.9 日期改为 2026-10-19**：checkpoint 时间和提交时间一致，旧 10-17 错标撤回。v0.8 修命令并同时加相位，不是单项对照；历史 100% 存活是无扰动速度档结果，3N 仅 10–15%，不能称推扰全档稳定。当前环境沿用 v0.8 配置；49 维环境 reset 未重置相位，`eval_walk.py` 改命令未更新首步观测，均待修。
- **历史记录完整性**：2026-10-19 元数据曾记录 23 个 final（含 2 个 smoke），21 个非 smoke 的 `num_timesteps` 合计 107,311,104；该合计不是完整历史训练总量。2026-10-31 当前工作区未找到 `checkpoints/`，不能视为仍可直接加载。旧“19 轮约 1.35 亿步”无法复核；当时 checkpoint 没有环境/模型/父 checkpoint/Git SHA 快照，训练 seed 均为 null。详见[元数据](../docs/references/动作训练软件研究/checkpoint-metadata-20261019.json)。
- 下一步建议：先冻结可重建的策略/环境契约，修接口问题，再在同场景做小规模单项对照与渐进推扰课程；不直接用堆步数或改 MJX 代替定位。长期步骤见 research.md 6.2 十阶段。
- 模型层已知差距：质量惯量为 XL330 版 CAD 值（上机前须实测替换）；静置有轻微接触抖动。

## 边界声明

- 本工程产物（模型/策略/checkpoint）仅用于仿真学习，**不接入 Radxa、不驱动实物**；上机须满足 research.md 6.2 第 9 步的防烧板与支撑前提。
- `checkpoints/`、`.venv/` 不入版本库（见 `.gitignore`）。
