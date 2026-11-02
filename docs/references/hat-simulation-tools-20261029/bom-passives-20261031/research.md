# HAT 电容与TVS料号选择、剩余物料复核（2026-10-31）

> 历史检查点：随后4个排针/排母MPN与J101实体修复、通孔环宽修复已完成。现行MPN46/54、剩8件，见[现行审查](../annular-rings-20261031/research.md)。本页电容/TVS选型及偏压/ESR限制继续有效。

## Overview

用户持续授权解决全部已知问题。本轮由主会话执行，未使用子代理；选择23个拟装电容及D301的设计MPN，C307保留DNP但补同系列料号。原容量/封装/引脚/铜几何未改。**料号录入不等于偏压容量、ESR、瞬态与整板制造已放行。**

主PCB SHA256：a101bc83040836d1f130179b636896ece6fca460334afa4b39c861c329c97c93。68封装、929线段、96过孔、4铜区；普通DRC/未连接/parity/ERC/netlist mismatch全0。54个拟装器件中42个已录入设计MPN，余12件；有效分组26/38。

## Previous Review Delta

- MPN覆盖18/54→42/54，待选36件→12件；物料类别为7个IC、11个电阻、23个电容、1个TVS。
- 电路数值与铜未变；I2C5上拉、U701.7连通、fiducial和C305/C309盘中孔修复均保留。
- kicad-happy的SS-001缺料号error变为SS-002 warning，仍未达到完整BOM。
- 新输出为production-20261031-passives-review；前一cap-vias输出退为历史。

## Critical Findings

1. 尚未选定J101/J301/J401/J402/J403/J502/J504/J505/J506/J802、L301、R309的MPN，共12件。
2. 电源MLCC有效容量/偏压/温度/老化与LP38691输出ESR仍需数据或模型核算，不能用标称容量代替。
3. 热/回流、U701.7微孔与HDI条件、0.1mm环宽、连接器及动力路径额定仍未完成。
4. 实物功能、温升和装配未测试；不可投板，不以已有文件检查通过替代首板验收。

## Component Summary

| 位号 | 设计MPN | 规格/厂商表格依据 |
|---|---|---|
| C301 | 08055A332JAT2A | KYOCERA AVX，3.3nF/50V/C0G/5%/0805；Rev4 PDF p1编码、p3范围 |
| C302 | C0805C104K5RACTU | KEMET，100nF/50V/X7R/10%/0805 |
| C303/C304 | C1206C106K3RACTU | KEMET，10µF/25V/X7R/10%/1206 |
| C305/C306；C307 DNP | C1206C226M4PACTU | KEMET，22µF/16V/X5R/20%/1206；该组合只提供M容差 |
| C308/C309 | C0805C105K5RACTU | KEMET，1µF/50V/X7R/10%/0805；LDO有效C/ESR未放行 |
| C310/C312/C319/C320/C327 | C0402C104K3RACTU | KEMET，100nF/25V/X7R/10%/0402 |
| C311/C313/C315/C321/C322/C325/C326 | C0402C105K4PACTU | KEMET，1µF/16V/X5R/10%/0402 |
| C317/C318 | C0402C106M9PACTU | KEMET，10µF/6.3V/X5R/20%/0402；该组合只提供M容差 |
| C323 | C0805C106K3PACTU | KEMET，10µF/25V/X5R/10%/0805 |
| D301 | SMBJ12A-E3/52 | Vishay，12V单向、SMB，商业级无铅7英寸卷盘 |

KEMET X7R资料C1002，2026-09-01，p2编码/p5可供组合；X5R资料C1006，2026-09-07，p1编码/p2尺寸/p5与p6组合。按表格选实际存在的组合：未采用不在X7R表中的0402 1µF或1206 22µF/25V。表中额定不代表当前库存或具体批次。

## Power Tree

2S→U301→5V；Radxa 3.3V→U702→1.8V；R309接SERVO_VBAT。C303/304在电池输入、C305/306在5V输出、C308/309在LDO输入/输出、C323在5V功放供电。电源来源和网络未变。

## Analyzer Verification

geometry-connectivity-check.json：249个非fiducial焊盘几何、原走线/过孔和原赋网不变，连接无丢失；U701.7与R308.2仍同组。候选完整检查通过后回写；post-promotion-summary.json为现行主工程重新复制后的完整检查，全部0。

第一次回写SHA为156b6ac0…；随后把D301属性的订货页码p4纠正为p3（两处CAD字段和选择记录同步），只改引用文字，重新检查并导出得到当前SHA。旧输出保存在outputs-before-page-fix；原始回写与最终现行状态分别见promotion.json和checkpoint.json，不混用哈希。

## Pinout / Footprint Verification

D301原pad1=VBATT、pad2=GND；Vishay PDF p1说明色带为单向管阴极，p2为SMBJ12A电气表，p3订货表，p5封装/推荐焊盘。KiCad焊盘2.5×2.3mm、中心距4.3mm，内间隙1.8mm；厂商图推荐内间隙≤2.159mm、焊盘宽≥1.52mm及高≥2.18mm，文件侧满足这些几何条件。没有实装极性核验。

电容均非极性，两端焊盘网络不变。按厂商尺寸表核公制1005/2012/3216对应0402/0805/1206；高容量0402的额外外形公差仍须进入最终装配高度/外形核查，不能只凭库名作整机适配承诺。

## Signal Analysis Review

C317/C318实际是HP_L/HP_R到AUDIO_L/R的AC耦合，**不是供电去耦**。10µF若接32Ω负载，理想高通约497Hz；若接10kΩ线输入约1.59Hz。以上是C标称、忽略源阻抗的计算，实际偏压会改变容量；不能把本接口写成已核准的宽带低阻耳机输出。用户音频播放主通路仍是PAM8302A→J506，实际功能未测试。

1µF/0402组包括电源旁路、功放输入和麦克风耦合，不能仅因容量相同就混写用途。I2C5两颗4.7kΩ上拉与初始100kHz/240pF条件不变。

## Power Analysis

AP64350 PDF说明输入采用大于10µF陶瓷；输出22–68µF为通常范围，需按实际负载瞬态计算。其设计示例2×22µF约30µF有效容量是**示例条件**，不是本板已取得的数据，也不是通用最低值。本板2×10µF输入、2×22µF输出的有效C尚未取得对应料号曲线。

LP38691 PDF p15–16强调有效容量和5–500mΩ输出ESR；约0.7µF下限示例不能只用“标称1µF”满足。当前选50V X7R 0805，额定余量较大，但尚未取得对应DC bias/ESR数据，故在BOM Comments明确保留验证项，没有宣布LDO稳定性通过。

## PDN Impedance

尚无选定MLCC的完整电压/频率/温度模型。自动ESR/ESL默认模型不升级为PDN验收；后续按料号补曲线并检查电源环路/去耦位置。

## Power Budget

D301规格：12V stand-off、13.3–14.7V击穿@1mA、19.9V钳位@30.2A/10–1000µs、600W峰值（厂商规定条件）。它不是持续过压或过流保护；没有实测电池线缆浪涌/器件温度协调。

R309候选WSLP1206已取得厂商资料，但低阻端子的推荐焊盘与当前通用1206需详细核对；未把1mΩ料号冒充0Ω写入。连接器、电感的实际额定及整板电流预算仍需完成。

## PCB Layout Analysis

本次仅元数据字段更新，容量、封装、位置、铜几何及填充连通不变。前一检查点的原生正反面图可代表本次铜几何；不会为“新版本”伪造不同布局图。

## Thermal Analysis

热analyzer已运行，仍为2件、0.043W假设，不接受100分为热验收。X5R系列工作温度上限85°C，需结合实际热点温度；codec可选热孔与TO-252/WSON边界沿用前一勘误，未套统一孔数。

## EMC / Cross-Domain Analysis

cross和EMC已重跑；由于铜/电路未改，原有回流/HDI限制保留。原“无地孔”和U701.7孤岛误判已用原文件/原生连接证据处理，但未做EMC实测。

## Simulation Verification

ngspice已运行12个自动子电路；模型仍是理想/行为级。自动AP64350反馈参数0.6V不符合真实0.8V，不能为电源背书；本次料号选择也没有自动带入真实MLCC偏压模型。

## Component Lifecycle / Sourcing

26个唯一MPN查询均unknown；LCSC接口无生命周期字段。额外用kicad-happy的lcsc脚本查B3B-EH-A(LF)(SN)和BM04B-SRSS-TB，分别返回IB0303LS-1WR3电源模块、TA1839C滤波器，**型号不符，全部拒绝**，未下载其PDF、未写BOM。744325550查询无结果。

原始输出保存在jst-eh-search.json、jst-sh-search.json、inductor-search.json。不能把搜索脚本exit0当作型号匹配/采购通过；以后必须先比较MPN/厂商/封装，再审厂商PDF。这也限制自动生命周期信息的可信度。

进一步去掉details富化后重查BM04B-SRSS-TB，原始搜索仍返回TA1839C，说明本次错配在搜索结果阶段就已存在，不归因于后续富化覆盖。B3B-EH-A简化查询超时，无有效新结果；分别见jst-sh-raw-search.json和jst-eh-raw-search.json（后者无有效JSON）。没有更改第三方工具，也没有用错误搜索结果选连接器。

## Manufacturing / DFM

新同版[生产审查包](../../../../hardware/custom_hat/rev_a/production-20261031-passives-review/README.md)包含Gerber/钻孔/坐标/BOM和指纹。未放行HDI、微孔填孔、0.1mm环宽、拼板/夹持或最终装配。选择的MPN不是下单授权。

## Sources / Failure Record

sources-manifest.json保存全部尝试URL、HTTP结果和成功PDF哈希。原厂成功资料包括KEMET X7R/X5R、KYOCERA AVX C0G/X7R、Vishay SMBJ/WSLP。重要选型页PNG已打开核对，脚本collect_bom_sources.py可复现。

JST/TDK/ST/Coilcraft/Würth/Samtec的部分尝试返回403/567或连接失败；若干猜测的资料路径404，后来找到KEMET正确C1006文件。**未取得页面内容不等于器件没有资料或已停产。** 失败缓存已加入，避免每次重复请求；后续只对新的可靠来源继续查找。网页搜索工具没有给出可引用结果，未伪称通过搜索核验。

## False Positives / Reviewer Overrides

SS-002是实际料号缺口；DS-002未发现工程同级datasheets目录，但原厂资料按专题归档。RS-001中的+5V_FB为反馈节点、SERVO_VBAT经R309接入，不能据此判断网。FID边距、热孔误计、Paste闪光比例等既有误报处理见前一检查点；没有关闭原生检查。

## Analyzers Actually Run

aklofas/kicad-happy提交2fd9aa0fe2d620f36627d9221e8b1393987ae38e；实际运行schematic、pcb --full、gerbers、cross、EMC、thermal、SPICE、lifecycle和prior schematic delta。命令/日志/JSON同目录。另使用其lcsc skill查资料，型号不符的结果未采用。

## Not Performed / Review Limits

未完成12件MPN、全部电容曲线/ESR/偏压分析、负载/热/回流/层叠验证、实物功能/温升/装配或库存锁定；没有新增制造批准、订单、付款、上电、commit或push。

## Final Verdict

本轮把缺MPN从36件降至12件，并把电容额定/介质/容差、TVS型号和证据写入原理图及PCB；没有改变电路或铜。继续处理连接器/电感/动力跳线和实际电源/热条件。总体目标仍未完成，不可投板。

final-audit.json核对：现行源指纹、生产输出指纹、25个所选器件（含DNP）的原理图/PCB属性均匹配；现行新增链接无断链，git diff --check返回0。主机本地日期实查2026-10-31（+08:00）；工具run采用UTC，故部分路径为20261030，不混同历史检查点。修改未提交。
