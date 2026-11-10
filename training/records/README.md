# 训练文档目录

`training/records/` 是训练平台唯一的训练记录入口。每个 `*.json` 必须由训练流程或明确的历史迁移流程生成，`record_kind` 必须为 `training-run`；网页、CLI 和回放工具只读取这里的文档，不扫描 `docs/`、`training/logs/` 或其他临时目录。

文档至少包含运行 ID、任务/版本、完整配置、预算、流程状态、产物归档引用和能力判定。能力字段分别说明 `replay`（检查点和冻结源码可回放）、`scratch`（冻结输入可从零重训）、`warm`（兼容 actor 可接权重）和 `resume`（原账本可续训）。训练完成不自动等于行为验收通过。

训练流程第③步（环境组装）的记录须引用本机训练环境登记条目，并写明解释器绝对路径、文件系统位置（ext4/9p）及冷/热启动实测；解释器或依赖位于 `/mnt/c` 等跨盘挂载时，该步不得标记完成。规则见[训练流程 Spec](../../docs/specs/20261105-自主训练平台/spec.md)，登记示例见[本机训练环境](../../docs/references/本机训练环境/research.md)。

历史材料清理由 [`cleanup_training_records.py`](../scripts/cleanup_training_records.py) 执行；WSL 双足正式重试的显式迁移由 [`migrate_wsl_gait_records.py`](../scripts/migrate_wsl_gait_records.py) 执行。只有同时满足检查点内冻结源码哈希合同和可验证 rank0 检查点的材料才能迁入；清理只删除 `training/artifacts/runs/` 下的平台副本，原始专题证据仍由其原目录负责保存，不会被平台再次当作训练记录导入。清理台账使用 `record_kind=maintenance`，不会被训练工具读取。
