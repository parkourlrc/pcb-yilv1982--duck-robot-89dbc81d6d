# HAT：极性标记完成与原厂装配资料补齐

> 后续现状：现行9daf71d8为避免参考对插姿态下的长针干涉，J301已改B面、针孔/网络不变，B面新增明确编号电源标记。其它17方向标记保留；当前同源r12及名义板间距范围见[机械报告](../归档扩展板机械适配复核/research.md)。本页96dc/r11只描述前一检查点，不作为当前J301装配面。

日期2026-11-02；上一轮属于实质进展，本轮继续解决确有依据的设计/资料问题。主会话执行，没有子代理、询价外发、下单、付款、上电或Git提交。

## 当前结果

**[文件核对] 主源SHA256为`96dcce92ca42bbfcee423ef8590e3e1318c5e10c660d5d688f634b0924fa7036`。** 本轮仅新增17个丝印标记、把D301原K由1mm增到1.27mm；不改原理图、BOM、器件位置、铜、阻焊或锡膏。此前24热连接、C310避孔和U701分层via保持。原生DRC/未连接/parity/ERC/网表全0，DRU加载有效。

全部18个有方向器件覆盖：D301、U301/U501/U701/U702/U801/U802/U803和10个J连接器。U801/U802为0.8mm实心圆点，其余IC为1mm圆点；连接器新增1mm高、0.15mm笔画的“1”；D301 K高1.27mm。每个标记位于同面，距该面所有焊盘铜至少0.3mm，与58个拟装器件Fab包围框均不相交且至少0.05mm筛查余量，目标器件最近的编号焊盘均为1。既有方向标记保持且方向一致。Fab包围框是保守二维模型，不代表实际本体尺寸公差或装配偏移实测。

[geometry-connectivity-check.json](geometry-connectivity-check.json)独立核对18项、逐对象差异、电气快照以及9个非丝印Gerber绘图完全相同。正反[原生图](polarity-front.png)/[背面图](polarity-back.png)已打开，背面镜像用于翻板观察；坐标表不再次镜像。标记设计侧的尺寸/方向/遮挡缺口已处理，元件实物本体标记与来料品质仍在收料阶段核查，不能提前填通过。

当前内部包：[production-20261102-polarity-review](../../../hardware/custom_hat/rev_a/production-20261102-polarity-review/README.md)。当前同源拼板：[r11](../../../hardware/custom_hat/panels/a1-smt-2up-20261102-r11/README.md)。国内RS-274-X从[交付入口](../../../hardware/custom_hat/release-review/README.md)进入。上一轮153bd/r9保留历史，0263/r8明确撤出候选。

## 拼板生成器问题及修复

新标记触发r10第二单元J301丝印间距0.1101mm告警。**[源码/文件核对] 根因不是主板标记间距：** 原PCB_FIELD保存角270°，实际绘制角因自动保持可读为90°；旧生成器转换成PCB_TEXT时复制保存角，文字实际转180°，笔画位置变了。现改复制`GetDrawRotation()`并保留水平/垂直对齐、镜像、粗体/斜体。未降低0.15mm丝印规则、未移动主板器件。

独立[负对照](panel-label-negative-control.json)确认r10复制角270°不符原90°，r11为90°匹配；拼板验证新增全部可见位号样式比对。r10失败证据保留，不发包。r11原生0违规/0未连接，原焊盘/线网、单元隔离、逐层via尺寸、PFID均通过；104SMT/12THT、12POFV、32个BMI088开口81%保持。

## 本轮原厂资料

嘉立创规范依据继续为已归档62705极性、62781耐温、62745湿敏、62811供料及双面装配等规则；页面原文见[已有来源清单](../归档扩展板嘉立创规则自查/sources-manifest.json)。本轮没有把建议参数冒充IPC条文原文，也没有把文档转引当实物验收。

| 来源与定位 | 直接证据与结论 | 限制 |
|---|---|---|
| [Vishay IHLP-4040DZ-5A产品页](https://www.vishay.com/en/product/34315/)中的Solder Profile and Assembly链接；[34213 PDF](sources/vishay-34213.pdf)，Rev2024-04-22，p1–2 | 官方精确系列页关联指南；无铅SnAgCu典型峰255±5℃，峰值5℃范围≤30s，液相约217℃/60–150s，预热150–200℃/60–120s，升温≤3℃/s、冷却≤6℃/s | 页面HTTP尾部IncompleteRead，已读部分含完整标题/链接；PDF完整取得。不是借用DZ-11规格；MSL数字仍未取得，不自定MSL1 |
| [Diodes TN1](sources/diodes-tn1.pdf)，AP02014 Rev3，2016-07，p5–7、Fig10 | 厂商通用装配指导：无铅235–255℃，预热≤2.5℃/s、soak≤2min、reflow段≤85s、冷却≤4℃/s；p7明确>260℃超规格 | 原厂声明示例需按PCB调整；JEDEC分类曲线不是生产曲线。AP64350/PAM8302A精确封装MSL1依据仍为各datasheet，不能从TN1推实际良率 |
| [KYOCERA AVX MLCC Attachment](sources/avx-attachment.pdf)，p2 Scope/p3 Table2 | Scope明确陶瓷chip电容，适用于本板C301的MLCC装配指导；无铅对流/IR表峰250–260℃，回流30–60s，预热≤2℃/s、冷却≤4℃/s | 不使用Hi-Temp330–340℃栏；推荐范围不是所有器件统一的允许极限，不能仅取数学交集就发整板配方 |
| [JST SH官方目录](sources/jst-sh-official.pdf)，p1/p3–4 | 通过官方可见Catalog链接下载4页原件。BM02/03/04B-SRSS-TB板端为耐热PA、压纹编带、1500/reel；3000/reel属于SM侧插型，线端壳体PBT也是另一个部件 | 表格视觉核对修正了纯文本错序引起的卷盘数量误读；官网没有回流峰值/耐时，不能把工作温度−25～85℃当回流参数 |
| [JST Handling Precautions](sources/jst-handling.pdf)，p5§3 | SH目录直接要求参考此文件；SMT使用耐热树脂，焊接质量取决于曲线、锡膏和空气/N2气氛，要求实际评估；吸湿可能起泡 | 没有统一MSL或峰温数值；已把“拿不到官网资料”改成“原厂公开规范要求应用评估”，不无限搜索一个不存在于此文档的数字 |
| [JST官方FAQ](https://www.jst.com/resources/faq/)，General→through-hole reflow | 多数通孔座材料不能承受回流，供波峰/浸焊；正文已保存[snapshot](sources/jst-tht-reflow-faq-visible.txt) | 支持既有THT后焊方案，不把SMT耐热PA结论套给EH/Samtec通孔座 |

下载原件、来源URL、哈希、失败结果在sources下各manifest；浏览器只读，没有表单提交。Vishay48329是IHLP2020CZ的PPAP，虽附2012版34339，**不能作为4040DZ-5A精确认证**，保留负证据；最终采用精确产品页关联的2024版34213。JST直连403后，正常浏览器页面验证自动通过，可见官方链接下载成功；没有绕过验证码或浏览器安全警告。

## 材料与工序

当前[35MPN矩阵](material-process-matrix.csv)按本轮原件更新，58拟装件仍52SMT+6THT，未换料。U701/U702的MSL2和U702管装结论保持；本轮补齐L301、Diodes、AVX原厂指导，SH原件也已取得。未给出数值的器件不统一标MSL1，也不把所有“未列MSL”升级成设计错误。

[装配执行依据](assembly-process-basis.md)明确双面回流/THT后焊、管料处理、MEMS/电感清洗条件，以及设计资料已完成和工厂过程尚未实际执行的边界。原指南对炉温的示例范围并不全相同；尤其AVX表格下限250℃、Vishay电感典型250–260℃与WSL正文≤250℃，不能只取250℃一个点就声称整板有充分工艺裕量。需要按实际锡膏和热容量测温优化，缺精确窗口的SH按JST说明评估。当前无新板、未备料，不伪造这些结果。

## 同源审查及未完成项

固定kicad-happy版本2fd9aa0fe2d620f36627d9221e8b1393987ae38e已跑schematic、PCB full、cross、EMC、thermal、Gerber、SPICE和delta。与上一轮相同规则/summary没有新增告警；原59项PCB、54项EMC风险提示保持，按先前逐项解释。12项自动SPICE通过、默认26℃热估算都不是实际稳压环路/满载/EMC验收。生命周期复用同MPN旧unknown，没有查询库存。

真正未完成的是：SH精确回流窗口或原厂所要求的应用评估；整板锡膏/曲线/二次回流保持方式与来料标签；官方结构基线的实际制造选择/成品记录；连接器尾针/对插堆叠与首板功能。极性尺寸缺口、缺MPN、未连线和双面Mark不再作为待办重复出现。原目标仍未完成，未放行制造或上电。

过程失败：第一次在遍历GetDrawings时Remove触发KiCad SWIG访问异常，只发生在隔离副本，主源未变；改为保留原文字并新增圆点。D301第一次自相交判定误用了Python包装对象身份，改按UUID排除自身；原生检查随后通过。验证API的IsFilled不存在，改用实际IsSolidFill。r10失败独立保留；没有静默修改上游库或放松规则。

收尾[completion-check.json](completion-check.json)确认主源/报告/ZIP/r11输出和材料附件同源，18标记与58个拟装Fab框覆盖，163钻孔、104SMT和32个81%开口保持；三份软件审计绑定新源。r11独立规则哨兵199项证明加载，最终Gerber审查在panel-gerbers-final.json。7个相关脚本语法、当前文档/随包链接和`git diff --check`通过；只读参考库无变更，修改未提交。

便携附件修订：初版工序说明含仅在仓库有效的相对报告链接，r2已消除；JST第3页表格打开后发现文本提取把侧插3000/reel列混入顶插，r3已更正为BM顶插1500/reel。两个修订都不改铜、钻孔或Paste；最终入口只指r3，早期准备包不外发。
