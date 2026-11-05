# 功放就近去耦生产审查包（不可下单）

PCB SHA256：d6c72facdd3b68fda23a7f09b557c01a5e9bf0eb06f7662aa46990d9bd7bb805。C323移近U803并改22µF，新增C328=2.2µF及局部VDD/地回路；原连接保留，原生DRC/ERC/未连接/parity/网表全0。

70封装、1101线段、98过孔；56拟装件、37拟装BOM分组、35唯一MPN。所有文件与源绑定在manifest.json；6处filled/capped要求未变，自动默认层叠Job已隔离留证。

## 文件用途

- Gerber与钻孔：PCB加工审查；不是已获厂商接受的HDI订单。
- bom-tracking.csv：工程追踪，包含C307 DNP；不要忽略DNP列直接采购。
- bom-fitted.csv：56个拟装件，已排除DNP；含通孔件。
- bom-smt.csv + positions-smt.csv：50个拟贴装件及原生坐标子集，数量/位号一一对应。
- positions.csv：56个拟装件的完整坐标；没有再次镜像或改原点。
- assembly-plan.csv：逐位号分类；C307不装，J101/J301/J401/J402/J403/J802共6件为通孔装配，手焊/厂商代装待选择。
- assembly-front.svg / assembly-back.svg：位号/外形/DNP定位图；**底面图已镜像，CSV没有再镜像**。为避免拥挤不显示元件值，值和MPN查BOM。

装配图只由显示副本生成，源设计值、网络和几何未改；不能拿显示副本或历史Job替代本包数据。装配服务、库存、替代料与工艺尚未确认，不自动下单。

详见[同版审查与限制](../../../../docs/references/扩展板电路仿真工具/amp-decoupling-20261031/research.md)。TTL本地去耦、保护、层叠/HDI、热/控制环及实物验收仍需继续；本设计不支持带电USB源与HAT并供。未制造、未上电、未提交。
