# 百轮步幅参数实验

> 最新用户约束：Kd固定2，历史Kd试验已停止并封存，含Kd变更的组合不得再运行。`prepare.py`已拒绝damping!=2，`run_parallel.py`当前仅开放ema010；下文原列表为历史实验记录。

2026-11-07用户在参考步态分析后明确“试试”：新增`prepare_gait.py`、`gait.py`、`run_gait.py`执行独立足部奖励/渐进平滑四组百轮，不改变物理层；这套入口与旧`run_parallel.py`分开。方案见spec末节，状态、必要检查与结果见[足部奖励百轮对照](../../../docs/references/自主训练平台/足部奖励百轮对照-20261107.md)。新增`check_gait.py`及`check_gait_airborne.py`仅验证测量/物理一致性，`snapshot_gait.py`只读进度；既有`compare.py`仍用于真实接触起落的复核。

实施依据：[已批准 spec](../../../docs/specs/20261107-步幅参数优化/spec.md)。本目录自建工具仅用于仿真，现行 `mjlab_duck` 与第三方依赖文件保持原样。

`prepare.py` 核验原冻结基线的每项 SHA，创建不允许覆盖的独立目录，复制源码并施加精确锚点补丁。训练和评估读取同一 `variant.json`；参数、生成器和诊断脚本加入 checkpoint 合同 SHA。仅支持固定的批准候选，保持 4096 环境/64 步/100 更新，seed 可为配对复核指定。

| preset | alpha | 平滑权重 | Kd |
|---|---:|---:|---:|
| baseline | 1 | 0.05 | 2 |
| ema025 | 0.25 | 0.05 | 2 |
| ema050 | 0.5 | 0.05 | 2 |
| smooth020 | 1 | 0.2 | 2 |
| kd100 | 1 | 0.05 | 1 |

alpha=1 的默认分支保留原目标计算语句；其余两参数默认数值与原值相同，reset 增加的滤波缓冲不进入默认计算。滤波处理限幅后的 raw，初值 0，reset 清零；目标依旧受实际关节限位约束。保留原 raw 上一动作观测，**未额外观测滤波器状态**，因此滤波实验包含此记忆状态的影响；不能外推为单纯频率响应改善。质量、惯量、摩擦、刚度、力矩上限均不改。

`diagnose.py` 严格校验 checkpoint 与冻结源码，在同一 seed/命令下冻结 actor 和归一化。与训练一致设置单 CPU 线程、TF32 关闭；通过实例方法包装记录实际 PD 输入及输出、现有子步测量之后的关节状态和接触几何。原 PD 返回值原样送回，不修改依赖源码或动力学。脚底离地用碰撞盒最低点；接触由有效地面-足部 pair 且距离≤0定义，接触点水平速度由刚体线/角速度计算，不冒充接触力。连续 20 个物理子步离地 >3 mm 且无接触计作 ≥40 ms 事件；至少两次同脚事件才计算逐周期关节摆幅。

每组训练沿用现有预算账本/保存/评估，额外在连续 5 次更新 raw 裁剪率>50%时写 STOP，在本更新边界保存退出；`amplitude_stop.json` 说明提前退出原因。提前退出不能算完整百轮。

WSL 示例（各运行名须唯一）：

```bash
python training/experiments/amplitude/prepare.py --source /root/duck-training-runs/amplitude-20261107-baseline/frozen --destination /root/duck-training-runs/amplitude-20261107-ema025-s42 --preset ema025 --seed 42
cd /root/duck-training-runs/amplitude-20261107-ema025-s42/frozen/training
/mnt/c/Projects/duck-robot/training/.venv-wsl/bin/python -u -m mjlab_duck.train_locomotion --config ../../config.json --output ../../run --experiment-dir ../../experiment
```

诊断使用该组冻结的 `training/experiments/amplitude/diagnose.py --base RUN_BASE --output NEW_OUTPUT --render`。原基线未携带新诊断脚本，可用本目录脚本读取，诊断输出单独记录脚本 SHA，不改旧模型合同。

2026-11-07用户要求“一次多测一些方向”后，`run_parallel.py`增加6个滤波/阻尼方向，以3个新增槽加原队列1槽并发：`kd075`、`kd050`、`ema010`、`ema025_kd100`、`ema050_kd100`、`ema025_kd075`。各组独立从零100更新，组合组用于检验交互影响，不冒充单因素结论。配置仍完整冻结并加入合同；不改变奖励定义。任一新增工作进程非零退出时，停止后续排队组的启动，保留其他已启动组及全部账本。并发对吞吐有影响，不用于和独占运行比较算法速度。

## 2026-11-08足部对照收尾

四组各100更新、dev9、三场500Hz诊断及50fps视频已完成，四组dev9均0/9；20mm组仅在2/3场景形成有效迈步，不能宣布小摆幅解决。`summarize_gait.py`汇总实际预算及合格起落，`detail_gait.py`提取奖励、实际/周期幅度、接触间隙和分档dev9，`plot_gait.py`出图，`inspect_gait_video.py`保存视频SHA和六时刻取帧。上述分析脚本不改变策略或训练参数。

完整结果见前述[足部奖励百轮对照](../../../docs/references/自主训练平台/足部奖励百轮对照-20261107.md)。新增[航向罚项提案](../../../docs/specs/20261107-步幅参数优化/航向约束下一轮提案.md)待确认，未实现，不属于当前已运行预设。
