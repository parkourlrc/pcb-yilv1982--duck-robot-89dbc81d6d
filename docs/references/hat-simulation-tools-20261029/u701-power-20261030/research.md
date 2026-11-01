# U701.7 +3V3 连接复核（2026-10-30）

## 范围

复核 `hardware/custom_hat/rev_a/custom_hat_rev_a.kicad_pcb` 中 `R308.2 [+3V3]` 到 `U701.7 [+3V3]` 的唯一未连接项，尝试局部重布，并确认自动布线是否能安全收敛。所有候选均在 `hardware/custom_hat/candidates/` 或独立运行目录中生成，未回写主板。

## 当前源版本证据

- 主 PCB SHA-256：`dfb094272b6c7e2420281b60e1f3e87a40adfe083df47b051b5ec491651d9251`。
- KiCad 10.0.7 CLI 重铺铜 DRC：普通违规 `0`，未连接 `1`，原理图一致性提示 `101`。
- 唯一未连接：`R308.2`（`146.96, 110.81`）↔ `U701.7`（`150.3625, 112.1`）。原始报告：`final-current-drc.json`。
- `analyze_pcb.py --full` 的连通图仍报告 `+3V3` 两个岛，`U701.7` 位于孤立岛；其余 `+3V3` 负载在另一岛。

## 候选尝试

| 候选 | 结果 | 证据 |
|---|---|---|
| 标准过孔/短线，左侧局部扇出 | 电气上可降到未连接 `0`，但与 `I2S_SDO`、`I2S_SDI`、`I2S_BCLK` 及 `+5V` 内层走线产生短路/间距违规 | `hardware/custom_hat/candidates/power-scan/`、`u701-sdo-shift-power2-drc.json` |
| U701 右侧绕行 | 与 `I2C5_SDA`、`I2S_LRCK`、`AUDIO_MIC_AC`、`+5V` 及 U701 裸焊盘发生冲突 | `hardware/custom_hat/candidates/u701-right-route-drc.json` |
| I2S_SDI 局部改道 | 未能同时避开 SDO/LRCK/BCLK、C305 地焊盘和内层 +5V；保留候选会新增短路或间距错误 | `u701-sdi-reroute-power-drc.json`、`sdi-via-149p8-113p0-drc.json` |
| FreeRouting 2.5.0（JRE 25） | 在固定已有走线的完整板上识别到 117 个预存固定项违规；导入 SES 后 KiCad DRC 为 `203` 项违规，`U701.7` 仍未连接，已丢弃 | `hardware/custom_hat/candidates/freerouting-u701/drc.json`；运行日志显示 `117 unfixable` 固定走线/过孔违规 |
| 清空 codec 局部后重布（FreeRouting 2.5.0） | 局部走线清空后自动布线导入，KiCad DRC 为 8 条悬空提示、13 个未连接；`U701.7` 仍未接入，且 +3V3 多个既有连接被拆散，已丢弃 | `hardware/custom_hat/candidates/freerouting-codec/drc.json` |
| R308 器件级移动候选 | 将 R308 移到 codec 左上方并重接 `CODEC_RST/+3V3` 后产生 19 条违规、3 个未连接，已丢弃 | `hardware/custom_hat/candidates/r308-move-147-109-drc.json` |
| U701/U301/U702 热过孔候选 | 一次性补孔会与 `+5V`、`BUCK_SW`、`AUDIO_MIC_*` 和现有电源焊盘产生短路/孔距违规，未回写 | `hardware/custom_hat/candidates/thermal-vias-all-drc.json`、`u701-blind-thermal-drc.json` |

## 真实性结论

1. **[实测/工具复核]** 当前唯一未连接确实存在；不是旧报告残留，也不是一致性 `101` 项的重复计数。
2. **[推断]** 仅增加板框面积不能自动解决。冲突发生在 U701 左侧 0.5 mm pitch 扇出、SDO/SDI/BCLK/LRCK、U701 裸焊盘和 +5V 内层跨线的局部几何关系；板外空余区域不会改变这些局部约束。
3. **[推断]** 继续盲目补标准过孔或放宽 DRC 会把未连接变成短路/间距违规，不能作为修复。
4. **[假设]** 可行方向是 codec 区域的联动重排：预留一个可制造的电源扇出口，重新规划 I2S 扇出和 +5V 跨区走线；是否采用盲/埋孔、改层叠或改 U701 朝向，须在工艺目标明确后决定。

## 保留的下一步

- 在独立副本中做 U701/C305/C306/C310/C313/R308 及 I2S 五根信号的整体重排，不再做单条补线搜索。
- 方案验收必须同时满足：KiCad DRC 普通违规 `0`、未连接 `0`、原始有网焊盘无丢失、`net-contract` 无新增差异、I2S 与 +3V3/+5V 层间净距通过。
- 若采用盲/埋孔或 via-in-pad，须先把制造工艺和供应商能力写入方案；在此之前不将其当作生产修复。

## 最新管线复核

2026-10-30 13:00 完整副本管线：普通 DRC `0`、未连接 `1`、ERC `0`、网表 mismatch `0`、parity `107`。未连接仍为 `R308.2 ↔ U701.7`；新增 parity 仅来自 6 个 fiducial footprint。

## 状态

主 PCB 已安全回写双面 fiducial 与板边地缝合修复，但仍未提交、不可投板。最新主板 SHA-256：`be2861ccf12aea4688b4ec5c49feb5bf6373a04151de0f90fd0a39d99c0310d7`。此前 `kicad-happy` 审查结论仍适用：BOM MPN、工艺环宽、热过孔、I2C 上拉、平面回流和真实硬件验证仍未闭合；`FD-001` 已关闭。
