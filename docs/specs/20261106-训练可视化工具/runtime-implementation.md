# Runtime实施与后端复核

- 日期：2026-11-06。
- 状态：代码、独立审查与方案限定的工具验收已完成，未提交。三模式训练转换合计576；本记录中的worker与合成检查不消费训练预算。
- 来源：[批准方案](implementation-plan.md)、[运行时协议](../../../training/dashboard/runtime_protocol.md)、[总实施记录](implementation-record.md)。

## 已实现及文件证据

`training/runtime_versions/locomotion-v1/`冻结修改前包源码、模型、HOME及原run；9个原合同SHA与`original-run.json`逐项一致，新增manifest登记全部冻结文件。现行任务描述`training/tasks/locomotion.json`登记新的源码哈希，v1没有因新接口改写。

现行runtime支持单/双rank、完整JSON配置、独立C/E、跨rollout完整回合统计与一秒阶段心跳、更新边界停止、原预算账本恢复。完整回合窗口按`rollout_step,rank,env_id`合并后取最近100个，避免按整rank拼接造成顺序错误。评估后有课程决定尚未执行的中间checkpoint仍可推理，但manifest及底层加载明确禁止完整恢复，用户选择final/stage2点。

回放actor严格核对原checkpoint/合同/冻结源码，只加载对应actor和归一化；输出根xyz、wxyz、命名14关节、命令/实际速度和由四元数计算的姿态角。Studio mouth固定由显示适配处理。WSL对Windows盘原子替换偶发PermissionError已加入有限重试；单次占用保留旧目标，不将一帧文件竞争升级为仿真失败。

## 实测与合成检查

| 检查 | 证据与结果 | 边界 |
|---|---|---|
| v1/现行来源、语法 | 本轮脚本核验全部冻结manifest、原合同9/9与现行任务9/9，Python语法通过 | 文件核验，不是策略行为验收 |
| 完整回合累积与窗口 | CPU合成跨两次采样累计return/length；两rank错序例最终保留`[10,20]`，下更新保留`[40,50]` | 合成验证统计语义 |
| pending课程决定 | 合成write_manifest：evaluated含stage2 pending时完整但不可恢复；final可恢复 | 未消耗训练转换 |
| 100轮worker | [摘要](checks/runtime-worker-check.json)及[压缩原始帧](checks/runtime-worker-100-frames.jsonl.gz)；模拟至20.74秒后reset，pause/2倍play/close通过 | 未完成23秒整场，早期“完成”口径已撤回 |
| 1000轮worker | [初/末帧及状态](checks/runtime-worker-1000-check.json)及[压缩原始帧](checks/runtime-worker-1000-frames.jsonl.gz)；完整23秒且actor/normalizer不变，随后close退出0 | completed指完整场景，不等于dev行为门槛通过 |
| 原子文件竞争 | 合成前两次PermissionError第三次成功；持续占用保留原JSON并清理临时文件 | 浏览器实际多窗稳定性仍由主会话验收 |

## 后端独立复核

按源码核验及临时目录合成复现检查，首轮发现并由backend修正：数据库游标被源seq覆盖、续训缓存计数继承、停止意图被旧快照覆盖、单节点停止失败阻断其他节点、失联跳过已知失败、缺rank误标完整、回合样本字段、评估采样量从轮次错误推算、回放失效会话与关闭释放。后端[八项合成记录](backend-checks.json)训练转换为0。

复核确认：训练`save_collective`将全部rank payload集中到rank0写完整manifest，所以控制面只从rank0缓存rank文件正确；续训由rank0载入后广播，不依赖节点共享文件系统。原实验账本独立同步，旧checkpoint回退不返还预算。事件DB cursor与source_seq分离；评估采样轴读关联manifest或同轮真实日志；缺测不补零。

三模式实际执行和浏览器验收现已完成，证据见总实施记录及下文。首次准备期服务崩溃、初始化异常、节点中断等路径仍按总实施记录区分真实执行与合成检查，不以合成检查替代端到端验收。

## 资源采集与网页会话独立复核

2026-11-06 17:19（Asia/Shanghai），只读访问`http://127.0.0.1:8766/api/resources`：本地、Spark 1、Spark 2分别有350、265、235个样本，均报告connected；Windows为`host_total`，另有`resource.wsl.sample`且包含4个匹配进程RSS。Spark采集入口通过SSH在宿主执行。此处是[实测] API结果与源码路径核验，非额外训练验收。

当时资源审查发现四项缺口：前端ResourceCard没有渲染WSL字段；WSL样本只驻内存、未写JSONL；`nvidia-smi`异常被统一标为unsupported，未与设备字段不支持区分；曲线没有接收时刻字段和失联断点。前后端随后已修源码：增加WSL子卡与samples/JSONL、GPU查询超时/失败标error、所有采样保留received_utc且连接last_seen用接收时间，前端超过10秒间隔插入null断点。服务重启后的API及浏览器资源卡已验收：三节点connected、WSL独立时序及JSONL存在、received_utc贯通；GPU失败分类经合成检查，不声称实际拔除设备。缺测及首次rate无基线均保留null。

[实测] Spark 1的sample_utc在多次读取中持续比Windows约早45秒，样本数仍增长，而另两个节点时间接近Windows。[推断] 可能为节点时钟差或固定链路延迟，尚未分离，不能把该差值直接称为采集过期。建议同时保留源sample_utc和Windows received_utc，连接时效按接收时刻计算；本轮未修改任何系统时钟。

网页已创建的两路真实worker由本代理只读复核：cp100会话generation 0完成23秒；cp1000会话generation 0完成23秒后，generation 1已reset到0.12秒并暂停，控制状态speed=2。均输出14关节与根位姿。摘要见[网页会话runtime复核](checks/browser-replay-check.json)。该记录不替代主会话的浏览器布局/按钮/四窗与关闭释放验收，也不把状态speed=2当作暂停期间的实测速率。

孤儿作业源码复核：`_prepare_launch`先持久化全部`_locations`再调用launch，因此重启发现preparing且无locations可判尚未发起训练；已有locations时先读取监督状态，并以完整argv项核验同作业进程，网络错误保留disconnected，不把无法访问当成退出。后续复核发现的两条边界已由backend修正：重启恢复stopping且无locations转为stopped；缺失/陈旧监督的进程核验同时适用于recovered_runs和_launch_failed。该部分通过源码复核，backend另有十项合成回归记录，未新增训练转换。

主会话CUA已观察四路实际显示，刷新后仍为原四会话未重复创建，[四窗截图](checks/dashboard-four-replays.jpg)宽1600像素；本代理API交叉复核三路为generation 0/23秒completed，原cp1000为generation 1/0.12秒paused，详见browser-replay-check。刷新后曲线只保留末点的问题已修复：重启后从closed会话取回983帧，独立页完整曲线及Studio模型恢复、控制禁用，未启动新worker；见[最终验收](checks/final-browser-check.json)。

四路关闭释放已完成：主会话确认API全部会话closed；本代理读取四个status.json均为closed，并在WSL独立执行`pgrep -af '[r]eplay_worker.py'`无匹配。关闭后四路原始frames.jsonl及四窗截图SHA256已成功补录到browser-replay-check；早期文件仍打开时哈希读取失败的限制已由关闭后取证解除。该结果支持本轮四个worker已释放；本记录未另行核验Windows父PID，不代表其他程序或GPU进程退出。

截图来源登记：`checks/dashboard-four-replays.jpg`（四窗）、`checks/dashboard-overview.jpg`（运行总览）、`checks/dashboard-restored-replay.jpg`（已关闭会话历史曲线）、`checks/dashboard-resources.jpg`（资源卡）均为2026-11-06本次工具页面CUA截图，非用户原图或硬件照片；原始文件保留在本专题。
