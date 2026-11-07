# 第④步同任务短PPO测速复现记录

日期：2026-11-06，本机Asia/Shanghai；工作区上下文日期2026-11-05。用户授权短测速，不执行2000轮正式训练。三方输出与结论见[比较记录](../../references/自主训练平台/Spark与本地训练比较.md)。

本页记录原64环境基线。用户随后要求扩大工作量，256/1024/4096环境及单机env对齐补跑见[规模runbook](benchmark-scale-runbook.md)；两轮输出和窗口数分开，不覆盖原记录。

## 共同输入与输出

入口：`training/scripts/benchmark_locomotion.py`。全局64环境、每环境64步、每轮4096转换、2预热＋3计时；actor/critic均61维输入、128×128 ELU，actor14均值、初始log标准差0.30。PPO5epoch/4minibatch，精确解析配置在JSON中。FP32、关闭TF32、1个torch CPU线程、seed42（多rank环境种子42+rank）。finite_horizon=True，不随机episode_length，不保存checkpoint。

每窗包含环境采集、returns与20次优化；CUDA同步，双机窗前barrier，按每窗最大rank总耗时聚合，全局样本只算一次。窗口外有限数值检查与归档耗时不计；更新段包含通信和等待，未分别计时。初始化、编译与2轮预热单列。三窗是连续更新而非独立重复；每环境总6.4秒，可能中途done/reset，不代表完整轨迹。

输出：`benchmark-local.json`、`benchmark-spark-single.json`、`benchmark-spark-dual.json`；均保留每rank版本、配置、5项输入SHA256、初始化/预热/计时、done次数、raw超界比例、loss及PyTorch内存（不含Warp）。Spark完整stdout/stderr另存3个`.log`文件；本地stdout见执行会话，未额外保存完整本地文本日志，JSON为本地归档原始计时。

## 本地执行

PowerShell调用现有WSL环境，当前Windows仓库入口映射到`/mnt/e/Projects/duck-robot`：

```powershell
wsl -d Ubuntu -- /mnt/e/Projects/duck-robot/training/.venv-wsl/bin/python /mnt/e/Projects/duck-robot/training/scripts/benchmark_locomotion.py --output /mnt/e/Projects/duck-robot/docs/specs/20261105-原地转圈策略/benchmark-local.json --label rtx4080
```

## Spark隔离准备

两机任务根目录：`/home/yilv/dspark/duck-benchmark-20261106`，容器挂载`/bench`。镜像固定`nvcr.io/nvidia/pytorch:25.10-py3`。准备脚本为`training/scripts/prepare_spark_benchmark.sh`，先在spark2执行，保留NGC torch/torchvision；依赖为mjlab1.3.0、MuJoCo3.10.0、mujoco-warp3.8.1、Warp1.12.0、rsl_rl5.0.1、tensordict0.10.0。

最小包为`benchmark_locomotion.py`、`mjlab_duck/__init__.py`、`locomotion_cfg.py`、`locomotion_env.py`、`models/duck_v0.xml`、`params/home_pose.json`，保留`training/`目录结构，解包至`/bench/project`。没有复制参考库或修改环境、奖励与物理。

```bash
sudo -n docker run --rm --name duck-benchmark-prepare --network host --entrypoint /bin/bash -v /home/yilv/dspark/duck-benchmark-20261106:/bench nvcr.io/nvidia/pytorch:25.10-py3 /bench/prepare.sh
```

原PyPI下载过慢，最终显式使用HTTPS阿里镜像、30秒timeout、2次retry与`/bench/pip-cache`，不改系统配置。首次tensordict0.15.1触发torch升级解析，在安装前停止；最终constraint保留NGC版本。pip check只报基础镜像既有pynvml缺项，基础镜像复核同样结果；实际本任务运行通过，未把pip check写成全通过。

spark1通过已授权直连SSH用`rsync -a`拉取spark2任务目录下venv/project/cache，不带delete。反向SSH尝试失败未更改用户SSH；仅在任务目录创建来自可信spark1公钥的known_hosts。Warp缓存由单机运行产生后复制到spark1，故各场景初始化缓存状态不同。

## 单Spark执行

在spark2执行，stdout/stderr重定向到任务根`single.log`：

```bash
sudo -n docker run --rm --name duck-benchmark-single --gpus all --network host --ipc host --ulimit memlock=-1 --ulimit stack=67108864 --entrypoint /bench/venv/bin/python -v /home/yilv/dspark/duck-benchmark-20261106:/bench -v /home/yilv/dspark/duck-benchmark-20261106/cache:/root/.cache nvcr.io/nvidia/pytorch:25.10-py3 /bench/project/training/scripts/benchmark_locomotion.py --output /bench/benchmark-spark-single.json --label spark2-single
```

## 双Spark执行

每台独立执行一次，spark1的`BENCH_RANK=0`、spark2的`BENCH_RANK=1`；端口29606，均重定向到各自任务根`dual.log`。只有rank0保存聚合JSON。

```bash
BENCH_RANK=0
sudo -n docker run --rm --name duck-benchmark-dual --gpus all --network host --ipc host --device /dev/infiniband --ulimit memlock=-1 --ulimit stack=67108864 --env-file /home/yilv/dspark/train-gx10/env.sh --entrypoint /bench/venv/bin/python -v /home/yilv/dspark/duck-benchmark-20261106:/bench -v /home/yilv/dspark/duck-benchmark-20261106/cache:/root/.cache nvcr.io/nvidia/pytorch:25.10-py3 -m torch.distributed.run --nnodes=2 --nproc-per-node=1 --node-rank="$BENCH_RANK" --master-addr=192.168.100.10 --master-port=29606 /bench/project/training/scripts/benchmark_locomotion.py --output /bench/benchmark-spark-dual.json --label spark-dual
```

本轮实际读取的公共env.sh有效值如下，未修改原文件：

```text
NCCL_NET=IB
NCCL_IB_DISABLE=0
NCCL_IB_HCA=rocep1s0f0,rocep1s0f1,roceP2p1s0f0,roceP2p1s0f1
NCCL_SOCKET_IFNAME=enp1s0f0np0
NCCL_IB_ADDR_FAMILY=AF_INET
NCCL_IB_ROCE_VERSION_NUM=2
NCCL_CROSS_NIC=1
NCCL_CUMEM_ENABLE=0
NCCL_NVLS_ENABLE=0
NCCL_IGNORE_CPU_AFFINITY=1
GLOO_SOCKET_IFNAME=enp1s0f0np0
TP_SOCKET_IFNAME=enp1s0f0np0
PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
NCCL_DEBUG=WARN
HF_HOME=/work/.hf-cache
```

本轮仅有配置与运行成功证据，WARN日志无NET/IB选路详情；没有复测四口RoCE带宽。单Spark未加载此分布式env文件，双机另含allocator配置差异，不能把1.45%差距归因于某一个因素。`HF_HOME`在本任务未使用。

## 结束状态与限制

一次性容器均已退出；隔离目录、venv、输入和日志保留，两机原镜像/已有服务/`train-gx10/work`未改。未部署真机、未生成正式策略、未提交/推送。若回滚，先核实该独立目录只含本轮内容，再移走或删除；本轮不执行删除。

本地torch2.14.1/tensordict0.15.1/NCCL2.30.7与Spark torch2.9.0a0/tensordict0.10.0/NCCL2.27.7不同。DDP归一化与优势为rank本地统计，done次数不同不说明训练质量。三方相同任务与总样本不等于相同优化轨迹。独立审查只确认计量、哈希和数值一致性；正式入口、续训、长期稳定与行为验收仍待完成。

收尾检查：3份结果JSON与更新后的输入检查JSON可解析；4个rank记录×5项SHA256共20次与当前文件比对一致，4096样本口径通过，四份主要文档本地链接可解析。限定已跟踪文件`git diff --check`通过，新建与外部文件空白/冲突标记检查通过。外部目录不在Git工作树内，最初对其执行带pathspec的`git diff --check`失败，未当作通过，改为上述文件内容检查。最初一次补丁用了错误的绝对路径而失败，随后相对路径应用成功；未修改错误路径。两机`docker ps`均未列出本任务容器。
