# Spec：训练环境登记、启动自识别与启动前探测

- 日期：2026-11-10
- 状态：已交付（2026-11-10 编码、验证并重启平台；未提交）
- 修订：2026-11-10 用户更正——“本机”不是仓库或代码里的固定概念。laptop-5090-24G 是另一台已知机器上提交的记录，不是本机回退名；平台应在启动时识别当前机器属于哪个已登记环境。

## 需求（2026-11-10 用户确认，含更正）

- 平台可登记多个训练环境；环境不保证在任一时刻都能连接。
- 每个登记环境保存信息：名称、类型、连接参数、硬件与身份标识。
- 仓库、代码与配置不把任何一台机器固定为“本机”；平台启动时识别当前机器是哪一个已登记环境，再使用该环境的名称、硬件与连接信息。
- 可用性以启动前能力探测为准：GPU、docker、环境变量；不同环境在登记时生成各自的探测脚本，由脚本判定环境是否准备好。
- 当前公司工作机登记为 **desktop-4080-16G**；`laptop-5090-24G`（RTX 5090 Laptop）是另一台环境的历史记录，两台机器的结论不互相迁移。
- 平台可能部署在多处；当前登记范围为公司工作机（desktop-4080-16G）与同一局域网的两台 Spark。

**负面范围**：不改前端文件、不加页面内的环境新增/编辑/删除入口；不在代码中写死任何机器名或“本机回退名”；不改训练合同、调度与归档；不自动重连或自动切换环境；不扫描未登记主机；不提交本地连接配置。

**验收标准**：

1. 代码中不存在硬编码的机器显示名（如 `laptop-5090-24G`、`desktop-4080-16G`、`本地 Windows / WSL`）；本机名称来自启动时识别结果。
2. 在当前公司工作机启动后，平台把自身识别为 `desktop-4080-16G`，资源卡显示该名称与 4080 硬件信息。
3. 把同一份代码放到已登记的 laptop-5090-24G 上启动时，应识别为 `laptop-5090-24G`，而不是沿用上一次机器的名称。
4. 识别不到时显示“未登记（主机名 / GPU）”，不冒充任何已登记环境，并拒绝本机训练（用户 2026-11-10 决定：本机匹配不上即没有本机环境）。
5. 三个环境均有登记；每个环境有独立生成的探测脚本，可单独执行并输出逐项结果。
6. 可用性随探测结果变化（就绪 / 不可用 / 离线 / 未探测），不可用环境仍显示；启动前未就绪拒绝启动并列出缺项。
7. 复用现有“计算资源”卡片徽章即可显示可用性，前端文件零改动。

## 现状与依据（文档确认）

| 项 | 现状 | 等级 |
|---|---|---|
| 登记载体 | `training/dashboard.local.json`（Git 忽略），已有 local / spark1 / spark2 | [实测] |
| 硬编码名称问题 | `server.py` 的本地资源默认 label 是写死的字符串（此前为“本地 Windows / WSL”，另一台机器提交后改为 `laptop-5090-24G`）。同一份仓库在不同机器上运行会显示别的机器的名字，正说明缺的是启动自识别，而不是换一个写死的名字 | [源码核验 + 实测] |
| 现有探测 | `Executor.probe()` 已被 `POST /api/resources/{id}/probe` 与 `Runs._prepare_launch` 使用；WSL 只查 python+torch，SSH 只查 env_file、benchmark venv 与 `docker info` | [源码核验] |
| 现有可用性 | 资源卡徽章由 2 秒遥测的 `connected` / `stale` / `unavailable` 驱动，不检查 GPU/镜像/环境变量 | [实测] |
| 前端能力 | `app.js` 已按 `connection.state` 渲染徽章；`stateNames` 与 `styles.css` 已含 就绪 / 可用 / 不可用 / 离线 / 状态未知 | [源码核验] |
| desktop-4080-16G 硬件 | Windows 主机名 `DESKTOP-36NFOE5`；NVIDIA GeForce RTX 4080，16376 MiB，驱动 616.92；WSL 发行版 Ubuntu | [该机器实测] |
| desktop-4080-16G WSL | torch 2.14.1+cu130，CUDA 可用，设备名 RTX 4080；PATH 内没有 `nvidia-smi`；存在 `/usr/bin/docker` | [该机器实测] |
| laptop-5090-24G | 另一台机器（RTX 5090 Laptop、Ubuntu-24.04、解释器 `/root/venvs/duck-wsl/bin/python`）；历史记录由其提交，不能作为本机回退值 | [文档记录] |
| spark1 | `spark-c416`，NVIDIA GB10，20 核，约 121 GiB；docker 29.2.1；benchmark venv 与 env.sh 存在；训练镜像存在 | [SSH 只读实测] |
| spark2 | `spark-752a`，NVIDIA GB10，20 核；docker 28.3.3；benchmark venv 与 env.sh 存在 | [SSH 只读实测] |
| spark2 SSH | 历史上出现过命令已输出但收尾超时；本轮只读查询正常 | [历史记录 / 待复测] |

**受影响的现行入口**：`training/dashboard/README.md`（登记、自识别与探测说明）、`docs/specs/20261106-训练可视化工具/api-contract.md`（`/api/resources` 可用性语义）、`docs/specs/README.md`（本 spec 索引）、`docs/references/本机训练环境/research.md`（按环境记录硬件与探测证据）、`PROGRESS.md`（实施后）。

## 修改方案

### 1. 配置模型：登记 + 身份

在 `training/dashboard.local.json` 的每个节点增加：

- `name`：显示名（缺失时回退 `label`）
- `hardware`：硬件摘要
- `identity`：用于启动自识别的机器标识
  - `hostname`：Windows 主机名（大小写不敏感）
  - `gpu_name`：归一化的 GPU 设备名（可选，用于同名主机区分）
  - `wsl_distro`：WSL 发行版（可选）
- `probe`：`gpu`（`torch` | `nvidia-smi`）、`docker`（bool）、`image`（可选）、`env_keys`（列表）、`benchmark`（bool）、`timeout_s`

登记值（本机一台、Spark 两台）：

| 环境 | name | hardware | identity | probe |
|---|---|---|---|---|
| local | desktop-4080-16G | NVIDIA RTX 4080 16GB / Windows + WSL Ubuntu | hostname=DESKTOP-36NFOE5、gpu_name=NVIDIA GeForce RTX 4080、wsl_distro=Ubuntu | gpu=torch、docker=false、env_keys=[] |
| spark1 | Spark 1 | NVIDIA GB10 / 20 核 / 128GB 统一内存 | 无（远端，不参与自识别） | gpu=nvidia-smi、docker=true、image=nvcr.io/nvidia/pytorch:25.10-py3、env_keys=[NCCL_NET, NCCL_SOCKET_IFNAME]、benchmark=true |
| spark2 | Spark 2 | NVIDIA GB10 / 20 核 / 128GB 统一内存 | 无 | 同 spark1（SSH 经 spark1 中转） |

说明：节点 id `local` 仍表示“平台运行所在主机上的执行目标”，但它的显示名、硬件与探测参数全部来自启动时匹配到的登记项；id 本身不携带机器身份。

### 2. 启动自识别

- 新模块 `training/dashboard/identity.py`：
  - `detect_host()`：取 Windows 主机名（`platform.node()`）、GPU 设备名（优先 Windows `nvidia-smi`，WSL 环境用登记 python 跑 torch）、WSL 发行版列表。
  - `match_environment(nodes, host)`：在带 `identity` 的登记项中匹配 `hostname`；多个候选时再用 `gpu_name` 归一化比较；唯一匹配返回该节点，否则返回 `None` 与原因（未登记 / 重复）。
- 启动时计算一次，结果注入运行期状态，供资源列表、训练启动、CLI 共用；不把结果写回 Git。
- 匹配成功：本机环境显示 `name` 与 `hardware`，执行目标仍用该节点 id。
- 匹配失败：显示“未登记（hostname / GPU）”，不冒充任何已登记环境；本机训练被拒绝，远端 Spark 训练不受影响。

### 3. 探测脚本（登记时生成）

- 新模块 `training/dashboard/environment_probe.py`：按节点配置生成 bash 脚本，写入 `training/.dashboard/probes/<环境>.sh`（运行时目录，Git 忽略，可手工查看）；平台启动和登记时生成/更新，配置变化时重写。
- 检查项：
  - GPU：`torch` 模式用登记 python 断言 `torch.cuda.is_available()` 并输出设备名；`nvidia-smi` 模式查名称与显存。
  - docker：`sudo -n docker info`（SSH）；配置了镜像时校验镜像存在。
  - 环境变量：source 登记的 env_file 后检查 `env_keys` 非空。
  - 其他：python 可执行、benchmark venv、work_root 目录（按节点配置启用）。
- 输出协议：逐项 `CHECK <名称> <ok|fail> <详情>`，最后 `DUCK_PROBE_READY 0|1`；平台解析为结构化结果。
- 执行：`Executor.run_script()` 经 stdin 传递脚本（WSL：`wsl.exe -d <发行版> --exec bash -s`；SSH：`ssh ... 'bash -s'`，兼容 spark2 中转），默认 30 秒超时。

### 4. 可用性与展示（前端零改动）

- 平台启动时探测一次、此后每 60 秒复测；现有刷新按钮与训练启动前均触发即时探测。
- 资源项增加 `readiness`（状态、逐项结果、检查时间、最后成功时间）以及识别结果 `self`；`/api/resources` 将 `connection.state` 映射为：
  - `ready` → 就绪
  - `not_ready` → 不可用
  - `unreachable`（超时/连接失败）→ 离线
  - 从未探测 → 状态未知
- 遥测采样继续负责负载曲线；探测失败不清空历史采样。
- `Runs._prepare_launch` 改用同一探测脚本；未就绪时拒绝启动并输出缺项。

### 5. 命令入口

- `python -m dashboard.cli environments`：列出已登记环境、身份字段与探测脚本路径。
- `python -m dashboard.cli self`：输出本机识别结果（hostname / GPU / 匹配到的环境）。
- `python -m dashboard.cli probe-environment <id>`：立即执行探测并输出逐项结果。
- `python -m dashboard.cli register-environment ...`：写本地配置并生成脚本，供以后新增环境。

### 6. 文档更新

- 实施后更新 dashboard README、api-contract 的可用性语义、`docs/references/本机训练环境/research.md`（按环境名记录，不用“本机”作固定主语）与 `PROGRESS.md`。
- 代码注释与文档不再出现“本机固定名称”的表述；需要指代当前运行时统一写“启动时识别的环境”。

## 风险与回退

- 主机名或 GPU 改名后匹配失败 → 显示未登记，需要重新登记；不能靠写死回退名绕过。
- 平台未来若改在 WSL/容器内启动，`platform.node()` 与 Windows 主机名可能不同；首期只在 Windows 侧启动，限制写入文档。
- 多台同型号 GPU 的机器要靠 hostname 区分；hostname 重复时标记为重复身份，不自动选一个。
- 每 60 秒对 Spark 执行一次 SSH 探测会增加连接次数；探测串行、30 秒超时，失败只标记离线，不影响遥测与训练。
- spark2 若出现历史性收尾超时，将显示离线并记录原因；不以一次超时判定设备损坏或长期不可用。
- 回退：删除节点 `identity`/`probe` 字段即回退到旧的固定 label 与轻量 `Executor.probe()` 逻辑；或整体 revert 本次提交。前端不涉及。

## 检查项（编码后执行，不启动训练）

1. `python -m dashboard.cli self` 在当前公司工作机输出 hostname、GPU 与匹配环境 `desktop-4080-16G`。
2. 代码搜索确认没有硬编码机器名（`laptop-5090-24G` / `desktop-4080-16G` / `本地 Windows / WSL`）作为回退显示值。
3. 生成三份探测脚本，`bash -n` 语法检查通过。
4. 实际执行：desktop-4080-16G、spark1、spark2 均返回 ready；记录逐项结果。
5. 失败注入：临时配置使用不存在的 `env_keys` / 镜像 → not_ready，且不缺项误报。
6. 不可达注入：临时配置指向不可解析主机 → unreachable（离线）。
7. 未登记注入：临时配置换成不存在的 hostname → 启动后显示未登记，不显示任何已登记机器名。
8. 重启平台后 `/api/resources` 的 `connection.state` 与徽章映射正确。
9. 启动前探测拒绝未就绪环境（用临时请求验证，不真正启动训练）。
10. 确认前端文件、训练合同与冻结产物未改动。

## 用户决定（2026-11-10）

- “识别”指当前是否能直接启动训练：本机身份匹配不上就等于没有本机环境，要本地训练必须先登记并搭建；局域网环境连不上就是不可用。
- 身份字段用 `hostname + GPU + WSL 发行版` 已经够用，不增加额外机器指纹。
- 按此实现：未匹配的本机显示“未登记主机”并拒绝本机训练；已登记但探测未通过显示不可用；不可达显示离线。
- 探测脚本放 `training/.dashboard/probes/`（Git 忽略），复测间隔 60 秒，均由实施默认采用，未另提反对。
- 2026-11-10 用户统一环境命名：公司工作机改为 `desktop-4080-16G`（原 4080-16g），另一台改为 `laptop-5090-24G`（原 MSI-laptop）；身份字段与硬件登记不变。

## 变更记录（实施）

新增：

- `training/dashboard/identity.py`：主机名/GPU/WSL 发行版探测与环境匹配。
- `training/dashboard/environment_probe.py`：按登记生成 bash 探测脚本、解析检查结果、写出脚本文件。
- `training/dashboard/check_environment_probe.py`：脚本生成、解析、身份匹配的离线合同检查。

修改：

- `training/dashboard/config.py`：`node_name()` 取登记显示名。
- `training/dashboard/runs.py`：启动时识别本机环境；未登记时拒绝本机校验/启动；构造时生成探测脚本。
- `training/dashboard/server.py`：删除写死的本机回退名；启动/每 60 秒/手动按钮执行探测；`/api/resources` 输出 `self` 与 `readiness` 映射；未登记本机显示“未登记主机”。
- `training/dashboard/executors/remote.py`：`run_script()` 经 stdin 在 WSL/SSH 执行脚本；`probe_result()/probe()` 改用生成脚本。
- `training/dashboard/cli.py`：新增 `self`、`environments`、`probe-environment`、`register-environment`。
- `training/dashboard/config.example.json`：补 `name/hardware/identity/probe` 示例。
- `training/tasks/locomotion-v3.json`：按当前源码刷新 `source_hashes`，并把三个新模块加入 `source_files`。
- 文档：dashboard README、api-contract、本 spec、`docs/references/本机训练环境/research.md`、`docs/specs/README.md`、PROGRESS。

未改：前端文件、物理/接口/奖励合同、训练调度与归档逻辑、冻结历史产物。本机连接配置写在 Git 忽略的 `training/dashboard.local.json`。

## 验证结果（2026-11-10，不启动训练）

- [本机实测] `python -m dashboard.cli self`：hostname `DESKTOP-36NFOE5`、GPU `NVIDIA GeForce RTX 4080`、WSL Ubuntu，matched `local`。
- [本机实测] 三环境探测均 ready：desktop-4080-16G（python/torch CUDA/work_root）、spark1（GB10/docker 29.2.1/镜像/env/venv/work_root）、spark2（GB10/docker 28.3.3/同项）。
- [本机实测] 平台重启后 `/api/resources`：local 显示名 `desktop-4080-16G`、`connection.state=ready`；spark1/2 ready；`self.environment_id=local`。
- [本机实测] 负向：不匹配 hostname → `environment_id=null`、“未登记主机”、offline；缺 python → 不可用并列出缺项；不可达主机 → offline（超时）。
- [本机实测] 未登记配置下 `validate(local)` 返回 `valid=false`，错误为“本机训练环境未登记”。
- [本机实测] v3 任务在哈希刷新后恢复 ready；v2 仍为历史缺项。
- [本机实测] `check_environment_probe.py` 离线检查通过；`dashboard` 模块编译通过；`bash -n` 检查生成的本地脚本通过。
- [基线对照] `check_archive_contract.py` 在刷新 v3 哈希后仍失败于“重建索引后读取运行”断言；在 HEAD 工作树按相同步骤复现，属既有问题，本次未改。
- 未启动训练、未改前端文件、未删除历史归档。

## 偏差与限制

- 原方案未提任务哈希：dashboard 属于 v3 `source_files`，任何代码改动都会使 v3 失配；本次按当前源码刷新哈希，物理/接口/奖励合同未变，旧运行仍使用各自冻结快照。
- 为兼容旧配置/合同测试：配置中完全没有 `identity` 时按旧行为使用 `local`（`state=unconfigured`），不阻止本地训练；一旦存在 `identity` 而匹配失败则按本 spec 拒绝。
- 平台仍在 Windows 侧启动；若改在 WSL/容器内启动，`platform.node()` 与 Windows 主机名不同，需要另行处理。
- 历史运行列表仍为 0（记录对应归档缺失），与本功能无关。
