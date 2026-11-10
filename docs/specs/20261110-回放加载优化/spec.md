# 检查点回放加载优化 Spec（2026-11-10）

## 1. 现象与范围

用户反馈"检查点回放加载很慢"。本机实测 2026-11-10 上午，五个已有回放会话从创建到首帧：

| 回放 | 检查点 | 创建→首帧 |
|---|---|---|
| migration-validation-gait020 | amplitude-20261107-gait020 final_000100 | 61.9 s |
| bb6f6817… | 同上 | 64.7 s |
| 53dd7443… | 同上 | 71.6 s |
| 70c6636c… | 同上 | 81.2 s |
| a33fedd1… | history-0c644b checkpoint100 | 61.2 s |

现象层：[实测] 回放窗口打开后 60–80 秒内没有机器人画面。`studio-model.js` 在首帧前 `root.visible=false`，因此这段时间窗口确实是空的。

范围仅限**回放加载链路**；不改冻结的时间步、观测、动作、checkpoint 合同与策略，不改训练入口。

## 2. 诊断（2026-11-10 本机实测）

同一 WSL 解释器、同一依赖栈（`torch, tensordict, rsl_rl.models, mjlab, mujoco_warp, warp`）导入耗时：

| 位置 | 冷缓存 | 热缓存 |
|---|---|---|
| `/mnt/c/Projects/duck-robot/training/.venv-wsl`（DrvFs） | 42.8 / 43.0 s | 46.8 / 49.6 s |
| `/root/venvs/duck-wsl`（ext4，复制自同一 venv） | 8.0 / 9.3 s | 6.0 / 6.4 s |

复制 9.9 GB venv 从 `/mnt/c` 到 ext4 用时 948.9 s（约 10 MB/s）。

分阶段探针（`probe-env.py`，单一进程内顺序计时）：

| 阶段 | 耗时 |
|---|---|
| import torch | 19.63 s |
| import tensordict/rsl_rl/mjlab | 51.12 s |
| torch.load checkpoint | 0.06 s |
| import mjlab_duck | 0.26 s |
| build actor | 0.19 s |
| build env | 1.92 s |
| reset | 0.27 s |
| first step | 0.52 s |
| 后续 20 步 | 1.59 s（约 80 ms/步） |

结论：[实测] 冷启动约 95% 时间耗在 Python 导入，导入的主要代价来自 `/mnt/c` 跨盘 9P I/O；建环境、载权重、reset、首步合计约 3 秒。另有两点旁证：
- [实测] `a33fedd1…` 回放结束后 worker 仍存活 4 小时 53 分、常驻 2 GB 内存并占用 GPU（会话状态 completed，直至手动关闭）。
- [实测] 用 Windows PowerShell 写出的 `controls.json` 带 UTF-8 BOM，worker 的 `json.loads` 抛错后被静默 `continue`，关闭指令未生效。

## 3. 需求与验收

必需：
1. 首帧延迟：冷启动（清页缓存）≤ 15 s，热启动 ≤ 8 s；同一检查点连续回放稳定不劣化。
2. 回放结束后的 worker 必须在可配置的空闲时间后自行退出并释放 GPU，不依赖用户点关闭。
3. 控制文件解析须容忍 UTF-8 BOM，非法内容不得让 worker 每 40 ms 空转且无任何诊断。
4. 回放的冻结合同不变：仍校验 manifest、rank 文件 SHA、冻结源码 SHA；不改变 mjlab 时间步和动作接口。
5. 旧入口不因 venv 迁移而中断：工作台配置、`play-mujoco.ps1` 指向新路径；旧 `/mnt/c` venv 暂留作回退。

非目标：
- 不改播放步进性能（当前 1 倍速实际约 0.37× 实时，23 s 片段约 62 s 播完），此项另立任务。
- 不改前端视觉与 Studio 模型显示逻辑。
- 不删除历史研究材料与原始证据。

## 4. 实施

1. WSL venv 迁移：`training/.venv-wsl`（DrvFs）→ `/root/venvs/duck-wsl`（ext4）。不改依赖版本；迁移后 `import torch` 与 `torch.cuda.is_available()` 核验通过。
2. 工作台 `training/dashboard.local.json` 的 `nodes.local.python` 指向新路径；`config.example.json` 补充说明。
3. `training/play-mujoco.ps1` 按 `DUCK_WSL_PYTHON` → 新路径 → 旧路径顺序解析解释器。
4. `training/dashboard/replay_worker.py`：
   - 新增 `--idle-timeout`（默认 300 s，0 表示禁用）；episode 完成（completed）后计时，超时写 `closed` 并退出。
   - 控制文件按 `utf-8-sig` 读取；解析/字段错误按可重试处理，不再让异常终止会话。
5. `training/dashboard/replays.py`：把配置项 `replay_idle_timeout_s`（默认 300）传给 worker。
6. 文档：`training/README.md` 环境与启动说明、`docs/references/本机训练环境/research.md` 记录迁移与测量、`PROGRESS.md` 当日结论。

## 5. 验证

- [实测] 首帧：用历史 checkpoint `history-0c644b checkpoint100` 经工作台 API 创建回放，记录创建→首帧时间；关闭后确认无 worker 残留、GPU 0 MiB。
- [实测] 空闲退出：worker 以 `--idle-timeout 5` 跑完一个完整 episode（约 23 s 仿真），确认完成后约 5 s 退出、状态 `closed`、GPU 释放。
- [实测] BOM 控制：向运行中的回放写入带 BOM 的 `controls.json`，确认会话按指令关闭。
- 冻结合同：上述回放仍通过 manifest、SHA 与冻结源码校验；不改变 checkpoint 或策略。

## 6. 风险与回退

- venv 位于 WSL ext4，WSL 发行版重置会丢失；重建步骤沿用 `docs/references/本机训练环境/research.md` 的锁定版本，旧 `/mnt/c` venv 暂留可直接回切配置。
- 迁移只在当前 WSL `Ubuntu-24.04` 生效；其他发行版需自行指定 `distribution` 与 python 路径。
- 空闲超时只关闭已完成的会话；暂停中的会话不自动释放，避免误关正在观察的画面。

## 7. 状态

2026-11-10 已完成环境迁移、配置与 worker 健壮性修改。验证结果：首帧 4.8 s（热缓存）、9.1 s（清页缓存冷态），空闲 5 s 超时释放、BOM 控制生效、工作台端到端关闭后 GPU 归零。播放吞吐（约 0.37× 实时）与前端预览未改，留待后续任务。详见[实施记录](implementation-record.md)。
