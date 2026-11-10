# Spec：训练环境登记与启动前探测

- 日期：2026-11-10
- 状态：文档确认（修改方案待批准，尚未编码）

## 需求（2026-11-10 用户确认）

- 平台可登记多个训练环境；环境不保证在任一时刻都能连接。
- 每个登记环境要保存信息（名称、类型、连接参数、硬件），并在平台显示当前是否可用。
- 可用性以启动前能力探测为准：GPU、docker、环境变量；不同环境在登记时生成各自的探测脚本，由脚本判定环境是否准备好。
- 本机训练环境登记到平台，命名 **4080-16g**。
- 平台本身可能部署在多处；当前登记范围为公司工作机（1 个本机环境）与同一局域网的两台 Spark。

**负面范围**：不新增页面内的环境新增/编辑/删除入口，不改前端文件；不改训练合同、调度与归档；不自动重连或自动切换环境；不扫描未登记主机；不提交本地连接配置。

**验收标准**：

1. `local` / `spark1` / `spark2` 均有登记信息，本机显示名为 4080-16g。
2. 每个环境有独立生成的探测脚本，可单独执行并输出逐项结果。
3. 平台可用性随探测结果变化（就绪 / 不可用 / 离线 / 未探测），不可用环境仍显示。
4. 训练启动前强制探测，未就绪时拒绝启动并列出缺项。
5. 复用现有“计算资源”卡片徽章即可显示可用性，前端文件零改动。

## 现状与依据（文档确认）

| 项 | 现状 | 等级 |
|---|---|---|
| 登记载体 | `training/dashboard.local.json`（Git 忽略），已有 local / spark1 / spark2 | [实测] |
| 现有探测 | `Executor.probe()` 已被 `POST /api/resources/{id}/probe` 与 `Runs._prepare_launch` 使用；WSL 只查 python+torch，SSH 只查 env_file、benchmark venv 与 `docker info` | [源码核验] |
| 现有可用性 | 资源卡徽章由 2 秒遥测的 `connected` / `stale` / `unavailable` 驱动，不检查 GPU/镜像/环境变量 | [实测] |
| 前端能力 | `app.js` 已按 `connection.state` 渲染徽章；`stateNames` 与 `styles.css` 已含 就绪 / 可用 / 不可用 / 离线 / 状态未知 | [源码核验] |
| 本机硬件 | Windows 侧 NVIDIA GeForce RTX 4080，16376 MiB，驱动 616.92 | [本机实测] |
| 本机 WSL | torch 2.14.1+cu130，CUDA 可用，设备名为 RTX 4080；PATH 内没有 `nvidia-smi`；存在 `/usr/bin/docker` | [本机实测] |
| spark1 | `spark-c416`，NVIDIA GB10，20 核，约 121 GiB 内存；docker 29.2.1；benchmark venv 与 env.sh 存在；训练镜像存在 | [本机实测，SSH 只读] |
| spark2 | `spark-752a`，NVIDIA GB10，20 核；docker 28.3.3；benchmark venv 与 env.sh 存在 | [本机实测，SSH 只读] |
| Spark 环境变量 | env.sh 定义 NCCL_NET、NCCL_SOCKET_IFNAME、NCCL_IB_HCA、GLOO_SOCKET_IFNAME、HF_HOME 等 | [本机实测] |
| spark2 SSH | 历史上出现过命令已输出但收尾超时；本轮只读查询正常 | [历史记录 / 待复测] |

**与 2026-11-07 记录区分**：那次登记的是 RTX 5090 Laptop 机器；本机是公司工作机的 RTX 4080 16GB，两者硬件、WSL 路径和运行目录不同，不混用历史性能或验收结果。

**受影响的现行入口**：`training/dashboard/README.md`（登记与探测说明）、`docs/specs/20261106-训练可视化工具/api-contract.md`（`/api/resources` 可用性语义）、`docs/specs/README.md`（本 spec 索引）、`docs/references/本机训练环境/research.md`（硬件与探测证据）、`PROGRESS.md`（实施后）。

## 修改方案

### 1. 配置模型（只改本地登记）

在 `training/dashboard.local.json` 的每个节点增加：

- `name`：显示名（缺失时回退 `label`）
- `hardware`：硬件摘要
- `probe`：`gpu`（`torch` | `nvidia-smi`）、`docker`（bool）、`image`（可选）、`env_keys`（列表）、`benchmark`（bool）、`timeout_s`

登记值：

| 环境 | name | hardware | probe |
|---|---|---|---|
| local | 4080-16g | NVIDIA RTX 4080 16GB / Windows + WSL Ubuntu | gpu=torch、docker=false、env_keys=[] |
| spark1 | Spark 1 | NVIDIA GB10 / 20 核 / 128GB 统一内存 | gpu=nvidia-smi、docker=true、image=nvcr.io/nvidia/pytorch:25.10-py3、env_keys=[NCCL_NET, NCCL_SOCKET_IFNAME]、benchmark=true |
| spark2 | Spark 2 | NVIDIA GB10 / 20 核 / 128GB 统一内存 | 同 spark1（SSH 经 spark1 中转） |

### 2. 探测脚本（登记时生成）

- 新模块 `training/dashboard/environment_probe.py`：按节点配置生成 bash 脚本，写入 `training/.dashboard/probes/<环境>.sh`（运行时目录，Git 忽略，可手工查看）；平台启动和登记时生成/更新，配置变化时重写。
- 检查项：
  - GPU：`torch` 模式用登记 python 断言 `torch.cuda.is_available()` 并输出设备名；`nvidia-smi` 模式查名称与显存。
  - docker：`sudo -n docker info`（SSH）；配置了镜像时校验镜像存在。
  - 环境变量：source 登记的 env_file 后检查 `env_keys` 非空。
  - 其他：python 可执行、benchmark venv、work_root 目录（按节点配置启用）。
- 输出协议：逐项 `CHECK <名称> <ok|fail> <详情>`，最后 `DUCK_PROBE_READY 0|1`；平台解析为结构化结果。
- 执行：`Executor.run_script()` 经 stdin 传递脚本（WSL：`wsl.exe -d <发行版> --exec bash -s`；SSH：`ssh ... 'bash -s'`，兼容 spark2 中转），默认 30 秒超时。

### 3. 可用性与展示（前端零改动）

- 平台启动时探测一次、此后每 60 秒复测；现有刷新按钮与训练启动前均触发即时探测。
- 资源项增加 `readiness`（状态、逐项结果、检查时间、最后成功时间）；`/api/resources` 将 `connection.state` 映射为：
  - `ready` → 就绪
  - `not_ready` → 不可用
  - `unreachable`（超时/连接失败）→ 离线
  - 从未探测 → 状态未知
- 遥测采样继续负责负载曲线；探测失败不清空历史采样。
- `Runs._prepare_launch` 改用同一探测脚本；未就绪时拒绝启动并输出缺项。

### 4. 命令入口

- `python -m dashboard.cli environments`：列出已登记环境与探测脚本路径。
- `python -m dashboard.cli probe-environment <id>`：立即执行探测并输出逐项结果。
- `python -m dashboard.cli register-environment ...`：写本地配置并生成脚本，供以后新增环境。

### 5. 文档更新

新增本 spec；实施后更新 dashboard README、api-contract 的可用性语义、`docs/references/本机训练环境/research.md` 与 `PROGRESS.md`。

## 风险与回退

- 每 60 秒对 Spark 执行一次 SSH 探测会增加连接次数；探测串行、30 秒超时，失败只标记离线，不影响遥测与训练。
- spark2 若出现历史性收尾超时，将显示离线并记录原因；不以一次超时判定设备损坏或长期不可用。
- 回退：删除节点 `probe` 字段即回退到旧 `Executor.probe()` 逻辑；或整体 revert 本次提交。前端不涉及。

## 检查项（编码后执行，不启动训练）

1. 生成三份探测脚本，`bash -n` 语法检查通过。
2. 实际执行：local、spark1、spark2 均返回 ready；记录逐项结果。
3. 失败注入：临时配置使用不存在的 `env_keys` / 镜像 → not_ready，且不缺项误报。
4. 不可达注入：临时配置指向不可解析主机 → unreachable（离线）。
5. 重启平台后 `/api/resources` 的 `connection.state` 与徽章映射正确。
6. 启动前探测拒绝未就绪环境（用临时请求验证，不真正启动训练）。
7. 确认前端文件、训练合同与冻结产物未改动。

## 待确认

- 探测脚本放 `training/.dashboard/probes/`（Git 忽略）是否符合预期，或要求入库？
- 60 秒复测频率是否合适？
- `register-environment` 是否本期就要，还是先只做登记 + 探测？
