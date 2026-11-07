# 本轮双机并行机制核对

## 是否为常用方法：官方资料补充

2026-11-06核对：同步数据并行是分布式PPO的常用路线之一，不是本项目自创。RLlib scaling guide明确使用DDP扩展Learner；RSL-RL官方支持多GPU训练，PPO源码有梯度归约；DD-PPO原论文展示多机同步PPO。不能据此声称本项目完全复现DD-PPO，或框架成熟就保证当前超参/归一化/奖励正确。

来源及定位：
- https://docs.ray.io/en/latest/rllib/scaling-guide.html ，Scaling the number of Learner actors：学习节点的数据并行；采样节点可独立扩展。
- https://github.com/leggedrobotics/rsl_rl ，README多GPU支持；https://github.com/leggedrobotics/rsl_rl/blob/main/rsl_rl/algorithms/ppo.py ，分布式PPO实现。在线main不是本机安装版本，本轮实际机制仍以此前读取的安装源码为准。
- https://arxiv.org/abs/1911.00357 ，摘要及Introduction：多机、去中心化、同步DD-PPO；论文的性能结果不移用于本项目。

项目判断：并行架构本身有成熟先例；本轮已观察到动作std和均值失控，但没有控制其他变量的单机/双机学习对照，不能证明或排除分布式细节对失败的贡献。rank本地归一化是需要明确记录的实现选择，不属于所有并行PPO必然采用的规则。本轮仅问答查证，未改训练配置。

日期：2026-11-06。问题：两机如何更新同一网络，本轮使用何种设备。

依据：`checks/step5-run-001/run.json`、双rank日志及容器退出记录；`training/mjlab_duck/train_locomotion.py:100`起；spark1实际依赖 `/home/yilv/dspark/duck-benchmark-20261106/venv/lib/python3.12/site-packages/rsl_rl/algorithms/ppo.py:369`、`:508`、`:522`。

首轮1000次更新在spark1和spark2两台GB10执行。每机2048环境，每环境64控制步，每机每轮131072转换，全局262144转换。本地RTX4080用于短检查及之后第100/1000轮模型的诊断回放，不参与这次正式双机更新。

每机有完整actor和critic副本。启动时rank0广播模型状态，使初始参数一致；两机并行采样各自环境，各自计算minibatch梯度。已安装PPO在每次optimizer.step之前调用reduce_parameters，把actor/critic梯度拼接，通过torch.distributed.all_reduce(SUM)同步，再除world_size=2，写回两机梯度，随后分别执行梯度裁剪和Adam更新。每轮5个epoch×4个minibatch，所以20次同步优化步骤，而非每轮仅同步一次。

公式示意：共同梯度=(spark1梯度+spark2梯度)/2。按相同起点、优化器状态及同步学习率，两副本沿同一组梯度更新；不是分别练两套模型后挑一个，也不是把网络层分成两半。项目使用NCCL梯度通道，Gloo负责控制及检查点对象传输。归一化统计和优势归一化保持rank本地，因此不能声称所有状态逐位一致或与单机拼接全部数据完全等价；本轮独立评估使用rank0策略，保存各rank状态以便恢复。

官方机制参考：https://docs.pytorch.org/docs/2.15/distributed.html 的all_reduce章节；该网页仅解释集合通信语义，实际安装版本及本轮行为以本地运行元数据和已安装源码为准。本轮未修改训练或启动新任务。
