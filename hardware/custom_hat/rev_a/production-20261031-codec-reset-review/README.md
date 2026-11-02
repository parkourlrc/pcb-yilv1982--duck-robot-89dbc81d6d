# 历史Rev A生产审查包（已被A.1替代）

**不要用于当前制造。** 本包J502仍是旧V/G/SCL/SDA顺序，不能当标准Qwiic直插；F.Paste仍有C307两个开口。现行请使用[Rev A.1包](../production-20261031-qwiic-review/README.md)，原文件保留追溯。

源PCB：`6fe440f3cfcd9a30550299258cba5bf9355d888b0c166f62919a21adfc5de82a`。新增J101.33至CODEC_RST通路，保留R308/C310 RC并补回codec 3.3V支路；另整理40P/TTL原理图显示。详见[修复记录](../../../../docs/references/hat-simulation-tools-20261029/codec-reset-20261031/research.md)及[kicad-happy复审](../../../../docs/references/hat-simulation-tools-20261029/codec-reset-20261031/review.md)。

- 72封装、1129线段、100贯通via，无盲/埋/微孔。
- 58拟装件、38组、35唯一MPN；52 SMT、6 THT，C307不装。
- PTH/NPTH钻孔159/4，共163孔逐项匹配；6处仍需填孔盖铜。
- 底面装配SVG已镜像，CPL/CAM不再镜像；工艺CSV同时给板坐标和CAM名义坐标。
- 制造数值参考[工艺提案](../../../../docs/references/hat-simulation-tools-20261029/npth-clearance-20261031/manufacturing-brief.md)，使用本目录同版文件；小孔/land/POFV、实际层叠、铜厚与装配仍待接受。

manifest.json绑定源与输出；默认未知stackup的Gerber Job已隔离。codec复位波形、当前主控驱动、音频/TTL/IMU/ToF、供电/热和实装没有完成实测。未下单、上电或采购。
