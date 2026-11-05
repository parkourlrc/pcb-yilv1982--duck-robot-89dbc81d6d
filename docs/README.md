# docs 目录索引

本目录放本项目自己的方案、测试单、训练存档、图纸/照片索引和调研证据；上游只读资料在 [references](../references/README.md)，本机调研在 [docs/references](references/README.md)。

## 阅读顺序

[AGENTS](../AGENTS.md) → [项目概览](../README.md) → [PROGRESS](../PROGRESS.md) → [BOM](../BOM.md) → 本索引 → 任务专题。

## 子目录

| 目录 | 内容 |
|---|---|
| [references/](references/README.md) | 本机调研证据；按纯中文主题名，入口 README |
| [photos/](photos/README.md) | 用户硬件照片、标注图与索引 |
| [schematics/](schematics/README.md) | 原理图、设计源、网表及来源/版本 |
| [specs/](specs/README.md) | 任务 spec；每任务一个 `YYYYMMDD-主题/` |
| [video-notes/](video-notes/) | 视频笔记、时间戳与核验材料 |
| [archive/](archive/README.md) | 已移出入口的历史事件与过期指南 |

## 根级文档

- 流程与计划：[硬件模块研发流程](hardware-module-development-workflow.md)、[PCB 全流程运行手册](pcb-production-runbook.md)、[Spec 流程](spec-process.md)、[real2sim2real 工具链计划](real2sim2real-toolchain-plan.md)
- 供电：[v2 架构](power-architecture-v2.md)（讨论基线）、[v1](power-architecture-v1.md)（历史）、[过流保护](overcurrent-protection.md)
- 测试单：[HAT V1.2](hat-v1.2-test.md)（历史版）、[IMU 台架](imu-gd32-bench-test.md)（历史版）、[降压模块](buck-module-test.md)
- 训练：[A 线](a-training.md)、[B 线](b-training.md)、[A 线验收数据](a-training-validation.json)
- 工具/映射：[台架工具](bench-tools.md)、[舵机 ID 映射](servo-id-mapping.md)
- 回退：[A 线基线](route-a-baseline-20260928.md)、[A 线 BOM](bom-route-a-20260928.md)

## 边界

- 调研证据与原始照片只追加不覆盖；结论分级与来源写在专题 `research.md`。
- 历史测试单和旧路线文档保留，但不得直接作为当前接线/上电依据。
