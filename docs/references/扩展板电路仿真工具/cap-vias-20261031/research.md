# 电容盘中孔与热孔要求复核（2026-10-31）

> 历史检查点：随后新增电容/TVS料号，现行MPN为42/54，源哈希和审查包已更新；铜几何不变。[现行物料审查](../bom-passives-20261031/research.md)保留本报告的布局/连通证据。

## 范围与源文件

用户持续授权解决全部已知问题。修改前基线为I2C5修复后PCB，SHA256 a96508311bfc66dbab1b94b54d0391a7552f8f979acbbe26603ca281171336dc。候选经原生填铜、连通验证和图像检查后已回写，现行SHA256为d0e549e27994542f50850702add9ddbb8fb4d80f2a5dee9ebf907d9754c03959；68封装、929线段、96过孔。

**[本机文件/工具检查] C305/C309盘中孔已修。** DRC普通违规、未连接、parity、ERC、netlist mismatch全部0；没有放宽规则。kicad-happy已完成本检查点复审，VP-001从2项降至0。整板仍有物料、热/回流、HDI工艺和实物验证缺口，**不可投板**。

## 原始几何事实

| 对象 | 现有孔坐标/mm | 问题 |
|---|---|---|
| C305.1 / +5V | (148.03,114.21) | F.Cu焊盘内，连接In1.Cu的0.6mm线 |
| C309.2 / POWER_GND | (138.11,118.75) | B.Cu焊盘开窗内；F.Cu有0.25mm短线 |

移动目标：焊盘开窗外放通孔，保持网络和已连功能焊盘，按原线宽重接各层。不能只移动via而留下原线段悬空；不采用新增盘中孔、修改网络/规则或削细动力线的方式规避检查。

## 搜索与失败记录

第一次80个候选未成：C305的In1.Cu起点被保守几何网格判阻挡。原点在现有0.6mm斜线端部，附近MCLK间距接近模型额外余量；这不是物理无空间证据。后续从原短线的另一个端点重接，允许仅修改这两段目标短线及两个via，其他原有铜和焊盘需保留。搜索与CLI结果见search-failure.json、route-plans.json及candidate指向的报告。

## 热孔要求勘误

资料均为前一metadata-repair专题sources中的厂商PDF，未用KiCad库或analyzer经验值代替厂商规定。

- **AP64350 PDF p22 / Figure 32**：建议外层2oz铜，四层及以上把第2/3层用于GND，GND与VIN周围增加孔以散热。当前In2为+3V3，不能直接套用厂商45°C/W测试条件；该条件为四层、2oz、推荐焊盘。功耗、铜面积和实际布局仍需处理。
- **TLV320AIC3104 PDF p101、RHB封装注5**：热孔取决于应用，可选；在锡膏下的孔建议填/塞/盖。p100注3要求热焊盘可靠焊到PCB；p92布局及引脚图说明接driver ground。**不能仅凭0孔或analyzer的“最少5孔”就认定codec不合格。** 实际耗散与接地回路仍要核算。
- **LP38691 PDF p15及p18–19**：先按功耗/封装热阻和外部铜面积评估；WSON DAP热孔建议不能套到本板TO-252-3。**不能把analyzer的“18孔最低要求”作为TO-252验收门。** 当前U702主要负载为codec DVDD，应按真实工作模式电流核算，尚未取得实测。

## 验证和后续

已完成完整DRC/ERC/parity/网表检查、重铺铜保存、原焊盘连通保留验证及原生图/Mask距离检查后回写；生产资料已同版重出。上一步I2C5审查包仅历史。热设计/HDI和全部物料目标仍保留；未下单、实物操作、提交或推送。

## Previous Review Delta

| 对象 | 修改前 | 当前 |
|---|---|---|
| C305.1 +5V via | (148.03,114.21)，焊盘内 | (145.025,117.5)，焊盘外；F.Cu/In1.Cu各0.6mm路径重接 |
| C309.2 GND via | (138.11,118.75)，开窗内 | (138.85,119.375)，开窗外；B.Cu/F.Cu各0.25mm路径重接 |
| analyzer VP-001 | 2 | 0 |
| 普通规则/网表/ERC | 全0 | 保持全0 |
| 原理图/MPN | 18/54已选 | 未改变；36件待选 |

## Analyzer Verification

geometry-connectivity-check.json保存源/候选哈希、原生填铜命令、原焊盘几何及网络一致、原连接无丢失。旧铜只改变2个目标via与2段相连短线，其余原铜保留；新增146段网格绕线。没有把“原连接保留”写成所有走线未变。post-promotion-summary.json为回写主工程后重新复制完整项目的复验。

从via铜外缘到最近焊盘铜包围框的保守距离：C305孔0.325mm（最近L301.2），C309孔0.27866mm（最近C309.2）；原生GetSolderMaskExpansion读得对应开窗扩展0，因此开窗间距同值。未以假设0.05mm替代实际字段。这个结果只证明当前这两孔不落在焊盘开窗内，不是全板制造批准。

## Component Summary

原理图、电阻选型及BOM均未变：54拟装器件、18件已选MPN、36件待选；有效分组16/38。资料/订货表逐项依据继承[I2C5检查点](../i2c-pullups-20261031/research.md#component-summary)，不重新将缺料号元件算作已核准。

## Power Tree

仍是2S入口→AP64350→5V；Radxa 3.3V→LP38691→codec 1.8V。R309接舵机动力分支。改孔保持网络及线宽，额定电流、输入/输出电容有效容量和真实负载预算尚未完整锁定。

## Signal Analysis Review

I2C5两颗4.7kΩ上拉继续有效，100kHz/240pF为初始设计条件。I2S、TTL、IMU/ToF和音频没有新增电路修改，仍未实物验证。

## Power Analysis / PDN

C305新F.Cu路径6.195mm、In1.Cu路径5.478mm；C309两侧路径各1.553mm，见route-plans.json。走线为几何规划结果，含较多短段，不能把移出盘中孔当作电源环路/寄生优化完成。电容实际偏压容量、回路寄生与buck动态响应仍需随电感/电容选型和电源布局一起核查。

## PCB Layout Analysis

原生board-F/board-B SVG与PNG已导出，cap-vias-detail.png已打开核对。底面按顶视坐标输出、未镜像。两via为通孔，未增加HDI孔；U701.7原微孔仍保留，工艺待核。

## Thermal Analysis

已跑热analyzer，但仍仅用2件、总功耗0.043W假设，100分不作验收。AP64350布局/真实耗散需解决；codec与TO-252不使用泛化的5孔/18孔最低门槛。0孔是文件事实，是否不足必须由具体封装/功耗/铜面条件判断。

## EMC / Cross-Domain Analysis

cross仍2 warning；EMC仍57项（9 error/35 warning/13 info）。这是拓扑/启发式结果，不是EMC实测。旧无地孔/孤岛误判按原文件和原生连通证据驳回，实际参考平面与层叠核查保留。

## Simulation Verification

ngspice 47：12子电路12pass，为理想/行为模型。AP64350自动反馈模型0.6V误设仍不能用于验证0.8V实际器件；未验证本轮路径寄生或热模型，不把pass升级为整板通过。

## Component Lifecycle

LCSC重新查询16唯一MPN，全部unknown；接口不返回生命周期。库存/采购状态未放行。

## Manufacturing / DFM

新同版审查包为[production-20261031-cap-vias-review](../../../../hardware/custom_hat/rev_a/production-20261031-cap-vias-review/README.md)。Gerber/钻孔/坐标/BOM全部重出，manifest绑定本次源哈希；普通坐标排除DNP和board-only。U701.7微孔、23个0.1mm环宽、拼板/夹持仍待制造条件锁定。

## False Positives / Reviewer Overrides

PCB剩2个error是FID2/5包围框边距，不等于圆铜离边0.25mm；圆铜边距1mm、Mask边距0.5mm，夹持仍待核。Gerber的2个Paste闪光比例警告包含通孔/过孔/标记铜差异，不能直接判漏锡膏。热孔误计、无地孔、自动孤岛、缺datasheets目录和RS-001误判沿用上轮原始交叉证据；没有豁免本机DRC。

## Analyzers Actually Run

aklofas/kicad-happy本地仓库提交2fd9aa0fe2d620f36627d9221e8b1393987ae38e。实际运行schematic、pcb --full、gerbers、cross、EMC、thermal、SPICE、lifecycle和schematic delta，命令、返回码、日志和JSON均在本目录。PCB findings由58降至56（消除2项VP-001），原理图delta无电路变化。

## Not Performed / Review Limits

未完成全部物料厂家核验、实际层叠/阻抗/回流、含寄生的电源瞬态与热计算、实物功能/温升/装配及板厂批准。自动评分和规则通过不能证明这些条件。仍在解决全目标，没有把本轮局部修复当作最终交付。

## Final Verdict

本轮关闭C305/C309电容盘中孔，并澄清热孔数量不能套统一阈值。现行仍缺36件MPN及热/回流/HDI条件，首板尚未制造。下一阶段继续物料和电源/热布局，完成后再做最终同版kicad-happy审查与首板验收。

收尾核对见final-audit.json：现行源指纹、制造输出指纹与manifest相符，新导航链接有效，git diff --check无空白错误（仅LF/CRLF提示）；原生正反面及局部图已打开检查。修改保留工作区，未提交。
