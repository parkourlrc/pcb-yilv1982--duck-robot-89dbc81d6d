# 本机训练环境登记

## 节点名称（2026-11-10）

本机训练节点统一登记名为 `MSI-laptop`。节点类型仍为 Windows + Ubuntu-24.04 WSL2，工作台配置入口为 `training/dashboard.local.json`；名称只用于节点识别，不改变硬件、训练参数或运行路径。

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
| 训练解释器 | 仓库 `training/.venv-wsl/bin/python`，Python 3.12.3；复用现场已有独立环境 |
| WSL 仓库定位 | 现场 `pwd` 为 `/mnt/c/Projects/duck-robot`；已按现场结果配置，不从历史路径推定 |
| PyTorch | 2.13.0+cu129，CUDA runtime 12.9 |
| torchvision | 修正为 0.28.0+cu129；原 0.29.1 要求 torch >=2.14.0，与现有环境冲突 |
| 训练依赖 | mjlab 1.3.0、MuJoCo 3.10.0、mujoco-warp 3.8.1、warp-lang 1.12.0、rsl-rl-lib 5.0.1、tensordict 0.15.2、viser 1.1.1 |
| 工作台 | 新建 Windows `training/.dashboard-venv`，按 `training/dashboard/requirements.txt` 安装 fastapi 0.115.6、uvicorn 0.34.0、psutil 6.1.1、websockets 14.1 |
| 本地节点配置 | `training/dashboard.local.json`，发行版 Ubuntu-24.04，本地运行目录 `/root/duck-training-runs`，端口 8766；配置由 Git 忽略 |

这台机器与历史 RTX 4080 / CUDA 13.0 训练机分开登记。历史性能、成功回放和策略结果不作为本机验收。

### 安装操作与来源

现场已有训练环境与 CUDA，无需重装驱动或 WSL。依赖修复命令（仓库根目录的 WSL）：

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
