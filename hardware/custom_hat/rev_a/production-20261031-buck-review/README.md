# Buck 热通道与输入去耦检查点生产审查包

> 历史包，已被[反馈/补偿重排包](../production-20261031-control-review/README.md)替代；不得混用旧坐标/钻孔与新PCB。

源PCB SHA256：6555f994e1ee6b99949df5ee4cfc35ce31169f6b0d01421cdd037f6736ec410d。68封装、1131线段、102过孔；54/54拟装件有设计MPN。原生检查全0，原连接保留。

U301.9新增5个0.55/0.3mm地热孔；C303靠近VIN，C308直接接LDO输入。**via-process-requirements.csv列出的5个热通孔和1个微孔必须填孔盖铜**，坐标为同一绝对毫米坐标系，B面未镜像。PCB字段/CSV表示制造要求，不表示供应商已接受或实物已经加工。

HDI层叠/介质、填充材料/盖铜平整度、钢网及热/电气/载流条件尚未核准；普通无填孔四层工艺不能直接代用。H1/H2排母侧≤4.5mm圆柱头且无垫圈要求继续有效。

**仅供审查，不可下单。** [完整报告及标注图](../../../../docs/references/hat-simulation-tools-20261029/buck-thermal-20261031/research.md)。各输出含CSV的哈希见manifest.json，旧阶段包不混用。
