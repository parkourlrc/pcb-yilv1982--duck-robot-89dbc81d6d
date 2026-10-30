# Spec 目录索引

功能/修改任务的 spec 存档：每任务一个 `YYYYMMDD-主题/` 目录，内含 `spec.md`。流程与模板见[简单 Spec 开发流程](../spec-process.md)。

| 目录 | 任务 | 状态 |
|---|---|---|
| [20261028-custom-hat](20261028-custom-hat/spec.md) | KiCad 自设计 HAT；[kicad-happy review](../references/hat-simulation-tools-20261029/kicad-happy-review-20261030/review.md)、[供电/地检查点](../references/hat-simulation-tools-20261029/power-repair-20261030/research.md)、[制造条件](20261028-custom-hat/order-checklist.md) | **局部修复完成，最终审查不通过**；普通DRC为0，仍1项未连接，另有MPN/fiducial/工艺/热/回流缺口；不可投板 |
| [20261027-sync-read-cascade](20261027-sync-read-cascade/spec.md) | SYNC_READ 主机侧缺席连锁错位缺陷（缺席 ID 之后全部应答被错位吃掉；实测坐实，含单舵机 294.7ms 逐项对账与 386 拍 bad_id 5786 精确吻合） | **待确定（未立项）**：排障期保持上游对照，暂不修；候选修复方向已列 |
