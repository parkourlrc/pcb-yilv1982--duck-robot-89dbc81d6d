# HAT Buck 热通道与输入去耦修复（2026-10-31，现行）

> 历史检查点：随后FB/COMP器件和走线已集中到U301旁。现行见[控制回路布局修复](../buck-control-20261031/research.md)；本页热孔、输入电容与6处工艺要求继续有效，下面哈希/计数仅对应本阶段。

## Overview

主会话按持续授权执行，未用子代理。**[文件/工具核对] U301散热焊盘内新增5个真正同网的地通孔；C303移近VIN；C308移出Buck背面并直接接到LDO输入。** 所有原有焊盘连接保留，未放宽工程规则。

现行PCB SHA256：6555f994e1ee6b99949df5ee4cfc35ce31169f6b0d01421cdd037f6736ec410d。68封装、1131线段、102过孔（101通孔+1微孔）、4铜区；54/54拟装件MPN与数值不变。原生DRC普通违规、未连接、parity、ERC、网表mismatch全部0。**这是布局检查点，尚不可投板。**

## Previous Review Delta

| 项目 | 修改前 | 当前 |
|---|---|---|
| U301.9热焊盘内同网孔 | 0 | 5，均连EP及F/In1/B地铜 |
| C303输入电容 | VIN引脚到电容正极直线距离14.17mm | 电容移至(126.84,108.8)，新增0.6mm供电线2.7025mm |
| C308 LDO输入电容 | 覆盖Buck背面，独立via供电 | 移至(123.7,115.6)、90°，0.3mm同层线直接接U702.3，路径2.8304mm |
| 原C308供电via/支线 | 存在 | 删除1个via/1条支线；放开热孔空间 |
| 填孔盖铜要求 | 微孔仅有未锁定工艺记录 | 5个热孔和1个微孔显式标为filled/capped，并导出坐标表；厂商尚未接受 |
| 原理图文字 | 错写35V abs-max、未限定44µF、旧音频骨架说明 | 按厂商资料与现有电路修正 |

## Critical Findings

1. **完整热能力仍未验收。** 新热孔是明确的铜通路，不能由孔数推出本板θJA或持续输出电流。
2. **有效电容、控制环和载流预算仍待完成。** 输入电容变近不能替代DC bias/ESR/温度核算；FB/COMP外部件仍需要集中复核，整板入口、EH/SH与线束额定尚未协调。
3. **工艺要求尚未获接受。** 5处热通孔与U701.7盲孔需按via-process-requirements.csv填孔盖铜；HDI层叠、介质、材料/平整度等仍待正式工艺单，不能用tenting代替。
4. **首板未制造，音频/I2S/TTL/IMU/ToF/供电/温升/装配均未实测。** H1/H2排母侧≤4.5mm M2.5圆柱头且无垫圈的装配约束继续有效。

## Component Summary

没有新增采购器件、改变容量/MPN或删除功能；C303仍10µF/25V，C308仍1µF/50V。54个拟装件、38个BOM分组、36个唯一MPN不变，C307仍DNP。5个热孔和1个输入地孔是板内铜对象，不伪造采购料号。

## Power Tree

保持2S→AP64350→5V；Radxa 3.3V→LP38691→codec 1.8V；R309桥接舵机动力网。图上AP64350的40V推荐输入/42V DC绝对最大值仅是**芯片额定**，不是HAT可接40V的许可；整板继续按2S应用设计。

## Analyzer Verification

geometry-connectivity-check.json在两份完整项目重铺铜并保存后核对：只允许C303/C308的4个焊盘移动/转向；删除原C308供电via及支线、4段AUDIO_AMP_EN；保留其余原线路，除BUCK_EN的1个via和2段接线作指定移动。所有原赋网/原焊盘连接保留。

每个新热孔均在U301.9真实矩形内、网络POWER_GND、原生连接图连到EP；保存后的F.Cu/In1.Cu/B.Cu地铜在via中心存在。没有使用分析器的放大包围框/混网计数作为证据。候选和回写主板的完整检查均全0，post-promotion-summary.json绑定当前源哈希。

## PCB Layout Analysis

- C308位于B.Cu，直接供电线2.8304mm；其旧供电via移除，避免把新地焊盘放到旧3V3孔上。AUDIO_AMP_EN仅在局部绕开新位置，0.25mm线宽及端点不变。
- C303位于F.Cu，正极对齐U301.2，新增0.6mm直线2.7025mm；原14.17mm是引脚直线距离，**不是原走线长度**。其原位置的VBATT三路铜仍保持连续，不留悬空支线；C304保留原位作另一颗输入电容。
- 新增C303地via位于(129.5,108.2)，0.6/0.3mm，焊盘外；BUCK_EN via移至(128.8,110.4)并同步两段线，避开电容与RT焊盘。
- 5个热孔均0.55/0.3mm，环宽0.125mm，孔心最小间距0.8mm。位置与UUID在thermal-vias-added.json，未加到背面其他焊盘内。
- 原生F/B图及[标注图](thermal-layout-review.png)已打开检查；B面以同一顶视坐标呈现，未镜像，不能直接当插头观察面。

## Thermal Analysis

**[文件事实]** 新热孔给EP与三层地铜建立了明确连接；**[推断]** 这提供了额外垂直导热通道，但实际温升还受铜厚/面积、气流、装机环境及芯片损耗影响，不能排除这些因素成为主要限制。

Diodes DS41976 Rev5-2 p22建议输入电容靠近VIN/GND、外层2oz及更多地热孔；p4/p11的45°C/W对应四层、2oz、推荐布局测试条件。本板In2仍是3V3及其他走线，铜厚/工艺尚未锁定，不能套该热阻值宣称温升通过。codec热孔依应用可选，TO-252不套WSON孔数门槛。

analyze_thermal.py本轮仍仅评估2件、总耗散0.043W假设，100分不是验收；原始同网热孔数U301=5，工具报“6/5 adequate”仍有混网/范围误计。U701=0、U702=0不自动判失败，需按封装/功耗评估。

## Power Analysis

buck-loss-scenarios.json使用原厂p5典型25°C导通电阻HS75mΩ/LS45mΩ、标称5.6µH/500kHz/4.984V，计算Vin6.6/7.4/8.4V及1/2/3.5A九个场景。3.5A时导通项约0.772–0.830W。**只是导通损耗示意，不是实测，也不是完整损耗的保证上/下界**；未含开关、磁芯、栅驱动、温变Rds和控制环。不能用自动0.043W假设覆盖这些负载条件。

## PDN Impedance

电容位置和连接改善不等于有效电容/PDN已核准。MLCC DC bias/ESR/老化与AP64350、LP38691要求仍待逐项核对；C303名义10µF与C305/C306名义44µF不能直接作模型有效值。

## Power Budget

本轮未改变接插件或供电分支，整板输出额定仍未锁定。EH 3A/AWG22、SH 1A/AWG28、J301实际配对及PCB铜箔各有约束；不能把跳线65A或Buck芯片3.5A当整板持续额定。

## Signal Analysis Review

AUDIO_AMP_EN是本轮唯一重绕的音频控制网，未改其逻辑；其他音频/I2S信号端点和电路保持。原理图不再声称音频只是待实现骨架，也没有把实际驱动/音质未测改成已验收。I2C5上拉与100kHz/240pF初始设计条件不变。

## EMC / Cross-Domain Analysis

cross仍2 warning；EMC57项（9 error/35 warning/13 info），不是EMC实测。现在原文件有13个地via，VS-002仍说无地孔，不能采纳该数量判断。增加地连接不等于I2S回流/参考层连续性已核准。

## Simulation Verification

ngspice自动子电路12/12 pass仍为理想/行为模型；AP64350自动反馈Vref0.6V不符合真实0.8V，未用其结果放行电源。没有把本轮铜布局自动等同于完整寄生/闭环/热仿真。

## Component Lifecycle

36个唯一MPN重复查询均unknown；接口不提供生命周期，不推导为在产或库存通过。BOM数值/料号本轮未变。

## Manufacturing / DFM

[现行审查包](../../../../hardware/custom_hat/rev_a/production-20261031-buck-review/README.md)新增via-process-requirements.csv。共有6个必须单独处理的位置：5个F–B热通孔、1个In2–B微孔。PCB已设置filled/capped，CSV为同版绝对毫米坐标；它是**制造要求**，不是厂商确认或实物填孔证据。

钢网开口本轮未改；不凭泛化建议认定现有1:1开口必错。正式钢网/焊接工艺需与填孔盖铜后的表面条件协调。微孔层叠/介质和填充材料、平整度仍须在正式工艺单明确；不可拿普通四层无填孔服务直接下单。

## False Positives / Reviewer Overrides

PCB analyzer共56项，3个error仍为J101/FID2/FID5的courtyard边距，实际实体/铜边距另有记录；原生铜间距全0。Gerber的2个Paste闪光比例警告不是漏锡膏证明。热孔计数混入其他网、VS-002及DS-002目录发现限制沿用原始交叉核对，不关闭原生规则。

## Text Corrections

power.kicad_sch撤回“14–16V热插拔扫参即可说明低于35V绝对最大值”的旧说明：35V不是AP64350本项DC额定，旧理想扫参也不是本板实测。现在注明Vishay SMBJ12A的特定脉冲钳位条件及AP64350的40/42V器件边界，整板瞬态协调仍待验。

C305+C306改为每颗22µF**标称**，有效值未验证；audio.kicad_sch的“待完整实现C1音频骨架”退出现行，更新为已画电路但驱动/电气未验证。未改器件数值或误称已实测。

## Failures / Source Basis

原位置扫描0.6/0.3mm和0.55/0.3mm热孔均无合格网格点，阻挡来自C308、AUDIO_MIC、DXL_DIR等；有限扫描不证明绝对不可能。初次C308搬移产生13违规，改成直接接U702输入、删旧供电via并绕AUDIO_AMP_EN后通过。C303新位置最初7违规，BUCK_EN/地via移位后余1个RT间距问题，修正后全0；失败报告仍在run目录。

原厂依据为已归档metadata-repair-20261030/sources/AP64350.pdf：p3引脚、p4额定/热条件、p5典型Rds、p11热公式、p22布局；来源https://www.diodes.com/assets/Datasheets/AP64350.pdf。TVS条件来自bom-passives专题Vishay88392，LDO/电容依据沿用前一专题。通路/坐标/规则证据取自本机现行文件，所有推断未升级为实测。

## Analyzers Actually Run

kicad-happy提交2fd9aa0fe2d620f36627d9221e8b1393987ae38e，实际跑schematic、pcb --full、gerbers、cross、EMC、thermal、SPICE、lifecycle、prior schematic delta；命令与JSON/日志同目录。最后又通过原生连接图/字段/指纹复核，未把单一评分作为放行。

## Not Performed / Review Limits

完整负载/载流预算、MLCC有效参数、控制环/寄生、装机热、I2S回流、HDI工艺接受及首板实物功能/装配未完成。未下单、付款、上电、commit或push。

## Final Verdict

关闭U301散热焊盘“没有同网热孔”的布局缺口，并把一颗输入电容移到VIN附近；C308也改为靠近LDO输入的直接连接。文件检查及原连接保留通过。**热能力与整板制造仍未放行**；下一步继续反馈/补偿布局、有效电容/载流和HDI条件，首板制造后再做必要实测。

收尾final-audit.json核对了54个MPN及原理图/PCB五字段一致、BOM位号/数量、当前源及制造输出（含孔工艺CSV）哈希、新导航链接和git diff --check，均通过。标注图已打开复核，所有变更未提交。
