# HAT 通孔环宽与地连通修复（2026-10-31，现行检查点）

> 历史检查点：随后已完成54/54设计MPN并修L301/R309封装、相关局部布线。现行见[全量设计料号审查](../final-bom-20261031/research.md)；本页通孔环宽与地连通结论仍有效，下列源哈希/计数仅对应本阶段。

## Overview

规则勘误：本阶段实际扩大23个孔的几何记录保留；当时新增DRU数值缺单位，不能把零报告解释成0.125mm规则已有效执行。后续已修单位、验证加载并采用一处限定小机械孔工艺，现行见[规则复核](../npth-clearance-20261031/research.md)。

用户持续授权解决全部已知问题；主会话执行，未用子代理。**[本机文件/工具检查] 23个旧0.1mm环宽的通孔已增大，现行96个通孔的标称环宽全部≥0.125mm。** 原0.3mm钻孔未缩小；U701.7的0.35/0.15mm激光微孔仍是0.1mm环宽，继续按HDI处理，未混入通孔验收。

现行PCB SHA256：ac2df1571ac0fe778bbbf427bd90e8d548cdb644fca0e0728c79e034d6767abc。68封装、932线段、97过孔（96通孔+1微孔）、4铜区。DRC普通违规、未连接、parity、ERC、netlist mismatch全0。MPN46/54，剩8件。总体设计未完成，**不可投板**。

## Previous Review Delta

| 项目 | 上阶段 | 当前 |
|---|---|---|
| 0.1mm通孔环宽 | 23个 | 0个；扩大到0.55/0.3mm |
| 地缝合孔 | 6个 | 7个；新增U702附近0.6/0.3mm通孔 |
| 通孔环宽规则 | 可被旧0.09mm原型规则覆盖 | 新增最后优先的Through-via最小0.125mm规则 |
| U701.7微孔 | 0.35/0.15mm | 未改，HDI条件仍待完成 |
| 文件检查 | 全0 | 保持全0，原焊盘连接全部保留 |

之前完成4个连接器MPN、J101外壳/预留区错位与H1/H2装配约束修复，详见[连接器报告](../connectors-20261031/research.md)。这些是同一任务连续进展，不把阶段检查点当完整制造放行。

## Critical Findings

1. 仍缺8件MPN：J401/J402/J502/J504/J505/J506、L301、R309。
2. 选定MLCC偏压容量/ESR、LDO稳定性条件、buck负载瞬态、整板电流预算/入口和配对线束额定仍需核算。
3. AP64350热/回流布局、U701.7微孔的HDI层叠/填孔与制造接受条件未完成。
4. H1/H2靠排母一侧必须用外径≤4.5mm的M2.5圆柱头，不加垫圈或六角隔离柱；螺钉长度/另一侧堆叠仍待核。实物功能、温升、装配未验证。

## Component Summary

54个拟装器件：46个有设计MPN，8个待选；30/38有效采购分组已填，C307仍DNP，3个铜测点不采购。4安装孔+6fiducial为board-only。本轮未更改任何元件值、封装、引脚或物料字段。

## Power Tree

2S→AP64350→5V；Radxa 3.3V→LP38691→codec 1.8V；R309桥接舵机动力网。新增地孔只把U702地引脚所在B.Cu区接回其他地层，未增设电源或改变分支。

## Analyzer Verification

geometry-connectivity-check.json逐项检查：原焊盘几何/网络不变；旧铜只改变changes.json指定23个via、shifts.json列出的相连短线及1段MCLK；新增3段MCLK线和1个地孔。所有原焊盘连接保留，通孔数量96、最小环宽0.125mm；原工程.kicad_pro逐字哈希相同，DRU仅新增更严格通孔规则。

原生CLI重铺铜并保存后读连接图；候选和回写主工程均完整检查通过，见post-promotion-summary.json。进一步加pipeline配置指纹护栏后又运行完整副本检查，报告在hardware/custom_hat/runs/20261030T182035Z-84d3d590/reports/1c6bffdaec9b/summary.json。

## PCB Layout Analysis

23个via铜盘0.50→0.55mm，保持0.30mm孔径。6个via在局部移动：5个移动0.025mm，1个约0.276mm，相连短线同步移动；位置在shifts.json。为避开codec附近两条平行信号，MCLK仅局部绕开0.05mm，线宽保持0.25mm、原端点不变，细节见mclk-detour.json。

较大铜盘改变铺铜颈部后，U702的一个GND焊盘所在区曾断开；尝试B.Cu直连及两个供电via小位移未成功，均未回写。最终在(125.25,120.75)添加0.6/0.3mm地通孔，直接连接各地层。其铜外缘距最近焊盘实际Mask包围框0.15mm，没有新增盘中孔；完整DRC和原焊盘连通恢复通过。原生F/B图已导出，B图已打开检查；底面未镜像。

## Signal Analysis Review

MCLK端点网络、宽度保持；局部路径改变没有经过实物时序/EMI验证。I2C5上拉、I2S方向、TTL、IMU/ToF和音频网络不变。不能把DRC或连接保留称为这些功能已运行。

## Power Analysis

孔径未缩小，扩大环宽不以牺牲孔壁截面换取通过。via电流、热和电源环路仍需结合板厚、镀铜厚度、负载/温升条件核定；0.125mm只是本设计设置的几何下限，不是IPC等级认证或制造公差保证。

## PDN Impedance

本轮修复局部地连通，不等于整个参考平面连续性优化。真实MLCC偏压/ESR/ESL和布线寄生尚未进入完整模型；自动默认曲线不用于PDN验收。

## Power Budget

J301电池入口承载逻辑与舵机分支之和，不能把Samtec两接点通电条件的电流额定当成整板额定。EH座/线规、R309、L301及主控真实负载预算待完成；未上电或改变现有机器配电。

## Thermal Analysis

热analyzer已运行，仍仅评估2件、总耗散0.043W假设，不把100分当温升验收。新增地孔不在U301/codec的大散热焊盘内，未声称完成热布局；codec热孔依应用可选，TO-252不套WSON孔数要求，详见cap-vias专题勘误。

## EMC / Cross-Domain Analysis

cross仍2 warning，EMC仍57项（9 error/35 warning/13 info）。VS-002“没有地孔”与当前7个原生地孔矛盾；PS-002孤岛结论仍需原生连接图/实际参考层交叉解释。文件电气连通已保留，实际高速回流和EMI仍未验收。

## Simulation Verification

ngspice 47自动子电路12/12 pass，仅理想/行为模型。自动AP64350反馈Vref仍错用0.6V，真实器件0.8V；未用其结果放行电源。没有把本轮绕线自动代入真实寄生/频域仿真。

## Component Lifecycle

30个唯一MPN已查，全部unknown；接口不返回生命周期，不表示在产/库存通过。之前连接器查询返回型号不符的条目已拒绝，本轮未采用错误供应数据。

## Manufacturing / DFM

新同版[生产审查包](../../../../hardware/custom_hat/rev_a/production-20261031-annular-review/README.md)包括Gerber、钻孔、坐标、BOM与manifest。23个旧细环宽通孔已不再是现行问题；analyzer仍报0.1mm环宽/0.15mm孔径是因为那一个激光微孔，不能把它重新解释为仍有23个细环宽通孔。

U701.7仍需HDI层叠/介质厚度/填孔接受条件。PM-002的J101约0.345mm是courtyard到边，实体约0.845mm；FID2/5同理是courtyard边距，实际铜边距1mm。没有忽略KiCad DRC，拼板夹持和机械实装仍待核。

## False Positives / Reviewer Overrides

PCB analyzer共56项（3 error/15 warning/38 info）；3个error均为上面已说明的包围框边距。Gerber两项Paste数量比例警告不能直接判漏锡膏。DS-002未发现同级datasheets目录，但原厂资料在各专题；未知MPN和未取得曲线的部分仍未核准。

## Failure Record / Workflow Correction

初版扩大23via产生13个间距错误；通过原生形状检查、局部移动/MCLK绕行后，出现1处U702地断开，后以焊盘外缝合孔恢复。

一次局部偏移试验错误地从无配套项目的独立PCB快照加载，SaveBoard把**候选**.kicad_pro写成默认值，造成233项不可比DRC。主工程未被该操作修改。已保留错误设置/报告，按源manifest精确恢复候选设置；脚本改为先把快照恢复到配套项目路径再加载。该233项不算新增设计缺陷，也不掩盖真实1处地断开。

pipeline新增.kicad_pro指纹护栏：默认必须与prepare源一致，若有意修改项目设置，需在manifest记录经审阅的approved_project_settings_sha256；不再静默用默认规则继续跑DRC。DRU加强单独记录，本轮未放宽旧间距/线宽/孔径规则。

早期native-connectivity-diagnostic.json的层标签受GetLayerName接口默认值影响不正确，只保留为历史诊断；脚本已改用board.GetLayerName(layer)，该旧文件不是最终验收依据，最终依据为geometry-connectivity-check.json和原生DRC。

## Analyzers Actually Run

kicad-happy提交2fd9aa0fe2d620f36627d9221e8b1393987ae38e；实际运行schematic、pcb --full、gerbers、cross、EMC、thermal、SPICE、lifecycle、prior schematic delta，日志和命令JSON同目录。源文件、原生图与脚本也保留。

## Not Performed / Review Limits

8件剩余MPN、已选电容有效参数、入口/动力载流、整体热/回流/HDI条件、实物功能/温升/装配均未完成。没有首板、订单、付款、实物操作、commit或push；不能从文件绿灯升级为可制造。

## Final Verdict

已关闭23个通孔环宽问题，并修复由铜盘变化暴露的地连通；原连接全部保留。4个连接器MPN和J101实体错位也已在前一检查点修正。总体目标继续，下一阶段处理剩余JST连接器、电感、动力跳线及电源/热/HDI条件，再做最终审查与首板验收。

收尾证据写入final-audit.json；规则护栏用本次真实捕获的错误默认设置重放，必须在执行任何CLI命令前拒绝，源板保持不变。新导航链接、源/输出哈希及git diff --check一并核对；修改未提交。
