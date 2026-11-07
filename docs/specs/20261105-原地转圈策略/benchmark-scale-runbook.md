# 第④步扩大工作量短测速

日期：2026-11-06（本机Asia/Shanghai；上下文日期2026-11-05）。用户要求“加大工作量，再对比看看”，本轮执行256、1024、4096全局环境，比较RTX4080/WSL、单Spark（spark2）、双Spark（每机全局环境的一半）。原64基线保留；正式64环境×2000轮预算不变。

## 结论与计量

三档全部完成，无OOM、无非有限数值失败。主比较采用加载同一`train-gx10/env.sh`的`single-env`补跑，所有吞吐均为`aggregation.global_transitions_per_s`，即5窗总转换数/5窗总耗时；不是每轮样本/中位耗时的另一列。

| 全局环境 | 每轮样本 | 本地转换/秒 | 单Spark转换/秒 | 双Spark转换/秒 | 双/单 | 双/本地 |
|---:|---:|---:|---:|---:|---:|---:|
| 256 | 16384 | 5866.00 | 9457.22 | 9855.77 | 1.042× | 1.680× |
| 1024 | 65536 | 18451.87 | 26632.86 | 31227.55 | 1.173× | 1.692× |
| 4096 | 262144 | 41040.05 | 46332.98 | 75490.74 | 1.629× | 1.839× |

| 全局环境 | 本地中位秒/轮 | 单Spark中位秒/轮 | 双Spark中位秒/轮 |
|---:|---:|---:|---:|
| 256 | 2.746176 | 1.732048 | 1.664186 |
| 1024 | 3.514812 | 2.460681 | 2.101649 |
| 4096 | 6.361396 | 5.672361 | 3.478775 |

[实测] 在此次工作量扫描中，双机相对单机吞吐收益随全局环境数增加，从约4.2%升到17.3%、62.9%。[建议/推断] 如果后续采用4096环境，双Spark值得优先选择；当前正式方案仍为64环境，本轮不自动扩预算或修改训练方案。256的小差距需谨慎解释；每组只有一次运行的连续5窗，不是5次独立实验，不能给出稳定加速保证。

本地4096的窗口从6.711降至6.091秒，单Spark从5.738降至5.570秒，说明短窗仍存在变化；本次不是热平衡后的长期基准。每环境总采集7×64×0.02=8.96秒（可能中途失败reset），不覆盖60秒原地转或133秒联合轨迹。不同规模PPO每轮样本/minibatch大小也改变，吞吐增长不等于收敛更快、5cm更易达标或正式训练总时间同比下降。

## 保持项、差异与原始证据

沿用原`benchmark_locomotion.py`，任务、物理、奖励、61/14接口、actor/critic128×128、每环境rollout64、5epoch/4minibatch、种子及FP32/TF32关闭不变。每组2预热＋5计时，每轮仍20次优化；三档单次minibatch的全局样本分别4096/16384/65536，双机各rank为其一半。不同设备阶段串行；没有单/双Spark同时占用相同GPU。

主要原始JSON：

- 本地：[256](benchmark-scale-local-256.json)、[1024](benchmark-scale-local-1024.json)、[4096](benchmark-scale-local-4096.json)。本地stdout仅在执行会话，未额外捕获完整文本日志；JSON保存所有计时与每窗done/raw超界/loss/有限检查，不能宣称已保存本地完整stdout。
- 对齐单Spark：[256](benchmark-scale-single-env-256.json)、[1024](benchmark-scale-single-env-1024.json)、[4096](benchmark-scale-single-env-4096.json)。对应`benchmark-scale-single-env-{规模}.log`均归档。
- 双Spark：[256](benchmark-scale-dual-256.json)、[1024](benchmark-scale-dual-1024.json)、[4096](benchmark-scale-dual-4096.json)。`benchmark-scale-dual-{规模}.log`为rank0，`benchmark-scale-dual-{规模}-rank1.log`为rank1，均归档。
- 初次单Spark`benchmark-scale-single-{规模}.json/.log`保留为未对齐容器env的补充数据，其吞吐9382.51/26703.30/46339.62，不用于主表。初次未设置env-file、memlock/stack限额与infiniband设备；补跑与dual对齐这些启动参数。主表256远端曾命名`single-aligned-256`，回收时文件名映射为`single-env-256`，JSON label仍保留原名；内容未改写。

本地torch2.14.1/tensordict0.15.1/NCCL2.30.7，Spark torch2.9.0a0/tensordict0.10.0/NCCL2.27.7；主要任务依赖相同，未重装或升级。主表单/双Spark均加载原env-file的`PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`等值；单机world_size=1，不初始化跨机通信，NCCL网络变量不代表单机有网络同步。双机按既有IB配置运行，但WARN日志无实际NET/IB选路详情；不宣称复测四口RoCE。

双机归一化与优势仍按rank本地样本计算，seed按42+rank；不同done/clip不能当作行为或质量排名。5项输入SHA256、版本、初始化/预热和每窗数值详见各JSON。缓存沿用既有任务目录，各场景缓存与负载不保证相同；初始化不计入表中，不能按初始化耗时排名。

## 资源记录与未完成项

本轮未在各档开始前保存完整资源快照；不能把补采的值当作每档起跑条件。补采时间2026-11-06T07:31:11+08（本地三档已结束、远端补跑期间）：RTX4080总16376MiB、占用9141MiB、GPU利用率0%；Windows可用物理内存24395644KiB。未停止任何用户服务释放资源。每组JSON的torch_peak_allocated/reserved只计PyTorch，不含Warp及其他分配，不能用于整体显存容量结论。

全部任务容器结束后两机`docker ps --filter name=duck-benchmark`为空；原始远端目录保留。未输出正式checkpoint，未部署真机，未提交/推送。正式runner/分族日志/保存续训、长期稳定与第⑥步行为验收仍待完成，第④步整体进行中。

## 实际启动方式

本地逐档执行以下命令，`SIZE`依次为256、1024、4096，输出名互不覆盖：

```text
wsl -d Ubuntu -- /mnt/e/Projects/duck-robot/training/.venv-wsl/bin/python /mnt/e/Projects/duck-robot/training/scripts/benchmark_locomotion.py --global-envs SIZE --warmup 2 --iterations 5 --output /mnt/e/Projects/duck-robot/docs/specs/20261105-原地转圈策略/benchmark-scale-local-SIZE.json --label rtx4080-scaleSIZE
```

Spark复用`/home/yilv/dspark/duck-benchmark-20261106`及`nvcr.io/nvidia/pytorch:25.10-py3`；没有调用原带delete的编排。所有结果输出与stdout/stderr写独立名称。

单机env对齐补跑的共同docker参数：`--gpus all --network host --ipc host --device /dev/infiniband --ulimit memlock=-1 --ulimit stack=67108864 --env-file /home/yilv/dspark/train-gx10/env.sh --entrypoint /bench/venv/bin/python`；挂载任务根至`/bench`、任务cache至`/root/.cache`。256手动执行（容器名`duck-benchmark-scale-single-aligned-256`）；1024/4096由[顺序脚本](../../../training/scripts/run_spark_scale_single.sh)运行，输出`benchmark-scale-single-env-{规模}.json`与`scale-single-env-{规模}.log`。

双机共同docker参数与补跑单机一致，但Python执行：

```text
-m torch.distributed.run --nnodes=2 --nproc-per-node=1 --node-rank=RANK --master-addr=192.168.100.10 --master-port=PORT /bench/project/training/scripts/benchmark_locomotion.py --global-envs SIZE --warmup 2 --iterations 5 --output /bench/benchmark-scale-dual-SIZE.json --label spark-dual-scaleSIZE
```

spark1为rank0、spark2为rank1；256/1024/4096的端口分别29616/29626/29636，容器名为`duck-benchmark-scale-dual-{规模}`。公共环境快照沿用[原runbook](benchmark-runbook.md)；正式模型/奖励未改。

## 执行异常与纠正

没有OOM或PPO数值失败。Windows到spark2的SSH/scp常在已输出完成后尾部挂起，部分退出1不表示GPU失败；通过spark1到spark2直连核对最终JSON、日志及容器退出。后续回收由spark1无delete的rsync暂存后scp，原数据保留。一次单机日志scp误写任务目录日期20261105，得到不存在错误，随后改为20261106成功；一次PowerShell汇总在foreach后直接接管道导致解析错误，改为先收集数组后汇总，未改原JSON。未对用户服务或系统配置做修复。

收尾：12份规模JSON（含未对齐单机补充）可解析，15个rank记录×5项输入共75项当前SHA256比对一致；2预热/5计时、各档全局样本与聚合吞吐重算通过。单机env补跑及双机全部12份Spark日志已回收，主要本地文档链接及限定diff检查通过；独立结果/文档审查通过。不追加GPU复测，不扩大正式训练参数。
