# HAT：邮票孔、BMI088电源支路与双联规则继承修复

2026-11-02启动，2026-11-03 Asia/Shanghai续核与打包。主会话完成，无子代理。用户要求依据嘉立创公开资料自行核对，不再等待人工回答全量问卷。

## 当前结果与证据等级

2026-11-03全目标审计见[full-goal-audit.md](full-goal-audit.md)：22条规范、原问题与功能项逐一列完成证据及缺口。官网两页已通过直接HTTPS重新取得并核正文，前几轮web工具无返回不再当作当前所有渠道不可读；能力表正文与前次相同。没有工厂/实物新证据，不能以重复下载或状态整理宣称又解决了一项问题。

**[文件核对] 主源为86654c03b6c1c8f51f7d5a4bef469aceed2ddfc73433b3e50426940c2a23164a，制造拼板r18为fd6cd170fc09848e37feb88e10dad3bbf1d21954a8139f7bb0f8a303e4ceb22c。** 主板65×30mm/四层/72封装/1132线段/100贯通via；58拟装=52SMT+6THT、35唯一MPN。原生DRC、未连接、parity、ERC、网表差异均0，主板DRU加载哨兵163项。零计数只说明规定的文件检查通过。

本轮解决三个具体问题：邮票孔原在成品外侧；局部分板退铜情景暴露BMI088电源支路连接依赖；拼板第二单元遗漏Power网络类别。后者是对旧“复制等价/DRC0”结论的实质勘误。**r1～r17拼板及旧r14完整PCBA ZIP退出当前制造入口**，保留原始文件供追溯。旧主单板没有B2网络，不能把该拼板错误归咎所有旧单板。

仍未制造，没有自主新板实物；全部实际制造过程、完整机械和首板功能按[剩余事项](remaining-actions.md)保留，不把本轮文件审查升级为生产放行。

## 公开规范与历史版本裁决

依据嘉立创SMT 62704“邮票孔”设计规范：[原始网页](https://www.jlc-smt.com/technology/detail/62704.html)，[已归档正文](../归档扩展板嘉立创规则自查/sources/smt-rule-62704.txt)第65～70行与[来源清单](../归档扩展板嘉立创规则自查/sources-manifest.json)。规范建议每组5～8个0.6mm无铜孔、孔边距0.35～0.40mm、孔中心在板框线或板内、常规槽1.6/2.0mm。本轮续核web打开未返回可用正文，采用前轮已取得官方正文，不宣称再次在线确认。设计值与文章建议对应，不等于实际工厂生产稿已经接受。

| 版本 | 观察到的文件结果 | 判定 |
|---|---|---|
| r14及更早 | 孔中心偏单元外侧0.25mm，且第二单元Power映射遗漏 | 旧DRC0未覆盖这两个问题，不能继续作现行交付 |
| r15 | 居中孔、旧X112/153位置；4个孔铜距违规、1个未连接 | 未采用，原始DRC保留 |
| r16 | 改X108/160；违规0但仍1个BMI088电源支路未连接 | 未采用；不能用普通违规0掩盖未连接 |
| r17 | 增加BMI088桥线后原生0；随后发现第二单元类别不完整 | 仍未采用，规则继承不足 |
| r18 | 两单元Power类别补全，孔居中/局部退铜、原生0、逐项复制与参考铜检查通过 | 当前本地制造资料候选，非制造验收 |

[各版DRC](panel-drc-r15.json)、[r16](panel-drc-r16.json)、[r17](panel-drc-r17.json)、[r18](panel-drc-r18.json)均保留。原b610单板在同样完整工程检查中仍为0未连接；因此不得倒推旧单板一直断线，也没有把机理写成已确认的算法/浮点错误。观察能支持的是不同填铜几何下连接状态不同；填铜窄颈、边缘变化与软件行为尚未分离为唯一机理。

## 主板唯一新增铜线

[geometry-connectivity-check.json](geometry-connectivity-check.json)记录F.Cu +3V3、宽0.2mm、长0.5mm的新增支路，(160.19,111.1)→(160.69,111.1)，UUID 3aebda7b-40ee-4d64-ad87-936153d8329d。它明确连接BMI088两处电源扇出，不改变原针网；全部原焊盘、原走线/via与原连接保持，4421个I2S参考铜取样未减少。[原生局部图](bmi-bridge-detail.png)已打开；[拼板反例修复探针](bridge-panel-probe.json)与[回写记录](promotion.json)绑定对应源。

前轮U301四窗69.63%项目选择保持，U701/U702窗口、J301 B面、24热连接、18方向标记、35MPN均未撤销。本轮不能继续描述成“只有F.Paste变化”。

## r18制造副本的明确差异

85×82mm双联；单元Y偏移32mm，8mm工艺边/R2角，4个定位孔，双面各3个不对称PFID。X108/160为连接带中心，40个0.6mm孔形成8行，每行5孔、1mm节距、孔边间隙0.4mm，中心在Y100/130/132/162单元名义边线。

8个分板退铜矩形为中心X±2.8mm、孔行Y±0.6mm。只修改拼板zone边界，原焊盘/走线/via保持；不能声称制造拼板与单板每一处铜图形相同。原生填铜后差异位于分板带及允许的局部圆角/窄颈区域（横向再0.15、法向再0.25mm），区域外对称差≤1e-6mm²。每单元每层约减少4.50～4.55mm²边缘铜，两个单元各4421个I2S参考铜样点无减少。中心分板线±0.2mm无铜命中，镂空586.809mm²/8.423%，外形为一个闭合整体。证据见[edge-copper-reference-check.json](edge-copper-reference-check.json)。

## Power类别遗漏及负对照

原生成器复制项目后增加B2/网络，却未同步netclass_patterns。原+3V3按Power0.2mm，B2/+3V3错误使用Default0.15mm；重铺出现第二单元额外铜。这不是原连接相同或原生DRC0能自动排除的问题。

已修生成器，保留全部原项目设置，扩展netclass_patterns、netclass_assignments及net_colors；两单元codec专属DRU继续保留。验证器现在比较完整项目与预期扩展，并绑定PCB/project/DRU/edge审计哈希；导出器拒绝缺项或证据变更。[18版项目清单](historical-panel-netclass-inventory.json)逐一核原项目哈希，确认仅r18具有完整第二单元Power匹配，不只是从r17推测所有旧版。

[真实负对照](netclass-loading-negative-control.json)：两单元各加一对0.175mm间隙的临时走线。r17仅A1报Power违规，B2漏报；r18两者均被0.2mm Power规则拒绝。探针未写回主板/交付板，不是设计本身有违规。[最终复制检查](panel-verification.json)原焊盘/线、连接、两单元隔离、逐层via和文字样式均通过。

## 交付与审查

[完整PCBA ZIP](../../../hardware/custom_hat/release-review/HAT-A1-JLC-PCBA-86654c03b6c1-20261103-assembly.zip)，SHA256 46413368d6837e2b7f131f91f67a7f359d85bd663f88ff39f4a52a3b3de24194。含11层RS-274-X、370钻孔、104SMT/12THT/116拟装坐标、118含DNP位号映射、12项POFV、制造选项/材料/工序说明及单元正背装配图。402实际Paste开口，BMI08832个开口81%，C307/B2_C307不装无Paste。0.125mm钢网基线最小面积比0.68334/宽厚比1.8，通过几何筛查，非印刷实测。

[单板RS-274-X格式参考](../../../hardware/custom_hat/release-review/HAT-A1-JLC-RS274X-86654c03b6c1-20261103-panel-edge.zip)，SHA256 4cf5cacca00c27636e9f4652bb47c1c9e0dc39febcde500f904299e6b813d0bd；其BMI088原始Paste100%，不可混作实际SMT钢网。原生X2[内部包](../../../hardware/custom_hat/rev_a/production-20261102-panel-edge-review/README.md)用于审计。

固定kicad-happy版本2fd9aa0fe2d620f36627d9221e8b1393987ae38e完成同源schematic、PCB full、cross、EMC、thermal、Gerber、SPICE与delta；最终PCBA Gerber另行审查。完整告警裁决/能力缺口见[kicad-happy审查](design-review.md)，不能说自动告警全清零。三份软件离线审计已绑定新源，旧证据存software-before-edge；没有重新部署或操作硬件。

[正面](panel-r18-front.png)、[背面镜像](panel-r18-back.png)、[邮票孔局部](panel-r18-mouse-bites.png)均已打开；[图片清单](image-manifest.json)与照片总索引登记，都是CAD派生，不是实物照片。完成检查见[completion-check.json](completion-check.json)。

## 流程改进与边界

### 2026-11-03续查：补实际阻焊开窗证据

先前native-dimensions明确不覆盖mask-bridge，本次对当前20261103-assembly包补实际Gerber开窗核对：[报告](mask-review.md)。642开窗逐一匹配原生pad/阻焊外扩，最小名义间隙约0.229mm；没有异网铜或未填孔外露，12个被开窗覆盖的via恰为12项POFV。0.05mm负对照被识别；不能用原生PAD mask shape直接代替Gerber，因为其API未含FID外扩。没有发现需要改板的新阻焊缺陷，CAD与交付包不变；实际生产稿/成品公差仍待工厂阶段。

### 2026-11-03继续核对：先分板、后装通孔连接器

[全部8条连接带切线检查](depanel-process-check.json)对两个单元116个Fab框逐一计算，SMT最小距切线5.32635mm；若先安装THT，J101距上沿切线只有0.795mm，且两单元之间还会遇到另一单元排母。这里是名义包络筛查，没有把它写成实际焊点已裂或实际刀具可达。

明确工序为B面SMT→F面SMT→支撑切断连接带并检查毛刺→THT逐点手工焊接，不手掰、不在装排针后分板。见[分板工序](depanel-process-notes.md)。此选择降低切割阶段紧邻排母/排针的限制；实际刀具、夹具、板弯/振动、碎屑和焊点状态仍需工厂过程，不凭距离推定应变合格。62704/62692原文继续使用已归档官方资料，web续开仍无正文，未伪称重新在线确认。

同时修正真正的文件不一致：上轮增加专门手焊计划后，panel-assembly-plan.csv及unit-reference-map.csv的12个THT条目仍继承“手焊或厂商通孔装配待确认”；现在两份CSV只改这12项Assembly字段为“分板后手工逐点焊接”，其余106行/所有其它字段不变。总ASSEMBLY-NOTES、制造JSON/说明/README也统一。旧20261103-tht包保留，当前20261103-assembly包SHA为46413368d6837e2b7f131f91f67a7f359d85bd663f88ff39f4a52a3b3de24194；[差异记录](depanel-package-comparison.json)确认13份Gerber/钻孔和3份位置CSV逐字节相同，最终kicad-happy Gerber复审仍4项既有告警，CAD没有改动。

### 前阶段THT工序补充与勘误

重新核62761发现详细工序/规格只写“后焊”，尚未明确采用手工逐点。**后续逐文件核实的勘误：旧包ASSEMBLY-NOTES.txt已明确排除整板波峰焊，因此“旧包完全未排除波峰”不成立。** 这次工作把分散约束和具体手焊方式统一到规格、工序和逐件计划，不是首次发现整板波峰禁用。原生59针对反面52个SMT的Fab框复核显示，6个THT连接器均存在5mm以内邻近件，最近J403.3到R703孔边/Fab框0.809mm。这属于设计工序选择，不是工厂已接受或焊接已通过。具体元件面/焊接面见[工序说明](tht-process-notes.md)与[12件/118针计划](tht-soldering-plan.csv)，逐针原始依据在[JSON](tht-soldering-plan.json)。手焊温度/时间、烙铁头可达性、热影响和焊点质量仍需实际过程，未随意填统一温度。

前阶段20261103-tht ZIP相对无后缀版新增3份工序附件、更新4份说明/规格，见[当时包差异](tht-package-comparison.json)。之后被当前20261103-assembly包取代，后者另加分板附件、统一CSV工序文字，见[当前包差异](depanel-package-comparison.json)。两次均保持13份Gerber/钻孔、原坐标/BOM/Paste；kicad-happy最终包[Gerber](gerbers-pcba-r18-assembly.json)仍是同4项已分类提示，几何未改不重跑无关全电路仿真。

当前本体间距筛查也已更新：[27对低于参考值](assembly-clearance-current/smt-layout-audit.json)，最小Fab框0.405mm，没有<0.3mm；不同网SMD铜隙未见<0.2mm，24处chip热连接保持。旧25对是早期源，不再作为当前统计。Fab框/按U位号分组不是精确实体或吸嘴测量，27对保留适用性评估，不以0.3mm筛查无命中宣称所有装配空间通过。原始资料重读也确认JST只要求应用评估，不能从公开文件凭空填SH统一回流峰值。

续查验证：[工序包与几何差异](tht-package-comparison.json)、[当前包完整性](completion-check.json)及[文档/语法检查](tht-documentation-check.json)通过，只读参考库未改。阅读旧remaining-smt目录的assembly-process-basis.md失败，确认工序说明实际位于后续专题后使用现行文件；未把不存在的文件当证据。一次合并补丁重复指定research.md被工具拒绝，拆成不重复目标后成功，旧包不覆写。本轮继续保持目标未完成：无制造/来料与实际工艺记录，没有新板可供功能或实装验收。

另补导出前的当前源身份检查：必须同时核候选及验证报告的source_pcb_sha256与current-review一致，防止主板更新后把旧拼板重新标为新源。[负对照](stale-export-negative-control.json)模拟不同当前SHA，在创建输出目录前被拒绝；实际当前身份满足，主板与已有交付包未改变。没有为验证该入口而重导已完成的制造包。

拼板验收必须同时检查原生连接、全项目规则复制、实际filled copper局部差异、制造导出的非Paste保持以及实际钢网/钻孔/CPL，不能只比较元件/走线数。输出绑定已扩至规则和边缘审计，真实负对照覆盖第二单元。r18另用9mm孔径规则哨兵得到199项，见[规则加载](panel-rule-loading/rules-loading.json)；这是故意违规的临时副本，不是交付板违规数。9个Python脚本语法、渲染脚本语法、61个相关文档链接、git diff --check与只读参考库状态检查通过，见[文档核对](documentation-check.json)。BOM/坐标/同源[审计](final-audit.json)和163孔[原生导出核对](drill-export-audit.json)通过。

高度仍按用户要求列可装配名义范围11.6～13.33mm，未选隔离柱；[机械依据](../归档扩展板机械适配复核/research.md)不含公差、线束、散热附件和头壳。实际工厂接单、来料与工艺记录、首板电气功能尚不存在，不提前填写通过。

续核工具记录：首个shell工作目录指向错误映射，git拒绝；随后按会话已存真实根路径恢复，只读失败未改设计。首次渲染库探查无cairosvg，使用已安装sharp完成原生SVG栅格化。新增孔比对最初直接用Python round，14个半微米边界值与Excellon舍入差1µm；改用既有审计同样的逐孔唯一匹配/0.001mm容差，实际最大偏差0.0006404mm，没有修改钻孔。复用Paste解析器读铜层被region拒绝，改专用flash中心提取，明确只核中心不冒充全部填铜CAM；四层862个原生铜焊盘中心全部对应。文档批量补丁曾因hunk不按原行序被拒绝，重新排序后成功，未用失败结果宣称更新。历史证据中的E:/Projects与旧用户名按原始记录保留，不改写成当前执行路径。所有本轮修改保留工作区，未commit/push。
