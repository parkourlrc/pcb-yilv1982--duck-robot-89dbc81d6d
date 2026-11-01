# Rev A 生产审查包（不可下单）

- 来源：`custom_hat_rev_a.kicad_pcb` 当前主版本，KiCad 10.0.7。
- 导出内容：当前 Gerber、Excellon drill、drill map、BOM CSV、CPL CSV。
- 用途：检查当前源到制造格式的导出链路；不是生产放行包。
- 阻塞：`R308.2` 与 `U701.7` 的 `+3V3` 仍未连接；BOM 缺 MPN；无双面 fiducial；环宽/热过孔/via-in-pad/I2C 上拉和 +3V3 平面回流仍需审查。
- 当前 `kicad-happy` review：见 `docs/references/hat-simulation-tools-20261029/kicad-happy-review-20261030/review.md`。
- 重新导出时必须使用当前主 PCB 和原理图，不能复用旧 `production/` 文件。
