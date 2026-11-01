# 地缝合与 EMC 复核（2026-10-30）

## 结果

- 在板边空旷位置加入 3 个 `POWER_GND` 过孔：`(105,115)`、`(105,124)`、`(160,124)` mm。
- 候选及主板 KiCad 10.0.7 DRC：普通违规 `0`，未连接仍为原有 `R308.2 ↔ U701.7` 一项。
- PCB analyzer：`POWER_GND` 过孔由 3 增至 6；未改变走线段、焊盘赋网或原有信号连接。
- 位置 `(160,115)` 被拒绝：与右侧 `+1V8_CODEC` 走线产生 2 条 clearance；未回写。

## EMC 复核

- 最新 `aklofas/kicad-happy` EMC analyzer 运行结果：58 项（9 error、36 warning、13 info），但 fab gate 未产生 critical EMC blocker；这些结果仍属于离线拓扑/启发式分析，不是 EMI 实测。
- `PS-002`：`+3V3` 仍有 2 个岛，`I2S_LRCK` 穿越；这是当前需要整体 codec/平面重排处理的真实布局风险。
- `VS-002`：cross analyzer 仍报告“无地缝合过孔”，与原始 PCB/最新 PCB analyzer 的 6 个 `POWER_GND` 过孔矛盾，判为分析器字段/判定逻辑限制，不继续为消警告盲目加孔。
- EMC analyzer 的 `DC-002`、`IO-001`、`GP-001` 等需结合实际去耦、接口环境、层叠和实测波形/EMI 决定，不能直接写成已证实故障。

## 状态

地缝合修复已回写主 PCB；主板仍不可投板，`U701.7` 连接、MPN、工艺环宽、热过孔、I2C 上拉、平面回流和硬件验证仍未闭合。
