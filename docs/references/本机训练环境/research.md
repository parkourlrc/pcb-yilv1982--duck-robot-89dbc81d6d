# 本机训练环境登记

## 节点名称（2026-11-10，laptop-5090-24G）

laptop-5090-24G 机器的训练节点登记名为 `laptop-5090-24G`。节点类型仍为 Windows + Ubuntu-24.04 WSL2，工作台配置入口为 `training/dashboard.local.json`；名称只用于节点识别，不改变硬件、训练参数或运行路径。公司工作机另登记为 `desktop-4080-16G`，见文末 2026-11-10 条目；两台机器不共用硬件与解释器结论。

2026-11-10 用户统一环境命名：公司工作机为 `desktop-4080-16G`（原 4080-16g），MSI 机器为 `laptop-5090-24G`（原 MSI-laptop）。历史条目已按新名更新，硬件、身份字段与运行结果不变。

## 环境登记规则（2026-11-10，训练流程第③步）

按[自主训练平台流程 Spec](../../specs/20261105-自主训练平台/spec.md)“环境组装与登记的强制规则”，环境登记至少包含以下字段；当前值同步记录在下方对应环境的 2026-11-10 条目，不用“本机”代替具体环境名。

| 字段 | 要求/当前登记 |
|---|---|
| 节点与发行版 | `laptop-5090-24G`；Ubuntu-24.04 WSL2，内核 6.18.54.1-microsoft-standard-WSL2 |
| 解释器绝对路径 | `/root/venvs/duck-wsl/bin/python`（Python 3.12.3） |
| 文件系统位置 | WSL 原生 ext4 虚拟磁盘（`/dev/sdd`；宿主文件 `%LOCALAPPDATA%\wsl\{distro-id}\ext4.vhdx`，物理位于 C: 的 NVMe SSD） |
| 仓库源码位置 | `/mnt/c/Projects/duck-robot`（DrvFs/9p，允许放源码与产物，不允许放解释器和依赖） |
| 依赖版本 | torch 2.13.0+cu129、mjlab 1.3.0、MuJoCo 3.10.0、mujoco-warp 3.8.1、warp-lang 1.12.0、rsl-rl-lib 5.0.1 |
| 启动实测 | 完整依赖栈导入：冷 8.0–9.3 s、热 6.0–6.4 s；回放首帧：冷 9.1 s、热 4.6–4.8 s（2026-11-10） |
| 运行校验 | `torch.cuda.is_available() == True`；工作台节点探测 `connected` 并返回 RTX 5090 Laptop GPU |
| 测量方法 | WSL `drop_caches` 后计时导入；工作台 API 创建回放并记录创建→首帧 |

- 解释器及其 venv/site-packages 必须位于 WSL 原生 ext4；放在 `/mnt/c` 时第③步判不合格（2026-11-10 实测跨盘导入 42.8–49.6 s，原生盘 8–9 s）。
- 迁移、重建或升级依赖后必须重新登记并复测；旧记录保留，不因新结论删除。
- “能跑”不足以通过：登记需给出路径、文件系统位置与启动实测；工作台节点探测只证明连接性，不代表策略行为验收。
- 登记变化需同步到本文件对应日期条目，并在涉及流程或进度时更新 [PROGRESS.md](../../../PROGRESS.md)。

## 2026-11-10：laptop-5090-24G 回放冷启动定位与 WSL venv 迁移

[本机实测] 用户报告检查点回放加载慢。工作台回放从创建到首帧 61.2–81.2 秒（5 个会话：61.2/64.7/71.6/81.2 及 61.9 s）。窗口在首帧前不显示机器人（前端 `root.visible=false`），因此表现为长时间空画面。

同一 WSL 解释器、同一依赖栈（`torch, tensordict, rsl_rl.models, mjlab, mujoco_warp, warp`）导入实测：

| 位置 | 冷缓存 | 热缓存 |
|---|---|---|
| `/mnt/c/Projects/duck-robot/training/.venv-wsl`（DrvFs/9P） | 42.8 / 43.0 s | 46.8 / 49.6 s |
| `/root/venvs/duck-wsl`（ext4） | 8.0 / 9.3 s | 6.0 / 6.4 s |

9.9 GB venv 从 `/mnt/c` 复制到 ext4 用时 948.9 s（约 10 MB/s）。分段探针（`training/.dashboard/probe-env.py`，单进程顺序计时）：import torch 19.63 s；import tensordict/rsl_rl/mjlab 51.12 s；torch.load 0.06 s；import mjlab_duck 0.26 s；build actor 0.19 s；build env 1.92 s；reset 0.27 s；首步 0.52 s；后续 20 步 1.59 s（约 80 ms/步）。[实测] 冷启动约 95% 时间在导入，跨盘 I/O 是主因；建环境、权重、reset、首步合计约 3 秒。

同轮发现两项：`a33fedd1…` 回放完成后 worker 仍存活 4 小时 53 分、常驻约 2 GB 并占用 GPU；用 Windows PowerShell 写出的 `controls.json` 带 UTF-8 BOM，worker 的 `json.loads` 失败后被静默 `continue`，关闭指令不生效。

处置与验证：[实测] venv 迁移到 `/root/venvs/duck-wsl`；`training/dashboard.local.json` 的 `nodes.local.python` 指向新路径；`play-mujoco.ps1` 按 `DUCK_WSL_PYTHON` → 新路径 → 旧路径解析；`replay_worker.py` 新增 `--idle-timeout`（默认 300 s）并按 `utf-8-sig` 读取控制文件。改后经工作台 API 创建回放首帧 4.6 s（历史 checkpoint）与 4.8 s（复测），关闭后无 worker 残留、GPU 0 MiB；`--idle-timeout 5` 测试在 13:26:25 完成、13:26:30 转 `closed`，随后进程退出；带 BOM 的关闭指令 3 秒内生效。

限制：新位置依赖当前 WSL 发行版，重置发行版会丢失，需按锁定版本重建；旧 `/mnt/c` venv 暂留回退（9.9 GB，未删除）；冷缓存复测首帧 9.1 s（`drop_caches` 后创建回放），热态 4.6–4.8 s。本次未改播放步进性能：23 s 仿真片段实际耗时约 62 s（约 0.37× 实时），另立任务。见[回放加载优化 Spec](../../specs/20261110-回放加载优化/spec.md)。

## 2026-11-09：启动工作台与当日更新核对

用户要求启动训练环境并查看今天更新。以本机 `main@88e4a507` 和现有 `gitee/main` 记录为依据，本轮未拉取、未开始训练。11月9日四个提交为：`29f6e73f` 训练数据提交范围与计算环境登记，`79ce1321` 合并步幅实验归档，`96e31d4c` 训练档案分级导入及三类复训，`88e4a507` LF换行与冻结清单修正。功能细节及原验证边界见[实施记录](../../specs/20261109-训练档案与复训/implementation-record.md)：67字段、奖励配方、原状态续训/从零/接权重派生、历史材料分级及耐久档案。其96转换GPU验证是既有实施记录，不是本轮运行，也不代表策略行为通过。

[本机软件实测] 通过 `training/start-dashboard.ps1 -NoBrowser` 启动8766工作台，首页HTTP 200；Windows/WSL监控connected，v3与冻结v1任务ready，参数目录67字段，本机49条历史记录，活动训练为空。已请求在应用内打开页面。结果见[startup-20261109.json](startup-20261109.json)。历史条目数量是本机材料盘点，不与另一环境57条记录混同，也不代表独立训练次数；未做浏览器视觉验收或GPU训练。

[文件核验及修复] 启动时v3有16个来源SHA不匹配：工作区CRLF、HEAD内容LF，规范化后均与HEAD及现行清单一致。仅保留这16个v3来源的LF恢复，无代码/参数语义变化。首次递归处理误覆盖范围过宽，遇WSL `lib64`链接失败；随后切换Git文件清单，额外触及的受管文件已恢复原换行，冻结历史文件未保留修改。过程中遇默认GBK读取失败及一次文件打开失败，显式UTF-8及重试后完成；最终Git无训练源内容差异。旧v2清单仍指向已被v3更新的现行源码，报9项SHA不匹配；本轮未改旧合同或绕过校验，需要旧任务时使用相应冻结来源核验能力。

状态为本次启动时点快照，不表示重启电脑后自动启动。本轮检查记录保留工作区，未提交。

## 2026-11-07：RTX 5090 Laptop / Windows + WSL2

用户要求在本机搭建训练环境并登记。本轮沿用本项目 `training/` 的 mjlab 联合运动训练入口，配置本地执行环境与网页工作台；不改变训练任务、奖励或正式训练预算。基线提交 `a5ad1357`。

### 现场核查与配置

| 项目 | 本轮现场结果 |
|---|---|
| 机器 | MSI Stealth A18 AI+ A3XWJG，物理内存约 63.1 GiB |
| GPU | NVIDIA GeForce RTX 5090 Laptop GPU，24463 MiB，Windows 驱动 577.05 |
| WSL | Ubuntu-24.04 / WSL2，内核 6.18.54.1-microsoft-standard-WSL2；可见内存约 30 GiB、swap 8 GiB |
| 训练解释器 | 2026-11-10 起为 `/root/venvs/duck-wsl/bin/python`（WSL ext4，Python 3.12.3）；原仓库内 `training/.venv-wsl` 保留为回退 |
| WSL 仓库定位 | 现场 `pwd` 为 `/mnt/c/Projects/duck-robot`；已按现场结果配置，不从历史路径推定 |
| PyTorch | 2.13.0+cu129，CUDA runtime 12.9 |
| torchvision | 修正为 0.28.0+cu129；原 0.29.1 要求 torch >=2.14.0，与现有环境冲突 |
| 训练依赖 | mjlab 1.3.0、MuJoCo 3.10.0、mujoco-warp 3.8.1、warp-lang 1.12.0、rsl-rl-lib 5.0.1、tensordict 0.15.2、viser 1.1.1 |
| 工作台 | 新建 Windows `training/.dashboard-venv`，按 `training/dashboard/requirements.txt` 安装 fastapi 0.115.6、uvicorn 0.34.0、psutil 6.1.1、websockets 14.1 |
| 本地节点配置 | `training/dashboard.local.json`，发行版 Ubuntu-24.04，本地运行目录 `/root/duck-training-runs`，端口 8766；配置由 Git 忽略 |

这台机器与历史 RTX 4080 / CUDA 13.0 训练机分开登记。历史性能、成功回放和策略结果不作为本机验收。

### 安装操作与来源

现场已有训练环境与 CUDA，无需重装驱动或 WSL。以下为 2026-11-07 当时的安装命令，venv 路径为旧位置；2026-11-10 迁移后新环境应使用 `/root/venvs/duck-wsl`，重建时按同一锁定版本安装。依赖修复命令（仓库根目录的 WSL）：

```bash
uv pip install --python training/.venv-wsl/bin/python torch==2.13.0+cu129 torchvision==0.28.0+cu129 --index-url https://download.pytorch.org/whl/cu129
uv pip check --python training/.venv-wsl/bin/python
```

Windows 工作台：

```powershell
python -m venv training/.dashboard-venv
training/.dashboard-venv/Scripts/python.exe -m pip install -r training/dashboard/requirements.txt
powershell -File training/start-dashboard.ps1 -NoBrowser
```

启动后访问 `http://127.0.0.1:8766`。本机仅登记 local 节点，没有配置或探测 Spark。训练/回放使用 WSL Python，Windows Python 只运行网页控制服务。环境与运行缓存不提交。

本轮来源：`training/README.md`、`training/dashboard/README.md`、`training/dashboard/config.py`、`training/dashboard/executors/remote.py`、`training/scripts/benchmark_locomotion.py`、现场 `nvidia-smi` / `wsl --list --verbose` / Python 包元数据。torchvision 修复包来自 PyTorch 官方 CUDA 12.9 wheel 索引；工作台依赖来自现有项目 requirements。

### 验证记录

- [软件实测] CUDA 可用，GPU 名称正确，CUDA 张量运算返回预期值。
- [软件实测] 修复后 WSL `uv pip check`：158 个包全部兼容；Windows 工作台 `pip check`：无破损依赖。
- [软件实测] 现有 `benchmark_locomotion.py` 完成 16 环境 × 64 步、1 次预热 + 3 次计时 PPO 更新，共 4096 次转换，进程退出码 0；观测、奖励、损失和模型参数有限。Warp 日志确认物理模块运行在 RTX 5090 Laptop `cuda:0`（sm_120），CUDA Toolkit/Driver 均为 12.9。原始结果见 [JSON](benchmark-20261107.json) 和 [日志](benchmark-20261107.log)。此小负载只验证环境，不作为设备性能比较或策略验收；未输出正式策略。
- [软件实测] 工作台首页 HTTP 200，`/api/tasks` 中 locomotion v2 为 `ready`，无缺失依赖；`/api/resources` 中 Windows/WSL 均为 `connected`，local 节点主动探测返回 RTX 5090 Laptop，见[工作台证据](dashboard-20261107.json)。服务保持运行于本机 8766，重启电脑后需重新执行启动命令；未配置开机自启。网页交互和模型回放本轮未另验收。资源采集最初有 GPU 查询超时，后续 WSL GPU 采样恢复；不将单次连接正常视为长期监控验收。
- [文件核验与修复] 初次工作台报告 7 个训练源文件 SHA 不匹配；逐一检查发现全部由 Windows CRLF 转换引起，转换为 LF 后与任务清单和 HEAD blob 完全一致。设置本仓库 `.git/config` 的 `core.autocrlf=input`，并从 HEAD 恢复这 7 个原本无本地改动的文件；训练源码及任务合同无内容变更，不修改全局 Git 设置。此设置保留检出时的原始 LF，并正常识别已有 CRLF 文档的文本差异。
- 首次使用历史用户目录拼接 WSL 路径失败，随后以现场 WSL `pwd` 定位；首次配置文件写入错误工作区，节点探测报缺项，已移除该误写文件并在本项目配置。

### 边界

仅确认本地训练环境的运行能力；不宣称策略行为达标，不启动原正式训练的第二轮，不部署机器人。短跑日志中的模型 keyframe/integrator 拼接及 Warp 弃用警告保留；未为搭环境改模型或依赖源码。短跑对已跟踪 `MUJOCO_LOG.TXT` 的自动追加已还原，本轮完整日志另行归档。之前 Gitee 更新保存的 `pre-gitee-update-20261107` stash 仍保留，本轮不处理其硬件文档冲突。登记修改默认不提交、不推送。

## 2026-11-10：公司工作机（desktop-4080-16G）与两台 Spark 的现场核对

用户确认训练平台可能部署在多处；当前为公司工作机器，该机器一个训练环境，两台 Spark 在同一局域网。平台启动时应按主机名/GPU 识别当前属于哪个已登记环境，不把任何机器名写死为“本机”回退值（方案见 spec）。仓库同时用于 `laptop-5090-24G`（RTX 5090 Laptop）与本公司工作机（`desktop-4080-16G`）两台物理机，WSL 解释器路径、依赖版本和运行目录不同，本节只描述 desktop-4080-16G，不覆盖另一台机器的记录；两台机器的结论不互相迁移。当轮先做只读核对并把结论落到 [训练环境登记 spec](../../specs/20261110-训练环境登记/spec.md)，随后按用户确认进入编码；实施结果见本节末尾。

### 硬件与训练环境 [本机实测]

| 项 | 结果 |
|---|---|
| Windows 主机名 | `DESKTOP-36NFOE5` |
| Windows GPU | NVIDIA GeForce RTX 4080，16376 MiB，驱动 616.92 |
| WSL | Ubuntu；WSL 内 PATH 没有 `nvidia-smi`；torch 2.14.1+cu130，`torch.cuda.is_available()` 为 True，设备名 RTX 4080 |
| WSL docker | 存在 `/usr/bin/docker`；本机训练走 venv python，不依赖 docker |
| spark1 | `spark-c416`；NVIDIA GB10；20 核；约 121 GiB；docker 29.2.1；benchmark venv 与 env.sh 存在；`nvcr.io/nvidia/pytorch:25.10-py3` 镜像存在 |
| spark2 | `spark-752a`；NVIDIA GB10；20 核；docker 28.3.3；benchmark venv 与 env.sh 存在 |
| Spark env.sh | NCCL_NET=IB、NCCL_SOCKET_IFNAME=enp1s0f0np0、NCCL_IB_HCA、GLOO_SOCKET_IFNAME、HF_HOME=/work/.hf-cache 等 |

### 平台现状 [实测/源码核验]

- `/api/resources` 返回 local、spark1、spark2 三项，核实时均为 connected；local 当时仍显示旧的通用文案。
- 现有 `Executor.probe()` 只做轻量检查（WSL：python + torch；SSH：env_file、benchmark venv、`docker info`），不检查 GPU 名称/显存、训练镜像和 env 变量；资源卡徽章由 2 秒遥测的 connected/stale/unavailable 驱动。
- 前端 `app.js`/`styles.css` 已具备 ready / available / unavailable / offline 徽章映射，可用性显示不需要改前端文件。

### 结论与边界

- 本机是 RTX 4080 16GB 的公司工作机，与 2026-11-07 登记的 RTX 5090 Laptop 不是同一台；历史性能、回放与验收结果不迁移到本机。
- 只按 SSH/进程可达判断“可以训练”不充分；GPU、docker、环境变量需要启动前探测，方案见 [spec](../../specs/20261110-训练环境登记/spec.md)。
- spark2 历史 SSH 收尾超时本轮未复现；实施探测后需实测，单次超时不能判定设备长期不可用。

### 实施结果（2026-11-10）[本机实测]

- **启动自识别**：`python -m dashboard.cli self` 输出 hostname=`DESKTOP-36NFOE5`、GPU=`NVIDIA GeForce RTX 4080`、WSL 发行版 Ubuntu/docker-desktop，匹配 `local`，state=matched；平台 `/api/resources` 的 `self.environment_id` 为 `local`。本机登记名 `desktop-4080-16G`。
- **探测脚本**：登记/启动时生成 `training/.dashboard/probes/local.sh`、`spark1.sh`、`spark2.sh`。local 检查 python、torch CUDA、work_root；spark 检查 nvidia-smi、`sudo -n docker info`、训练镜像、env.sh 变量、benchmark venv、work_root。
- **三环境探测均就绪**：本地（RTX 4080）、spark1（GB10，docker 29.2.1，镜像存在）、spark2（GB10，docker 28.3.3，镜像存在）；平台资源卡显示“就绪”。
- **负向验证**：不匹配的 hostname → `environment_id=null`、本机显示“未登记主机”、连接状态 offline；python 路径不存在 → 不可用并列出 python/gpu 缺项；不可达主机 → offline（探测超时）。
- **任务来源哈希**：dashboard 代码变更会使 v3 任务 `source_hashes` 失配；本轮按当前源码刷新 v3 哈希并加入新模块（identity/environment_probe/check_environment_probe），v3 恢复 ready。v2 仍为历史缺项，未改。
- **契约检查**：`check_archive_contract.py` 在刷新 v3 哈希后仍于“重建索引后读取运行”断言失败；在 HEAD 基线工作树按同样步骤复现，是既有问题，不由本功能引入，本轮未改该检查。
- 前端文件未改；本轮未启动训练；平台以新代码重启于 8766，历史运行列表仍为 0（归档缺失，见 2026-11-10 早前记录）。
