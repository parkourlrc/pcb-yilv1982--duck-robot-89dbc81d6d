# 回放加载优化实施记录（2026-11-10）

## 1. 变更

| 文件 | 变更 |
|---|---|
| `/root/venvs/duck-wsl`（WSL ext4，不在版本库） | 由 `training/.venv-wsl` 复制迁移，依赖版本不变；`import torch`、`torch.cuda.is_available()` 通过 |
| `training/dashboard.local.json`（Git 忽略） | `nodes.local.python` → `/root/venvs/duck-wsl/bin/python` |
| `training/play-mujoco.ps1` | 解释器按 `DUCK_WSL_PYTHON` → `/root/venvs/duck-wsl/bin/python` → `training/.venv-wsl/bin/python` 顺序解析 |
| `training/dashboard/replay_worker.py` | 新增 `--idle-timeout`（默认 300 s，0 禁用）；完成后超时写 `closed` 并退出；控制文件按 `utf-8-sig` 读取，解析/字段错误按可重试处理 |
| `training/dashboard/replays.py` | 创建 worker 时传 `--idle-timeout`（取配置 `replay_idle_timeout_s`，默认 300） |
| `training/dashboard/config.py` / `config.example.json` | 新增 `replay_idle_timeout_s` 默认 300 |
| `training/README.md`、`training/dashboard/README.md`、`training/dashboard/runtime_protocol.md` | 解释器位置、冷启动实测、空闲释放与控制文件编码说明 |
| `docs/references/本机训练环境/research.md`、`PROGRESS.md` | 测量、处置与限制落盘 |

未改：冻结源码、checkpoint、观测/动作接口、物理步长、Studio 显示、前端视觉。

## 2. 验证证据

### 2.1 导入对照（WSL Ubuntu-24.04，同一 venv 内容）

栈：`import torch, tensordict, rsl_rl.models, mjlab, mujoco_warp, warp`

| 位置 | 冷缓存（drop_caches） | 热缓存 |
|---|---|---|
| `/mnt/c/.../training/.venv-wsl` | 43.042 s / 42.789 s | 49.607 s / 46.824 s |
| `/root/venvs/duck-wsl`（ext4） | 9.343 s / 8.033 s | 6.372 s / 5.995 s |

复制：`cp -a training/.venv-wsl /root/venv-ext4` 用时 948.867 s（9.9 GB）。

### 2.2 分段（`training/.dashboard/probe-env.py`，历史 checkpoint final_000100）

```
import torch: 19.63s
import tensordict/rsl_rl/mjlab: 51.12s
torch.load checkpoint: 0.06s
import mjlab_duck: 0.26s
build actor: 0.19s
build env: 1.92s
reset: 0.27s
first step: 0.52s
20 more steps: 1.59s
```

### 2.3 优化前后首帧

| 场景 | 首帧 |
|---|---|
| 优化前 5 个会话 | 61.2 / 64.7 / 71.6 / 81.2 / 61.9 s |
| 迁移并通过 API 创建（旧代码） | 4.6 s |
| 重启工作台加载新代码后复测 | 4.8 s |
| `drop_caches` 冷缓存后复测 | 9.1 s |

冷、热两项均满足 Spec 验收（冷 ≤15 s、热 ≤8 s）。

### 2.4 空闲释放（`--idle-timeout 5`，手动运行）

```
completed 13:26:25 → closed 13:26:30（5 s）→ 进程退出，GPU 0 MiB
```

### 2.5 控制文件 BOM 容错

运行中写入带 UTF-8 BOM 的 `controls.json` `{"seq": 1, "action": "close"}`：3 秒内状态转 `closed`、worker 退出。修复前同一操作会因 `json.loads` 失败被静默忽略。

### 2.6 工作台端到端

- `POST /api/replays` 使用 `history-0c644bb9471038a9fd18-checkpoint100`：首帧 4.8 s，worker 命令行含 `--idle-timeout 300`。
- `DELETE /api/replays/{id}`：状态 `closed`，无 worker 残留。
- `POST /api/resources/local/probe`：`connected`，返回 `NVIDIA GeForce RTX 5090 Laptop GPU`，证明配置的新解释器可执行。
- 修复前滞留的 `a33fedd1…` worker（运行 4 h 53 min、约 2 GB RSS）已按控制文件关闭，GPU 由 418 MiB 归零。
- `training/play-mujoco.ps1` 保存为 UTF-8 with BOM，用 Windows PowerShell 5.1 解析 0 错误。
- 分段探针脚本位于 `training/.dashboard/probe-env.py`（Git 忽略的本地临时脚本），不属于产品代码。

## 3. 限制与后续

- `python -m dashboard.check_backend` 在当前工作区和 `HEAD`（e210fa42）的独立 worktree 都失败（本工作区停在 stop 断言，HEAD 停在 resume 断言），与本轮改动路径无关；该检查当前不作为绿色门，未在本次修复。
- 新 venv 位于 WSL ext4，发行版重置会丢失；重建按 `docs/references/本机训练环境/research.md` 的锁定版本执行。旧 `/mnt/c` venv 暂留回退（9.9 GB），验证稳定后可另行确认删除。
- 本次只优化加载，未改播放吞吐：23 s 仿真片段实测约 61.6 s（约 0.37× 实时，18.7 帧/秒）。若要接近实时，需要另立任务分析每步约 80 ms 的构成（管理器开销、Warp 同步、帧写出）。- 首帧前前端仍隐藏机器人（`root.visible=false`），窗口显示"等待真实仿真姿态…"。当前等待已缩短到约 5–12 s，未改前端；若仍需改善感知，可另立任务加静态预览与进度。
