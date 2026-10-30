# HAT BOM MPN 锁定记录（2026-10-30）

## 结论

- 当前原理图分析器列出 41 个 BOM 分组、56 个器件；所有 BOM 分组的 `mpn` 字段为空。
- 这不是可以从 KiCad footprint 名称安全推导的字段：同一封装/阻容值存在多个厂商、额定电压、介质、容差、温度等级和供货状态。
- 未经用户或采购来源确认，不向原理图写入制造商型号，不把候选型号当作已锁定 BOM。

## 当前分组

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
| resistor | 52.3k | `Resistor_SMD:R_0805_2012Metric` | 1 | R301 | 待确认 |
| resistor | 10k | `Resistor_SMD:R_0805_2012Metric` | 1 | R302 | 待确认 |
| resistor | 200k | `Resistor_SMD:R_0805_2012Metric` | 1 | R303 | 待确认 |
| resistor | 14k | `Resistor_SMD:R_0805_2012Metric` | 1 | R304 | 待确认 |
| resistor | 100k | `Resistor_SMD:R_0805_2012Metric` | 1 | R305 | 待确认 |
| resistor | 10k | `Resistor_SMD:R_0402_1005Metric` | 1 | R308 | 待确认 |
| resistor | 0R | `Resistor_SMD:R_1206_3216Metric` | 1 | R309 | 待确认 |
| resistor | 100k | `Resistor_SMD:R_0402_1005Metric` | 2 | R310, R311 | 待确认 |
| resistor | 2.2k | `Resistor_SMD:R_0402_1005Metric` | 1 | R312 | 待确认 |
| test_point | VBATT_2S_IN | `TestPoint:TestPoint_Pad_D1.5mm` | 1 | TP801 | 待确认 |
| test_point | +5V | `TestPoint:TestPoint_Pad_D1.5mm` | 1 | TP802 | 待确认 |
| test_point | +3V3 | `TestPoint:TestPoint_Pad_D1.5mm` | 1 | TP803 | 待确认 |
| ic | AP64350 | `duck:SO-8EP_AP64350` | 1 | U301 | 待确认 |
| connector | BMI088 | `Package_LGA:Bosch_LGA-16_4.5x3mm_P0.5mm_LayoutBorder7x1y_ClockwisePinNumbering` | 1 | U501 | 待确认 |
| ic | TLV320AIC3104 | `Package_DFN_QFN:VQFN-32-1EP_5x5mm_P0.5mm_EP3.1x3.1mm` | 1 | U701 | 待确认 |
| ic | LP38693DT-1.8 codec 1V8 | `Package_TO_SOT_SMD:TO-252-3_TabPin2` | 1 | U702 | 待确认 |
| ic | SN74LVC1G126 | `Package_TO_SOT_SMD:SOT-23-5` | 1 | U801 | 待确认 |
| ic | SN74LVC1G125 | `Package_TO_SOT_SMD:SOT-23-5` | 1 | U802 | 待确认 |
| ic | PAM8302A | `Package_SO:SOIC-8_3.9x4.9mm_P1.27mm` | 1 | U803 | 待确认 |

## 锁定所需输入

1. 连接器：确认实际厂商/系列、直立或卧式、镀层和可替代范围。
2. 被动件：确认耐压、介质/容差、额定电流、精度和 DNP 规则。
3. 电感与 TVS：确认饱和电流、温升电流、VRWM/封装和目标供应商。
4. IC：确认目标采购渠道与完整后缀；封装后缀必须和 PCB footprint 对齐。
5. 测试点和 fiducial：通常可作为装配辅料处理，但仍需按生产商规则确认。

## 状态

MPN 缺失仍是投板阻塞项；本轮没有凭空补填。
