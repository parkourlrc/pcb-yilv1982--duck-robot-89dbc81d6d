# 全量设计MPN检查点生产审查包

> 历史包，已被[Buck布局修复包](../production-20261031-buck-review/README.md)替代；特别是新增热孔的填孔盖铜清单不可遗漏或与旧钻孔文件混用。

源PCB SHA256：335aea311c179be20bfd9f6531bdad8687ba58be211df88c81e49cd5f35471ca。54/54拟装器件、38/38有效分组均有设计MPN；C307仍DNP，裸铜测点不采购。

L301为5.6µH IHLP4040DZER5R6M5A，R309为WSL120600000ZEA9，专用焊盘已匹配；68封装、968线段、97过孔。DRC/未连接/parity/ERC/网表全0，原连接保留。H1/H2排母侧≤4.5mm圆柱头且无垫圈要求继续有效。

**BOM字段完整不等于可下单。** 载流、偏压/ESR、热/回流、HDI及实物验证仍未完成，见[现行kicad-happy审查](../../../../docs/references/hat-simulation-tools-20261029/final-bom-20261031/research.md)。输出指纹在manifest.json，旧包不与本版混用。
