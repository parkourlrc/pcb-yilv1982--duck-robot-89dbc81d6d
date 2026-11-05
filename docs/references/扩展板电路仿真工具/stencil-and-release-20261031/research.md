# C307 DNP锡膏图修正检查点（2026-10-31）

本目录保留在PCB源6fe440f3…上首次验证的钢网导出修复。**已被后续[Rev A.1同版结果](../qwiic-pinout-20261031/research.md)取代，不作为当前生产包。** 原始证据和失败定位仍保留。

旧F.Paste包含C307的两个D03 flash，坐标为(157.525,-114.0)与(160.475,-114.0)mm（CAM坐标）；BOM/CPL已按C307 DNP排除。这不证明已有实物短路，但不符合本次不贴装该器件的钢网意图。

export_dnp_stencil.py在完整绘图副本中仅移除两个DNP pad的F.Paste成员，由KiCad原生重新输出；AST恢复对照确认除此之外未改其它字段，原PCB保持。其余9个非paste层仅忽略生成时间/校验元数据后相同，所有非DNP paste的坐标/aperture/宏定义一致；F61→59，B128不变。原始图在unfiltered-paste/，修复结果在dnp-stencil-policy.json。

流程已接入checkpoint_i2c_review.py，后续A.1重出也执行同样规则；BOM总审计已增加实际Gerber比对，防止仅更新清单却继续输出DNP锡膏。不存在制造接受或实物测试结论，未发送/下单。
