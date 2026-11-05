# MuJoCo 实时查看工具优化：实施记录与原方案

日期：2026-10-21。状态：**本轮实现已跑通；本机精细回放、浏览器主要操作及模型物理一致性已验证，浏览器 FPS 未测**。原计划中的全部功能并未一次实现，未完成范围见下。

## 当前实施记录（现行）

采用本项目 mjlab 任务和已训练 checkpoint，以现有 viser/native viewer 为基础完善单环境回放；显示层复用来源明确的精细网格，物理模型、任务、14 维动作/49 维观测继续遵守本项目契约。该决定替代方案阶段“显示网格仅待评估、工具尚未实施”的状态。

| 分片 | 交付范围 | 当前状态 |
|---|---|---|
| A 回放与界面 | [play_mujoco.py](../../../training/play_mujoco.py)、[play-mujoco.ps1](../../../training/play-mujoco.ps1)、[playback.py](../../../training/mjlab_duck/playback.py)、[viewer.py](../../../training/mjlab_duck/viewer.py)；WSL mjlab、单环境，viser 默认 `127.0.0.1:8080`，native 实验入口；提供 `--simple`、`--checkpoint`、`--duration`、`--metrics` 等 | 已实现并完成默认 viser 的 20 s 精细回放与浏览器交互；native 低速已复现，首次退出异常未复现，保留为实验入口 |
| B 精细显示 | [build_visual_model.py](../../../training/scripts/build_visual_model.py)、[duck_visual.xml](../../../training/models/duck_visual.xml) 与 [来源清单](../../../training/models/visual/SOURCE.md)；70 个 visual、38 个 STL（20.59 MiB），地面/显示/15 个原碰撞体分别 group 0/2/3 | 已生成；物理数组、碰撞属性与 100 步轨迹对照通过；四面板预览已打开核看 |
| C 旧 CPU 入口 | [play.py](../../../training/play.py)、[interact.py](../../../training/interact.py)、[env.py](../../../training/duckstand/env.py) 的显示路径 | 已修：先创建 viewer、模块级控制频率、绝对 deadline、摔倒非阻塞等待、显式 checkpoint 和形状检查、退出清理、`rgb_array` 导入遮蔽；AST 与 diff 检查通过，独立代码审查通过；未运行 CPU GUI |
| D 文档 | 本专题、项目与训练 README、AGENTS、PROGRESS | 完成：已同步实现范围、来源边界、实际 CLI、运行数据及最终图片核看记录 |
| R 独立审查 | 回放调度、模型契约、许可/来源与使用说明 | 最终通过：PowerShell 相对路径、FPS 误标和 mesh 可见性同步均已修；Reviewer 另打开最终碰撞截图确认，核心交付无阻塞项；native 限制保留 |

### 现场环境与固定策略

主会话于 2026-10-21 现场核查并运行：WSL Python **3.12.3**、mjlab **1.3.0**、MuJoCo **3.10.0**、torch **2.14.1+cu130**、Viser **1.1.1**、rsl-rl **5.0.1**；RTX 4080 的 CUDA 可用。默认策略固定为 `training/logs/rsl_rl/duck_walk/2026-10-19_15-02-25/model_9999.pt`，不自动挑选其他 checkpoint。它是本机产物，不随版本库分发。该环境已完成本轮运行，仍不能倒推用户此前卡顿时使用了同一入口。

### 启动与交互

在仓库根目录运行 `powershell.exe -File .\training\play-mujoco.ps1`，打开实际打印地址（默认 [http://127.0.0.1:8080](http://127.0.0.1:8080)）。`-Simple` 切简模，`-Viewer native` 切原生窗口；`-Duration 20 -Metrics .\training\logs\viewer-metrics.json` 可保存一次初始化完成后的 20 s 后端计时。WSL 内在 `training/` 运行 `.venv-wsl/bin/python play_mujoco.py`；完整参数及路径说明见 [training/README](../../../training/README.md)。Windows 启动脚本为 UTF-8 with BOM。

viser 已提供暂停/继续、单步、重置、退出，0.5×/1×/2×，前后速度 −0.2 至 0.2 m/s 及归零，四个相机预设、跟随/世界视角、“仅显示碰撞体”、机身 XYZ 与姿态显示。碰撞模式隐藏 group 2 外壳、显示 group 3，避免壳内碰撞体被遮挡。高级 mjlab 诊断折叠收纳；单步在运行时先暂停再前进一个控制周期。控制仍为 50 Hz（2 ms ×10），状态显示以 60 Hz 调度；场景任务最多 1 个在途，忙时跳过显示提交，仿真与场景读写共用锁。

### 资产与运行边界

2026-10-21 用户明确接受显示资产复用：仅取 mesh、材质和挂接变换；原绝对“不加载上游网格”的限制撤下。38 个 STL 原样复制，70 个显示 geom 挂在自建骨架，未增加 body/joint；原 `duck_v0.xml` 和训练默认模型保留。显示版仅另加光照，geom 为 `contype=conaffinity=0`、`density=mass=0`，不参与碰撞或质量/惯量计算。

作者为 Pollen Robotics；来源固定快照、实际文件 SHA-256、材质和挂接变换见 [SOURCE.md](../../../training/models/visual/SOURCE.md) 与 [manifest.json](../../../training/models/visual/manifest.json)。上游原文为 CC BY-SA-NC、未单独注明版本，本地参考声明按 CC BY-NC-SA 4.0 保留；模型许可不继承代码的 Apache-2.0。外观包含 XL330、NP-F970、Pi Zero 等上游部件，**不是本机 C 线 HD-1910-C001 的精确 CAD**；嘴保持固定视觉节点，未增加第 15 个策略关节。

### 本机验证结果与原始数据

| 核查 | 条件与结果 | 证据 |
|---|---|---|
| 单环境精细回放 | PowerShell → WSL，RTX 4080，固定策略，1×，初始化后约 20 s；999 控制步、1198 次场景完成；实时率 **0.998991×**，控制 **49.94956 Hz**，后端场景完成 **59.89947 Hz**；在途任务最大 1、繁忙跳过提交 2 次、无错误 | [playback-metrics.json](playback-metrics.json) |
| 正常回放耗时 | 控制主机耗时 p50/p95/max = 9.985/13.512/18.123 ms；场景完成间隔 p50/p95/max = 17.985/22.365/31.002 ms。控制耗时含推理/步进主机部分，不是独立 GPU kernel 时间 | 同上；`browser_fps=null` |
| 网页交互 | 现有 Chrome **153.0.8010.53 headless**；暂停后姿态稳定，重置回 HOME，暂停/运行时单步、四相机、跟随/世界、0.5×/1×/2×、速度调节/归零与退出均实际操作；速度命令跨 reset 保持 **0.05 → 0.05 m/s**。无页面错误；最终截图已确认纯碰撞/精细外观真正互切 | [browser-validation.json](browser-validation.json)、[interaction-metrics.json](interaction-metrics.json)；主会话与独立 Reviewer 核看最终碰撞图 |
| 显示不改物理 | Windows Python 3.13.12、MuJoCo **3.16.0**：编译后的质量/惯量、关节、执行器、原碰撞属性和物理选项一致；初始 qacc 及 100 步 qpos/qvel 对照最大误差为 **0**；WSL MuJoCo **3.10.0** 另已实际编译并成功回放 | [visual-validation.json](visual-validation.json)；Windows 对照结果不冒称在 WSL 重做了同一整套数组对照 |
| 原生 viewer 首次运行 | 约 3.17 s 仅 16 控制步、10 次 sync，约 0.101×、5.05 Hz；PowerShell 退出码 1，而 Python 报告 `error=null` | [native-metrics.json](native-metrics.json) |
| 原生针对性复核 | GLFW context 的 renderer 为 `llvmpipe (LLVM 20.1.2, 256 bits)`；开启 faulthandler 后约 3.203 s、20 控制步、11 次 sync、0.12488×，Python 子进程退出码 0。低速复现，首次退出异常未复现，未证明软件渲染是所有低速的唯一原因 | [native-diagnostics.md](native-diagnostics.md)、[环境/进程证据](native-diagnostics.json)、[复核运行计时](native-diagnostic-metrics.json)、[日志](native-diagnostic.log) |

交互运行中含暂停与倍率改变，`interaction-metrics.json` 的汇总实时率、长提交间隔不能作为稳定 1×性能数据；稳定回放以 `playback-metrics.json` 为准。第一版浏览器脚本未捕获速度字段，后来补测取得 `speed_before_reset=0.05`、`speed_after_reset=0.05` 与 `speed_retained_across_reset=true`，已动态确认重置保留手动速度命令。

### 图片归档

以下均为 **2026-10-21 本机生成**的仿真截图/渲染，非实物照片，不登记为硬件实测；核看状态见表，不覆盖上游原图。

| 文件 | 来源、用途与状态 |
|---|---|
| [viewer-browser.png](viewer-browser.png) | 本机 Chrome 153 headless 实际 viser 页面；最终修复后重置、暂停、速度为 0，取消碰撞模式后恢复完整精细模型；主会话已打开确认姿态一致、无裁切 |
| [viewer-collisions.png](viewer-collisions.png) | 同一网页勾选“仅显示碰撞体”后的最终截图；只有盒/胶囊，精细外壳隐藏，复选框与真实画面一致；主会话及独立 Reviewer 均已打开核看通过 |
| [model-preview.png](model-preview.png) | B 分片用本机 MuJoCo 生成四面板预览；照明增强后重新渲染并打开核对，显示外观及碰撞对照 |

### 失败、修正与本轮未完成范围

- 浏览器验收最初遇到 Playwright 默认 bundled headless executable 缺失；随后使用机器已有的 Chrome 153 完成页面验证，没有为此安装系统软件。
- 独立审查修正 PowerShell 相对 checkpoint/metrics 路径处理，并把原先容易混淆的 FPS 标签改为状态同步/提交 Hz，渲染 FPS 明确“未测量”。这些修正已进入实际运行入口。
- 最终截图复核曾发现“仅显示碰撞体”复选框变化，但场景 mesh 可见性未跟随。原因是仅 `refresh_visualization()` 不会同步 mesh handle 的 `visible`；现已在 setup 和切换回调按依赖的 `_apply_visualization_change` 路径调用 `_sync_visibilities()`，保留锁及 atomic 更新。重启后截图确认纯碰撞/精细外观互切，主会话和独立 Reviewer 均通过；没有只凭控件状态判成功。
- native 在本机未通过实时回放验收，CLI/启动器已标实验入口，日常默认使用 viser；未安装驱动或调整 WSLg/Windows 图形配置。CUDA 可用不等于原生图形窗口使用 RTX 4080。
- **尚未实现** Viser 鼠标推扰、录制、专门关节检查器和显示插值；原第 4/6 节中的这些内容仍是后续目标。原生 viewer 的内置施力能力未在本轮做完整交互验收。
- **尚未测量**浏览器屏幕 FPS；后端约 60 Hz 不保证显示端每秒呈现 60 帧。没有保留用户最初卡顿版本的同场景时序，因此不能给出“提速几倍”或将最初卡顿唯一归因为采样。
- 动画中的姿态来自仿真本体：交互记录曾显示 pitch **+39.9°**、z **0.097 m**，重置后为 pitch **0°**、z **0.118 m**。运行中的前倾不能靠改显示伪装为策略更稳；本轮未重新评价站立/步行质量。
- 本轮未重训、未接入/驱动实物，未修改只读参考库或环境依赖；外观不代表物理参数已与本机对齐。2026-10-21 实现验收结束时未提交；后续版本同步以 Git 记录为准。

---

**以下第 1–8 节保留实施前的方案与调研证据。源码行号及“未导入/待选择”等状态描述属于当时基线，不作为当前状态；现行结论以上述实施记录和后续验收为准。**

## 1. 目标与范围

用户反馈当前 3D 工具 UI 不好用、机器人仍是简模、动作很卡，并明确工具是 **MuJoCo**。目标是让仿真观看、回放和交互操作流畅且直观，同时提高机器人外观辨识度。

推荐顺序：**先定位实际入口并评估匹配的现有 viewer → 修回放节奏 → 复用现有操作界面与精细网格 → 按缺口补充显示能力**。保留 MuJoCo 物理引擎，不通过更换训练框架或重训来处理尚未定位的显示问题。

**同日工具清点补正**：此前排查漏查 B 线 `software/servo-web/`；上游已经有整机 3D 网页调试台，本地参考目录包含源码、模型包和截图。此外训练框架 mjlab 已有 native/viser 回放界面。它们均不能写成本项目已经部署或用户已经使用的页面，但方案不应再默认所有 Web 界面都要从零新建。具体工具、用途与复用边界见第 2.1 节。

版本范围为本轮工作区源码。安装目录可见 `mjlab-1.3.0.dist-info`、`mujoco-3.10.0.dist-info`，不证明用户当时运行了这些版本；具体启动命令、运行环境和 checkpoint 尚未定位。

## 2. 实施前证据与判断边界（修前快照）

本节记录修复前的代码，行号对应当时快照；`play.py`/`interact.py` 的启动与等待问题、训练入口的旧回放示例已修，现行状态和入口见本文顶部。

| 来源与修前定位 | 当时静态确认 | 当时能支持的判断 |
|---|---|---|
| [play.py](../../../training/play.py) 第 20、26–31 行 | 使用 `human` viewer；每轮推理与 `step()` 后固定等待 `1/50 s` | 若此循环实际运行，周期约为工作耗时加 20 ms，可能慢放且节奏不匀；不是本次卡顿的已证根因 |
| 同文件第 22、26 行；[env.py](../../../training/duckstand/env.py) 第 180–201、282–286 行 | `reset()` 不创建 viewer，循环却先要求 `_viewer` 非空 | 当前独立入口还可能直接退出，不能假定它就是用户看到的版本 |
| [interact.py](../../../training/interact.py) 第 43–71 行 | 原生 `launch_passive`；按本轮剩余 20 ms 等待；摔倒后阻塞 1 s | 工作耗时超过 20 ms 时无法维持实速；摔倒暂停是显式行为，和持续卡顿需区分 |
| [env.py](../../../training/duckstand/env.py) 第 28–29、224–227、268–286 行 | 2 ms 物理步 ×10，50 Hz 控制；每控制步后同步 viewer | 控制频率、状态同步频率、屏幕呈现 FPS 是不同指标；50 Hz 本身不等于卡顿 |
| [env_cfg.py](../../../training/mjlab_duck/env_cfg.py) 第 50、61–65、225–226 行 | mjlab 也读取 `duck_v0.xml`，使用 2 ms ×10 | 两条仿真路径都会显示相同简模；其任务、执行器与策略契约不能直接互换 |
| [build_model_v0.py](../../../training/scripts/build_model_v0.py) 第 25–35、139–157、195–209 行 | 躯干/头/脚用盒，连杆用胶囊，已有显式惯量 | 简模来自模型生成方式，当前缺少独立精细外观层 |
| [train_duck.py](../../../training/mjlab_duck/train_duck.py) 第 5、52–55、67–69 行 | 用法文字列 `--play`，`main()` 实际始终转交训练入口 | 应提供与当前任务配套的明确回放入口，不能直接把该示例当已核准回放命令 |
| [training/README](../../../training/README.md) 自建边界与当前接口；[关节表](../../servo-id-mapping.md) | 现工程自建模型、未复制上游 mesh；当前策略 14 维，实物另有嘴部舵机 | 现有实现与下文拟议的视觉资产复用分开记录，不擅自扩大策略动作维数 |
| [HD1910 任务](../../../references/microduck-replica/software/training/src/mjlab_microduck/tasks/microduck_hd1910_env_cfg.py) 第 20–42 行；[基础任务](../../../references/microduck-replica/software/training/src/mjlab_microduck/tasks/microduck_velocity_env_cfg.py) 第 266 行；[模型入口](../../../references/microduck-replica/software/training/src/mjlab_microduck/robot/microduck_constants.py) 第 16、39–40、159–166 行 | HD1910 任务复用基础机器人并替换执行器配置，仍载入 `robot_walk.xml`；该 XML 第 10–12 行定义独立 visual mesh 层 | B 线飞特训练已有精细网格，与基础 Microduck 训练共用几何；可以优先评估作为本项目外观显示层 |
| [B 线打印说明](../../../references/microduck-replica/print/README.md) 第 9–19 行；[来源记录](../../../references/microduck-replica/software/training/UPSTREAM.md) 第 8–18 行 | 训练快照来源 `d9e1926c5220a0eb79fa5aab9df7b336f8e9a226`；保留网格未同步为最新实物 CAD，飞特/XL330 打印件分版本 | 共用训练几何不代表与本机飞特结构件逐件一致；精确外观差异须另核对应飞特 CAD |

本地依赖源码还有两项反证，避免把所有 MuJoCo viewer 归为同一种循环：

- `training/.venv-wsl/lib/python3.12/site-packages/mjlab/viewer/base.py:304–330` 已按仿真时间预算和帧 deadline 推进；若实际入口使用它，应先查现有预算、超时状态和配置，不重造同类调度。
- 同依赖的 `mjlab/viewer/viser/viewer.py:485–493` 明确隔一个 60 Hz tick 提交场景，即该提交逻辑为 30 Hz；这只适用于该 viser 路径，也不能直接当作浏览器 FPS。

以上依赖文件被环境目录排除出版本库，定位仅供本机复查。未用安装目录名称代替运行时版本证据。

本轮 Windows/WSL 进程核查未找到正在运行的项目 viewer，未取得运行帧时序；`ssh radxa` 连接超时，没有证据将它与 MuJoCo 卡顿联系起来。未启动仿真、训练或硬件，也未取得用户当时画面。WSLg、GPU/驱动、推理耗时和轨迹自身抖动仍是待区分项，不能写成已确认原因。

### 2.1 B 线已有的查看与调试工具（2026-10-21 补查）

| 工具与来源 | 已有能力 | 对本任务的用途与限制 |
|---|---|---|
| [servo-web 飞特网页调试台](../../../references/microduck-replica/tools/servo-web/README.md)，本地源码 `server.py:37` 为 **0.15.2** | Three.js 精细整机模型；15 颗舵机滑块及反馈；姿态保存/序列；官方姿势叠加；模型重心投影；可选 IMU 躯干姿态；`--fake` 虚拟舵机演示 | B 线已有的整机 Web 工具，可复用界面、模型转换和关节显示思路；当前数据源是舵机反馈或虚拟舵机，接入 MuJoCo 仍需状态适配 |
| mjlab 的 `play`：native / viser（通用框架能力，非 B 线另写的物理引擎） | 本地 `mjlab/scripts/play.py:49,280–291` 选择后端；`viewer/viser/viewer.py:119–163` 已有播放/暂停、单步、重置、倍速，其他代码提供 checkpoint 切换、调试叠层与状态统计 | 对匹配的 mjlab 任务/策略，优先复用这些现成回放功能；B 线 [pyproject.toml](../../../references/microduck-replica/software/training/pyproject.toml) 第 17 行锁定 mjlab 1.3.0。本项目 CPU/SB3 与 mjlab 接口不同，不能只切一个参数便宣称全部兼容 |
| [STL 查看器](../../../references/microduck-replica/tools/stl_viewer.html) | 拖入 STL、旋转/缩放查看 | 静态几何检查，不是策略回放或整机动力学工具 |

`servo-web` 的核查定位与实际限制：

- [README](../../../references/microduck-replica/tools/servo-web/README.md) 第 9–28、36–46 行列出交互和 `--fake`；其模拟模式没有重力，不能代替 MuJoCo 验证站立、接触或训练策略。第 133 行也说明重心/支撑区是模型几何估计，不证明真机动态稳定。
- [server.py](../../../references/microduck-replica/tools/servo-web/server.py) 第 250–251、1353 行：真机状态默认 10 Hz，虚拟模式 30 Hz；[index.html](../../../references/microduck-replica/tools/servo-web/index.html) 第 973–1007 行按最新状态更新关节，仅变化时绘制。这些是配置和代码事实，不是本机实测 FPS。其 0.14.0 版本说明记录过精细模型持续重绘造成交互卡顿，不能推断换用该工具就能达到 60 FPS。
- 后端第 39–42 行仍为 `20–24=左腿、10–14=右腿`，与[本机映射](../../servo-id-mapping.md)相反；整套真机工具不能按默认映射直接接入。仿真适配宜按关节名传 rad 和根位姿，不经舵机 ID/2048 计数绕转；单独提供仿真控制通道。
- 其 [model/model.json](../../../references/microduck-replica/tools/servo-web/model/model.json) 与 `meshes.bin` 已在本地，转换源为 `robot_allcollisions.xml` 和 STL，不能直接假定与 `robot_walk.xml` 每个节点一致。**同日进一步核对生成物后勘误**：上游 README 的“嘴部 ID 34 不显示”已经与当前文件不符；`model.json` 的 `bodies[name=jaw_hinge].joint` 实际含 `name=mouth`、`id=34`、`synthetic=true`，前端会按关节 ID 更新该视觉节点。这是额外合成的显示关节，不证明原训练模型已有第 15 个受控自由度。部分 Three.js 资源仍从 CDN 加载。
- README 第 11 行和模型目录旧 NOTICE 将来源仓库的 Apache-2.0 泛化到了模型；与根 [NOTICE](../../../references/microduck-replica/NOTICE.md) 第 26–33、56 行冲突。复用网格按根 NOTICE 的 CC BY-NC-SA 模型声明记录，不改只读参考库。
- 界面证据：[仓库自带截图](../../../references/microduck-replica/assets/servo-web.png)，2026-10-21 只读打开核看；外部上游原件，拍摄日期未注明，可能早于 0.15.2，不是本机运行截图。不重复复制原图。

本次仅查阅源码、文档和存量截图，未启动这些工具、未验证其实际流畅度，也未连接实物。C 线的 `hls_servo_debugger` 则侧重寄存器与总线调试，不能与上述 B 线整机 3D 调试台混为同一工具。

### 2.2 IMU 与“六轴转向”的实际支持范围（2026-10-21）

用户追问 IMU 与模型六轴转向。静态核查结论：**支持 IMU 驱动整机三轴旋转，同时叠加关节姿态；目前不依据 IMU 跟踪整机三轴平移，因此不属于完整 6DoF 位姿跟踪。** 六轴 IMU 是三轴陀螺仪加三轴加速度计，不等于已具备三维位置测量。

| 能力 | 源码证据与限制 |
|---|---|
| 横滚 roll、俯仰 pitch、偏航 yaw | [index.html](../../../references/microduck-replica/tools/servo-web/index.html) 第 810–811 行显示三角度，第 849–850、1001–1003 行将 IMU 四元数施加到整棵机器人树的父节点；前倾、侧倾、转身均可在模型上表现 |
| 机身姿态与各关节同时变化 | 同文件第 977–983 行独立更新关节 pivot，IMU 控制其父级姿态；不是只显示一个 IMU 方块 |
| 安装方向、相对归零 | [imu_attitude.js](../../../references/microduck-replica/tools/servo-web/imu_attitude.js) 的 `mountQuaternion` / `displayQuaternion` / `ImuAttitude.receive` / `zero`；首次有效姿态自动归零，可切换原始姿态和安装方向。这些只改变显示参考 |
| 前后、左右、上下位移 | 没有实时根位置来源；`index.html:919–922` 仅在加载模型时设置固定根位置，更新循环只改根四元数。抬高或平移整机不会自动产生对应世界坐标位移；不能把鼠标平移相机当成机身位置跟踪 |
| 传感器数据数值 | [imu_bus.py](../../../references/microduck-replica/tools/servo-web/imu_bus.py) 第 40–48、171–173 行的总线 15 字节包提供陀螺与四元数，没有原始加速度；[imu_bridge.py](../../../references/microduck-replica/tools/servo-web/imu_bridge.py) 第 189–190、227–229 行的匹配固件 SWD/RAM 路径才带三轴加速度。前端存在加速度栏不代表每种接入方式都有数据 |

无磁力计/外部航向参考的六轴融合存在 yaw 漂移，不能把显示归零解释为绝对航向校准；这也是上游 README 第 91、133 行明示的限制。失效数据保留最后姿态并提示，详见 `index.html:802–815` 与 `imu_attitude.js` 的 `expire()`。

如果后续用 servo-web 显示 MuJoCo，仿真已经有根位置与根姿态，可以在状态适配层额外传入 `root_position_xyz` 并更新根节点位置，组成 6DoF 显示；须保持坐标系/单位/旋转顺序一致。若想跟踪真机世界位置，则还需要定位或接触/运动学融合，不能只积分 IMU 加速度就承诺可靠位置。

本机 GD32 IMU 的项目文档与该总线路径同为 ID 200、地址 56、15 字节基本契约，见[板②记录](../../imu-gd32-bench-test.md)第 18 行；但本轮未连接该板或运行 servo-web，安装方向、状态位细节和连续姿态效果仍未验证，不把 B 线 STM32 的 SWD 内存读取方案套到 GD32。

## 3. P0：找准入口，消除不必要的慢放和停顿

第一份实现应围绕**用户实际启动的入口**，同时固定模型、环境、checkpoint 和单环境回放配置。CPU/SB3 历史 45/47 维、当前 49 维与 mjlab checkpoint 不混用；批量训练的 4096 环境配置不作为交互观看默认值。

仅在现有场景短时记录 10–20 s，采用 `perf_counter()`，把必要数据写到本专题：

- 分开记录策略推理、物理 `step`、viewer `sync` 和等待的耗时，以及状态提交间隔。
- 同时记录仿真时刻和墙钟时间；实时率为 `Δsim_time / Δwall_time`，1×播放目标接近 1。
- 呈现帧间隔/FPS 应来自实际渲染端；若只能测 `sync()`，界面称“状态 Hz”，屏幕 FPS 标未知，不冒充显示帧率。
- 标记暂停、摔倒、reset 和速度倍率，避免把有意停住计入正常播放卡顿。

依据这一次短记录选择修法：

| 观测现象 | 优先处理 |
|---|---|
| 实时率长期低于 1，推理或物理耗时超预算 | 确认单环境、策略设备与数据搬运；优化耗时环节，界面展示实际速度 |
| 计算够快，但提交间隔不匀或固定额外等待 | 对自写循环采用单调时钟的绝对 deadline，等待剩余时间，避免每轮累计工作耗时 |
| 实时率正常、状态提交稳定，显示仍卡 | 查看渲染端帧间隔和实际图形后端，再决定降低显示开销或做 P3 |
| 原始关节/机身轨迹本身有抖动 | 按轨迹问题记录并另行定位控制/接触原因；不以插值或低通把它伪装成平稳动作 |

如果选定 `play.py`，先修 viewer 创建顺序和入口退出问题；如果选定 mjlab，沿用其现成回放与 viewer 能力，只补本项目明确入口和配置。

超预算时优先降低阴影、分辨率、诊断叠层或显示更新频率，允许丢弃过期显示快照。**不跳过必要物理/控制步，不增大 timestep 或改变策略频率来掩盖性能问题**。持续追不上时显示低于 1 的实时率，避免无限积压；从暂停/reset 恢复时重新锚定调度时间，不补跑整段暂停时间。

摔倒后的 1 s 可保留为可见的倒计时状态，但不得阻塞界面交互；提供“自动重置”开关。暂停时“单步”默认前进一个控制周期，并在界面说明其含 10 个物理步。

## 4. P1：把常用操作放到画面附近

先整理实际兼容的 viewer 已有能力。若当前回放使用 mjlab，优先评估其原生/viser 控件；CPU 原生入口则补明确入口和操作提示。B 线 servo-web 可作为整机面板与精细显示的复用参考，不把其虚拟舵机模式当仿真回放。以下是交互目标，已有功能直接复用；画面以机器人为中心，调试细节默认折叠。

| 区域 | 默认内容 |
|---|---|
| 顶栏 | 场景、checkpoint、仿真模式、暂停/运行状态、实际 FPS（可测时）、状态 Hz、实时率 |
| 中央 3D | 大画面、适当光照和地面参照；选中关节/机身有高亮，机体不被浮窗遮挡 |
| 底部控制 | 播放/暂停、单步、0.25×/0.5×/1×/2×、重置、录制 |
| 右侧检查器 | 选中关节的当前角/目标角/速度/限位；推扰方向、幅度、持续时间与施加按钮 |
| 视角工具 | 正面/侧面/顶部、跟随开关、一键找回机器人；当前操作模式和快捷键提示 |
| 折叠诊断 | 碰撞体、关节轴、接触点、力向量、性能详情；按需要开启 |

“旋转视角”和“拖拽施力”有明确模式或可见操作提示，不能只靠记住隐蔽按键；施力时显示作用对象、方向和幅度。状态面板始终标“仿真”，不暗示正在控制实物。

先比较现有原生/viser 界面能覆盖多少需求，再决定补哪些面板。若需要更强的整机联动，评估在本项目工作副本中适配 servo-web 的显示层；只有仍有明确缺口时才新增独立工作台。接仿真时以模型状态驱动画面，操作入口对应暂停、重置、命令和推扰，不照搬舵机写寄存器接口。

## 5. P2：优先核对现成精细网格，保留现有物理模型

**2026-10-21 同日修订**：用户指出“方案 2 里飞特版用的 3D 模型应该是一样的”，本轮按 B 线 `microduck-replica` 核查。源码确认其 HD1910 训练任务与基础 Microduck 共用 `robot_walk.xml` 和网格，飞特适配主要替换执行器配置。因此撤下“精细外观默认全部从零自建”的唯一方案，改为**优先核对现成 visual mesh 的复用范围，缺失或不匹配部分再自建**。

这里的“相同”是 B 线 HD1910 与基础训练任务共用几何；本项目当前 `duck_v0.xml` 仍是自建盒/胶囊简模，并未加载这些网格。B 线训练网格也未更新成最新飞特打印 CAD，不能将其直接称为本机精确数字模型。本轮未下载或核验独立 CAD 仓库的当前发布。

拟议复用只取显示所需的 mesh、材质及挂接变换，在本项目可写资产目录记录来源；先核对 body 对应、单位、关节零位和局部坐标，再接到现有骨架。训练模型、任务、碰撞体及执行器参数仍按本项目契约处理。当前工程“只借参数、自建模型”的实施记录保留；本轮增加视觉资产复用候选，不表示已经导入网格或替换训练工程。

需要补建的外观以[已归档照片](../../photos/README.md)、已溯源公开参数与用户确认尺寸为依据；缺少尺寸的部位标为外观近似，不宣称整机已做准确实物对齐。

第一批外观覆盖机身/头壳、眼睛/嘴、电池、舵机外壳、支架与脚掌轮廓。选中高亮、阴影和低成本材质配合这些部件提升辨识度；螺纹等小细节后置，依据实际显示耗时决定复杂度。

- MuJoCo 原生显示：外观 geom 挂在对应 body，使用 `contype=0`、`conaffinity=0` 和零质量/密度，按独立显示 group 管理。保留原有显式惯量、碰撞体、关节轴、限位和传感器契约。
- 默认显示外观，诊断时一键叠加或切回碰撞体。新增外观不参与接触，不改变训练的质量/惯量或接触形状；交付时核对这些物理属性未变。
- 若后续做 Web，可生成独立 GLB 外观资产，但 body/关节名称、单位、坐标系、旋转约定和零位须有一份明确映射，与 MuJoCo 状态一致。
- 嘴可先做静态或“未驱动”视觉节点；现有 14 维策略不因实物有 15 颗舵机就扩维。加入嘴控制是独立任务。
- 现成资产候选明确限定为上述 B 线训练 visual mesh，优先复核其挂接适配；需要贴合实际飞特结构的部件再对照对应 CAD。来源与模型许可见 [NOTICE](../../../references/microduck-replica/NOTICE.md)（模型为 CC BY-NC-SA，独立于代码许可）；三个上游参考库保持只读，不整包替换本项目 MJCF 或任务配置。

## 6. P3：必要时分离状态更新与显示

只有 P0 证明提交/显示节奏仍限制体验，才实施这一层。原生 MuJoCo passive viewer 已有自己的渲染线程，不能简单再加线程让两边无锁读写同一 `MjData`。

```mermaid
flowchart LR
    A[策略与物理推进] --> B[带时刻和回合编号的状态快照]
    B --> C[小型有界缓冲]
    C --> D[显示副本与插值]
    D --> E[原生窗口或后续 Web 画面]
    F[暂停/重置/推扰命令] --> A
```

控制/物理按既定频率推进，快照至少带 `sim_time`、`seq`、`episode_id`、位姿及运行状态。显示以 60 Hz 为初始目标，只保留少量快照；落地时使用受控锁或副本交接，避免图形线程争抢物理状态。

插值只作用于显示副本：平移线性插值，姿态用四元数 SLERP，关节角按关节类型与限位正确处理环绕。显示可接受短小、固定且可说明的缓冲延迟；插值状态不得写回物理环境或影响策略观测。

reset、新回合、摔倒暂停和状态中断必须切断旧快照，禁止从摔倒姿势“平滑穿越”到重置站姿。状态过期时停在最后有效画面并提示，不无限外推。真实轨迹抖动保持可查看，不新增低通滤波掩盖控制问题。

单机原生方案不需要 WebSocket；后续选择 Web 时再增加本地快照传输，并分别显示接收状态 Hz 与浏览器 FPS。viser 的 30 Hz 提交逻辑只有确认实际使用该后端后才值得调节。

## 7. 路径取舍与最少验收

| 路径 | 适用范围 | 决定 |
|---|---|---|
| 匹配任务的 MuJoCo 原生 / mjlab viser viewer + 精细外观层 | 改善当前仿真观看和交互体验 | **优先评估复用**；补本项目入口与缺失面板，避免重复实现播放控制 |
| B 线 servo-web 的显示层 + 本项目 MuJoCo 状态适配 | 需要更强的整机面板联动、以后衔接真机观察 | 已有工具的适配候选；需区分仿真/真机数据、关节映射和操作接口 |
| 全新本地 Web 工作台 | 现有 viewer 和 servo-web 都无法满足明确交互需求 | 后置；不再作为默认起点 |
| 更换物理引擎、扩大训练或直接改策略频率 | 无法单独解决当前已确认的外观与 UI 问题 | 不纳入此次显示优化方案 |

以下是**初版验收目标，不是现有实测结果或性能保证**。使用实际机器、同一兼容 checkpoint、同一场景、单环境、1×，只做能判断效果的短时确认：

1. 持续播放时实时率接近 1，60 Hz 屏上争取稳定 55–60 FPS；记录帧间隔异常，不能仅靠平均 FPS 掩盖明显长停顿。若硬件达不到，保留测得结果并调整显示质量预算。
2. 不看终端即可暂停、单步、重置、切视角和施加一次明确推扰；摔倒/reset 时画面切换真实，界面仍能响应。
3. 同一段轨迹在改前/改后对照，分清显示平顺和策略运动改善；确认外观层未改变质量/惯量、碰撞和关节接口。无需为纯展示改动重训或扩展硬件测试。

## 8. 方案阶段的后续建议与状态（历史）

实施时第一步：在用户实际打开工具的那台机器上确认启动入口/运行版本与 checkpoint，补一个单环境可复现回放入口和最小计时显示；取得 10–20 s 数据后决定是修自写循环、复用 mjlab 调度，还是处理图形后端。该信息尚缺，不影响先确定上述 UI、外观和数据契约。

方案阶段仅交付本方案及 [training 导航](../../../training/README.md)、[进度记录](../../../PROGRESS.md)，当时未修改实现、未运行仿真/训练/新评估、未操作实物；采样尚未被证明是卡顿根因。该阶段落盘检查限于 Markdown 链接存在与 `git diff --check`；后续实施已转入本文顶部的现行记录。

## mjlab 平台边界问答（2026-10-22，用户提问"mjlab 必须在 WSL 下跑么"）

**结论：训练——实际绑定 Linux/WSL；纯 MuJoCo 查看——Windows 原生即可。** 依据：① mjlab 物理后端 MuJoCo Warp 官方主平台 Linux，Windows 不在 GPU 训练官方支持范围（github.com/google-deepmind/mujoco_warp）；② 本项目锁定组合（mjlab 1.3.0 + mujoco 3.10.0 + mujoco-warp 3.8.1 + warp-lang 1.12.0，另有 scipy 手动补）仅在 WSL `.venv-wsl` 验证，且有已知版本雷（mujoco-warp 3.9.1 `ls_parallel` 删除崩溃）；③ 标准 `pip install mujoco`（CPU）Windows 原生支持，本机 Python 3.13 + MuJoCo 3.16 已在用（servo-mujoco-viewer），且 duck_visual.xml Windows 3.16 物理一致性 0 误差已验证（见上文 visual-validation）。**工作台远程用法**：工作台为 viser 网页（127.0.0.1:8080），在训练机启动后经 `ssh -L 8080:localhost:8080` 端口转发即可在装配机浏览器使用完整工作台，无需迁移环境。装配机（本机）当前未装 WSL（2026-10-22 复核 `wsl -l -v` 明确未安装）。

**2026-10-22 追记：装配机已按用户授权装 WSL2+Ubuntu-24.04 并重建 `training/.venv-wsl`（torch 2.13.0+cu129 替代 cu130，因驱动 577.05 仅暴露 CUDA 12.9；checkpoint 自 git 历史恢复），工作台在本机跑通（49.9 Hz 与训练机一致）——上文"装配机未装 WSL"的状态已过时，详见 PROGRESS 当日条目。**
