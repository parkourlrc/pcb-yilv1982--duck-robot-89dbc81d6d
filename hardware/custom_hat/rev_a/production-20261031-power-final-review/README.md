# 历史HAT生产审查包（已被替代，不可下单）

本包源70586fc6…已被[codec复位同版包](../production-20261031-codec-reset-review/README.md)替代。保留电源标识阶段证据，不用于当前制造。

源PCB：`70586fc6d5c68f322d49f56fa657ac89537fdf7702ad5e5261a5b253e5ca8fbe`。本版新增J301电池输入标识；电气参数与孔/线路保持。详见[电源核对](../../../../docs/references/扩展板电路仿真工具/power-acceptance-20261031/research.md)和[接口/保护范围](../../../../docs/references/扩展板电路仿真工具/power-acceptance-20261031/power-interface.md)。

- 58拟装件、38组、35唯一MPN；52 SMT、6 THT，C307不装。
- 普通4层、100贯通via；PTH/NPTH钻孔159/4，163孔逐项核对；6处仍需填孔盖铜。
- 底面装配图已镜像，CPL/CAM不再镜像。工艺CSV同时给板坐标和CAM名义坐标。
- 制造数值继承[上一版提案](../../../../docs/references/扩展板电路仿真工具/npth-clearance-20261031/manufacturing-brief.md)，但生产文件须使用本目录；小孔/land/POFV、实际层叠及装配尚待接受。

manifest.json绑定当前源与产物。不要将本轮模型计算当真实环路/温升/负载验收；未下单、上电或采购。
