# 5片自主HAT：缺料替代审查

> **历史选料审查，2026-11-04路线已变更。** 用户选择“全部使用嘉立创现货，准备改版方案”，因此下文外采两个关键IC方案不执行。7组通用候选证据继续参考，现行建议为AP64351＋软启动电容、PAM8302 MSOP封装及其它现货替换，见[Rev A.2方案](../../specs/20261104-hat-jlc-stock-redesign/spec.md)。本页库存均为11-03历史快照，不能作新采购数量依据。

日期：2026-11-03。用户选择“评估现货替代，核准后再用”。对象仅为86654c03单板、订单Y6，不涉及现有kissqy装机板。

## 2026-11-03历史结论

**9组缺料已逐组形成处理意见：7组有无需改铜的优先候选，U301和U803优先外采原型号。** 7组意见仍受下文条件约束，尚未被用户核准采用，也没有写入官网订单或CAD。已找到U301外部供料线索与U803现货，外采邮寄流程和整套报价未落实，不能放行全套订单。库存没有锁定，不能当已备料。

| 位号 | 原MPN | 当前候选／现货观察 | 审查状态 |
|---|---|---|---|
| C301 | 08055A332JAT2A | C0805C332J5GACTU，C2181569，贴片33／商城28 | 原厂规格匹配；3.3nF±5%、50V、C0G、0805，允许列入待采用清单 |
| R304 | CRCW080514K0FKEA | ERJ6ENF1402V，C2077244，贴片9153／商城91 | 原厂14k±1%/125mW/0805/±100ppm匹配；现有IPC焊盘与厂家示例不同，端子覆盖核对见下文 |
| C303/304/305/306/323 | C1210C226K3RACTU | GRM32ER71E226KE15L，C21397，贴片76215／商城55967 | 22µF±10%/25V/X7R/1210；已核尺寸与DC偏压，典型容量不低于原选择，允许作为首板替代候选；不是完整闭环验证 |
| L301 | IHLP4040DZER5R6M5A | **IHLP4040DZER5R6M01**，C845079，贴片55／商城55 | 原厂焊盘与现板一致；饱和电流增加、DCR略增、最高器件温度155→125°C；有条件推荐 |
| U702 | LP38691DT-1.8/NOPB | LP38690DT-1.8/NOPB，C2862452，页面17颗 | 同NDP0003B及脚位；1.71–1.89V落在codec DVDD范围内；限流更高，维持codec专用电源用途，有条件推荐 |
| U803 | PAM8302AADCR | 原型号DigiKey页面现货58687；JLC原型号0 | 优先外采原SOIC型号并邮寄SMT；**拒绝直接替**PAM8302AASCR（MSOP）。未购买、未确认邮寄/费用 |
| R703 | WSLP0603R0470FEA | **WSLP0603R0500FEB**，C2094520，贴片100／商城100 | 同结构/封装/0.4W，47→50mΩ需同步改值；被动网络差异检查没有发现新增低ESR场景，非LDO闭环仿真 |
| C317/318 | C0402C106M9PACTU | **GRJ155R60J106ME11D**，C469527，贴片17762／商城1768 | 原厂10µF±20%/6.3V/X5R/0402及尺寸已核；用于高阻音频线输出，不扩大成低阻耳机指标 |
| U301 | AP64350SP-13 | 原型号LCSC外部供应商页面73颗、5颗起、预计3–5工作日到LCSC | 优先保留原型号；AP64500候选暂不采用（限流上限5.75→9.2A），外部渠道接入嘉立创SMT尚未落实 |

以上“贴片/商城”是在嘉立创SMT替换搜索框中选“立创商城”读取的两个库存字段，不保证两者为独立可相加库存。网页对通用关键词会返回大量近似结果，表中只提取明确MPN；没有把搜索总条数当符合条件数量。

## 原厂依据与限制

### C301补偿电容

[厂商资料，高置信度] KEMET逐料号PDF `substitution-sources/kemet-c0805c332j5gactu.pdf` p1：3300pF±5%、50V、C0G、±30ppm/°C、无老化；2.0±0.2×1.25±0.2mm、厚0.9±0.1mm。原设计为同规格0805非极性电容。此项不改补偿标称值和容差；既有整机环路验证限制保留，不把单件匹配解释为整板稳定性通过。

源：https://search.kemet.com/component-documentation/download/specsheet/C0805C332J5GACTU 。SHA与下载状态见同名manifest。

### R304补偿电阻

[厂商资料，高置信度] Panasonic逐料号页已保存`r304-panasonic-page.txt`，https://industrial.panasonic.com/ww/products/pt/general-purpose-chip-resistors/models/ERJ6ENF1402V ，规格14kΩ±1%、0.125W、2×1.25mm、±100ppm/K；原厂`panasonic-erj.pdf` p4外形2.0±0.2×1.25±0.1mm、端子0.4±0.2mm、厚0.6±0.1mm。

[文件核对/工程推断，中等置信度] 当前R304双盘1.025×1.4mm、中心距1.825mm，内间隙0.8mm、总跨距2.85mm；Panasonic通用示例为内隙1.0–1.4、总跨距3.2–3.8mm。两者不是尺寸完全一致。按元件最坏长度2.2mm，当前焊盘仍有0.325mm外侧伸出；最小0.2mm端子完整落入焊盘，1.4mm横向盘宽覆盖最大1.35mm本体宽，非极性、无底部公共金属。判断可保留现有IPC封装作为首板候选，装配偏移/锡量仍随SMT稿核对，未声称厂家对本板焊盘背书。

### 电源电容与音频耦合电容

[厂商资料] Murata的GRM32逐料号规格/曲线为`murata-grm32-spec.pdf`及`murata-grm32-characteristics.pdf`：3.2±0.3×2.5±0.2mm，高2.5±0.2mm，不超过原KEMET最高2.8mm；仍是22µF±10%/25V/X7R。原厂页面https://www.murata.com/en-us/products/productdetail?partno=GRM32ER71E226KE15%23 ，下载链接和SHA见manifest。

[计算/推断，中等置信度] 曲线栅格读取得5.119V下约17.4µF/颗、8.4V下约12.0µF/颗，对照原KEMET同点16.18/9.88µF；两颗输出/输入在“额外减2个百分点、容差−10%、温度−15%、不计老化”的敏感性情景约25.9/17.6µF。它们是典型曲线读数，非厂商保证下限，不能据此宣称闭环稳定已验收；老化、联合条件和AC幅值仍未合并。原与候选ESR在开关频段均属低毫欧量级，未用标称电容量掩盖偏压下降。

音频优先GRJ155R60J106ME11D而非仅有商城字段的Samsung候选，因为已取得逐料号规格和曲线：1.0±0.2×0.5±0.2×0.5±0.2mm、10µF±20%/6.3V/X5R；1.35/1.65V示意偏压下约7.4/6.6µF，若负载10kΩ对应约2.1/2.4Hz高通。偏压/负载是情景假设，不是本板实测；仍不核准32Ω宽带耳机输出。原厂页面https://www.murata.com/en-us/products/productdetail?partno=GRJ155R60J106ME11%23 。原厂下载未接受网页Agreement、未申请样品。

### L301与R703

[厂商资料，高置信度] Vishay 34193，2026-10-02，`vishay-ihlp4040dz-01.pdf` p1：5.6µH±20%，DCR典型17.6/最大19.3mΩ，热额定8.5A（温升40°C），饱和16A（L下降20%），器件总温度≤125°C；不是网页简写的“16A连续额定”。≥1µH图的3.251mm盘宽、12.065mm总跨、5.817mm内隙与当前焊盘一致；体积/最高4mm也一致。原5A系列最大17.6mΩ、温度155°C，按3.5A示意电流增加约0.021W铜损，尚未做实物温升。源：https://www.vishay.com/docs/34193/ihlp-4040dz-01.pdf 。

MDA1040候选已有原厂镜像，温升8A/ΔT40°C、饱和14.1A/L降30%，推荐焊盘12.5×3.5mm、内隙5.4mm；与现盘有差别，当前已有更贴合的Vishay现货，故不优先采用。不能将两个厂商不同L下降定义的饱和电流直接排名。

[厂商资料/计算] R703改候选为同系列WSLP0603R0500FEB，0.4W/±1%/50mΩ；Vishay30122 p1明确EB与EA仅卷盘数量不同，结构和本体相同。原47mΩ与50mΩ同阻值区间的TCR约束保留。原被动网络模型重算，所选10kHz–1MHz窗口最低实部12.41→12.79mΩ；1–10MHz仍有低于5mΩ情景，不把50mΩ当全轨ESR保证。新增3mΩ不在负载主回路；0.5A RMS假设下0.0125W。原厂文件沿用已存`vishay-wslp.pdf`，不是换成不明厚膜电阻。

Eaton MFL0603R0470FA镜像也已核：0.25W金属膜、±100ppm、专用焊盘和3oz铜额定说明，不能把250mW额定直接套到现有1oz板。现有Vishay50mΩ方案可避免该材料/焊盘变化，因此不优先采用Eaton。

### U702 LDO

[厂商资料，高置信度] TI SNVS322M（主文修订2015-12；PDF包装附录另有后续日期），`substitution-sources/lp38690.pdf`：p3 TO-252为1=OUT、3=IN、TAB=GND；p16输入建议1µF并置于IN 1cm内；p17输出1µF与5–500mΩ ESR，支持空载稳定。不能把p5测试条件的CIN=COUT=10µF误写成最低要求。原LP38691手册及现有LDO支路分析见[此前专题](../扩展板电路仿真工具/ldo-capacitors-20261031/research.md)。

[厂商资料] p5输出全温容差±5%，1.8V档在1A下最大压差1.6V，典型限流1.5A；原500mA器件不能因此被当作同样的短路保护。1.8V±5%=1.71–1.89V落在TLV320AIC3104原厂DVDD1.525–1.95V范围内；本板3.3V输入、codec负载用途保留，J301.6仍不分配外设供电预算。候选器件1A名义能力不提高本板额定。p32 NDP0003B图已目视核对。C308/C309的2.2µF和并联C311保持，R703候选50mΩ见上文。可作为首板候选，短路/动态与真实温升仍未实测。

源：https://www.ti.com/lit/ds/symlink/lp38690.pdf 。p3/p5已渲染目视核引脚和表格；衍生图在同目录pinout/electrical.png，原PDF未改。

### U301 Buck

[原厂文档副本，中等来源置信度] AP64500 DS41979 Rev5-2，2024-12，26页：p3的1BST/2VIN/3EN/4RT-CLK/5FB/6COMP/7GND/8SW/9EP-GND与当前AP64350一致；p6参考0.8V±1%、RT200k→500kHz与原相同；p19补偿模型gm=0.15mS、RT=0.089V/A亦相同。p6峰值限流6.8/8/9.2A，原AP64350为4.25/5/5.75A；即使正常负载不提高，故障电流差异也不能忽略。

原厂及LCSC直链下载403、Mouser超时后，取得第三方GitHub保存的Diodes原文，存`substitution-sources/ap64500-github-copy.pdf`，SHA d3bcdc7dd4ca44cb36ef893d3dbfabbd1742dfc736557777868f6ead5d0a98e8。来源：https://raw.githubusercontent.com/mehmetali-inanoglu/ESP32-S3-Flight-Control-Computer/main/Datasheets/AP64500.pdf 。未声称这是已经向原厂确认的最新版，镜像来源限制保留。

### U803功放

[厂商资料，高置信度] 既有Diodes DS41333 Rev6-2（2021-05）Ordering列出AADCR=SO-8、AASCR=MSOP-8。原PDF在`../扩展板电路仿真工具/metadata-repair-20261030/sources/PAM8302A.pdf`。网页有货的PAM8302AASCR不能当AADCR的包装后缀；需要真实封装/布线改版。PAM8301AAF/C3001605只有SOT-23-6，也不直接兼容。没有删去功放或音频功能。

**后续查证修正“必须改封装”的范围**：[网页观察] DigiKey原型号https://www.digikey.cn/zh/products/detail/diodes-incorporated/PAM8302AADCR/4033280显示现货58687，剪切带1颗¥5.54、10颗¥38.87（含13%增值税，不含运费）；8-SOIC 3.90mm宽，与当前原料号一致。因此只在“全部物料必须来自JLC现货库”约束下才需改封装；外采邮寄可保留功放原设计。未付款、未加入购物车、未设置收货人。备损数量及JLC私有库接收条件尚未确定，不能把买5颗等于完成5块全贴。

继续查询AP64350时DigiKey触发安全验证，Mouser也出现设备验证；未解验证码、未绕过校验。转查正常公开LCSC产品页https://www.lcsc.com/product-detail/C2071691.html ，自营库缺货，但“Other Suppliers on LCSC”列73颗、5颗起$2.4352/颗（5颗$12.176，未含国际/国内物流及其他费用）、预计3–5工作日到LCSC。这是平台展示的外部供应商可供量，不是嘉立创SMT已入库数量；供应商身份、渠道和国内私有库接收仍需在采购前核清。证据`ap64350-lcsc-external-supply.txt`。

## 证据、失败及下一步

- 每组网页观察保存为本目录`*-search.txt`；原始精确BOM为`exact-mpn-match-rows.json`，候选未写入该原始证据。
- `ap64350-smt-search.txt`曾在异步更新未完成时保存了PAM8302旧结果，**不是AP64350证据**；真实AP64350商城/SMT双库存用`ap64350-lcsc-search.txt`（0/1），车规AP64350QSP-13也0/0。
- `l301-same-family-search.txt`使用分词`IHLP4040 5R6`返回电阻等近似结果，不作为电感证据；精确连续前缀结果为`l301-prefix-search.txt`，记录M01现货55颗。
- R703原同系列FEA与FEB卷带变体均0/0，见`r703-same-family-search.txt`。
- 网络搜索工具未返回可读结果，转浏览器可见页面与原厂PDF；403、超时、PDF字体警告如实记录。第一次Python调用路径失效、现行runtime无requests，收集脚本改用标准库urllib；未安装软件或改变系统设置。
- 本阶段为供料差异审查，未改CAD、未重跑无差异的全板DRC/ERC/SPICE。已有kicad-happy结论只覆盖原锁定物料，不自动覆盖新候选。
- 原生只读几何脚本确认主板SHA仍86654c03，抽取11个有关元件；证据`substitution-native-geometry.json`。电容曲线数字化/50mΩ差异模型在`substitution-deltas.json`，是计算不是实测，也未构造新的LDO/Buck闭环模型。
- 派生图`lp38690-pinout/electrical/dimensions.png`、`panasonic-resistor-lands.png`、`murata-grm32/grj155-characteristics.png`、`mda1040-dimensions.png`、`vishay-ihlp4040dz-01-dimensions.png`、`eaton-mfl-dimensions.png`均来自同目录相应PDF并已打开目视核查；不是用户实物照片。
- 先完成原厂尺寸/电气和联合电源评估，再形成可审阅替代清单。涉及功放封装或电源保护变化时，须先确定方案，再更新原理图、PCB、BOM/CPL和生产文件；不能只在网站点替换绕过设计。
- 订单Y6保留未付款；SMT未点“备料完成”，未下整盘预购或收费代选型，未宣称已全套下单完成。
