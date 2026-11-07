# 实施记录

2026-11-06：用户批准修改方案，进入编码，未提交。

分片：runtime负责训练入口、任务描述、v1来源冻结和replay_worker；backend负责控制服务、执行器、持久索引、资源、启动脚本和API合同；frontend负责web与本地依赖。主会话统一审查、验收与现行入口更新。各分片不得修改其他分片文件。

backend只读核对：历史updates含rollout奖励及rank0 loss/std，缺逐轮UTC和完整episode return；manifest100/1000本地各仅rank0.pt，禁止以此宣称完整可恢复。Studio原件含完整模型与解码器但没有vendor；前端补固定版本及许可。

验证与限制见下文真实验收记录；本轮三模式总计消费576训练转换。

## Backend当前进展

2026-11-06：控制API、SQLite索引、历史曲线、配置预算校验、同源CSRF、WS流、监督进程、冻结源码、三种启动、停止和同拓扑恢复代码已写。启动脚本默认8766，8765已有用户服务，绝不停止该服务。真实配置写入gitignored `training/dashboard.local.json`，路径待probe成功后才运行。

TestClient检查：任务/历史接口200，双节点16环境×4步×3更新解析为每rank8环境、每更新64转换/预算192；两个旧checkpoint rank0哈希有效、rank1缺失，返回可推理不可恢复；22个真实指标系列；无CSRF写操作403。未启动本任务HTTP服务，由主会话统一运行；未执行新训练。

后端仍在补状态/资源和缓存边界检查，本段不构成整体验收。

2026-11-06后端代码进入独立审查：增加同拓扑续训（复用远端experiment账本、冻结源码）、启动失败仅停止同run容器/进程、全rank checkpoint哈希缓存确认、资源后台采集、回放控制request_id幂等和子进程退出检测。旧10次dev9报告已索引，22项连续指标另加稀疏开发通过率系列。实际配置为8766，gitignored；本地WSL必要probe返回RTX4080，spark1返回Docker29.2.1且宿主资源采集成功，spark2必要probe30秒超时，原因尚未定位。未执行新训练，三执行模式和续训仍待主会话按批准预算验收。

## 后端审查修复

2026-11-06：数据库游标与源seq分离；失联时仍处理已知节点失败；监督心跳过期显示stale；停止意图在持久锁下合并避免旧快照覆盖；续训清缓存计数并对缺文件重试；检查点schema/rank集合/路径与哈希验证；episode样本数字段和评估消费量按真实记录读取。合成检查保存backend-checks.json，训练转换为0。

浏览器首次回放失败原因为WSL路径参数反斜杠被处理：Python subprocess实际`wsl.exe -- wslpath ...`返回exit1。现改`--exec`与`Path.as_posix()`，同一Python调用实测返回`/mnt/e/Projects/duck-robot/training/dashboard/replay_worker.py`。失败会话保留错误状态，关闭后可释放列表项。

创建独立`training/.dashboard-venv`成功，FastAPI0.115.6、uvicorn0.34.0、psutil6.1.1，补固定websockets14.1供WS使用；未改训练环境。控制服务结束只向回放写STOP，训练监督继续；服务重启用回放心跳及PID创建时间核对死进程。Spark2只读probe超时不等同设备离线，继续检查SSH会话退出行为。

后端八项合成检查在独立Python3.11.15环境通过，0训练转换。修复checkpoint缺rank/越目录路径、回合samples、评估真实消费量、节点STOP投递互不阻断与重试；补纯采样/全程吞吐；损坏已存在checkpoint按哈希重试缓存。尊重runtime manifest的resumable=false课程决策边界，完整推理文件与可恢复状态分开。

Spark2排查：[实测] hostname与Docker查询均已输出，Docker版本28.3.3；SSH debug已报告`Exit status 0`但Windows Python communicate仍在15秒到期。`-T`、stdin=DEVNULL、ControlMaster=no/ControlPath=none均未解除；节点离线解释不成立，疑似ProxyJump子进程/句柄收尾，机理未确认。详细stderr仅存gitignored `training/.dashboard/spark2-probe-private.json`；未改SSH系统配置。

后续[实测]通过spark1中继执行`ssh -T spark2`，Windows端约1.8秒返回hostname与Docker28.3.3；gitignored本地配置增加`relay_target=spark1`和由`ssh -G spark2`解析的`relay_destination`。Executor对shell/同步/缓存统一使用中继，避免Windows OpenSSH ProxyJump退出句柄问题。中继配置仅本机，不进入仓库。

## 后端真实执行验收

2026-11-06，[实测]按批准限额逐个运行本地WSL、单Spark1、双Spark，每模式16环境×4步×3更新=192转换，总计576转换。每个实验先运行2轮128转换，保存完整final checkpoint，再通过`Runs.resume`在原experiment账本续1轮，累计192、余额0。全部六个run完成，未新增实验重复消费。原始公开状态分别保存于`checks/backend-e2e-local.json`、`checks/backend-e2e-single_spark.json`、`checks/backend-e2e-dual_spark.json`；原始runtime日志及账本位于gitignored `training/.dashboard-validation/<mode>/runs/`及各执行节点的同run目录。

| 模式 | 初段run | 续训run | 消费/预算 | 结果 |
|---|---|---|---|---|
| 本地WSL | 38a52442e17047a99d7f195e3a565061 | 7df606951e60435bb7d1c665836b02f5 | 192/192 | 完成；第2轮真实dev9评估 |
| 单Spark1 | 5b794601fa554ea29b46b612a3befc1e | 893b22c87c214ebdbfa81fd9215d6a7a | 192/192 | 完成；E100未触发评估 |
| 双Spark | 1d2c1afd1fda43cbbfd318299ccbe1ee | c76bae2f172745bca52ac6e8c30ca2ef | 192/192 | 完成；两rank完整缓存及同拓扑恢复 |

首次本地启动遇到监督文件与launch日志均未创建、0预算消费；增加监督JSON启动握手后，在同run内确认无进程与无账本才重新启动，未另建实验。`validate_execution.py --run-id`允许继续观察已有初段，避免验证脚本退出后误建新实验。控制服务重启时，无locations的preparing记录收敛failed；已有locations但缺监督，或监督心跳停止，必须确认同job进程不存在才失败。无法查询的节点保留失联状态。

Spark1节点时钟与主机有偏差；监督新鲜度改用本机monotonic观察远端心跳是否推进，资源连接last_seen使用本机received_utc，同时保留源sample_utc。WSL独立保留900个时序点及`resources.local-wsl.jsonl`，processes标记training/replay，不与Windows宿主相加。GPU查询超时/失败标error并给reason，工具缺失或单字段N/A仍unsupported。八项0转换合成回归再次通过；额外合成核对preparing孤儿收敛和GPU timeout语义通过。

验收边界：576转换仅证明受控小预算启动、完整检查点和同拓扑续训路径；不是策略效果、实物行走或长时性能验收。停止/重连/服务重启边界以合成检查及浏览器回放检查为主，未为验证这些边界额外消耗训练预算。未提交。

末轮修正（2026-11-06）：Run完成记录保留completion_reason；回放新增`GET /api/replays/{id}/frames`补齐当前代最近2500帧，文件offset增量缓存，不额外启推理。关闭会话读取、2500界限、after_seq、generation切换、半行重试五项0转换检查通过，证据`checks/backend-replay-frames.json`。十项后端合成回归再次通过。监督心跳缺失/不推进超过本机15秒，无需服务重启也核对精确作业；SSH同时查精确名称Docker运行容器与/proc，查询失败保持失联，不把仍活容器误判失败。

前端角色独立只读复核：六个run原始日志及全部manifest rank文件hash通过，合计576转换；本地第2轮dev9结果0/9。这是短预算工具验收，不能据此评价训练收敛。后端末轮接口已完成，可由主会话统一重启8766，再用已关闭会话验收history，不新增训练。
