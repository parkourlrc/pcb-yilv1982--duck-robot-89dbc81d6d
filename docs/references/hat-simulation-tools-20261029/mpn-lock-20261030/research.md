# HAT BOM MPN 锁定记录（2026-10-31 更新）

## 结论

- 当前58/58拟装器件有设计MPN，38/38有效分组完整，去重35个MPN。C303～C306及C323用C1210C226K3RACTU；C308/C309/C328用C0805C225K5RACTU，R703=WSLP0603R0470FEA；C329/C330用C0402C104K3RACTU，C307仍DNP。C309图形变体使分组增加1；最新[通孔/规则复审](../npth-clearance-20261031/research.md)未改料号，BOM完整不等于电气/热/制造/采购放行。
- 这不是可以从 KiCad footprint 名称安全推导的字段：同一封装/阻容值存在多个厂商、额定电压、介质、容差、温度等级和供货状态。
- 在用户授权的自主设计范围内，可以按厂商订购表/封装/额定值完成设计选型并写回原理图；这不代表已购实装或库存已确认。不得用虚构料号填空。

## 当前电容/TVS摘要

完整现行清单见[拟装BOM](../../../../hardware/custom_hat/rev_a/production-20261031-power-final-review/bom-fitted.csv)；[追踪BOM](../../../../hardware/custom_hat/rev_a/production-20261031-power-final-review/bom-tracking.csv)另保留C307 DNP。本轮电源标识/模型核对未改任何料号，52贴装/6通孔及分类见同包assembly-plan.csv；库存和装配服务未确认。下方历史基表不用于采购。

最新补齐：J401/J402=B3B-EH-A(LF)(SN)，J502=BM04B-SRSS-TB(LF)(SN)，J504=BM03B-SRSS-TB(LF)(SN)，J505/J506=BM02B-SRSS-TB(LF)(SN)，L301=IHLP4040DZER5R6M5A（5.6µH），R309=WSL120600000ZEA9。J101=SSW-120-01-G-D，J301/J403/J802分别TSW-108/103/102-07-G-S。

| 位号 | 当前MPN | 规格 |
|---|---|---|
| C301 | 08055A332JAT2A | 3.3nF 50V C0G 5% |
| C302 | C0805C104K5RACTU | 100nF 50V X7R 10% |
| C303/C304/C305/C306/C323 | C1210C226K3RACTU | 22µF 25V X7R 10%，1210 |
| C307 | C1206C226M4PACTU | 22µF 16V X5R 20%；DNP |
| C308/C309/C328 | C0805C225K5RACTU | 2.2µF 50V X7R 10%，0805 |
| C310/C312/C319/C320/C327/C329/C330 | C0402C104K3RACTU | 100nF 25V X7R 10% |
| C311/C313/C315/C321/C322/C325/C326 | C0402C105K4PACTU | 1µF 16V X5R 10% |
| C317/C318 | C0402C106M9PACTU | 10µF 6.3V X5R 20% |
| D301 | SMBJ12A-E3/52 | Vishay，单向12V，SMB |

### 历史基表（不用于当前采购）

| 类型 | 值 | 封装 | 数量 | 位号 | MPN |
|---|---|---|---:|---|---|
| capacitor | 3.3nF | `Capacitor_SMD:C_0805_2012Metric` | 1 | C301 | 待确认 |
| capacitor | 100nF | `Capacitor_SMD:C_0805_2012Metric` | 1 | C302 | 待确认 |
| capacitor | 10uF | `Capacitor_SMD:C_1206_3216Metric` | 2 | C303, C304 | 待确认 |
| capacitor | 22uF | `Capacitor_SMD:C_1206_3216Metric` | 2 | C305, C306 | 待确认 |
| capacitor | 22uF reserve | `Capacitor_SMD:C_1206_3216Metric` | 1 | C307 | 待确认 |
| capacitor | 1uF | `Capacitor_SMD:C_0805_2012Metric` | 2 | C308, C309 | 待确认 |
| capacitor | 1uF | `Capacitor_SMD:C_0402_1005Metric` | 7 | C311, C313, C315, C325, C326, C321, C322 | 待确认 |
| capacitor | 10uF | `Capacitor_SMD:C_0402_1005Metric` | 2 | C317, C318 | 待确认 |
| capacitor | 100nF | `Capacitor_SMD:C_0402_1005Metric` | 5 | C319, C320, C310, C312, C327 | 待确认 |
| capacitor | 10uF | `Capacitor_SMD:C_0805_2012Metric` | 1 | C323 | 待确认 |
| diode | SMBJ12A (fitted) | `Diode_SMD:D_SMB` | 1 | D301 | 待确认 |
| connector | RADXA_ZERO_3W_40P | `Connector_PinSocket_2.54mm:PinSocket_2x20_P2.54mm_Vertical` | 1 | J101 | 待确认 |
| connector | POWER_AND_RAILS | `Connector_PinHeader_2.54mm:PinHeader_1x08_P2.54mm_Vertical` | 1 | J301 | 待确认 |
| connector | DYNAMIXEL_TTL_1 | `Connector_JST:JST_EH_B3B-EH-A_1x03_P2.50mm_Vertical` | 1 | J401 | 待确认 |
| connector | DYNAMIXEL_TTL_2 | `Connector_JST:JST_EH_B3B-EH-A_1x03_P2.50mm_Vertical` | 1 | J402 | 待确认 |
| connector | HOST_UART2 | `Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical` | 1 | J403 | 待确认 |
| connector | TOF_I2C5 | `Connector_JST:JST_SH_BM04B-SRSS-TB_1x04-1MP_P1.00mm_Vertical` | 1 | J502 | 待确认 |
| connector | AUDIO_OUT_SH | `Connector_JST:JST_SH_BM03B-SRSS-TB_1x03-1MP_P1.00mm_Vertical` | 1 | J504 | 待确认 |
| connector | MIC_IN | `Connector_JST:JST_SH_BM02B-SRSS-TB_1x02-1MP_P1.00mm_Vertical` | 1 | J505 | 待确认 |
| connector | SPEAKER | `Connector_JST:JST_SH_BM02B-SRSS-TB_1x02-1MP_P1.00mm_Vertical` | 1 | J506 | 待确认 |
| connector | IMU_INT_TP | `Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical` | 1 | J802 | 待确认 |
| inductor | 5.5uH | `Inductor_SMD:L_12x12mm_H8mm` | 1 | L301 | 待确认 |
| resistor | 52.3k | `Resistor_SMD:R_0805_2012Metric` | 1 | R301 | CRCW080552K3FKEA |
| resistor | 10k | `Resistor_SMD:R_0805_2012Metric` | 1 | R302 | CRCW080510K0FKEA |
| resistor | 200k | `Resistor_SMD:R_0805_2012Metric` | 1 | R303 | CRCW0805200KFKEA |
| resistor | 14k | `Resistor_SMD:R_0805_2012Metric` | 1 | R304 | CRCW080514K0FKEA |
| resistor | 100k | `Resistor_SMD:R_0805_2012Metric` | 1 | R305 | CRCW0805100KFKEA |
| resistor | 10k | `Resistor_SMD:R_0402_1005Metric` | 1 | R308 | CRCW040210K0FKED |
| resistor | 0R | `Resistor_SMD:R_1206_3216Metric` | 1 | R309 | 待确认 |
| resistor | 100k | `Resistor_SMD:R_0402_1005Metric` | 2 | R310, R311 | CRCW0402100KFKED |
| resistor | 2.2k | `Resistor_SMD:R_0402_1005Metric` | 1 | R312 | CRCW04022K20FKED |
| resistor | 4.7k | `Resistor_SMD:R_0402_1005Metric` | 2 | R501, R502 | CRCW04024K70FKED |
| test_point | TP801/802/803 | 裸铜焊盘 | 3 | TP801/802/803 | 非采购件 |
| ic | AP64350 | `duck:SO-8EP_AP64350` | 1 | U301 | AP64350SP-13 |
| ic | BMI088 | Bosch LGA-16 | 1 | U501 | BMI088 |
| ic | TLV320AIC3104 | VQFN-32 RHB | 1 | U701 | TLV320AIC3104IRHBR |
| ic | LP38691DT-1.8 | TO-252-3，TAB=2 | 1 | U702 | LP38691DT-1.8/NOPB |
| ic | SN74LVC1G126 | SOT-23-5 | 1 | U801 | SN74LVC1G126DBVR |
| ic | SN74LVC1G125 | SOT-23-5 | 1 | U802 | SN74LVC1G125DBVT |
| ic | PAM8302A | SO-8 | 1 | U803 | PAM8302AADCR |

## 锁定所需输入

1. 连接器：确认实际厂商/系列、直立或卧式、镀层和可替代范围。
2. 被动件：确认耐压、介质/容差、额定电流、精度和 DNP 规则。
3. 电感与 TVS：确认饱和电流、温升电流、VRWM/封装和目标供应商。
4. IC：确认目标采购渠道与完整后缀；封装后缀必须和 PCB footprint 对齐。
5. 测试点和 fiducial：通常可作为装配辅料处理，但仍需按生产商规则确认。

## 状态

MPN字段缺口已关闭；仍需核准已选器件的载流/有效电容/热/制造适用性及库存。来源按各专题，历史新增8件见final-bom报告。供应搜索错误匹配仍拒绝；现35个拟装MPN生命周期unknown没有升级为在产或可采购，LCSC-only工具不提供生命周期状态。
