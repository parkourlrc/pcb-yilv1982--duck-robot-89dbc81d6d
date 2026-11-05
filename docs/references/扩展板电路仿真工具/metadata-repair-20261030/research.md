# HAT 元数据、BOM 与审查修复（2026-10-30—31）

> 本文为历史检查点；I2C5上拉随后已修，MPN覆盖已由7/52升至18/54。现行见[I2C5修复及电阻选型报告](../i2c-pullups-20261031/research.md)。下列“当前”均限定于本文当时源哈希，不作为最新状态。

## Overview

范围：现行 Rev A 的符号/封装关联、NC、DNP、fiducial、关键 IC MPN，以及前轮审查真实性。主会话执行，未使用 subagent，未提交、下单或操作实物。

**[本机工具检查，非硬件实测] 当前主工程 DRC 普通违规、未连接、schematic parity、ERC、netlist mismatch 均为 0。** 这表示规则和网表一致性通过，不代表整个电路、热设计或功能通过。

源 PCB SHA256：`d4fc46fa5fe08beb8e48d91caef4b23493d8d54641a8e31108c0f968642f61e2`。66 个 footprint、756 走线段、94 个过孔、4 铜区；73 个网络包括 41 个功能网络与 32 个显式 NC 网络。

## Previous Review Delta

| 项目 | 修改前 | 当前 |
|---|---|---|
| 一致性提示 | 107 项 | 0 项，未关闭任何检查规则 |
| 关键 IC MPN | 0 | 7 个 IC 已写入原理图和 PCB 属性 |
| U702 | 不存在于该三脚 TO-252 选型中的 LP38693DT 标识 | `duck:LP38691DT-1.8` / `LP38691DT-1.8/NOPB` |
| fiducial | 1mm 铜 + Paste 开窗，无有效净空描述 | 1mm 铜、2mm Mask 开窗、无 Paste、2.5mm courtyard，位置重排 |
| C307 | 原理图 DNP，PCB 未同步 | PCB DNP 同步；坐标清单排除 |
| 旧“无 ngspice”结论 | 未搜索到 PATH 就写未安装 | 已定位便携 ngspice 47 并补跑子电路仿真 |
| 旧“连通分区通过”依据 | 未保存新铺铜，U701.7 仍读为独立组 | 两份完整副本均重铺铜并保存，目标组连通且无连接丢失 |

## Critical Findings

1. **未完成：45 个贴装器件尚缺 MPN。** 已选 IC 的批次、库存和供货情况也未放行。
2. **设计缺项：I2C5 没有本板上拉。** Radxa ZERO 3W V1.11 官方图纸 p11/p20 显示 GPIO3_B3/B4（40P 29/31）直接连接主控；R52/R53 的 2.2kΩ 属于 I2C3，不能当作 I2C5 上拉。未取得 ToF 模块型号/电路；板载 codec/IMU 不能以必插外设作为上拉前提。
3. **热路径未完成：U301.9、U701.33、U702.2 大焊盘内，同网地过孔实数均为 0。** 这是严格焊盘框内计数，不等于没有外部铜面散热。U301 带载散热及各芯片推荐布局还需核算/修订。
4. **制造未完成：** U701.7 的 `0.35/0.15mm` B.Cu–In2.Cu microvia 已连通，但 HDI 层叠、介质厚度、填孔及板厂接单条件尚未锁定。C305/C309 via-in-pad 也需处理。

## Component Summary

本机导出：56 个物理原理图器件，其中 3 个铜测试点不采购，C307 DNP；52 个计划贴装器件中 7 个已选 MPN，45 个待选。采购分组为 37 个有效 BOM 行，已填 7 行（18.9%）；跟踪 CSV 另保留 1 个 DNP 行。安装孔和 fiducial 为 board-only，不伪造采购料号。

| 位号 | 设计选择 MPN | 厂商与依据 |
|---|---|---|
| U301 | AP64350SP-13 | Diodes，AP64350 PDF p23 ordering，p3 pin table |
| U501 | BMI088 | Bosch，归档 Rev 1.9，LGA-16；既有 p52/53/55 封装证据沿用 |
| U701 | TLV320AIC3104IRHBR | TI，PDF p95 ordering，RHB32 |
| U702 | LP38691DT-1.8/NOPB | TI，SNVS321O p1/3/4/22；三脚 NDP TO-252，无 EN |
| U801 | SN74LVC1G126DBVR | TI，PDF p20 ordering；DBV SOT-23-5 |
| U802 | SN74LVC1G125DBVT | TI，PDF p19 ordering；DBV SOT-23-5 |
| U803 | PAM8302AADCR | Diodes，PDF p9 ordering，SO-8 |

来源 URL、文件 SHA256、缓存/本轮下载区别见 [sources-manifest.json](sources-manifest.json)。这些是设计选择，不冒充已购实装型号。LP38691 与原有三脚网络 `1=OUT / 2=GND及TAB / 3=IN` 对应；原图缓存库标识已修正并保存为项目符号。

## Power Tree

`VBATT_2S_IN → U301 → +5V`；Radxa 提供 `+3V3 → U702 LP38691 → +1V8_CODEC`。实际带载能力尚未验证。AP64350 的厂商 Vref 为 0.8V；R301/R302=52.3k/10k 对应名义 `0.8×(1+52.3/10)=4.984V`，不是 analyzer 采用 0.6V 算出的 3.738V。

## Analyzer Verification

- 完整副本报告：[accepted-reports/summary.json](accepted-reports/summary.json)；清理新增行尾空格后，主工程复制再检查见[post-promotion-summary.json](post-promotion-summary.json)，DRC/未连接/parity/ERC/netlist mismatch仍全0。
- [geometry-connectivity-check.json](geometry-connectivity-check.json)：245 个非 fiducial 焊盘几何不变；所有走线/过孔几何、已赋功能网不变；193 个原有有网焊盘连接无丢失；重铺铜后的 U701.7 与 R308.2 同组。
- 60 个 footprint namespace 关联修正；32 个 NC 显式赋独立网；4 个 PWR_FLAG 设为非板上器件；安装孔/fiducial 标 board-only；C307 DNP 和 Datasheet 等字段同步。没有全局豁免 parity。
- 4 个带 `/` 的 NC 网在 KiCad 中存为 `{slash}`；pipeline 仅对显式 NC 接受该精确编码等价，并在 `nc_escaped` 列出，不忽略其他 mismatch。
- U301 丝印修改和 J101 既有行镜像属有意改版，已保存匹配的项目专用 footprint；未恢复库默认几何。

## PCB Layout Analysis

保留既有 microvia 与 +5V 路径；新铺铜已经保存。原先仅执行 `--refill-zones` 而不保存时，分析/生产文件可能读到旧填充。现行文件与审查包使用保存后的同版文件。

F.Cu 基准坐标 `(101.5,110)/(163.5,116)/(139,128.5)`；B.Cu 基准坐标 `(101.5,110)/(163.5,116)/(101.5,122)`。每个圆铜直径1mm，Mask开口2mm，无锡膏；有实际 courtyard，未省略 courtyard 规避重叠。原始核对见 [raw-board-audit.json](raw-board-audit.json)。夹持/拼板边距仍待制造确认。

## Signal Analysis Review

已查明 I2C5 上拉归属缺口；后续补本板可配置上拉，并按目标速率及外设并联阻值核定。其他 I2S、TTL、音频网络仅有设计文件连通证据，未升级为功能实测。

## EMC / Cross-Domain Analysis

运行 `cross_analysis.py`（2 warning）与 `analyze_emc.py`（57 findings）；不是 EMC 合规测试。`VS-002` 的“没有地孔”与原始文件6个地孔相矛盾。`PS-002` 把 U701.7 当独立组，与已保存填充后的原生连接图矛盾；该断网判定不采纳，但采样式回流提示仍需按实际层叠检查。

## Thermal Analysis

已运行 `analyze_thermal.py`；其只评估2个器件的0.043W假设模型，不接受100/100作为热验收。`analyze_thermal_pad_vias` 的第一轮计数不筛选 net，且采用1.5倍焊盘框；旧 U301“2个”、U702“12个”不等于同网热过孔。原生 API 按同网/真实焊盘框得到三个区域均0个，后续按真实功耗与厂商布局重新处理。

## PDN Impedance

默认电容 ESR/ESL、偏压容量和负载估计缺乏最终物料依据；自动阻抗曲线仅为假设模型，不作为 PDN 验收。

## Power Budget

不沿用 +5V“20mA”作为 HAT 总预算；该估计未计 Radxa、功放大信号和实际负载。最终预算需与已选器件、主控能力和首板实测对照。

## Power Sequencing

文件中有 U301 EN、codec RC reset；上电时序/掉电反灌尚未测量。LP38691 的三脚版本没有 EN，不采用 LP38693 的 EN 假设。

## Sleep Current Audit

分压回路应按约0.8V反馈节点计算 R302 电流，不能把网名 `+5V_FB` 解析成5V而给出500µA。R301/R302 整体名义分压电流约80µA，其余静态功耗仍待校核。

## Inrush Analysis

输出电容和软启动分析依赖器件/偏压参数；未将自动 inrush 数值写成实测。

## Bus Topology

I2C5：J101 29/31、U501、U701、J502。官方 Radxa V1.11 证据是参考板图纸，不证明用户手中修订版完全一致，但足以否定“无需证据默认依赖主控上拉”的设计前提。

## Test Coverage

保留 TP801/802/803 三个裸铜测点，排除采购 BOM；功能口也可作为调试接入点。未为了提高 coverage 分数新增无关测点。

## Assembly Complexity

双面细间距器件仍需要装配工艺确认。Fiducial 已从锡膏层和普通贴装坐标清单排除，铜/阻焊图保留；DNP C307 已同步排除贴装坐标。

## BOM Optimization

7个IC料号已写回源文件。阻容、TVS、电感及连接器继续依据额定值/尺寸完成选择；“没有 MPN 字段”不再被当成必须等待用户逐项指定的权限阻塞。

## SPICE 与 Lifecycle

实际运行 ngspice 47 与 `simulate_subcircuits.py`：12 pass / 0 fail，原始文件见 [spice.json](spice.json)。这是自动生成的理想/行为子电路仿真，不是实际整板或真实开关模型验证。反馈探针约0.8026V；脚本仍携带错误0.6V Vref元数据，不能用“12 pass”给 AP64350 整体背书。Windows 默认GBK写µ字符曾失败，已使用UTF-8运行并保留成功输出。

7个MPN运行生命周期查询；LCSC返回值全部unknown，见 [lifecycle.json](lifecycle.json)。这是该来源不提供生命周期字段，未确认在产、库存或供货。

## 制造与 Gerber

同版包：[production-20261031-review](../../../../hardware/custom_hat/rev_a/production-20261031-review/README.md)，含各层Gerber、通孔/盲孔钻孔、CPL和BOM跟踪CSV；带源/输出哈希manifest。Gerber analyzer剩2条paste flash比例提示；fiducial Paste已确实移除，数量比例本身不证明钢网错误。

JLCPCB官方HDI FAQ本轮实际取得正文：盲孔范围0.075–0.15mm，pad直径比孔径至少大0.15mm，支持4–24层。现有0.35/0.15mm尺寸在此范围内；这不等于当前未定义层叠已获板厂接受。网页快照及链接核验均在本目录；保持制造未放行。

## False Positives / Reviewer Overrides

- PM-002称FID2/5距板边0.25mm，量的是courtyard边界；裸铜边距是1mm、Mask开口距边0.5mm。它不是实体器件碰板边，但最终拼板光学/夹持要求仍未核准。
- fab gate的66对55数量差包含4安装孔、6fiducial及1DNP；真实功能器件对应关系由CLI parity=0与网表逐针检查证明。不能把计数差直接当遗漏11个元件。
- 不接受thermal score=100或EMC gate的pass作为热/EMC实物通过。

## Not Performed / Review Limits

45个贴装件未选MPN；未完成全器件数据手册/耐压/载流审查；热布局、I2C5补上拉、HDI层叠与装配仍未完成。没有实物制造、上电、音频、I2S、TTL、IMU/ToF或EMI测试。未经实测的功能不写[实测]。

## Final Verdict / readiness

**规则与网表检查通过；设计目标仍未完成，不能投板。** 下一步是补本板I2C5上拉、完成剩余MPN与功耗/热布局，并确定HDI层叠/盘中孔工艺。原始证据、候选失败及回写前快照均保留；默认不提交、不下单。
