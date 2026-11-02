# HAT孔工艺核查（2026-10-31，微孔已取消）

本页表示公开工艺能力核查，**不是板厂对本设计的接单/生产批准**。2026-10-31实际取得HDI FAQ正文和SHA256，见[本轮来源及阶段审查](../metadata-repair-20261030/research.md)。此前仅有搜索请求/链接时不能称为已核实正文。

## 当前设计

现行见[最终规则与孔铜距复审](../npth-clearance-20261031/research.md)：100个via均贯通，无盲/埋/微孔。99孔各层环宽≥0.125mm，codec原尺寸小孔名义环宽0.1mm；U301的5热孔与codec小孔共6处仍要求填孔盖铜。指定几何检查不等于厂商接受，tenting不替代POFV。参数见[普通四层送审提案](../npth-clearance-20261031/manufacturing-brief.md)。

- U701.7现为F.Cu–B.Cu机械通孔，0.35mm铜盘/0.15mm设计孔径；限定工艺规则已有反例核对，实际加工仍需接受。
- 当前原生检查包含DRU有效加载证明。历史缺单位规则下的CLI零报告不能解释为全部自定义规则通过。
- 小孔/盖铜属于需选择的工艺选项；analyzer的advanced标签不等于必须HDI，也不构成IPC等级认证。

## 外部工艺依据与历史范围

- 当前按[普通PCB能力页](https://jlcpcb.com/capabilities/pcb-capabilities/)所列小机械孔选项核对，不把推荐0.2mm误写成绝对不支持0.15mm。
- [via-in-pad指南](https://jlcpcb.com/help/article/via-in-pad-pofv-guide)作为POFV依据；U701窄向焊盘0.25mm、via铜环0.35mm的具体联合land/Mask仍需厂商审核。
- [HDI FAQ](https://jlcpcb.com/help/article/hdi-pcb-capabilities-faq)曾用于旧B–In2微孔的激光孔径/PP厚径比核查，原件与SHA保留；这些盲孔要求不再用于当前设计。

## 结论

当前不需要激光盲孔层叠，但普通4层的实际材料/铜厚、小机械孔、填孔盖铜和装配仍需核准。PTH/NPTH钻孔已分开；工艺CSV区分KiCad正Y向下与CAM名义Y取反的坐标，不能再次镜像B面。默认0.48mm×3介质Job仍被隔离。未确认前保持制造未放行，不以文件检查替代供电/保护或首板验收。

新增5处U301热通孔为0.55/0.3mm，且有整面散热焊盘锡膏开口；须按填孔盖铜后的表面条件协调钢网/装配。填充材料、盖铜平整度和实际层叠仍需在正式工艺单确定，CSV和PCB字段不等于已经加工或报价通过。
