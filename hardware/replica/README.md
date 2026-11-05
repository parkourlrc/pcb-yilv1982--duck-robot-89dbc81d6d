# 复刻整机基线（索引）

状态：2026-11-05 建，仅索引层；未移动或复制任何原图、原理图、工程文件。

## 当前装机（以 PROGRESS/BOM 为准）

- 主控：Radxa Zero 3W。
- HAT：kissqy HAT（REVA，按实物与来源核对）；白色 HAT V1.2 为历史。
- IMU：新单 3P 口板（2026-11-01 换装）；旧 GD32 单口板与 v0.3 双口板仅历史。
- 舵机：飞特 HD-1910-C001 ×15；ID 已对齐上游，2026-11-01 完成本机标定。

## 里程碑状态

- M1 已完成（用户确认 2026-11-05，已闭环）：装配、主控、15 舵机标定、IMU、上电检查。
- M2 已完成（用户确认 2026-11-05，已闭环）：官方模型上机与基本动作。
- 剩余：M3 PCB 全流程（已下单，待回寄/上机）、M4 自训上机、M5 参数重训/完整动作、线束与载流可靠性。

## 入口

- 物料与状态：[BOM](../../BOM.md)、[PROGRESS](../../PROGRESS.md)
- 照片/图纸：[照片索引](../../docs/photos/README.md)、[原理图索引](../../docs/schematics/README.md)
- 装配与中位：[整机装配与中位校准](../../docs/references/整机装配与中位校准/research.md)
- 供电与实物复核：[供电与扩展板实物复核](../../docs/references/供电与扩展板实物复核/research.md)、[v2 架构](../../docs/power-architecture-v2.md)
- 总线/缺答：[扩展板双口惯性缺答复核](../../docs/references/扩展板双口惯性缺答复核/research.md)、[舵机网页工具惯性显示](../../docs/references/舵机网页工具惯性显示/research.md)
- HAT 来源/版本：[白色扩展板原理图查证](../../docs/references/白色扩展板原理图查证/research.md)、[惯性单元三版来源对比](../../docs/references/惯性单元三版来源对比/research.md)

## 待办

- M1 已闭环；剩余 M3 PCB 回寄/上机、M4 自训上机、M5 完整动作与起身恢复、线束/载流可靠性，以及自主 HAT B.0 首板验收；按 [AGENTS](../../AGENTS.md) 的安全边界执行。
- 本页只做入口；版本变化先更新 BOM/PROGRESS 和对应专题，再回来改索引。
