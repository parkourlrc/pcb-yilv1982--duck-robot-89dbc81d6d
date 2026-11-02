# 当前HAT生产审查包（未放行，不可下单）

历史检查点：后续仅补电源输入丝印，现行使用[power-final-review](../production-20261031-power-final-review/README.md)。本包原工艺/几何结论保留，但制造文件不混用。

源PCB SHA256：`a65f2ad8cab72721944b670dbdb6505533ae60988ce5bb3c6be51be81b3ab0a1`。详情见[最终规则/工艺复审](../../../../docs/references/hat-simulation-tools-20261029/npth-clearance-20261031/research.md)和[送审参数](../../../../docs/references/hat-simulation-tools-20261029/npth-clearance-20261031/manufacturing-brief.md)。

- 普通4层，100个贯通via，无盲/埋/微孔；一个0.15mm小机械孔仍需特殊孔工艺/POFV接受。
- PTH/NPTH钻孔分开，159/4个圆孔逐项核对；没有盲孔分层钻孔文件。
- 58拟装件、38分组、35唯一MPN，52 SMT+6 THT，C307 DNP；BOM/坐标/双面装配图同版。
- 6处填孔盖铜要求及KiCad/CAM名义坐标见via-process-requirements.csv；底面装配图镜像，坐标不再镜像。
- 默认介质Job已隔离，实际铜厚/材料/工艺、保护及电气/实物验证仍未放行。

当前检查包含自定义规则加载哨兵证明，不再只依赖CLI返回码或零违规计数。manifest.json绑定源和产物；所有更早目录均为历史检查点，不混用文件。
