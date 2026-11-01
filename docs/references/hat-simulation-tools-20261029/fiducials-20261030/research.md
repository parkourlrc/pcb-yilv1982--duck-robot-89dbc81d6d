# 双面 Fiducial 修复记录（2026-10-30）

## 结果

- 在主板 F.Cu/B.Cu 各加入 3 个 `Fiducial_1mm`，位置为 `(106,101.5)`、`(159,101.5)`、`(106,128.5)` mm。
- 候选 `hardware/custom_hat/candidates/fiducials-clean2.kicad_pcb`：KiCad 10.0.7 DRC 普通违规 `0`，未连接仍为原有 `U701.7 ↔ R308.2` 一项。
- 回写主板后：footprint `60 → 66`，主板 SHA-256 为 `c40ada40b49978e30a189e93540449d49437c252264b08ce9a1a7d3e56c01d21`；完整管线 DRC 普通违规 `0`、ERC `0`。
- `analyze_pcb.py --full` 不再产生 `FD-001`；`analyze_gerbers.py --full` 对当前 Gerber 包未产生 fiducial 缺失项。

## 限制

- 原理图/PCB parity 提示增加 6 个 `extra_footprint`，这是装配基准未出现在原理图中的预期差异，不是信号赋网变化；pipeline 的 `netlist_check` 仍无新增 mismatch。
- 位置通过板级 DRC 和装配空间初筛，最终仍需结合贴片厂 fiducial 边距、板边夹持和拼板规则确认。
