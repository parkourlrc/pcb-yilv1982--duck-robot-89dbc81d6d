# Rev A 同版生产审查包（2026-10-31）

> 历史包，已被[补I2C5后的同版包](../production-20261031-i2c-review/README.md)替代。下列计数只描述旧检查点，不再作为现行BOM或设计状态。

来源主 PCB SHA256：`d4fc46fa5fe08beb8e48d91caef4b23493d8d54641a8e31108c0f968642f61e2`。源工程与每份输出哈希见 `manifest.json`。

- 包含4层铜、双面Mask/Paste/丝印、板框Gerber；通孔和In2–B微孔钻孔；排除DNP和板级标记的贴装坐标；BOM跟踪CSV。
- DRC、未连接、原理图一致性、ERC、网表 mismatch 均为0；不代表功能、热或制造验收。
- 7/52贴装器件已选MPN；余45件未选。U702已改为LP38691DT-1.8/NOPB，三个铜测试点不列采购件。
- Fiducial无锡膏，Mask开口2mm；前轮有fiducial Paste的包停用。
- U701.7采用0.35/0.15mm B.Cu–In2微孔；HDI层叠、填孔、热布局、I2C5上拉和实物验证尚未完成。

**仅供审查，不可下单。** 现行详细依据见[元数据与BOM阶段审查](../../../../docs/references/hat-simulation-tools-20261029/metadata-repair-20261030/research.md)。
