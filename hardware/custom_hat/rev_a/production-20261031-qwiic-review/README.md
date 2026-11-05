# Rev A.1生产审查包（未放行，不可直接下单）

> **2026-11-02用途更正：本目录保留X2内部审计基线。** 嘉立创国内文档要求RS-274-X，现行国内输出见[派生包入口](../../release-review/README.md)，11层绘图等价、钻孔和装配资料保持。本目录不再作为直接发国内工厂的格式包；不改变源A.1身份及既有检查证据。

PCB SHA256：`90f27091017525a22f45c8818c973c317ed6262387a98fdf06bdc26337dac2a6`。工程文件名保留rev_a系列，板面标识/实际修订为**A.1**。

**本版J502针序为1=GND、2=3V3、3=SDA、4=SCL。旧Rev A顺序不同，不能混用。** 本轮还按C307不贴装意图排除两个F.Paste开口，保持其PCB铜和阻焊。

- 65×30mm、4层；72封装、1130线段、100贯通via，无盲/埋/微孔。
- 58拟装件、38组、35唯一MPN；52 SMT、6 THT；C307 DNP。
- PTH/NPTH钻孔159/4，共163圆孔逐项匹配；6处填孔盖铜仍需接受。
- F.Paste为59个flash、B.Paste为128个；只有C307两个开口排除，其它拟装器件开口保持。
- 底面装配图已镜像；CPL/CAM坐标不再次镜像，工艺CSV同时列板坐标与CAM名义坐标。
- manifest绑定源、输出和钢网导出策略。默认未知stackup的Gerber Job已隔离，不能拿旧Job作为板厚/介质依据。

详见[修复记录](../../../../docs/references/扩展板电路仿真工具/qwiic-pinout-20261031/research.md)、[kicad-happy审查](../../../../docs/references/扩展板电路仿真工具/qwiic-pinout-20261031/review.md)及[制造参数提案](../../../../docs/references/扩展板电路仿真工具/qwiic-pinout-20261031/manufacturing-brief.md)。制造工艺/装配/输入条件与新板实测仍未完成；本轮未上传、下单或操作实物。
