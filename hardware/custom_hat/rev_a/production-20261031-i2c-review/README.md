# Rev A I2C5 修复后的生产审查包

> 历史包，随后C305/C309盘中孔已修。现行使用[cap-vias审查包](../production-20261031-cap-vias-review/README.md)，不能与新主PCB混用。

源PCB SHA256：a96508311bfc66dbab1b94b54d0391a7552f8f979acbbe26603ca281171336dc。设计和输出指纹见manifest.json。

- 4层铜、双面Mask/Paste/丝印、板框Gerber、通孔及微孔钻孔；排除DNP的贴装坐标；BOM跟踪CSV。
- 54个拟装器件中18件已选MPN、36件待选；3个裸铜测点不采购，C307 DNP。
- 两颗4.7kΩ I2C5上拉已加入；初始100kHz/总线电容240pF为设计条件，未实测。
- DRC普通违规/未连接/parity/ERC/netlist mismatch全0；热布局、HDI/盘中孔、剩余物料未完成。

**仅供审查，不可下单。** [kicad-happy阶段报告及原始数据](../../../../docs/references/hat-simulation-tools-20261029/i2c-pullups-20261031/research.md)。本包替代旧production-20261031-review的现行审查地位。
