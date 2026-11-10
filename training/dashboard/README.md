# 本地训练工作台

## 训练记录来源

工作台的训练记录唯一来源是 [`training/records/`](../records/README.md)。启动时只恢复其中 `record_kind=training-run` 的文档及对应 `training/artifacts/runs/<run_id>/` 归档；不会递归扫描 `docs/specs/`、`docs/references/`、`training/logs/`，也不会把测速 JSON、rank 残片或外部策略包显示成训练运行。

新运行由训练流程在登记和封存时写入记录文档。历史整理只允许显式执行 [`cleanup_training_records.py`](../scripts/cleanup_training_records.py)，脚本将同时满足冻结源码哈希合同和可验证 rank0 检查点的材料迁入统一文档，其余平台副本清除；原始研究材料保留在原目录。

2026-11-09：工作台完成克制赛博朋克配色：深海军蓝底、蓝灰面板、冰青主交互、少量电紫图表辅助色；状态颜色保留语义，机器人材质与训练逻辑不变。桌面/窄屏、档案、资源、回放控件及新建实验表单检查通过，见[配色Spec与检查证据](../../docs/specs/20261109-训练工作台配色/spec.md)。

2026-11-09：新增完整实验档案、67个参数/奖励字段目录、阶段/进度奖励配方、从零派生和接权重派生。物理、接口、网络与验收规则锁定。实施与限制见[训练档案任务](../../docs/specs/20261109-训练档案与复训/spec.md)。

## 档案和复训

大产物保存于`training/artifacts/`（Git忽略）；`training/.dashboard/index.sqlite`可从耐久`dashboard-run.json`和`training/records/`重建。任务/实验/运行可筛选，档案页包含流程、完整配置、来源差异、奖励设计、产物下载及分项缺失原因。历史材料只有在显式迁移后才进入记录目录；零散短跑/测速证据不会显示为训练运行。

- 原状态续训：保持来源运行时和完整合同，沿用预算；环境从HOME新回合开始。
- 从零重训：复制来源冻结运行时和配置，修改开放字段后建立新实验。旧v1使用外置适配器，旧奖励合同不变。
- 接权重训练：完整rank0策略及物理/接口/网络transfer合同匹配后可创建新实验；actor/归一化继承，critic、optimizer、探索、随机状态和课程重建。历史缺transfer证据明确不可接权重。

每次启动前登记前四步证据、配置哈希与精确预算；训练完成与归档完整、行为验收分别表示。档案不会自动删除产物，也不会自动追加预算。离线仍可浏览已同步文件，缺失的节点数据不能标完整。

CLI与网页共用`Runs`登记、校验、冻结和启动逻辑，从`training`目录运行：

```text
python -m dashboard.cli catalog
python -m dashboard.cli import-history  # 仅从 training/records 重建索引
python -m dashboard.cli archive RUN_ID
python -m dashboard.cli derive RUN_ID --mode scratch
python -m dashboard.cli validate REQUEST.json
python -m dashboard.cli start REQUEST.json --name 实验名称
python -m dashboard.cli resume RUN_ID --checkpoint-id CHECKPOINT_ID
```

CLI启动与续训前台持续同步到终态，终态缺失产物每30秒重试；Ctrl+C仅退出监视，监督进程继续训练，重新打开平台接续同步。同步未完成不会封存为完整。每个受管运行另导出Git可见`training/records/<run_id>.json`，含任务、配置、完整流程、预算及结果摘要；节点路径与主机信息脱敏。平台SQLite删除后从训练文档目录及耐久归档重建。直接底层CLI输出必须由训练流程封存到该目录，不能假定任意外部路径自动被发现。

`REQUEST.json`字段与`POST /api/runs/validate`相同；新增`source_run_id`、`initialization`（scratch/warm）和可选`checkpoint_id`，`parameters`允许有类型的嵌套配置。奖励项符号与公式由版本固定，网页不能执行任意代码。新增`GET /api/catalog`、`GET /api/runs/{id}/archive`、`POST /api/runs/{id}/derive`、`POST /api/history/import`、`GET /api/runs/{id}/artifacts/{artifact_id}`；文件仅从登记归档按ID获取，拒绝任意路径。已有`resume`接口保留原语义。

从项目根运行 `powershell -File training/start-dashboard.ps1`，默认端口8766；`-Port` 可指定其他空闲端口。首次创建独立 `.dashboard-venv` 并安装固定依赖，不修改训练venv。

复制 `config.example.json` 到 `training/dashboard.local.json`，填写已确认的WSL解释器、工作根及SSH节点环境。未配置时仍可查看历史运行及模型，启动明确报缺项。实际配置、数据库、运行缓存不提交。服务只绑定127.0.0.1，写操作使用同源会话与CSRF令牌。

历史首轮保留真实1000轮曲线和100/1000检查点，能力按来源材料分级；具备冻结运行时和配置时可从零派生；旧数据缺少的完整回合奖励/逐轮时间轴不补零。原实验预算耗尽不允许恢复。新运行源码、模型、配置冻结；双节点先全部准备再启动，监督进程与网页生命周期独立。停止在更新边界保存，异常只保留已完整checkpoint。恢复复用原远端experiment账本与冻结源码，不返还消费额度。

回放在本地WSL运行冻结actor及归一化；最大四路，可暂停/重置/倍率控制。关闭服务不结束训练；关闭回放通过会话控制文件释放。回放模型来自Studio部署来源原件，前端适配只改变显示。

接口合同见 `docs/specs/20261106-训练可视化工具/api-contract.md`。实现与验收边界见同目录 `implementation-record.md`，未验收的路径不等同已验证支持。
