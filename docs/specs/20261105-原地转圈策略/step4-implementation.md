# 第④步：训练入口实现与验证记录

日期：2026-11-06，Asia/Shanghai。用户已确认参数并要求继续实现。**第④步已完成**：需求、环境和算法方案已连接成可执行、可追溯、可恢复的训练任务，必要本地与双Spark短检查通过。第⑤步正式训练仍未开始。

## 1. 当前状态与分片

| 分片 | 输入与职责 | 已落盘产物 | 验证状态 |
|---|---|---|---|
| A 训练与恢复 | 已确认4096环境、64步、两阶段合计1000更新；PPO、预算和恢复合同 | `locomotion_train_cfg.py`、`train_locomotion.py`、`locomotion_checkpoint.py`、`locomotion_logging.py` | CPU合同、最终本地v3及双Spark64/4096环境更新/恢复通过 |
| B 课程与评估 | 61/14接口、两阶段配比、验收v2.1 | `locomotion_env.py`、`locomotion_cfg.py`、`locomotion_evaluator.py` | 15项合成正反例及环境GPU回归通过；完整行为96回合未运行 |
| C 检查与启动脚本 | A/B API、现有隔离Spark依赖环境 | `check_locomotion_training.py`、`check_locomotion_evaluator.py`、`run_spark_training_check.sh` | CPU双进程Gloo及双Spark64/4096环境保存恢复通过；正式规模短容量通过 |
| R 独立审查 | 上述代码、已确认合同及检查结果 | 审查问题与修复记录 | 输出目录防覆盖、课程切段浮点容差、阶段reset的inference模式及rank本地异常协调已修复并通过对应检查 |

代码位于[本项目训练目录](../../../training/README.md)。各检查JSON包含来源文件SHA256；修改后的代码须对应新的检查记录，不能直接沿用旧哈希的通过结论。

**第④步出口通过**：用户确认输入、代码实现、源码SHA与必要运行检查齐备；双Spark64/4096为两台GB10实机短检查，CPU Gloo证据单独保留。2026-11-06 09:25附近（+08:00）对spark1既有管理地址`192.160.2.51`和档案WiFi地址`192.160.113.159`的SSH连接均超时；09:46只读重查恢复：spark1返回`spark-c416`、spark2以`ProxyJump=none`直连返回`spark-752a`，退出码均0。Windows关闭时的IO warning保留。未修改用户SSH配置，后续两档双机检查均exit0，旧超时不是当前阻塞。

## 2. 当前可执行合同

- 正式规模为全局4096环境，每节点2048，rollout64，每更新262144个新转换；两阶段总上限1000更新、262144000新转换。5个epoch、每rank4个minibatch，共20次同步优化，重复学习不算新经验。
- 同一61维actor/critic、14维动作；两层128单元ELU、Gaussian初始标准差0.30/log；actor和critic分别使用rank本地归一化。PPO参数见[训练方案](training-plan.md)，从零学习，不加载旧walk权重。
- 阶段一100%直走，23秒自然结束。阶段二沿原family顺序采用静止原地20%、直走30%、移动转弯30%、联合15%、保持5%；完整轨迹分别84/31/44/133/20秒。新课程显式选择，旧测速默认课程保留。
- 每100个模型更新保存并评估：阶段一dev9、阶段二dev22；连续两个相邻且不同检查点dev9全通过才切阶段。阶段二直走连续两次低于9/9暂停；每阶段内200更新窗口统计联合后半段，连续两个窗口无覆盖暂停。dev22全通过才发起full96，完整96全部通过才可提前结束。
- `is_finite_horizon=True`，`init_at_random_ep_len=False`，wrapper不预裁剪动作；自然终止不加失败代价。普通rollout/update和联合动作切换不重置物理状态；课程切换/恢复从HOME新回合开始。
- NaN/Inf、保护时限或异常截断使训练停止，普通探索跌倒仅结束该环境回合。SIGINT/SIGTERM请求在完整更新边界保存有效状态；硬崩溃不承诺保存正在更新的模型。

## 3. 预算、文件与恢复

每次运行使用新的`--output`目录；同一实验续训或回滚复用原`--experiment-dir`。预算账本由rank0在采集前写入并`fsync`一整轮的预扣记录，完成后追加完成事件。未完成的预扣保守按整轮计费；回滚旧模型不返还预算，破损账本拒绝继续，不能靠新建账本伪装续训。

检查点保存actor、critic、Gaussian、各自归一化器、Adam、算法当前LR及optimizer参数组、各rank随机状态、课程/门控/诊断计数、模型轮数、已消耗转换和父检查点。配置、world size、源文件、模型和HOME哈希不一致时拒绝混续。

两节点文件系统可以独立：各rank通过Gloo将CPU状态汇集到rank0；rank0原子写入每rank文件并校验全集、轮号、阶段、配置、预算及SHA后，最后写完整manifest。恢复只接受显式manifest，由rank0读取并分发相应rank状态。不存在“自动找latest”或默认共享目录的假设。恢复包含随机状态，但仿真物理状态和旧rollout不恢复，不承诺轨迹逐位重现。

日志包含JSON/JSONL、TensorBoard、源码快照、依赖版本、命令、Git状态读取结果、源文件/模型/HOME哈希；未提交文件也有快照。记录loss、LR、raw动作统计、九项奖励、失败代价和reset前各族/各段覆盖。库未提供的实测KL标为未采集，`desired_kl`不是测量值。

## 4. 入口与操作

以下命令从`training/`目录运行，路径示例须替换成实际目录。它们是复现说明，本记录不代表已执行正式训练。

```bash
# 本地短集成：64环境，两次更新，新的runner恢复后再更新一次
.venv-wsl/bin/python scripts/check_locomotion_training.py \
  --runtime --num-envs 64 --updates 2 --output /absolute/checks/local-runtime.json

# CPU双进程检查，各rank独立目录；不是双Spark训练
.venv-wsl/bin/python scripts/check_locomotion_training.py \
  --collective --output /absolute/checks/cpu-collective.json

# 独立评估指标合成检查，不测策略能力
.venv-wsl/bin/python scripts/check_locomotion_evaluator.py \
  --output /absolute/checks/evaluator-synthetic.json
```

双Spark短检查脚本为`training/scripts/run_spark_training_check.sh NODE_RANK WORKSPACE RUN_NAME [GLOBAL_ENVS] [MASTER_PORT]`。两机分别用rank0/1，相同运行名和端口；示例全局64环境、端口29671。新工作目录内须先同步`project/training`；脚本仅只读挂载既有benchmark依赖目录`/home/yilv/dspark/duck-benchmark-20261106`为`/bench`，新项目/输出挂载为`/validation`，避免改写历史测速代码、数据或依赖。沿用NGC PyTorch 25.10镜像、既有RoCE环境文件和静态torchrun。

本轮在两机独立目录`/home/yilv/dspark/duck-training-check-20261106`完成`dual64-v1`（每机32环境）及`dual4096-v1`（每机2048环境）。64档端口29671，容器名为`duck-training-check-<运行名>-rank0/1`；两档短检容器已正常退出，原监控容器保留。传输包SHA256双方一致：`fee643b51f0f14e0fd9c6e2a4b00dcfebf65e4d6b6c3fba0618afd96c4c78326`。结果JSON与双rank日志已本地归档；rank0远端两档完整产物约16MiB/17MiB保留，包含checkpoint、manifest和源码快照，不把二进制检查点加入版本库。

正式训练使用两节点各一个进程，在相同隔离容器环境启动：

```bash
python -m torch.distributed.run --nnodes=2 --nproc-per-node=1 \
  --node-rank=0 --master-addr=192.168.100.10 --master-port=29681 \
  -m mjlab_duck.train_locomotion --output /work/runs/run-001 \
  --experiment-dir /work/experiments/locomotion-v1
```

另一节点只把`--node-rank`改为1。续训仍由两节点运行，使用全新`--output /work/runs/run-002`，保持原`--experiment-dir`并增加`--resume-manifest /work/runs/run-001/checkpoints/<明确集合>/manifest.json`。manifest路径只需rank0可读；各rank状态由控制通道分发。正式运行要求world size为2；检查模式与正式实验账本不能混用。

暂停后先查看`result.json`、开发评估/诊断或`failure.json`，明确退步、覆盖不足或运行故障；选择保留的完整manifest才恢复。不要改写或删除失败运行，不自动扩大预算、放宽5cm阈值或循环回退重训。

## 5. 已执行检查、失败与限制

| 记录 | 已确认范围 | 不能据此声称 |
|---|---|---|
| [评估合成结果](checks/step4-evaluator-synthetic.json) | 15项正反例：理想轨迹/跨±π、无旋转、零进度、子步漂移/侧偏、制动路径、未覆盖、速度往返抵消、接触和自然终止边界 | 实际策略已会走/转，或96回合通过 |
| [CPU合同与Gloo](checks/step4-cpu-contract-v2.json) | 门控、预算pending/rollback、坏manifest拒绝；2个CPU进程在独立目录恢复不同rank归一化状态 | 两台Spark/NCCL/GPU保存恢复已验证 |
| [环境GPU回归](checks/step4-environment-regression.json) | CUDA两环境、61/14、raw动作历史、奖励、限位、无效数据隔离、reset前终态快照 | 策略行为达标或4096环境容量已重新验证 |
| [首版本地GPU运行](checks/step4-local-runtime.json) | 64环境两更新8192转换，全新runner的actor/critic/normalizer/Adam/LR与固定输入确定性输出一致，续一更新共12288转换 | 最终修订代码已验证、双节点恢复或策略达标；此结果保留旧版本源码SHA |
| [最终CPU及异常协调](checks/step4-collective-errors.json) | 输出目录/嵌套experiment拒绝、两rank独立目录恢复；rank1配置不符、恢复失败、payload生成失败均由两rank同步拒绝 | 真实网络断连或节点硬崩溃一定可恢复；CPU进程不能替代Spark |
| [最终本地GPU运行](checks/step4-local-runtime-v3.json) | 64环境2＋1更新，恢复一致、旧output复用拒绝且未改写、rollout保留状态；真实23秒评估管线及实际阶段切换通过 | 未训练策略直走达标；阶段切换使用合成通过报告验证机制，不是dev9真实通过 |
| [双Spark64环境](checks/step4-spark-dual64.json) | 两台GB10各32环境，2＋1更新、各rank完整恢复/确定性输出一致、跨rollout状态保留、真实评估接线与实际课程切换通过 | 4096容量已验证、dev9晋级或full96策略验收通过；两rank日志分别保存 |
| [双Spark4096环境](checks/step4-spark-dual4096.json) | 各rank2048环境，2更新524288转换，完整恢复后1更新共786432转换；状态恢复与源码SHA一致，两rankexit0 | 正式1000更新已执行或长期稳定；课程切换另用4环境合成门控子检查，真实23秒行为判定仍未通过 |

实现和检查中遇到并已处理：旧版`init_noise_std`字段/错误`contract`观测组不匹配安装API，改用mjlab配置类型、`distribution_cfg`和actor/critic组；`PPO.load`需要显式`load_cfg`；归一化inference tensor复制须在合适模式下恢复，Adam保持可继续更新。浮点`0.10`被严格边界误拒，增加表示误差容差并夹定，未扩大命令范围；[首次环境失败日志](checks/step4-environment-first-failure.log)保留。

[CPU Gloo首次尝试](checks/step4-cpu-collective-attempt1.json)中两个worker等待且未生成rendezvous文件，仅停止本检查进程后改ASCII临时rendezvous并加超时，复测通过。中文`Path.as_uri`编码造成FileStore路径不匹配是当时假设，未独立证明，不能写成已确认根因。

独立审查提出的output覆盖和命令切段浮点边界已修复。第二版本地运行在真实阶段切换的`_environment_stage → env.reset`处因inference tensor原地清零失败，见[失败日志](checks/step4-local-runtime-v2.log)；现改为inference模式reset，第三版重测通过，不覆盖v2失败证据。各rank本地payload/配置/恢复异常也增加同步协调，CPU故障注入通过；不承诺硬崩溃一定保存成功。

首版本地检查约260秒，其中两次WSL Git状态读取各耗时超过100秒；元数据读取现设15秒timeout，超时显式记`git_error`，不能写成仓库干净或PPO本身耗时。最终本地v3及双Spark64/4096环境短集成exit0；真实23秒直走评估`passed=false`，说明评估接线可运行且该短训模型尚未达标。最终记录的所有源码SHA均与当前文件一致，独立审查无阻塞。第④步完成；正式1000更新、候选策略full96验收和实物验证均未执行。全部修改保留工作区，未提交、未推送。

`MUJOCO_LOG.TXT`保留拼接阶段integrator parent/child不同的提示。[源码核对] 编译后`MujocoCfg.apply`设置`model.opt.integrator`为配置的`implicitfast`，随后才创建数据和Warp；该提示不能直接推出训练使用了错误积分器。这是调用链核对，不是新增运行时字段实测。
