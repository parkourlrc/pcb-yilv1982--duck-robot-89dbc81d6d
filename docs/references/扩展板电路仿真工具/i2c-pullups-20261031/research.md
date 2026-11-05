# HAT I2C5 上拉及电阻选型检查点

> 历史检查点：随后C305/C309盘中孔已修，主PCB哈希和生产包已更新。现行见[电容盘中孔检查点](../cap-vias-20261031/research.md)；本报告保留上拉/电阻选型依据，BOM覆盖18/54仍有效。

## Overview

日期：2026-10-31。继续用户“解决所有已知问题”的授权，主会话执行，未用子代理。**[本机文件/工具核对] R501/R502已加入主工程，分别将I2C5_SCL/I2C5_SDA经4.7kΩ接到+3V3。** 另有9个既有电阻补齐MPN，原阻值、封装、网络未改。

主PCB SHA256：a96508311bfc66dbab1b94b54d0391a7552f8f979acbbe26603ca281171336dc。68封装、783线段、96过孔、4铜区。DRC普通违规、未连接、parity、ERC、netlist mismatch均0，规则未放宽。总体设计仍未完成，不可投板。

## Previous Review Delta

| 项目 | 上一检查点 | 本检查点 |
|---|---|---|
| I2C5本板上拉 | 缺失 | R501/R502已实现，4个新焊盘接到全部对应旧焊盘 |
| MPN器件覆盖 | 7/52 | 18/54，仍36件缺MPN |
| 有效采购分组 | 7/37 | 16/38，重复值不同封装不合并 |
| 铜连接 | 文件规则全0 | 仍全0，原有焊盘几何/走线/过孔未变、原连接无丢失 |
| 生产审查包 | production-20261031-review | production-20261031-i2c-review；旧包仅历史 |

结构化差异见schematic-delta.json。U701.7断线、fiducial缺失及“全部MPN未锁定”均已过期。

## Critical Findings

1. 剩余36件缺MPN：电容、连接器、TVS、电感和R309动力跳线；继续核额定值、偏压、温升、引脚和外形。
2. U301/U701/U702热焊盘内同网地孔仍0，真实功耗和散热布局未完成。
3. U701.7微孔、C305/C309盘中孔、23个0.1mm环宽及HDI层叠/填孔仍需处理。
4. 实物音频、I2S、TTL、IMU/ToF、供电、温升和装配未验证；制造条件完成后进入首板验收。

## Component Summary

58个有封装的原理图器件，去除3个裸铜测试点和1个DNP后为54个拟装器件；另有4安装孔和6fiducial，PCB合计68封装。BOM见[新审查包](../../../../hardware/custom_hat/rev_a/production-20261031-i2c-review/README.md)。

| 位号 | 值/封装 | MPN |
|---|---|---|
| R501/R502 | 4.7k/0402 | CRCW04024K70FKED |
| R301 | 52.3k/0805 | CRCW080552K3FKEA |
| R302 | 10k/0805 | CRCW080510K0FKEA |
| R303 | 200k/0805 | CRCW0805200KFKEA |
| R304 | 14k/0805 | CRCW080514K0FKEA |
| R305 | 100k/0805 | CRCW0805100KFKEA |
| R308 | 10k/0402 | CRCW040210K0FKED |
| R310/R311 | 100k/0402 | CRCW0402100KFKED |
| R312 | 2.2k/0402 | CRCW04022K20FKED |

依据：Vishay D/CRCW e3，document 20035，14-Apr-2026，p1额定、p2阻值系列、p3订货编码/包装、p11外形。均1%、100ppm/K；0402=ED、0805=EA。属于厂商编码表支持的设计选择，不代表库存/已购确认。R309不套用普通信号电阻额定。

## Power Tree

VBATT_2S_IN → U301 → +5V；Radxa供+3V3 → U702 → +1V8_CODEC。新增上拉接+3V3；未更换现有电源、TVS或动力分支。

## Analyzer Verification

- geometry-connectivity-check.json：245个原非fiducial焊盘几何和850个旧走线/过孔对象不变，原连接无丢失。R501.1/R502.1接全部+3V3旧焊盘；R501.2/R502.2分别接全部SCL/SDA旧焊盘；U701.7↔R308.2仍连通。
- 验证读取CLI重新填铜并保存后的完整副本。回写主工程后再跑完整pipeline，post-promotion-summary.json全部0。
- promotion.json记录源/候选指纹和6个回写文件；before-metadata目录为本轮回写前备份；format-normalization.json确认去行尾空格前后S-expression相同。
- 新增信号线均F.Cu，2个新增+3V3孔为0.6/0.3mm通孔，无新增微孔或盘中孔。原生SVG及pullups-detail.png已生成，局部图已打开检查。

## Signal Analysis Review

**[厂商资料]** Radxa V1.11 p11/p20：40P 29/31属I2C5，R52/R53属I2C3。Bosch BMI088 Rev1.9 §6.2（PDF p48）要求SCL/SDA外部上拉到VDDIO，支持标准/快速模式；未把SPI的2mA参数冒充I2C规格。codec逻辑限制沿用上一阶段厂商资料。

**[计算，非实测]** TI SLVA689A p3：tr=0.8473×R×Cb。4.7kΩ、1%上偏=4747Ω，标准模式1µs对应Cb上限248.6pF；初始限制取240pF（约965ns）。100kHz是首板配置要求，未声称已部署；实际总电容未知。400kHz/300ns对应约74.6pF，未验收前不默认提速。

3.3V/4.653kΩ≈0.71mA是每线拉低电流估算，功耗约2.34mW。外设若带4.7kΩ，并联约2.35kΩ、电流约1.42mA；增加并联支路前需重核，不能接5V上拉。外围资料、边沿和低电平实测将决定阻值/DNP/提速，目前没有总线实测。

## Power Analysis

9个既有电阻仅补元数据。AP64350 Vref=0.8V，52.3k/10k对应4.984V；1%分压电阻反向容差角约4.901–5.069V，不含IC基准误差。R305在8.4V全压下约0.71mW，3.3V的100k电阻约0.11mW。反馈/补偿/音频阻值未改，不能据这些计算验证带载能力。

## PCB Layout Analysis

R501=(145.5,110.0)、R502=(147.5,110.0)，F.Cu、90°，在J101 courtyard外。新增0.15mm信号线的CC-002是启发式警告，不是KiCad规则失败或I2C载流不足证据。

## Thermal Analysis

已跑analyze_thermal.py，仅评估2件、总耗散0.043W假设；100分不能作为热验收。TV-001的U301=2/U702=12仍含其他网络及放大区域，不接受其同网热孔计数；原始计数仍0，热任务保留。

## EMC / Cross-Domain Analysis

cross 2项warning；EMC 57项（9 error/35 warning/13 info）。VS-002“无地孔”与原文件6个地孔冲突；PS-002局部岛与原生保存后连通图冲突。实际回流/层叠仍未完成，电气连通不能代替EMI或参考平面连续性验收。

## Simulation Verification

ngspice 47已运行，12子电路12pass，均理想/行为模型；自动反馈模型仍带0.6V假设，不能验证AP64350。上拉RC边沿和分压容差用显式公式计算，未宣称板级瞬态、时序或稳定性已通过仿真。

## Component Lifecycle

对16个唯一MPN运行LCSC查询，见lifecycle.json，16个均unknown（接口没有生命周期状态）。unknown不改写成在产/可采购，脚本成功也不等于供货通过。

## PDN Impedance

未取得全部电容料号及偏压容量曲线，自动阻抗模型依然采用默认ESR/ESL。新增上拉没有改变去耦网络；本次不把默认曲线作为PDN验收。

## Power Budget

本轮只增加两路最多约0.71mA的上拉负载（3.3V、1%下偏、输出近0V假设）。主控、功放、外设与舵机的真实峰值/持续电流、R309及接插件额定仍需分别核算，不用芯片宣传最大电流作为整板额定。

## Manufacturing / DFM / Testability

同版Gerber、钻孔、坐标及BOM已导出并跑Gerber analyzer。GR-004把Paste与包含通孔、过孔、fiducial的全部铜闪光数比较，不能据比例判漏锡膏。fiducial保持无Paste；PM-002量的是courtyard至边0.25mm，铜边距1mm、Mask边距0.5mm，拼板/夹持仍待核。

## False Positives / Reviewer Overrides

RS-001：+5V_FB是反馈分压点，SERVO_VBAT经R309接输入，不能据此认定断网。DS-002未找到工程同级datasheets目录；项目按专题归档7个IC和电阻厂商PDF，仅已取得资料的器件有厂商依据，36个缺MPN器件未核准。BMI088用通用连接器符号，analyzer只认出U701为I2C设备，“1 device”不是总线真实器件数。

## Failures / Workflow Corrections

第一版位置侵入J101 courtyard等，产生9项DRC，未回写；后续避开SCL及+3V3旧过孔，逐项消除3项剩余违规。失败报告和布局快照保存在同一run。首次封装库路径定位失败也未改主板。

规划器修复两项真实缺陷：起点层不再硬编码B.Cu；间距也考虑目标网是Power，避免按信号间距布电源。规划仍只是候选生成，最终以完整DRC和连通验证判定。

## Sources / Images

- Vishay：https://www.vishay.com/docs/20035/dcrcwe3.pdf，本地sources/vishay-dcrcwe3.pdf；订货p3渲染已打开核对，p1图保留。
- TI：https://www.ti.com/lit/an/slva689/slva689.pdf，本地sources/ti-slva689.pdf；p3渲染已打开核对。
- Radxa/Bosch/codec沿用前一metadata-repair专题sources目录。新PDF哈希在sources/manifest.json。
- 图由hardware/custom_hat/scripts/render_i2c_review.py生成，F/B使用同一顶视坐标，底面未镜像，不用屏幕左右猜实际针序。

## Not Performed / Review Limits

没有实物测试、EMC认证、机械堆叠验证、全板寄生/热仿真、HDI厂商批准、库存锁定或所有器件逐针/偏压/温升核查。未下单、付款、上电、commit或push。

## Final Verdict

关闭“无本板I2C5上拉”，MPN缺口从45件减至36件，文件规则及原连接保留通过。**总体目标仍进行中，不可投板。** 继续剩余物料、热路径和制造条件；首板产生后再做实物验收。
