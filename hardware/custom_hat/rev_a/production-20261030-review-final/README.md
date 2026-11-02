# Custom HAT Rev A 生产审查包（2026-10-30）

- 来源主 PCB：`../custom_hat_rev_a.kicad_pcb`
- KiCad：10.0.7
- 本包包含当前主板的 Gerber、Excellon drill、drill map/report 和前后面 CPL/POS。
- 当前电气 DRC/ERC：普通 DRC `0`、未连接 `0`、ERC `0`、网表 mismatch `0`。
- 设计仍不可下单：BOM MPN 未锁定；U701.7 修复使用 `0.35/0.15 mm` B.Cu→In2.Cu microvia，需要制造商确认 advanced/HDI 工艺；热过孔、via-in-pad、I2C 上拉、平面回流和硬件实测未闭合。
- 这是审查包，不是投板放行包。
