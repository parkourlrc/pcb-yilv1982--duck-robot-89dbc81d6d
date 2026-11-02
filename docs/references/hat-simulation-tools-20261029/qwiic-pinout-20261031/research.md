# J502标准针序与Rev A.1修复（2026-10-31）

## 当前结果

**[文件/原厂图核对] 已将J502改为Qwiic/STEMMA QT针序，回写为Rev A.1。** 当前PCB SHA256为`90f27091017525a22f45c8818c973c317ed6262387a98fdf06bdc26337dac2a6`。原生DRC/未连接/parity/ERC/netlist全0，DRU加载证据有效；其它焊盘连接及I2S参考铜取样保持。

**旧Rev A针序与A.1不同，不能混用文件或直插判断。** [用户确认，2026-10-31] 自主HAT尚未送厂、没有新板实物；不是现有白色HAT V1.2。此前“制造状态待答复”已被此明确回答取代。没有操作实物、上传或下单，以下结果只针对CAD和导出资料。

| J502制造针号 | 旧Rev A / 6fe440f3… | Rev A.1 / 90f27091… |
|---:|---|---|
| 1 | +3V3 | POWER_GND |
| 2 | POWER_GND | +3V3 |
| 3 | I2C5_SCL | I2C5_SDA |
| 4 | I2C5_SDA | I2C5_SCL |

这里是JST/封装的针号，不是屏幕左右或翻板后重新从左编号。A.1保留原型号、朝向、位置和4针3.3V I2C功能。板面标识改为`DUCK HAT A.1`，各原理图rev同步为A.1；图纸Date保留原设计创建日期，修订日期/源身份以本记录和current-review绑定为准。

## 一、为什么需要修正

旧历史方案曾把J502称为Qwiic/STEMMA类，但实际文件是VCC/GND/SCL/SDA。SparkFun官方TMAG5273原理图PDF第1页直角接口及第2页Vertical Qwiic Connector都清楚标出1=GND、2=3.3V、3=SDA、4=SCL。两页均已渲染并打开核对，原件/图片/URL/SHA见`sources-and-scope.json`。来源：SparkFun，图纸v10，M. Odichkov，原图标CC BY-SA 4.0；本项目只归档/渲染作接口依据，不把霍尔传感器引入HAT。

旧接口不等于必然已烧坏任何设备；本项目没有这种实测。但若将它当标准Qwiic口配标准直连线，电源/地及SDA/SCL均不一致，因此属于应在设计侧解决的兼容性问题。没有用“外形同为SH4P”替代针序核对，也没有在新板继续要求用户自行猜线。

针序匹配不等于所有SH4P模块都兼容。仍须核模块为3.3V供电/逻辑、地址和上拉条件、线束实际对应及负载；不允许5V上拉直接进入本总线。此修复不包含ToF模块本体或测距实测。

## 二、具体修改与验证

- 原理图仅交换J502四条网络标签，更新net-contract，并补明确针序/旧版差异说明。J502位号/值移离针脚，避免遮挡pin1；其它功能针网保持。
- PCB仅改四焊盘赋网；删除5段原B层局部引线，增加6段新引线，保持原分支线宽：3.3V 0.2mm、SCL 0.25mm、SDA 0.1874mm。3.3V/SCL/SDA新分支长度约1.743/2.302/2.764mm，准确值见change-contract.json。
- 一枚普通3.3V贯通via从(158.92,112.0)移至(158.92,112.1)mm，避免改为GND的pin1与原电源via间距不足；无新增孔，不改原0.55/0.3mm尺寸。原6处填孔盖铜要求不变。
- 元件/焊盘几何、板框、项目设置和DRU不变；其余原铜对象保持。现72封装、1130线段、100贯通via、17地via；58拟装件、38组、35唯一MPN保持。
- 四针分别核到J101、codec、BMI088的正确网络；旧连接比较明确排除被有意改网的J502四针，其余旧焊盘连接无丢失。
- 对保存并重铺铜后的前后板，逐点比较5条I2S的其它层参考铜，采样间隔≤0.025mm；旧覆盖点零损失，所有覆盖长度差为0。不将此当回流阻抗或EMI实测。

完整证据：geometry-connectivity-check.json、reference-coverage-delta.json、accepted-reports/、promotion.json及checkpoint.json。成功后才回写；旧6fe440f3源在before-metadata/保存，不覆盖历史证据。

## 三、C307钢网导出修正

另发现旧生产审查包虽然BOM/CPL将C307列DNP，但F.Paste仍有该器件两个开口。按本次“不贴装C307”的装配意图，导出流程现只在完整绘图副本内移除其两个F.Paste层成员，再由原生KiCad绘图；原PCB的铜焊盘、阻焊和DNP标记保留。

**这项比较与J502电气修复分开：** 对同一A.1基线，DNP导出副本的4铜/2阻焊/2丝印/板框共9层在排除生成时间/校验元数据后完全一致；其它拟装件的锡膏位置和aperture定义逐项一致。F.Paste从61变59个flash，只去掉C307两项；B.Paste保持128。原始未过滤锡膏图保留于unfiltered-paste/，不能再混入当前送审包。

本轮先在6fe440f3阶段验证过该流程，证据在[钢网阶段记录](../stencil-and-release-20261031/research.md)；现行包已经按90f27091重出。`audit_complete_bom.py`新增实质钢网核查：重读原始/当前Gerber并按DNP名单比较，不只相信manifest中的accepted字段。

## 四、需求真实性核对

可访问的用户历史附件共447行，未检出“耳机/headphone”；其中J504只被描述为输出接口草案。现行已确认R04为音频播放/录音，R05为ToF/其它I2C扩展，明确不含ToF模块本体。原文定位与SHA见sources-and-scope.json。

因此撤回将“未定义的低阻耳机性能”当成已确认需求缺陷的表达：**J504低阻负载仍未核准，但它是未确认用途/使用限制，不是已有实测故障或必然需要改板的要求。** 也不能反过来宣称用户明确不要耳机；可查记录有边界，未来明确用途后再核设计条件。J504拓扑/容量未改，主播放/录音路径J506/J505保留。

## 五、失败与工具边界

- 首次只读脚本调用LIB_ID.Format遇到本机SWIG重载异常，没有写文件；改用必要的原生焊盘数据后取得针网。
- 初次候选原理图改名没有使用S-expression的Quoted类型，网表导出明确失败；保留rejected-unquoted-schematic/后从同基线恢复原理图并修正引号，重跑全部原生检查。失败结果未计为通过。
- 初次SVG叠加Fab字段过密，且误用了Gerber才有的exclude-value参数；本机SVG命令拒绝该参数。改为铜/丝印/边框原生预览后重新导出检查，未因此改PCB字段。
- J502原理图值遮住pin1的问题已做纯显示整理，修改前图片/源文件保留；现在针号与网络可读。

## 六、当前交付与未完成项

现行[生产审查包](../../../../hardware/custom_hat/rev_a/production-20261031-qwiic-review/README.md)同版导出，163圆孔逐项匹配、6处POFV保留。kicad-happy本轮重新运行schematic、PCB full、cross、EMC、thermal、Gerber、SPICE及prior delta；相同35个MPN身份只复用既有unknown生命周期结果。详细分类见[本轮审查](review.md)。

只读软件审计改用`hardware/custom_hat/current-review.json`，但会核当前所有源文件指纹、checkpoint/原生报告SHA、DRU加载证明及规则SHA，不是凭“current”文件名接受。codec overlay重新核新网表契约；codec模块、IMU程序和音频路由代码未因J502改线而重编。旧软件适用性报告保留于software-before-a1/，新的读审计明确绑定90f27091。

制造接受、实际层叠/铜厚/装配、入口配对/保护/负载及真实主控/首板功能仍未完成；不能把未制造前无法做的实测当成必须先完成的制板步骤，也不能提前代签通过。[用户确认] 尚未送厂、无新板；本轮未联系工厂、上传、下单或操作实物。目标保持未完成，不提交/推送，不使用子代理。原目标逐项核对及外部依赖见[完成情况审计](completion-audit.md)，已补[最短首板草案](../../../specs/20261028-custom-hat/first-article-a1.md)。

已准备[本地CAM/装配评审资料](../../../../hardware/custom_hat/release-review/README.md)，现行状态更新版ZIP的SHA256见review-bundle.json。仅包内说明反映用户已确认未送厂，22个制造输出保持；26个成员核SHA/ZIP完整性，仅含当前制造资料、便携清单和10项工艺询评问题，不含旧包、默认Job、未过滤钢网或内部运行路径。旧ZIP不覆盖，保留历史身份。资料没有被发送，也不是生产授权。

workflow-negative-checks.json使用隔离副本核了两个实际回归场景：源文件字节变化会使current-review绑定拒绝；把未过滤的C307钢网放回、同时伪更新所报hash/accepted字段，仍被Gerber语义对照拒绝。原主工程和原生产包摘要保持，没有在主文件上制造错误测试。

2026-10-31 13:53/13:56 UTC另做了两次有明确目标的只读uname查询。当前执行环境`ssh -G radxa`指向172.16.108.54，首先在该旧地址超时；依据10-25静态IP和10-27 servo-web来源记录，用单次HostName参数改查192.168.1.35也超时，均终态255、无版本输出。两个JSON保存命令与结果；没有持久修改SSH配置，没有扫网、部署、读I2C或改GPIO。超时只表示本会话未取得连接，不能推出主控关机、坏板或网络故障机理。
