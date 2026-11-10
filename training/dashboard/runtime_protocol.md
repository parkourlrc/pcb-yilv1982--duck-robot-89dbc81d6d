# 训练与回放进程协议

2026-11-06，第⑤步工具实施。以下数据来自仿真，不驱动实物。

## 训练

工作目录为冻结源码根的 `training/`：

```text
python -m mjlab_duck.train_locomotion --config CONFIG.json --output RUN_DIR --experiment-dir EXP_DIR --run-id ID --stop-file STOP_PATH
```

配置文件为 `LocomotionTrainConfig` 直接字段；允许缺省字段使用任务默认值。`stage1/stage2` 可从完整配置 JSON 反序列化。新任务将 `eval_interval` 默认设为 `save_interval`；正式模式支持 world size 1 或 2。双节点仍由 torchrun 提供 RANK/WORLD_SIZE/LOCAL_RANK。

续训追加 `--resume-manifest manifest.json`，使用原 experiment/账本和相同完整合同，输出目录必须新建；预算不随 checkpoint 回退返还。`--max-new-updates` 仅限制本段更新数，不增加总预算。停止为创建 `--stop-file` 指定文件（默认 `RUN_DIR/STOP`），或向该训练进程投递 SIGTERM/SIGINT。更新边界统一检查，评估结束后可停止，保存最终完整 manifest。

初始化发生在创建正式 RUN_DIR 之前，心跳写同级 `RUN_NAME-startup/status.rankN.json`；失败也记录在那里。进入训练后使用 `RUN_DIR/status.rankN.json`，一秒刷新 UTC/elapsed，phase 为 initializing/training/evaluating/saving/stopping/stopped/completed/failed。对应事件存 `events.rankN.jsonl`，rank0 另写 `events.jsonl`；字段含 run_id/rank/seq/utc/elapsed_s/phase。连接状态由控制面单独推断，不更改持久运行终态。

逐轮 `updates.jsonl` 保留原日志字段，增加 UTC、elapsed、seq、采样吞吐、全程吞吐和最近100个完整回合的 return/length均值及实际样本数。`episodes.rankN.jsonl` 记录跨 rollout 累积的完整 return 和控制步数；恢复/课程重置后的未完成片段丢弃。跨 rank 同一更新内按 `rollout_step` 排序，同一步再按 rank/env_id 决定窗口边界；不同更新按实际完成的更新顺序追加，JSON明确此作用域。

按 C 保存，按 E 评估；评估前保存候选，评估后保存门控状态。`state.last_evaluation` 保留精确候选/轮次/阶段/通过数；最终 checkpoint 是否刚评估可由 iteration 对照判断。课程、物理、奖励、PPO参数未改。

评估后若尚有课程/暂停/full_reference决定待执行，该 `evaluated` manifest明确写 `resumable=false`、`pending_decision`及原因，完整rank文件仍可推理；续训选择执行决定后的final或stage2 checkpoint。训练底层也拒绝恢复该中间状态，避免先多采样一轮才执行既有决定。字段缺省的旧v1保持原兼容边界。

## 回放

```text
python training/dashboard/replay_worker.py --manifest MANIFEST --runtime-root ROOT --session-dir DIR --replay-id ID --scenario straight_0.06_101 --seed 101 --idle-timeout 300
```

`--checkpoint` 等价 `--manifest`（允许目录），`--output-dir` 等价 `--session-dir`。可选 `--rank 0 --device cuda:0 --task-version v1`。运行根含 `training/mjlab_duck`；默认先找原 run 的 sources，v1 再找 `training/runtime_versions/locomotion-v1`。严格检查所选rank文件SHA、manifest身份、原合同SHA与全部冻结源；仅载 actor和归一化，不载训练器或预算。支持只有所选rank缓存的推理，但不能因此宣称完整恢复。

控制面原子替换 `controls.json`（兼容 `control.json`），字段 `{seq,action,speed}`；seq单调递增。action 为 pause/play/reset/speed/close（兼容 resume/set_speed/stop），speed仅0.5、1、2。兼容generation作为缺省seq，但推荐明确seq。物理步长保持0.02秒；reset固定同场景seed并增加输出generation，暂停/倍率不增加generation。创建 STOP文件同样关闭。

输出 `latest-frame.json` 原子最新帧和 `frames.jsonl` 增量帧，均为真实仿真采样。字段：

- replay_id、generation、seq、utc、sim_time_s、模型轮次/来源rank/scenario/seed。
- root_position_m为xyz；root_quaternion_wxyz为wxyz。
- joints_rad按名称映射14关节；Studio mouth由显示层固定，不新增训练动作。
- command为 `[vx,vy,wz]`，单位m/s、m/s、rad/s；actual包含velocity_m_s `[vx,vy]`、yaw_rate_rad_s、roll_pitch_rate_rad_s、yaw_rad。
- attitude包含从完整root quaternion求得的roll_rad/pitch_rad/yaw_rad。任务内部rp是角速度，不冒充姿态角。
- episode_return/episode_length、failed/reason/completed、speed、actual_realtime_factor。实际倍率以本次reset后活跃步进耗时计算，包含显示限速，排除初始化和暂停。

status.json状态为initializing/playing/paused/completed/closed/failed，每秒心跳；完成保留会话以允许reset，close才释放进程。新增 `--idle-timeout`（默认300秒，0禁用）：episode完成后超过该时长无reset则写 `closed`、关闭环境并退出，避免忘记关闭的窗口长期占用GPU。控制文件按UTF-8读取并容忍BOM；解析失败的写入被忽略并在下一轮重试，不让瞬时坏文件终止会话。stdout/stderr为日志，不能作为帧JSON通道。每个worker独占自己的会话目录、GPU环境与控制序号。

WSL写Windows盘时，Windows读取可能短时阻止`os.replace`。回放姿态/状态文件短重试后仍被占用则保留旧目标、丢弃本次替换并清理临时文件；下一帧/心跳重试，不因单帧文件竞争杀死仿真。连续竞争仍会表现为心跳过期，控制面不得伪装最新数据。

## 本轮局部检查

冻结v1合同9文件SHA全部与原正式run匹配。Python语法检查、JSON配置往返、跨两次采样累积完整episode return/length通过。旧第100轮rank0 checkpoint在本地WSL运行至模拟20.74秒后执行reset，验证generation=1、pause、2倍play、close与14关节/根位姿输出；该次未完成23秒整场，不能按等待时长声称完成。第1000轮另完成23秒确定性场景并校验actor/normalizer保持冻结，completed只表示场景走完，不表示行为阈值通过。未启动训练或消耗新训练转换预算。三模式短训及四窗验收由主会话协调。
