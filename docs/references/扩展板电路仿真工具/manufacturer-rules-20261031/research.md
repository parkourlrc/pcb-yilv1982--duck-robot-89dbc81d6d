# 制造文字约束、孔距预核与复审（2026-10-31）

本页为c6c09b33…历史检查点。后续确认旧DRU前置内容缺单位，整份文件未成功加载；本页内置文字负对照仍有自身依据，但不能延伸为全部自定义规则通过。现行见[通孔制造规则收敛](../npth-clearance-20261031/research.md)。

## 当前状态

**[文件/工具核对] 按嘉立创公开文字要求修正了小字与丝印间距，并将约束写入工程。** 现行PCB SHA256为`c6c09b3306832200c0c723443a350882a816cb00a92d79b10551363b588d35df`，工程设置SHA256为`f83c8fa60df10f5e97c6ee44c98c3c568d4d3da5d09e1de8d5d739e856c05cd3`。

原铜对象、所有焊盘几何、赋网和原连接保持；原生DRC/未连接/parity/ERC/netlist全0。72封装、1106线段、100过孔（99通孔+1微孔），58/58拟装件有MPN，38拟装分组、35唯一MPN，52 SMT+6 THT，C307 DNP。分组37→38仅因C309使用本地丝印变体封装，未新增器件或料号。

当前[生产审查包](../../../../hardware/custom_hat/rev_a/production-20261031-manufacturing-review/README.md)已重新导出。**仍不可投板**：源中仍有微孔，真实层叠/工艺接受、保护职责及电气/热与首板验收未完成。

## 来源与此次实际修改

官方[PCB能力页](https://jlcpcb.com/capabilities/pcb-capabilities)的Silkscreen段给出文字高度至少1.0mm、笔画至少0.15mm、焊盘到丝印0.15mm。已取得HTTP 200正文；原件/去脚本文本及哈希见sources-manifest.json，定位为sources/jlc-capabilities.txt的Silkscreen段。KiCad规则实现依据为[KiCad 10 PCB手册](https://docs.kicad.org/10.0/en/pcbnew/pcbnew.html)的Text constraints/Custom Rules段，同样归档。

| 对象 | 本次处理 |
|---|---|
| DUCK HAT Rev A | 由0.8mm/0.12mm改为1.0mm/0.15mm，移到(140,126.5)mm |
| pin1数字1 | 显式设0.15mm笔画，避免沿用未显式指定的厚度 |
| R501/R502位号 | 0.8mm小字移到F.Fab，装配图/BOM保留，焊盘不动 |
| U803位号 | 板边和封装外框之间无法满足当前文字间距，移到B.Fab；不移动器件 |
| J802位号 | 移到(160.42,123.4)mm，清除外框间距提示 |
| C309外框 | 一段与U702外框过近的线移到Fab；使用duck:C_0805_2012Metric_LDO_ClearSilk匹配本地库，原理图/PCB同步 |

C309本地库由已安装KiCad10的C_0805_2012Metric派生，来源路径与SHA见library-variant.json。仅丝印/Fab图形分配发生变化，焊盘、器件位置和电气连接不变；库不匹配警告已消除，没有忽略它。

## 约束必须证明实际生效

最初的自定义文字规则均未使缩小文字报错，已经撤回。后续确定前置DRU有缺单位错误，整份规则未加载；这些尝试不能用于比较层名写法或断言自定义文字功能失效。保留有效的内置文字限制即可，见顶部勘误。

最终改用.kicad_pro内置设置：min_text_height=1.0、min_text_thickness=0.15、min_silk_clearance=0.15、默认silk_text_thickness=0.15。除此之外的工程字段按结构比较保持；.kicad_dru原文完全保留。准确项目哈希已写入该run的approved_project_settings_sha256，没有绕过设置护栏。

负对照用另一份完整副本，仅把板名字恢复0.8mm/0.12mm：原生DRC明确产生text_height与text_thickness，状态design_blocked。修复副本则全0。manufacturing-rules-check.json记录该对照、所有现行可见丝印文字尺寸和允许设置差异。

间距加严先暴露4项提示：U803板边、J802两处外框间距、C309/U702图形间距；移位/改Fab后清零。第一次直接改C309图形产生lib_footprint_mismatch，随后建立来源明确的匹配变体，没有关闭库检查。FootprintSave返回None曾被误当保存失败，核实文件已生成后改为按输出存在性判断；该失败未提升主板。

## 孔距预核

audit_fabrication_holes.py读取59个PTH、4个NPTH、99个普通via和1个盲孔。全部是圆孔；按CAD标称孔边距离计算，所引用孔型组合未发现超限：

| 组合 | 本板最小孔边距 mm |
|---|---:|
| 普通via–via | 0.4503 |
| PTH–PTH | 1.5000 |
| PTH–via | 1.1456 |
| NPTH–PTH | 2.9527 |
| 盲孔–普通via | 0.9509 |

阈值逐项记录于hole-spacing-audit.json。勘误：0.254mm/0.5mm是保守项目筛查值，并非当前能力页0.2mm/0.45mm的逐字复制，工具归属说明已修正。未取得阈值的NPTH组合只列实际距离。此检查不含钻刀补偿、孔壁/公差、阻焊桥、槽孔或厂商审查，不是整板DFM认证。

## 微孔路线与制造资料

[U701替代分支](../u701-through-via-20261031/research.md)的局部改线候选均未采用，未修改主板铜。新的公开资料表明，普通0.15mm机械通孔值得单独复核；原坐标0.35/0.15mm通孔的只读四层异网铜筛查没有碰撞，但仍与项目0.125mm普通通孔环宽规则冲突，未运行完整接受检查，不可声称HDI已经移除。

已形成[制造参数送审提案](manufacturing-brief.md)，明确当前4层/1.6mm、1oz铜厚意向、微孔层对、6处填孔盖铜和需要返回的正式层叠信息。没有用自动Job中未经确认的0.48mm介质值替代真实层叠，也未将提案写成厂家已经接单。未发送询价、上传文件或创建订单。

## kicad-happy复审及边界

固定提交2fd9aa0fe2d620f36627d9221e8b1393987ae38e，重新运行schematic、PCB full、cross、EMC、thermal、Gerber、SPICE、prior delta和fab gate；位号/MPN/DNP身份不变，生命周期明确复用上次35个unknown，没有新库存/在产结论。

schematic仍44项（3 warning）、PCB58项（3 error/14 warning）、cross2 warning、EMC53项（7 error/33 warning），Gerber2个既有Paste比例warning。12个理想子电路pass，自动热估0.028W均不用于整板性能验收。电路/回流、扬声器差分启发式、外框边距与真实工艺的裁决沿用[上阶段逐项复核](../board-marking-20261031/research.md)，铜未改不能被写成这些风险全部关闭。

fab gate仍为10 pass/1 warn/1 fail；数量FAIL仍是10个board-only对象与C307 DNP的统计口径，advanced工艺提示仍真实需要处理。没有以退出码0替代门禁内容。未重新生成全板逐器件Deep Review；本轮人工范围是文字、孔距、本地封装图形及无电气变化的核对，既有手册验证边界继续保留。

正反装配图均已打开检查。第一版合成图的TP803 Fab位号压住了放大的板名，现仅在一次性显示副本中把TP803标签移到测试焊盘上方；源CAD不改。旧图assembly-before-tp803-front.png保留，现行图为assembly-front.png/assembly-back.png；底面已镜像，CSV不再镜像。相关数据和图像登记于[照片索引](../../../photos/README.md)。

修改未提交，未上电、下单或使用子代理；整体目标未完成。下一步先裁决0.15mm普通通孔工艺分支，再继续保护职责、完整电气/热与必要首板功能核查。其余图形线宽/阻焊工艺不能仅凭本次文字与孔距检查作全面放行。

final-audit.json确认58件原理图/PCB五字段、BOM/坐标/52件SMT子集与装配分类一致，源/输出哈希无差异、默认Job隔离有效、无意外产物，新链接和git diff --check通过。source-manifest.json仍是2026-10-28生成器阶段来源快照；本次新增封装的来源在library-variant.json，不能把初始清单当完整现行来源表。
