# 训练与回放接口核对

- 核对日期：2026-11-06。
- 范围：第⑤步训练网页实施前的本地源码只读分析；本文不构成新训练、恢复或回放验收。
- 证据等级：以下为源码核验，非本轮实测。WSL 清单读取仅确认 Ubuntu 处于 Running，不确认 GPU 或依赖可用。

## 训练入口

| 文件与定位 | 当前行为 | 实施约束 |
|---|---|---|
| `training/mjlab_duck/train_locomotion.py`，`build_runtime` | 按 `WORLD_SIZE` 分配全局环境数，检查每 rank 的 rollout 批量可被 mini-batch 数整除。 | 正式单机支持可复用此逻辑；`main` 和 `train_loop` 另有正式模式必须双 rank 的限制，两处须一致更新。 |
| 同文件，`train_loop` | `save_interval` 同时触发保存、开发评估和连续相邻评估门控。 | 保存与评估分开后，课程相邻性应使用 `eval_interval`；评估前候选和评估后课程状态都保留。 |
| 同文件，停止处理 | SIGINT/SIGTERM 置位，更新完成后 all-reduce 统一停止，保存 final manifest。 | 网页监督器必须标识具体作业，不按模糊进程名停止；双 rank 都退出才可标完成。 |
| `training/mjlab_duck/locomotion_logging.py`，`RolloutStatistics` | 每更新重新建立统计，终态记录含时间、原因和任务指标，未累计完整 episode return/控制步数。 | 需要跨 rollout 保留每环境 episode 累加器；恢复从 HOME 新回合开始，不把中断片段当完整回合。 |

## 旧来源与恢复

`training/mjlab_duck/locomotion_checkpoint.py` 的 `CONTRACT_FILES` 包含训练入口、配置、统计及 checkpoint 实现本身。修改这些文件会改变新合同，旧 checkpoint 不能直接用新源码恢复。

原正式运行的已归档来源哈希与配置位于 `docs/specs/20261105-原地转圈策略/checks/step5-run-001/run.json`；原远端工作根由 `step5-training-status.json` 记录为 `/home/yilv/dspark/duck-training-formal-20261106`。这些是历史来源定位，实际访问能力和文件存在须现场核验。冻结旧版本应依据该运行 `source_sha256`/`contract.sources` 核验，不能直接拿任意本地历史快照认作匹配版本。

`restore_payload` 会检查完整配置、源码和 world size 的合同哈希；`load_collective` 还检查原实验身份及预算账本。展示适配不得删除这些检查。纯推理读取 rank0 时保留双 rank 来源身份，不能用单 rank 新合同伪装完整续训。

## 联合任务回放

- `training/mjlab_duck/playback.py` 属于旧 `duck_walk`，不是本轮联合任务适配器。
- `training/scripts/diagnose_locomotion_run.py` 的 `replay` 已有联合任务 actor-only 路径：先核对 rank0 文件 SHA 和原合同源码，再以 `rsl_rl.models.MLPModel` 建立 61 维输入、14 维输出、两层 128 单元 ELU、观测归一化和 Gaussian log-std 分布，严格载入 `actor_state_dict`。
- 原实现使用 `actor.eval()`、`torch.inference_mode()` 和 `stochastic_output=False`，回放后比对完整 actor 状态，覆盖归一化冻结。
- `locomotion_evaluator.evaluate_episode` 的原生环境路径为 `locomotion_env_cfg(1, evaluation=True, seed=...)`，随后 `env.reset(seed=...)`、`command.set_fixed_schedule(scenario.segments)`。该环境关闭 auto-reset 并采集物理子步。
- `diagnose_locomotion_run.py` 采集 `env.sim.data.qpos[0]`；网页姿态应转为明确的世界位置、wxyz 四元数和名称关节。14 个训练关节不包含 Studio `mouth`。
- 已有 `checks/step5-diagnostic-replay/trace-100.npz` 与 `trace-1000.npz` 可核对显示映射，属于历史轨迹，不能标作本轮实时仿真。

## 尚待实施与验证

尚未执行 GPU 训练/回放、远端文件同步、旧源冻结或显示坐标核对。以上核验仅确定可复用代码与修改边界；实际参数/依赖版本、旧 checkpoint 完整性、Studio 根变换及多窗口资源释放仍需对应实施检查。
