# HAT 自主设计工作目录

**2026-11-05 工厂工程反馈：** 已核对[MK701/Y701的1脚方向](../../docs/references/扩展板乙版降本/engineering-feedback/research.md)，截图顶视分别在左上/左下；待用户向工厂回复，未确认制造放行或发货。本次仅响应工程反馈，研发暂停保持。

方法与复盘：[自主硬件模块研发流程](../../docs/hardware-module-development-workflow.md) · [HAT阶段总结](../../docs/references/自主扩展板阶段复盘/research.md)。涵盖需求、选型/工艺/成本、KiCad工程、同源交付、订单核对及未完成的首板阶段；不构成恢复研发的指令。

**2026-11-05 自主HAT线路暂停：** [用户确认] Y10／SMT2611051346已付款，84362651版5片，等待收货。最后合并支付页金额891.79元（含运费5.50）；未另核支付回执或发货状态。停止继续降本、设计修改、订单操作及主动跟进，等待用户明确恢复；首板尚未验收，原750元目标未达成。

**现行版本：B.0 / 84362651（[rev_b](rev_b/README.md)）。** 已用于 5 片付款订单，等待收货；原生 ERC、DRC、未连接与原理图/PCB 一致性为 0，不等于实物验收。报价、制造放行与首板验收分开记录；当前源与检查见 [rev_b/checkpoint.json](rev_b/checkpoint.json)；版本与交付包对照见 [VERSIONS.md](VERSIONS.md)。

**历史版本与报价：**

- A.1 在 [rev_a](rev_a/README.md)，保留历史设计、审查与首板草案，不与 B.0 混用。
- 2026-11-04 的 Y7/Y8 两套 5 片 PCB 实单与 SMT 草稿均未付款，只作版本比较；金额、缺料与证据见[两套扩展板订单与报价](../../docs/references/两套扩展板订单与报价/research.md)。
- 2026-11-03 源 86654c03/r18 已被 B.0 取代，仅作追溯；旧 r1～r17 退出制造入口。

**当前资料：**

- [B.0 降本与布局](../../docs/references/扩展板乙版降本/research.md)、[Y10 订单与费用边界](../../docs/references/扩展板乙版降本/layout-spacing/y10-quotation-status.md)。
- [历史 r18 报告](../../docs/references/扩展板邮票孔与电源修复/research.md)：U301分窗取舍已定；真实工艺/制造/首板未发生，不提前通过。
- [离线 codec 驱动与设备树](software/codec/README.md)：对应历史主控内核，已做 ABI/DTB 文件核查，未部署或实测。
- [BMI088 Linux I2C 适配器](software/imu/README.md)：双端点身份/配置/采集代码已构建，现场执行和实物数据未验收。
- [修复方案](../../docs/specs/20261028-custom-hat/recovery-plan.md)、[需求与阶段](../../docs/specs/20261028-custom-hat/spec.md)。

本目录根层的 `custom_hat.kicad_sch` 及功能页是历史骨架，含已取消的屏幕/摄像头，不再作为现行设计入口；保留供追溯。`rev_a/best.kicad_pcb` 等为布线实验，不能凭文件名判为可交付版本。B.0 现行工程在 `rev_b`；`rev_a` 保留 A.1 历史。
