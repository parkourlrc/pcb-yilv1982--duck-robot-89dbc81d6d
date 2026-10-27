# Microduck-Hat-for-Radxa-Zero — 原理图存档（图版本 V1.0）

- **实物**：白色鸭图案 HAT，PCB 丝印 **V1.2**（2026-10-10 照片更正，此前误记 V1.1；正反面照片与元件标注见 `../../photos/`，hat-v1.2-*.jpg）
- **原理图**：`SCH_Microduck-Hat-for-Radxa-Zero_2026-10-06.pdf`（5 页，2026-10-06 导出，图版本 **V1.0**——**与实物 V1.2 图物差异大**：背面 MCU 类器件未在旧图对应；正面圆柱件标记 10/50V，旧“超级电容”误判已撤回，接线/上电前须向板卡来源索取 V1.2 图或改动说明）
- 结构：官方 RPI Robot HAT 的嘉立创EDA 派生版（Radxa Zero 3W 适配 + 新增 BNO085）；逐页分析见 `../../references/microduck-hat-20261006/research.md`

- **2026-10-27 DATA 复核**：V1.0 两口共用 R31=1 kΩ/F1 的 DATA 路径；官方图对应 R33=150 Ω。V1.2 实装未核，详见[原理图对比与缺答分析](../../references/hat-imu-shared-bus-20261027/research.md)。

- **2026-10-27 PCB 检索**：沿用户提供的 ScrapMeta 地址取得其文档引用的[官方 C1 PCB 工程、Gerber 与 BOM](../pollen-hat-pcb-reference/README.md)，固定 `88d51fa`。**尚未找到这块白色 V1.2 的专用工程**，不能用 C1 位号直接定位 V1.2；检索范围与缺口见[记录](../../references/hat-imu-shared-bus-20261027/research.md#pcb-source-search-20261027)。
