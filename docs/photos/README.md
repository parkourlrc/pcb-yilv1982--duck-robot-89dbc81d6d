# 硬件照片存档

- **2026-11-05 嘉立创工程方向确认**：用户提供[脱敏截图](../references/扩展板乙版降本/engineering-feedback/engineer-feedback-redacted-20261105.png)与[局部放大](../references/扩展板乙版降本/engineering-feedback/engineer-detail-20261105.png)，对象为B.0／84362651的MK701、Y701；收到日期2026-11-05，拍摄日期未知。原图含客户编号，另存本地Git忽略目录；原厂PDF页面、生成脚本及哈希见[核对报告](../references/扩展板乙版降本/engineering-feedback/research.md)。派生图已打开检查，只证明图面方向对应，不是实物贴装验收。

- **2026-11-05 Y10重新上传回执**：[脱敏截图](../references/扩展板乙版降本/layout-spacing/y10-upload-receipt-redacted-20261105.png)，本机嘉立创UI截图裁剪/拼接，已检查；用于证明新文件前缀、5片工艺、初步33元、等待审核，非实物验收。原始截图含账号/个人信息，仅保留于Git忽略目录，见[状态及来源](../references/扩展板乙版降本/layout-spacing/y10-quotation-status.md)。

- **2026-11-05 自主HAT B.0焊接空间图**：[最终正反面合并图](../references/扩展板乙版降本/layout-spacing/final-access-20261105.png)，由84362651源的[空间JSON](../references/扩展板乙版降本/route-234520/access.json)及[生成脚本](../../hardware/custom_hat/scripts/render_rev_b_solder_access.py)制作，已打开检查；两面统一正面投影，非实物照片/接线图/工厂放行。[旧r3图](../references/扩展板乙版降本/layout-spacing/placement-r3/access.png)仅保留中断候选追溯，存在占位重叠，不作生产依据。

- **2026-11-04 自主HAT Rev B.0生成图**：布局、铜层及原理图可视检查图见[研究图片索引](../references/扩展板乙版降本/research.md#图片与来源索引)。来源为本机KiCad/PDF渲染及原厂PDF，不是实物照片；旧极性截图已标为历史，现行装配尚未放行。

**受损照片待归档（2026-10-27）**：用户确认HAT R31拆除后两侧焊盘脱落，尚未提供当前受损近照。既有HAT照片与R31待核区域图是损伤前资料，不能作为修复飞线定位图；见[维修记录](../references/扩展板焊盘脱落修复/research.md)。

用户实拍硬件照片及派生标注图的统一索引。附件或缓存可能被清理，取得原文件后应及时归档；已在其他专题保存的原件直接链接。**原图与标注图分别保存，每次新增都登记来源、日期及用途。** 全部规则见 [AGENTS.md](../../AGENTS.md)。

## 登记表

自主HAT当前86654c03/r18（A.1）；旧r1～r17第二单元Power映射不足，图片仅历史，不用于制造。

2026-11-03生成并打开[r18正面](../references/扩展板邮票孔与电源修复/panel-r18-front.png)、[背面镜像](../references/扩展板邮票孔与电源修复/panel-r18-back.png)、[邮票孔局部](../references/扩展板邮票孔与电源修复/panel-r18-mouse-bites.png)；来源为KiCad原生拼板，非实物。2026-11-02生成且已打开的[BMI088桥线](../references/扩展板邮票孔与电源修复/bmi-bridge-detail.png)一并登记。SVG原件/哈希/镜像状态见[清单](../references/扩展板邮票孔与电源修复/image-manifest.json)，关联[研究](../references/扩展板邮票孔与电源修复/research.md)。

**2026-11-02 归档**：旧白色 V1.2 HAT 与 jyg9 GD32 单口 IMU 的历史照片已移入 [archive/](archive/README.md)（对应登记行链接已指向归档）。当前整机 HAT/IMU 为 kissqy hardware，实物照片待补拍登记。

| 文件 | 拍摄对象 | 收到日期 | 一句话说明 | 关联待办 |
|---|---|---|---|---|
| [U301四窗源图](../references/归档扩展板钢网分窗审查/buck-paste-front.png) | KiCad原生F.Paste/Fab派生，非实物 | 2026-11-02（生成） | b610f1dc，已打开；U301四窗69.63%。源图可见C307原Paste，实际制造导出排除，勿直接拿此源图当钢网交付 | [本轮报告](../references/归档扩展板钢网分窗审查/research.md) |
| [本轮原厂/拼板/装配图清单](../references/归档扩展板钢网分窗审查/image-manifest.json) | Diodes/ADI/TI原件页与KiCad派生 | 2026-11-02（生成） | 原厂页包括SO8EP铜、ADI分窗参考及TI100%反例；项目选择不冒充Diodes工艺。面板/单元图镜像状态及打开检查在清单 | [当前交付](../../hardware/custom_hat/release-review/README.md) |
| [TI修正后的B面钢网](../references/归档扩展板钢网与裸露焊盘/stencil-final-back.png) / [r13双联](../references/归档扩展板钢网与裸露焊盘/final/panel-r13-paste.png) | KiCad原生Paste/Fab派生，非实物 | 2026-11-02（生成） | 已打开，B面镜像；U701四窗/U702十六窗、可选中脚无Paste，J301 B面保持。主源最终4440b22f仅再修库说明，图形相同；双联同源 | [当前钢网报告](../references/归档扩展板钢网与裸露焊盘/research.md) |
| [TI原厂封装/钢网页清单](../references/归档扩展板钢网与裸露焊盘/image-manifest.json) | TI PDF派生与候选历史图 | 2026-11-02（生成） | TLV320AIC3104 p100–102、LP38691 p34–36及SLUA271；文件/原件SHA和打开状态登记。候选03–05圆角错误未采用，不将API返回当实际图形 | [原厂依据](../references/归档扩展板钢网与裸露焊盘/sources/reference-manifest.json) |
| [J301插接面及名义间距图](../references/归档扩展板机械适配复核/j301-and-spacing.png) / [原生B面](../references/归档扩展板机械适配复核/outward-power-back.png) | KiCad文件派生，非实物 | 2026-11-02（生成） | 当前9daf71d8，已打开；J301为B面，pin1在B端子图左侧；原生B图已镜像。间距表仅参考CAD/目录，不含线束和公差 | [当前机械报告](../references/归档扩展板机械适配复核/research.md) |
| [旧F面接口与Radxa参考投影](../references/归档扩展板机械适配复核/radxa-hat-projection.png) | 官方STEP派生＋旧96dc包络 | 2026-11-02（生成） | 原STEP日期2024-04-25，图已打开；红框仅为11.05mm名义情景，不是实际烧板/短路。J301已在新源转B；STEP非有效闭合BRep，未伪称实体布尔通过 | [官方ZIP/来源](../references/归档扩展板机械适配复核/sources-manifest.json) |
| [本轮其它机械图片清单](../references/归档扩展板机械适配复核/image-manifest.json) | 原厂JST尺寸页和r12派生 | 2026-11-02（生成） | 每幅来源/打开状态/镜像记录在清单；同源拼板与实际实物验收分开 | [工艺和间距依据](../references/归档扩展板机械适配复核/research.md) |
| [当前极性F](../references/归档扩展板极性与装配资料/polarity-front.png) / [B](../references/归档扩展板极性与装配资料/polarity-back.png) | KiCad原生Fab/Mask/丝印派生 | 2026-11-02（生成） | 源96dcce92，18项明确方向标记；已打开检查。B镜像为翻板视角，不对CSV再次镜像；非实物 | [当前报告](../references/归档扩展板极性与装配资料/research.md) |
| [r11 F](../references/归档扩展板极性与装配资料/panel-r11-front.png) / [B](../references/归档扩展板极性与装配资料/panel-r11-back.png) | KiCad拼板派生 | 2026-11-02（生成） | 已打开；85×82mm、方向标记复制，J301位号实际绘制角已修；B镜像，Fab的B2编号用于映射 | [当前拼板](../../hardware/custom_hat/panels/a1-smt-2up-20261102-r11/README.md) |
| [本轮原厂资料图清单](../references/归档扩展板极性与装配资料/image-manifest.json) | 原厂PDF页派生，非实物 | 2026-11-02（取得/渲染） | Vishay34213、Diodes TN1、AVX MLCC、JST SH与Handling页；具体来源/页码及打开状态记录在清单，不混同工作温度与回流条件 | [材料矩阵](../references/归档扩展板极性与装配资料/material-process-matrix.csv) |
| [最终源F铜](../references/归档扩展板贴片与层叠复核/final/final-front.png) / [最终C310 B铜](../references/归档扩展板贴片与层叠复核/final/c310-back.png) | KiCad原生派生，非实物 | 2026-11-02（生成） | 源153bd0db…，已打开；C305/C310热连接、1/K补标；B为顶视未镜像，不能当翻板装配图 | [本轮报告](../references/归档扩展板贴片与层叠复核/research.md) |
| [r9正面](../references/归档扩展板贴片与层叠复核/final/panel-r9-front.png) / [背面](../references/归档扩展板贴片与层叠复核/final/panel-r9-back.png) | KiCad原生Fab/丝印派生 | 2026-11-02（生成） | 当前153bd0db双联，85×82mm；已打开，B未镜像；第二单元Fab带B2映射，原丝印位号保持。用于版图核查，实际装配用正式镜像图/CPL | [r9](../../hardware/custom_hat/panels/a1-smt-2up-20261102-r9/README.md) |
| [嘉立创4层1oz选择器](../references/归档扩展板贴片与层叠复核/jlc-four-layer-1oz.jpg) | 官方网页截图，非实物 | 2026-11-02（取得） | 已打开，实际选择4层/1.6mm/内外1oz，JLC041611-7628外35/内30µm；完整表在同名visible.txt；不是下单或成品验收 | [结构依据](../references/归档扩展板贴片与层叠复核/stackup-design-basis.json) |
| [原厂资料页及历史候选图](../references/归档扩展板贴片与层叠复核/image-manifest.json) | TI/Diodes原厂PDF派生及KiCad历史图 | 2026-11-02（生成） | 每幅对应来源/页码和核验状态在清单；0263候选因C310吸锡风险撤出，保留原图；不作实物照片 | [工艺复核](../references/归档扩展板贴片与层叠复核/research.md) |
| [现行分层via盘r7拼板F](../references/归档扩展板音频芯片焊盘/panel-r7-front.png) / [B](../references/归档扩展板音频芯片焊盘/panel-r7-back.png) | KiCad原生派生，非实物 | 2026-11-02（生成） | 源3b1d903c…双联，均已打开；85×82mm及同源热焊盘/分层via尺寸保持，B采用统一顶视未镜像；不是实物/装配通过证明 | [当前制造候选](../../hardware/custom_hat/panels/a1-smt-2up-20261102-r7/README.md) |
| [U701分层via铜盘局部](../references/归档扩展板音频芯片焊盘/padstack-detail.png) / [原生SVG](../references/归档扩展板音频芯片焊盘/padstack-B.svg) | KiCad B.Cu/Mask派生，非实物 | 2026-11-02（生成） | 源3b1d903c…，已打开；B面via铜盘0.25mm包含原QFN land，另三层0.35mm，孔0.15mm；白圈为钻孔显示，成品须填孔盖铜；统一顶视、B未镜像 | [修复证据](../references/归档扩展板音频芯片焊盘/research.md) |
| [22热焊盘F铜](../references/归档扩展板热焊盘回写/thermal-top.png) / [B铜](../references/归档扩展板热焊盘回写/thermal-bottom.png) | KiCad原生导出，非实物 | 2026-11-02（生成） | b369f9fc历史采用检查点，均已打开；22个热阻臂0.25mm，C305/C310未改，后续源仍保留；同顶视、B未镜像 | [热焊盘采用](../references/归档扩展板热焊盘回写/research.md) |
| [热焊盘阶段r6拼板F](../references/归档扩展板热焊盘回写/panel-r6-front.png) / [B](../references/归档扩展板热焊盘回写/panel-r6-back.png) | KiCad派生历史拼板，非实物 | 2026-11-02（生成） | 均已打开，b369f9fc源两单元，已被3b1d903c同源r7取代；尺寸/工艺边布局沿用，B未镜像 | [现行拼板](../../hardware/custom_hat/panels/README.md) |
| [HAT双联拼板F预览](../references/归档扩展板贴片规范复查/panel-preview.png) / [B预览](../references/归档扩展板贴片规范复查/panel-back.png) | KiCad原生导出派生，非实物 | 2026-11-02（生成） | 85×82mm候选，源43b56588…；两图已打开，同一顶视坐标、B未镜像，不是翻板装配视图；8mm边、PFID/定位孔/邮票孔可见；未解决的单板设计项继续有效 | [SMT复查与候选](../references/归档扩展板贴片规范复查/research.md) |
| [嘉立创最小过孔规则截图](../references/归档扩展板嘉立创规则自查/user-jlc-via-dimensions.png) | 用户提供的官方工艺表截屏，非实物 | 2026-11-02（收到） | 原图已归档并打开核对；区分孔径/铜盘直径/单边环宽，网页要求“外径−内径≥0.1mm”不能误写成单边环宽≥0.1mm | [国内规则自查](../references/归档扩展板嘉立创规则自查/research.md) |
| [v0.3 IMU 发送端与总线测点图](../references/飞特策略模型上机核对/imu-v03-probe-map-20261101.png) | 新制 ScrapMeta v0.3 生产焊盘坐标图，非实物照片 | 2026-11-01（制作） | 来源为下单 Gerber 的 FlyingProbeTesting.json；元件面顶视、J2 在上；标 A=U6-2 TX、B/C=R6 两端、D=R3-2 OE#、G=U6-3 GND。未画铜线/焊锡，实际板朝向仍须核对；脚本 scripts/render-v03-probe-map-20261101.py，输出已打开验收；[来源与哈希](../references/飞特策略模型上机核对/imu-v03-probe-map-source-20261101.json) | [站姿坏帧发送端取证](../references/飞特策略模型上机核对/root-cause-investigation-20261101.md) |
| [A.1正面铜/丝印](../references/扩展板电路仿真工具/qwiic-pinout-20261031/qwiic-board-F.png) / [底面](../references/扩展板电路仿真工具/qwiic-pinout-20261031/qwiic-board-B.png) / [J502局部](../references/扩展板电路仿真工具/qwiic-pinout-20261031/qwiic-b-detail.png) | 原生KiCad派生，非实物 | 2026-10-31（生成） | 源90f27091…，已打开；B图镜像为翻板观察，针号不能从屏幕左右重编。保持元件/板框、局部改线及via移动0.1mm，板面标A.1 | [A.1修复](../references/扩展板电路仿真工具/qwiic-pinout-20261031/research.md) |
| [A.1传感器原理图](../references/扩展板电路仿真工具/qwiic-pinout-20261031/qwiic-schematic.png) / [J502针序局部](../references/扩展板电路仿真工具/qwiic-pinout-20261031/qwiic-schematic-detail.png) / [字段整理前](../references/扩展板电路仿真工具/qwiic-pinout-20261031/qwiic-schematic-before-label-tidy.png) | 原生PDF派生，非实物 | 2026-10-31（生成） | 已打开；pin1/2/3/4为GND/3V3/SDA/SCL，J502字段已移开。整理前图片只是显示问题历史，当时电气针序也已是A.1 | [针号/版本边界](../references/扩展板电路仿真工具/qwiic-pinout-20261031/research.md) |
| [A.1正面装配](../references/扩展板电路仿真工具/qwiic-pinout-20261031/assembly-front.png) / [底面装配](../references/扩展板电路仿真工具/qwiic-pinout-20261031/assembly-back.png) | 同版装配SVG派生，非实物 | 2026-10-31（生成） | 双面已打开；底面图镜像，CPL不再镜像；C307 DNP叉号保留，52 SMT+6 THT，值/MPN查同版BOM | [生产审查包](../../hardware/custom_hat/rev_a/production-20261031-qwiic-review/README.md) |
| [C307原锡膏开口](../references/扩展板电路仿真工具/qwiic-pinout-20261031/c307-paste-before.png) / [排除DNP后](../references/扩展板电路仿真工具/qwiic-pinout-20261031/c307-paste-after.png) | 原生F.Paste SVG局部，非实物 | 2026-10-31（生成） | 两图已打开；只删C307的两个开口，其它开口保留。before是源板默认绘图对照，不是当前应投用钢网；原铜/阻焊不删 | [钢网策略与逐项对照](../references/扩展板电路仿真工具/qwiic-pinout-20261031/research.md) |
| [SparkFun原理图PDF](../references/扩展板电路仿真工具/qwiic-pinout-20261031/sources/sparkfun-qwiic-schematic.pdf) / [直角接口页](../references/扩展板电路仿真工具/qwiic-pinout-20261031/sources/sparkfun-qwiic-p1.png) / [垂直接口页](../references/扩展板电路仿真工具/qwiic-pinout-20261031/sources/sparkfun-qwiic-p2.png) | 外部原图/渲染，非本机实物 | 2026-10-31（获取/生成） | 原作者SparkFun/M. Odichkov，图v10/2023-11-28，CC BY-SA 4.0；两页均已打开核1GND/2VCC/3SDA/4SCL，仅用于标准针序依据，不移植其传感器电路 | [来源与SHA](../references/扩展板电路仿真工具/qwiic-pinout-20261031/sources-and-scope.json) |
| [复位版F铜](../references/扩展板电路仿真工具/codec-reset-20261031/reset-board-F.Cu.png) / [B铜](../references/扩展板电路仿真工具/codec-reset-20261031/reset-board-B.Cu.png) / [In2铜](../references/扩展板电路仿真工具/codec-reset-20261031/reset-board-In2.Cu.png) | 自设计HAT原生SVG派生，非实物 | 2026-10-31（生成） | 源6fe440f3…；均已打开，铜层图保持同顶视坐标，B铜未镜像。Pin33复位线及3.3V补连已通过原连接/参考铜取样检查；不代表高频或硬件测试 | [修复及图源清单](../references/扩展板电路仿真工具/codec-reset-20261031/research.md) |
| [40P原理图](../references/扩展板电路仿真工具/codec-reset-20261031/radxa_40p-review.png) / [局部](../references/扩展板电路仿真工具/codec-reset-20261031/radxa_40p-detail.png) / [TTL原理图](../references/扩展板电路仿真工具/codec-reset-20261031/servo_ttl-review.png) / [局部](../references/扩展板电路仿真工具/codec-reset-20261031/servo_ttl-detail.png) | 原生PDF派生，非实物 | 2026-10-31（生成） | 已打开核Pin33/GPIO3_C3及MCLK Pin13；J101/TTL字段、VCC/OE/地/DATA标签不再重叠，DATA显式junction；同目录保存原生PDF和修改前原理图 | [图纸显示修复](../references/扩展板电路仿真工具/codec-reset-20261031/research.md) |
| [复位版正面装配图](../references/扩展板电路仿真工具/codec-reset-20261031/assembly-front.png) / [底面装配图](../references/扩展板电路仿真工具/codec-reset-20261031/assembly-back.png) | 同版装配SVG派生，非实物 | 2026-10-31（生成） | 源6fe440f3…，双面均已打开；底面装配图已镜像，CPL不再镜像；C307 DNP叉号保留，值/MPN查BOM，render-manifest.json绑定来源 | [同版生产审查包](../../hardware/custom_hat/rev_a/production-20261031-codec-reset-review/README.md) |
| [电源输入阶段标识](../references/扩展板电路仿真工具/power-acceptance-20261031/j301-input-final.png) / [正面装配图](../references/扩展板电路仿真工具/power-acceptance-20261031/assembly-front-final.png) / [底面装配图](../references/扩展板电路仿真工具/power-acceptance-20261031/assembly-back-final.png) / [初版紧邻标识](../references/扩展板电路仿真工具/power-acceptance-20261031/j301-input-tight.png) | 自设计HAT原生图派生，非实物 | 2026-10-31（生成） | 历史源70586fc6…，F元件面观察，右侧J301.1=2S+、.2=GND；标识继续有效，后续走线以复位版为准。底面装配图镜像，坐标不再镜像；初版仅留证，不作上电许可 | [输入与保护说明](../references/扩展板电路仿真工具/power-acceptance-20261031/power-interface.md) |
| [补偿网络模型图](../references/扩展板电路仿真工具/power-acceptance-20261031/compensation-network-check.png) / [原厂图27与Eq12裁片](../references/扩展板电路仿真工具/power-acceptance-20261031/ap64350-compensation-excerpt.png) | 计算曲线/手册派生，非实测 | 2026-10-31（生成） | 均已打开；原PDF页17与SHA在datasheet-source.json，模型用零DC扰动；图不含功率级，不能读为真实环路相位裕量。脚本plot_compensation_check.py，数值在compensation-ac.csv | [公式与模型边界](../references/扩展板电路仿真工具/power-acceptance-20261031/research.md) |
| [补偿选值公式裁片](../references/扩展板电路仿真工具/power-acceptance-20261031/ap64350-selection-excerpt.png) | AP64350原厂PDF第18页，非实测 | 2026-10-31（生成） | 已打开核对Eq17/18/19；裁图范围和源SHA登记于datasheet-source.json，示例方法不等于本板相位裕量 | [选值核对](../references/扩展板电路仿真工具/power-acceptance-20261031/research.md) |
| [电源标识初版正面图](../references/扩展板电路仿真工具/power-acceptance-20261031/assembly-front.png) / [初版底面图](../references/扩展板电路仿真工具/power-acceptance-20261031/assembly-back.png) | 3cc3c240…历史检查点，非实物 | 2026-10-31（生成） | 后续只拉开标识字距，现行使用70586fc6…图；这些过程图不再作为当前装配入口 | [阶段说明](../references/扩展板电路仿真工具/power-acceptance-20261031/label-spacing/research.md) |
| [原始含值预览](../references/扩展板电路仿真工具/power-acceptance-20261031/label-spacing/preview-detail.png) / [初版输入局部](../references/扩展板电路仿真工具/power-acceptance-20261031/j301-input-detail.png) | 过程预览，非实物 | 2026-10-31（生成） | 前者叠加Fab数值，不用于判断生产丝印；后者属3cc3c240…初版。现行清晰图见70586fc6…标识记录，保留过程不混用 | [标识阶段](../references/扩展板电路仿真工具/power-acceptance-20261031/label-spacing/research.md) |
| [现行贯通孔局部图](../references/扩展板电路仿真工具/npth-clearance-20261031/codec-pth-layout.png) / [F原图](../references/扩展板电路仿真工具/npth-clearance-20261031/codec-F.png) / [In1原图](../references/扩展板电路仿真工具/npth-clearance-20261031/codec-In1.png) / [B原图](../references/扩展板电路仿真工具/npth-clearance-20261031/codec-B.png) | 原生铜层图派生，非实物 | 2026-10-31（生成） | 源a65f2ad8…，render_codec_pth.py生成并打开；三层同顶视、B未镜像，图中孔圆为钻孔标记，成品要求填孔盖铜；不表示加工接受 | [现行规则复核](../references/扩展板电路仿真工具/npth-clearance-20261031/research.md) |
| [现行正面装配图](../references/扩展板电路仿真工具/npth-clearance-20261031/assembly-front.png) / [现行底面装配图](../references/扩展板电路仿真工具/npth-clearance-20261031/assembly-back.png) | 同版装配SVG渲染，非实物 | 2026-10-31（生成） | 源a65f2ad8…，均已打开检查；底面已镜像，CSV/CAM不再镜像；TP803仅在显示副本移位，值/MPN查BOM | [当前生产审查资料](../../hardware/custom_hat/rev_a/production-20261031-pth-clearance-review/README.md) |
| [贯通转换阶段图](../references/扩展板电路仿真工具/codec-pth-20261031/codec-pth-layout.png) / [F](../references/扩展板电路仿真工具/codec-pth-20261031/codec-F.png) / [In1](../references/扩展板电路仿真工具/codec-pth-20261031/codec-In1.png) / [B](../references/扩展板电路仿真工具/codec-pth-20261031/codec-B.png) | 历史原型规则阶段，非实物 | 2026-10-31（生成） | 源9eaffba7…，已打开；当时zone规则范围过宽，后续已退役，不用这组较大铺铜作现行回流改善证据 | [阶段与规则勘误](../references/扩展板电路仿真工具/codec-pth-20261031/research.md) |
| [制造文字阶段正面图](../references/扩展板电路仿真工具/manufacturer-rules-20261031/assembly-front.png) / [底面图](../references/扩展板电路仿真工具/manufacturer-rules-20261031/assembly-back.png) / [TP803旧叠字预览](../references/扩展板电路仿真工具/manufacturer-rules-20261031/assembly-before-tp803-front.png) | 历史c6c09b33…检查点，非实物 | 2026-10-31（生成） | 已逐面打开；后续源改为全贯通并修规则加载/范围，现行见a65f2ad8…图。底面镜像，CSV不再镜像 | [阶段复审](../references/扩展板电路仿真工具/manufacturer-rules-20261031/research.md) |
| [TTL本地去耦标注](../references/扩展板电路仿真工具/ttl-bypass-20261031/ttl-bypass-layout.png) / [原生B面SVG](../references/扩展板电路仿真工具/ttl-bypass-20261031/after-back.svg) / [U801局部](../references/扩展板电路仿真工具/ttl-bypass-20261031/ttl-1-detail.png) / [U802局部](../references/扩展板电路仿真工具/ttl-bypass-20261031/ttl-2-detail.png) | 自设计HAT文件派生，非实物 | 2026-10-31（生成） | render_ttl_bypass.py由原生SVG生成，已打开核对；B面顶视、未镜像，彩框/文字不是铜。C329/C330及地孔位置、线长边界见报告；源143a483d…，后续仅补板名丝印 | [TTL修复](../references/扩展板电路仿真工具/ttl-bypass-20261031/research.md) |
| [TTL原理图](../references/扩展板电路仿真工具/ttl-bypass-20261031/ttl-schematic.png) / [旁路局部](../references/扩展板电路仿真工具/ttl-bypass-20261031/ttl-schematic-detail.png) | 原理图派生，非实物 | 2026-10-31（生成） | 由同专题schematic-preview原生SVG渲染，已打开核对100nF、+3V3与POWER_GND标签及标注；后续丝印阶段未改原理图 | [手册/连接依据](../references/扩展板电路仿真工具/ttl-bypass-20261031/research.md) |
| [板名阶段正面装配图](../references/扩展板电路仿真工具/board-marking-20261031/assembly-front.png) / [底面装配图](../references/扩展板电路仿真工具/board-marking-20261031/assembly-back.png) / [板名局部](../references/扩展板电路仿真工具/board-marking-20261031/board-name-detail.png) | 历史原生装配SVG派生，非实物 | 2026-10-31（生成） | 源b06b1051…，已打开；后续字高/笔画与图形间距已加严，现行图见c6c09b33…记录。底面已镜像，CSV不再镜像，值/MPN查同版BOM | [阶段复审](../references/扩展板电路仿真工具/board-marking-20261031/research.md) |
| [TTL阶段正面装配图](../references/扩展板电路仿真工具/ttl-bypass-20261031/assembly-front.png) / [底面装配图](../references/扩展板电路仿真工具/ttl-bypass-20261031/assembly-back.png) / [修复前B面](../references/扩展板电路仿真工具/ttl-bypass-20261031/before-back.png) | 历史检查图，非实物 | 2026-10-31（生成） | 前两图为加板名丝印前的143a483d…检查点；before-back为d6c72fac…局部，均已打开。现行装配以b06b1051…图为准，旧图不覆盖原始证据 | [差异与失败记录](../references/扩展板电路仿真工具/ttl-bypass-20261031/research.md) |
| [功放局部去耦标注](../references/扩展板电路仿真工具/amp-decoupling-20261031/amp-decoupling-review.png) / [F原图](../references/扩展板电路仿真工具/amp-decoupling-20261031/board-F.png) / [B原图](../references/扩展板电路仿真工具/amp-decoupling-20261031/board-B.png) | 自设计HAT原生图派生，非实物 | 2026-10-31（生成） | 原图/标注图均已打开核对；B未镜像、两面同顶视坐标，彩框/圆不是铜；C323/C328在F，U803在B，平面线长另计通孔。render_amplifier_decoupling.py生成；源d6c72fac… | [功放复审](../references/扩展板电路仿真工具/amp-decoupling-20261031/research.md) |
| [音频原理图](../references/扩展板电路仿真工具/amp-decoupling-20261031/audio-schematic.png) / [C328局部](../references/扩展板电路仿真工具/amp-decoupling-20261031/bypass-schematic-detail.png) | 同版原理图派生，非实物 | 2026-10-31（生成） | 已打开核连线、说明与阻容标注；当前SVG在schematic-preview-readable-final。早期根页、透明线/文字冲突预览仅失败证据，不用于判定通过 | [显示问题及修复边界](../references/扩展板电路仿真工具/amp-decoupling-20261031/research.md) |
| [正面装配定位图](../references/扩展板电路仿真工具/amp-decoupling-20261031/assembly-front.png) / [底面装配定位图](../references/扩展板电路仿真工具/amp-decoupling-20261031/assembly-back.png) | 原生Fab/Silk定位图，非实物 | 2026-10-31（生成） | 已逐面打开核位号与C307叉号；**底面图已镜像，CSV不得再镜像**。render_assembly_views.py用显示副本隐藏值、去重/补显位号，源值/网络/几何不变；值与MPN查BOM，原值拥挤图保留raw SVG | [装配资料与未放行边界](../references/扩展板电路仿真工具/amp-decoupling-20261031/research.md) |
| [主控5V路径对照](../references/扩展板电路仿真工具/five-volt-paths-20261031/five-volt-path-review.png) / [In1原图](../references/扩展板电路仿真工具/five-volt-paths-20261031/board-In1.png) / [In2原图](../references/扩展板电路仿真工具/five-volt-paths-20261031/board-In2.png) | 自设计HAT文件派生，非实物，历史检查点 | 2026-10-31（生成） | 对照/原生层图均已打开核查；该主干改动保持，整板以新功放检查点为准；源af8da97f→0fd6c689…，不是电压/温升实测 | [5V路径审查](../references/扩展板电路仿真工具/five-volt-paths-20261031/research.md) |
| [Radxa V1.11电源页22](../references/扩展板电路仿真工具/five-volt-paths-20261031/sources/radxa-v111-p22.png) / [既存40P页20](../references/扩展板电路仿真工具/metadata-repair-20261030/sources/radxa-page20.png) | 官方图纸派生，非用户实物 | 2026-10-31（复核/新增页22图） | 两页已打开核针2/4与USB VBUS同网及下游R107；原PDF复用旧归档，SHA/URL见radxa-evidence.json。不能据此识别用户板卡版本或许可双供 | [供电边界依据](../references/扩展板电路仿真工具/five-volt-paths-20261031/research.md) |
| [主电流路径加宽对照](../references/扩展板电路仿真工具/power-paths-20261031/power-path-review.png) / [In1原图](../references/扩展板电路仿真工具/power-paths-20261031/board-In1.png) / [B原图](../references/扩展板电路仿真工具/power-paths-20261031/board-B.png) | 自设计HAT文件派生，非实物，历史检查点 | 2026-10-31（生成） | 对照图和原生层图均已打开核查；入口/舵机局部改动继续保留，整体内层以新5V检查点为准。源70d00bf6→af8da97f…；不作温升/整板额定验证 | [电流路径审查](../references/扩展板电路仿真工具/power-paths-20261031/research.md) |
| [TI方阻表p9](../references/扩展板电路仿真工具/power-paths-20261031/sources/ti-smps-layout-p9.png) / [Radxa电源规格PDF p6](../references/扩展板电路仿真工具/power-paths-20261031/sources/radxa-zero3w-brief-p6.png) | 外部厂商资料，非本机实测 | 2026-10-31（下载/提取） | 原PDF/文本/SHA均保留，两参数页已目视核对；collect_power_path_sources.py生成。Radxa p2目录图仅归档，不作参数证据；新JST直链404已记录 | [来源、适用边界与模型](../references/扩展板电路仿真工具/power-paths-20261031/research.md) |
| [I2S参考地铜前后对照](../references/扩展板电路仿真工具/i2s-reference-stitch-20261031/reference-stitch-review.png) | 自设计HAT原生填铜轮廓派生，非实物，历史检查点 | 2026-10-31（生成） | before/after SVG、PNG保留并通过对照图打开核验；紫线是In1 LRCK投影，绿色为F地，白色不代表无其它铜。该局部改动继续保留；源fda50c80→70d00bf6…，不能作EMI实测 | [地铜修复审查](../references/扩展板电路仿真工具/i2s-reference-stitch-20261031/research.md) |
| [LDO局部回路标注](../references/扩展板电路仿真工具/ldo-capacitors-20261031/ldo-layout-review.png) / [B原图](../references/扩展板电路仿真工具/ldo-capacitors-20261031/board-B.png) / [F原图](../references/扩展板电路仿真工具/ldo-capacitors-20261031/board-F.png) | 自设计HAT，非实物，历史检查点 | 2026-10-31（生成） | F/B与标注图已打开核对，B未镜像；render_ldo_review.py标C308/C309/R703/U702。该电源局部布局继续保留，整板已由后续地铜检查点更新；源哈希fda50c80…，不是稳定性/实装验证 | [LDO检查点](../references/扩展板电路仿真工具/ldo-capacitors-20261031/research.md) |
| [电容升级F图](../references/扩展板电路仿真工具/capacitor-upgrade-20261031/board-F.png) / [B图](../references/扩展板电路仿真工具/capacitor-upgrade-20261031/board-B.png) | 自设计HAT，非实物，历史检查点 | 2026-10-31（生成） | 同版KiCad SVG及PNG均保留，F/B已打开核对；B未镜像，四颗1210电容与0.6mm输出支线已改。源哈希818becfd…；LDO部分以后续图为准，不是实装/热测试 | [电容升级检查点](../references/扩展板电路仿真工具/capacitor-upgrade-20261031/research.md) |
| [控制回路布局标注](../references/扩展板电路仿真工具/buck-control-20261031/control-layout-review.png) / [F原图](../references/扩展板电路仿真工具/buck-control-20261031/board-F.png) / [B原图](../references/扩展板电路仿真工具/buck-control-20261031/board-B.png) | 自设计HAT，非实物，历史检查点 | 2026-10-31（生成） | 标注图与F局部已打开核对；FB/COMP布局保留，电容部分以后续升级图为准。F/B同顶视坐标、B未镜像，源哈希及render_buck_control_annotations.py见专题；不作稳定性/噪声实测证据 | [反馈/补偿修复](../references/扩展板电路仿真工具/buck-control-20261031/research.md) |
| [电容逐料号PDF与模型图](../references/扩展板电路仿真工具/capacitor-models-20261031/research.md) | KEMET/YAGEO原厂典型模拟图，非实物测量 | 2026-10-31（下载/提取） | sources与plot-manifest.json列全部原生图；用于结论的DC偏压/ESR图、部分规格页及AP64350 p17已打开核对，其余频率/纹波图仅归档。extract_capacitor_plots.py直接提取，1210与LDO2.2µF方案均已采用；典型模型不是实测或保证下限 | [模型边界与下一步](../references/扩展板电路仿真工具/capacitor-models-20261031/research.md) |
| [Buck布局标注图](../references/扩展板电路仿真工具/buck-thermal-20261031/thermal-layout-review.png) / [F原生图](../references/扩展板电路仿真工具/buck-thermal-20261031/board-F.png) / [B原生图](../references/扩展板电路仿真工具/buck-thermal-20261031/board-B.png) | 自设计HAT，非实物 | 2026-10-31（生成） | 均已打开核对；标注C303、C308和5个地热孔，F/B同顶视坐标、B未镜像。原始SVG及局部PNG保留，render_i2c_review.py与render_buck_thermal_annotations.py生成；源SHA见专题；标的是设计与制造要求，非测温或填孔实物证据 | [热通道/去耦修复](../references/扩展板电路仿真工具/buck-thermal-20261031/research.md) |
| [全量MPN版F图](../references/扩展板电路仿真工具/final-bom-20261031/board-F.png) / [B图](../references/扩展板电路仿真工具/final-bom-20261031/board-B.png) | 自设计HAT，非实拍 | 2026-10-31（生成） | 原生SVG渲染，已打开核对；底面未镜像，L301/R309厂家焊盘及3个via/音频支线改变有同版数据，脚本render_i2c_review.py；不作为热/噪声或实物验收 | [全量料号检查点](../references/扩展板电路仿真工具/final-bom-20261031/research.md) |
| [JST/电感/跳线资料页](../references/扩展板电路仿真工具/final-bom-20261031/research.md#sources--acquisition-failures) | 原厂PDF与授权目录镜像，非实拍 | 2026-10-31（取得/渲染） | sources内JST SH p1/2、官方目录p35/36、Vishay34315 p2/4、30192 p1/2等已打开核对；SH焊盘局部放大另存。原PDF/哈希和collect_final_bom_sources.py保留；未采用的Bourns/DZ-11/目录无关页不作选型结论 | [尺寸和额定依据](../references/扩展板电路仿真工具/final-bom-20261031/research.md) |
| [环宽修复F层](../references/扩展板电路仿真工具/annular-rings-20261031/board-F.png) / [B层](../references/扩展板电路仿真工具/annular-rings-20261031/board-B.png) | 自设计HAT，非实拍 | 2026-10-31（生成） | KiCad原生SVG渲染，底面未镜像，源SHA和23个via扩大/6个移动/MCLK绕线/新增地孔数据见专题；用于文件布局检查，不作实物/制造验收；render_i2c_review.py生成 | [环宽修复](../references/扩展板电路仿真工具/annular-rings-20261031/research.md) |
| [J101修复F图](../references/扩展板电路仿真工具/connectors-20261031/board-F.png) / [原厂图页目录](../references/扩展板电路仿真工具/connectors-20261031/research.md) | HAT与Samtec/Würth资料，非实拍 | 2026-10-31（生成/下载） | J101原生图已打开检查；sources内SSW目录/钻孔/mkt第1页、TSW目录1/2页及钻孔/mkt第1页、Würth M2.5第1页均已打开核对。原PDF和渲染脚本保留；H1/H2排母侧≤4.5mm圆柱头且无垫圈为新板设计约束，未实装 | [连接器修复](../references/扩展板电路仿真工具/connectors-20261031/research.md) |
| [电容/TVS厂商资料页组](../references/扩展板电路仿真工具/bom-passives-20261031/research.md#sources--failure-record) | KEMET、KYOCERA AVX、Vishay原厂PDF，非实拍 | 2026-10-31（下载/渲染） | 同专题sources中X7R p2/5、X5R p1/2/4/5/6、C0G p3、SMBJ p2/4/5、WSLP p2已打开核对；原PDF保留，1.5倍整页渲染，由collect_bom_sources.py生成。不作实物验收 | [物料选型](../references/扩展板电路仿真工具/bom-passives-20261031/research.md) |
| [电容改孔局部图](../references/扩展板电路仿真工具/cap-vias-20261031/cap-vias-detail.png) / [F层](../references/扩展板电路仿真工具/cap-vias-20261031/board-F.png) / [B层](../references/扩展板电路仿真工具/cap-vias-20261031/board-B.png) | 自设计HAT，非实拍 | 2026-10-31（生成） | KiCad原生SVG经PyMuPDF渲染，底面未镜像、无新增标注；局部已打开检查，源SHA256与生成脚本参数见专题；不作热/寄生/装配验证 | [C305/C309盘中孔修复](../references/扩展板电路仿真工具/cap-vias-20261031/research.md) |
| [上拉局部图](../references/扩展板电路仿真工具/i2c-pullups-20261031/pullups-detail.png) / [顶层图](../references/扩展板电路仿真工具/i2c-pullups-20261031/board-F.png) / [底层图](../references/扩展板电路仿真工具/i2c-pullups-20261031/board-B.png) | 自设计HAT Rev A，非实物照片 | 2026-10-31（生成） | KiCad原生SVG及PyMuPDF派生，F/B同一顶视坐标、底面未镜像；R501/R502局部已打开核对，脚本hardware/custom_hat/scripts/render_i2c_review.py，源PCB哈希见专题；不作实物/工艺验收 | [I2C5修复](../references/扩展板电路仿真工具/i2c-pullups-20261031/research.md) |
| [Vishay订货页](../references/扩展板电路仿真工具/i2c-pullups-20261031/sources/vishay-dcrcwe3-p3.png) / [TI上拉计算页](../references/扩展板电路仿真工具/i2c-pullups-20261031/sources/ti-slva689-p3.png) | 厂商文档，非实拍 | 2026-10-31（下载/渲染） | 同目录PDF第3页1.5倍完整渲染，已打开核对；Vishay第1页另存，仅作额定参考；来源哈希及脚本见专题 | [电阻选型与计算](../references/扩展板电路仿真工具/i2c-pullups-20261031/research.md) |
| [Radxa GPIO页](../references/扩展板电路仿真工具/metadata-repair-20261030/sources/radxa-page11.png) / [40P页](../references/扩展板电路仿真工具/metadata-repair-20261030/sources/radxa-page20.png) | Radxa ZERO 3W V1.11官方图纸，非实拍 | 2026-10-30（下载及渲染） | 同目录官方PDF第11/20页以PyMuPDF 2倍整页渲染，已打开检查；29/31的I2C5与R52/R53所在I2C3分开核对，不代表实物修订完全一致 | [I2C5上拉证据](../references/扩展板电路仿真工具/metadata-repair-20261030/research.md) |
| [Radxa ZERO 3W 40P 原理图页](../references/惯性单元输入电压复核/sources/radxa-zero3w-connector-20.png) | 官方 V1.11 CONNECTOR 第20页 | 2026-10-31（制作） | Poppler 从官方 PDF 整页渲染，已打开核对 CON1 pin2/pin4 同属 +5V_INPUT；不是本机实物图，不代替针位实物核对；原件同专题 sources 内 | [pin4/DAPLink 两类故障分析](../references/惯性单元输入电压复核/research.md) |
| [v0.3 原理图整页](../references/惯性单元输入电压复核/sources/imu-v03-schematic.png) | ScrapMeta v0.3 导出图，非实物照片 | 2026-10-31（制作） | 本轮从归档原理图 PDF 用 Poppler 生成，已打开核对 VIN/EN/3V3/DATA；不把图纸脚号当作插合视角 | [电压复核](../references/惯性单元输入电压复核/research.md) |
| [AP2210 p4](../references/惯性单元输入电压复核/sources/AP2210-page04.png) / [p11](../references/惯性单元输入电压复核/sources/AP2210-page11.png) / [p12](../references/惯性单元输入电压复核/sources/AP2210-page12.png)；[台舟 U6 p1](../references/惯性单元输入电压复核/sources/techpublic-page1.png) / [p2](../references/惯性单元输入电压复核/sources/techpublic-page2.png) / [p3](../references/惯性单元输入电压复核/sources/techpublic-page3.png) | 原厂参数页渲染 | 2026-10-31（制作） | PDF 原件同专题 sources 内；已逐页查看，AP2210 VIN/EN 推荐 13.2V、绝对最大 15V；台舟 U6 供电规格不等于 VBATT 规格 | 同上 |
| [kissqy R33旁路候选点](./kissqy-hat-r33-bypass-reference-20261027.png) | kissqy HAT REVA参考PCB，非白色V1.2实物 | 2026-10-27（制作） | 左为10-07工程原预览，右由两版已核PAD/LINE坐标重绘；A=R32 pad2，B=TH1 pad1，连线等效跨过R33并保留TH1。顶视40P在上、舵机口在左；两点、型号/网名与脚号已核，不能用于直接指认用户焊点。脚本`scripts/inspect-kissqy-hat-bypass-20261027.py`；最终图已打开检查 | [证据、坐标与版型限制](../references/扩展板焊盘脱落修复/research.md#kissqy-bypass-points-20261027) |
| [kissqy 10-07 PCB预览](../schematics/kissqy-hat-reva-reference/pcb-preview-2026-10-07.webp) / [10-15 PCB预览](../schematics/kissqy-hat-reva-reference/pcb-preview-2026-10-15.webp) | 原EPRO2内嵌PCB预览 | 2026-10-27（提取） | 来源为kissqy固定提交7c5fba9的两个工程，原成员直接提取、未改写；非用户照片，日期不是用户拍摄日期；两版已打开对照 | [原件、哈希与来源](../schematics/kissqy-hat-reva-reference/README.md) |
| [IMU R31/R5/F1 定位标注](archive/imu-gd32-single-port-20261014/imu-single-port-r31-r5-f1-location-20261027.png) / [无标注局部放大](archive/imu-gd32-single-port-20261014/imu-single-port-data-front-end-crop-20261027.png) | 当前单 3P GD32 IMU，元件面右下通信前端 | 2026-10-27（制作） | 源为 10-14 用户原图 `imu-board-b-20261014-b.jpg`；元件面朝向观察者、白座朝右，未旋转/镜像。红框 R31、黄框 R5、蓝框 F1（PTC 保险丝）；照片丝印与公开 PCB 布局交叉核对。R5 表面可见 510；照片本身不确认 R31 阻值/F1 参数，用户随后已补[在板测阻](../references/扩展板双口惯性缺答复核/research.md#imu-resistance-measured-20261027)；不标针序。脚本 `scripts/annotate-imu-data-components-20261027.py`，原图保留，输出均已打开核框 | [定位依据、坐标与限制](../references/扩展板双口惯性缺答复核/research.md#imu-photo-components-20261027) |
| [供电/地修复对照](../references/扩展板电路仿真工具/power-repair-20261030/power-route-review.png) / [中间检查草图](../references/扩展板电路仿真工具/power-repair-20261030/inspection-current.png) | 自设计HAT Rev A，非实物照片 | 2026-10-30（生成） | 前后PCB几何派生，顶视坐标、底层未镜像，焊盘外框近似、未显示铺铜；正式图已打开复核。黄色+3V3、绿色地。旧中间草图局部截断仅追溯。脚本scripts/render-hat-power-repair.py，源PCB与geometry同专题保留。不作载流/制造/实物验收 | [修复记录](../references/扩展板电路仿真工具/power-repair-20261030/research.md) |
| [I2S路径与扇出对照](../references/扩展板电路仿真工具/i2s-sdo-repair-20261030/i2s-route-review.png) / [早期检查草图](../references/扩展板电路仿真工具/i2s-sdo-repair-20261030/inspection.png) | 自设计HAT Rev A，非实物照片 | 2026-10-30（生成） | 前后PCB几何派生，F/B/In1同一顶视坐标，底层未镜像；焊盘外框近似、未画铺铜。正式图已打开检查；旧草图网格标注不完整仅追溯。脚本scripts/render-hat-i2s-repair.py，源PCB/geometry同目录保留。不作时序/制造/上电放行依据 | [I2S修复证据](../references/扩展板电路仿真工具/i2s-sdo-repair-20261030/research.md) |
| [J506修复前后底层对照](../references/扩展板电路仿真工具/j506-repair-20261030/j506-before-after.png) / [早期检查草图](../references/扩展板电路仿真工具/j506-repair-20261030/before-inspection.png) | 自设计HAT Rev A，非实物照片 | 2026-10-30（生成） | 当前前后PCB几何派生；同一顶视坐标、底层未镜像，焊盘外接框近似、未绘铺铜。正式图已打开检查；早期草图标注不完整，仅追溯。脚本scripts/render-hat-j506-repair.py，geometry和PCB快照同目录保存。不作接线/制造放行依据 | [修复证据](../references/扩展板电路仿真工具/j506-repair-20261030/research.md) |
| [U501修复前后铜几何](../references/扩展板电路仿真工具/u501-repair-20261030/u501-before-after.png) | 自设计HAT Rev A，非实物照片 | 2026-10-30（生成） | 由前后PCB提取的geometry JSON生成；F/B按同一顶视坐标，底层未镜像，焊盘外接框近似，未画填充铜与内层。红色为移除的2短线+1过孔；已打开核对。脚本为scripts/render-hat-u501-repair.py，原前后PCB及JSON均保留，不作制造/接线放行依据 | [修复证据](../references/扩展板电路仿真工具/u501-repair-20261030/research.md) |
| [HAT 审计厂商图页组](../references/扩展板电路仿真工具/audit-20261029/review.md#5-证据与来源) | AP64350 与 BMI088 手册 | 2026-10-29（取得/渲染） | AP64350第3/22/24页、BMI088第52/53/55页共6张PNG，110dpi整页，无标注；原厂PDF与图像同目录保留，均已打开核对。用于引脚/焊盘/布局复核，非本机实拍，不作上电依据 | [HAT修复方案](../specs/20261028-custom-hat/recovery-plan.md) |
| [Murata PRG 型号编码页](../references/扩展板双口惯性缺答复核/sources/murata-prg-series-r31-20261027-p3.png) / [规格表页](../references/扩展板双口惯性缺答复核/sources/murata-prg-series-r31-20261027-p4.png) | HAT 图中 F1 料号的厂商参考，非本机测量 | 2026-10-27（取得/渲染） | 来源为同目录 Murata PRG PDF 第 3/4 页；PyMuPDF 1.5 倍整页渲染，无裁剪标注，已打开检查。PRG18BB101MB1RB 标称 25℃ 100Ω±20%，与 R31 分开识别，实装待核 | [R31 作用与来源](../references/扩展板双口惯性缺答复核/research.md#r31-function-20261027) |
| [用户圈选原图](archive/hat-v1.2-white-20261010/hat-resistor-user-circle-20261027.png) / [局部放大](archive/hat-v1.2-white-20261010/hat-resistor-user-circle-crop-20261027.png) | 用户确认 HAT 背面圈选电阻，照片自身未显示版本号 | 2026-10-27（收到/放大） | 用户提供带橙圈原图，拍摄日期未知；后续确认作者为 ScrapMeta，并转述其建议检查圈选电阻是否为 0Ω，否则更换或短接。**[用户确认] 圈选电阻为 HAT R31；当前阻值待核**。位号依据为用户后续确认，不是照片辨字。局部按原方向最近邻放大，未镜像，已打开核对；未建立与 C1/D1 图纸的逐件对应。该建议早于同日后续拆除造成焊盘损伤，原图作为历史保留；不作为现行改阻指令，成功修复效果未核 | [作者建议、来源与限制](../references/扩展板双口惯性缺答复核/research.md#author-bug-search-20261027) |
| [官方 C1 R33/TH1 参考标注](archive/hat-v1.2-white-20261010/hat-c1-r33-reference-20261027.png) | Pollen HAT C1，非白色 V1.2 实物定位 | 2026-10-27（制作） | 源为 ScrapMeta 归档的 C1 背面 CAD 截图；红框 R33=150Ω，蓝框 TH1=100R thermistor，仅适用参考版。裁剪/等比放大、未镜像，已打开核框；脚本 `scripts/render-hat-c1-reference-20261027.py` | [PCB 来源链与版本限制](../references/扩展板双口惯性缺答复核/research.md#pcb-source-search-20261027) |
| [C1 CAD 正面](../references/扩展板双口惯性缺答复核/pcb-search/scrapmeta-wiki--assets--pcb--hat-3d-front-2026-09-04.png) / [背面](../references/扩展板双口惯性缺答复核/pcb-search/scrapmeta-wiki--assets--pcb--hat-3d-back-2026-09-04.png) | 官方 C1 CAD 截图原件 | 2026-10-27（取得） | 外部来源 ScrapMeta 固定提交 `db04d32`；原始文件名日期沿用上游，不是用户实拍。图物对应待核，原件不改 | 同上 |
| [C1 PCB 整页](../schematics/pollen-hat-pcb-reference/c1-pcb-page1.png) / [D1 装配正面](../schematics/pollen-hat-pcb-reference/d1-ass-page1.png) / [D1 装配背面](../schematics/pollen-hat-pcb-reference/d1-ass-page2.png) | 官方生产 PDF 的查看用渲染 | 2026-10-27（制作） | Poppler `pdftoppm` 渲染同目录对应 PDF；C1 单页、D1 装配第 1/2 页，已完整打开核对，不是本机 V1.2 图 | [图纸档案](../schematics/pollen-hat-pcb-reference/README.md) |
| [HAT R31 待核区域](archive/hat-v1.2-white-20261010/hat-v1.2-r31-search-area-20261027.png) / [无标注局部放大](archive/hat-v1.2-white-20261010/hat-v1.2-data-region-crop-20261027.png) | HAT V1.2 背面舵机接口附近 | 2026-10-27（制作） | 用户要求在既有照片定位 DATA 串阻；源为 10-10 收到的 `hat-v1.2-back.jpg`，按 EXIF 转正、未镜像。**仅圈待核范围，未识别单颗 R31 的位号/阻值/网络**；红框不是拆焊目标。生成脚本 `scripts/annotate-hat-r31-search-20261027.py`，最终图已打开检查 | [定位依据与限制](../references/扩展板双口惯性缺答复核/research.md#photo-location-20261027) |
| [HAT DATA 路径对比](../references/扩展板双口惯性缺答复核/hat-data-path-comparison.png) | 社区 V1.0 / 官方 D1 原理图派生对比 | 2026-10-27（制作） | 本轮制作；源为归档社区 PDF 第 4 页、官方固定提交生产 PDF 第 4 页。红框 DATA 串阻、蓝框共总线接口，图纸针序不等于照片方向；已打开核框，实物 V1.2 阻值未核。脚本 `scripts/render-hat-bus-review-20261027.py` | [缺答原理图分析](../references/扩展板双口惯性缺答复核/research.md) |
| [社区原理图局部](../references/扩展板双口惯性缺答复核/hat-servo-crop.png) / [官方原理图整页](../references/扩展板双口惯性缺答复核/sources/upstream-servo-page.png) | HAT DATA 连线核对 | 2026-10-27（制作） | 前者裁自已有 `sch/page4.png`，后者由本轮归档官方 PDF 渲染；原图保留，不是用户新照片，不作 V1.2 接线放行 | 同上 |
| [TI 125 参数页](../references/扩展板双口惯性缺答复核/sources/sn74lvc1g125-ti-p5.png) / [真值表页](../references/扩展板双口惯性缺答复核/sources/sn74lvc1g125-ti-p11.png)；[126 参数页](../references/扩展板双口惯性缺答复核/sources/sn74lvc1g126-ti-p5.png) / [真值表页](../references/扩展板双口惯性缺答复核/sources/sn74lvc1g126-ti-p11.png) | SN74LVC1G125/126 原厂资料页面 | 2026-10-27（制作） | 本轮从 TI 原厂 PDF 渲染第 5/11 页，已完整目视核对；同型号参考，非本机贴装厂商鉴定 | 同上 |
| [multimeter-delixi-6000counts.jpg](./multimeter-delixi-6000counts.jpg) | 万用表（德力西） | 2026-10-09 | 6000 位手动量程数字万用表，本项目的电测工具 | 降压模块实测、banana_pcb 核极性 |
| [dc-power-supply-delixi-dlx-30v10amf.jpg](./dc-power-supply-delixi-dlx-30v10amf.jpg) | 直流稳压电源（德力西） | 2026-10-10 | DLX-30V10AMF 可调电源，30V/10A 上限 | 降压模块输入下限扫描、首次上电限流保护 |
| [buck-module-xt60.jpg](./buck-module-xt60.jpg) | 黑色降压模块原件 | 2026-10-10 | XT60 输入、选压焊盘 5/6/7V（无电位器） | 输入下限扫描、输出档位确认 |
| [buck-module-xt60-annotated.jpg](./buck-module-xt60-annotated.jpg) | ↑ 的元件标注版 | 2026-10-10 | v2（实测后勘误）：10 处元件编号 + 图例，⑧=3P 排针⑨=PWR OUT 红塑 2P；脚本 `scripts/annotate_buck_module.py` | 对照实物讲解/测试接线 |
| [buck-module-xt60-back.jpg](./buck-module-xt60-back.jpg) | 降压模块背面 | 2026-10-10 | 板名 BUS SERVO POWER SUPPLY V1.3（By 造物の乐趣），背面有 VOLT_SEL 选压焊盘/排针焊点/二维码 | 确认板子身份与接口定义 |
| [buck-module-xt60-back-annotated.jpg](./buck-module-xt60-back-annotated.jpg) | ↑ 的接口标注版 | 2026-10-10 | v4（勘误无 DC 母座）：① 金色圆孔（疑安装孔）② 二维码 ③ XT60 焊点 ④ VOLT_SEL 焊盘（改焊处）⑤ PWR OUT 焊点 ⑥ 3P 排针焊点 ⑦ 安装孔 | 实测/改焊时对照 |
| [waveshare-bus-servo-adapter-a.jpg](./waveshare-bus-servo-adapter-a.jpg) | 微雪总线转接板正面 | 2026-10-10 | Bus Servo Adapter (A) v1.1，双舵机口 + UART 排针 + USB-C + DC 母座/端子 | 台架总线调试接线对照 |
| [waveshare-bus-servo-adapter-a-annotated.jpg](./waveshare-bus-servo-adapter-a-annotated.jpg) | ↑ 的元件标注版 | 2026-10-10 | 7 处标注 + 用法要点；脚本 `scripts/annotate-waveshare-adapter.py` | 台架接线/模式跳线对照 |
| [hat-v1.2-front.jpg](archive/hat-v1.2-white-20261010/hat-v1.2-front.jpg) | HAT 正面 | 2026-10-10 | 实物丝印 **V1.2**（此前档案误记 V1.1）；舵机口×2、Qwiic×4、扬声器/麦克风座群、圆柱电容（标记 10 / 50V） | 图物差异核对 |
| [hat-v1.2-back.jpg](archive/hat-v1.2-white-20261010/hat-v1.2-back.jpg) | HAT 背面 | 2026-10-10 | **F303 类 MCU（V1.0 原理图无此件）**、PAM8406、40P 排母、圆形焊盘×8 | 索取 V1.2 原理图 |
| [hat-v1.2-front-annotated.jpg](archive/hat-v1.2-white-20261010/hat-v1.2-front-annotated.jpg) | 历史正面标注 | 2026-10-10 | **过期，不用于接线**：含“超级电容”等错误；旧脚本 `scripts/annotate-hat.py` 亦需修订后再用 | 现行接口识别见下方复核图 |
| [hat-v1.2-back-annotated.jpg](archive/hat-v1.2-white-20261010/hat-v1.2-back-annotated.jpg) | 历史背面标注 | 2026-10-10 | **过期，不用于接线**：八焊盘不能认作独立电池入口 | 现行接口识别见下方复核图 |
| [imu-ldo-location.png](./imu-ldo-location.png) | IMU 板 U3 定位及放大图 | 2026-10-10（制作） | 本会话生成，源图为下行的用户实物标注原件；去掉错误的 5.5V 上限说明，按设计识别 AP2210K-3.3 | [供电复核](../references/供电与扩展板实物复核/research.md) |
| [IMU 旧实物标注原件](../schematics/imu-to-dxl-scrapmeta-v0.3/实物板元件标注.jpg) | IMU 板历史总览 | 2026-10-09（原登记） | 原件已在原理图专题保存；**电压说明过期，不用于接线**，仅保留来源追溯 | U3 位置说明使用上行新版 |
| [hat-v1.2-port-review.png](archive/hat-v1.2-white-20261010/hat-v1.2-port-review.png) | HAT V1.2 接口复核 | 2026-10-10（制作） | 本会话生成；源图为本表正反面原图，标出两个 3Pin 口、两组 4Pin 空位及圆柱电容；背面旋转 90° | [供电复核](../references/供电与扩展板实物复核/research.md)，入口仍待电气核验 |
| [hat-v1.2-wiring-plan.png](archive/hat-v1.2-white-20261010/hat-v1.2-wiring-plan.png) | HAT 单链供电历史意向图（非当前实物接线图） | 2026-10-10（制作） | 本轮用户指定本表 `hat-v1.2-port-review.png` 为底图（已有原件，不重复拷贝）；裁出正背面面板，加 A/B/C 和功能箭头。脚本 `scripts/annotate-hat-wiring.py`；**不标照片上下针极性，不代表 10-24 的外部分叉或 10-25 单口 IMU 改接第二口，也非上电放行** | [当前接线记录](../references/配电与保护方案对比/research.md#hat-port2-20261025)、[验证单](../hat-v1.2-test.md) |
| [hat-v1.2-servos-closeup-user-20261010.png](archive/hat-v1.2-white-20261010/hat-v1.2-servos-closeup-user-20261010.png) | 用户提供的 HAT SERVOS 局部图 | 2026-10-10（收到） | 从本轮剪贴板临时附件原样归档，保留 A/B 框选；对应疑似 EH 3Pin 板端座，照片不独立证明实物额定/品牌 | [接口与配电比较](../references/配电与保护方案对比/research.md) |
| [dxl-hub-power-distribution-explained.png](./dxl-hub-power-distribution-explained.png) | 社区 dxl_hub 配电解释图 | 2026-10-10（制作） | 来源为只读社区库 `hardware/dxl_hub/docs/1.jpg`；脚本 `scripts/annotate-dxl-hub-power.py`，框示 J3 输入与分支；**是另一块板的设计图，不是本机 HAT 接线图** | [配电比较及证据](../references/配电与保护方案对比/research.md) |
| [hat-v1.2-a1-pinout.jpg](archive/hat-v1.2-white-20261010/hat-v1.2-a1-pinout.jpg) | HAT A1 量点标注 | 2026-10-11 | 舵机口 pin1 ↔ 排母 pin6 定位方法（脚本 `scripts/annotate-hat-a1.py`） | HAT A 段核对 |
| [hat-v1.2-a3-inductor.jpg](archive/hat-v1.2-white-20261010/hat-v1.2-a3-inductor.jpg) | HAT A3 电感量点标注 | 2026-10-11 | AP63205 电感（CK 6R8）输出侧 ↔ 排母 5V 脚量点 | HAT A 段核对 |
| [hat-v1.2-back-gnd-marks.png](archive/hat-v1.2-white-20261010/hat-v1.2-back-gnd-marks.png) | HAT 背面排母 GND 实测标注 | 2026-10-11 | 与安装孔相通的 8 个排母脚位置（GND 反查法定针序，结果见 PROGRESS A3 行） | HAT A 段核对 |
| [hat-v1.2-header-pinout.jpg](archive/hat-v1.2-white-20261010/hat-v1.2-header-pinout.jpg) | HAT 排母针序标注 | 2026-10-11 | pin1 在下排最右；pin2/4(5V)、pin6(GND)、pin8/10(UART2) 位置 | HAT A/B 段测试 |
| [board-servo-socket-pinout.png](./board-servo-socket-pinout.png) | 三板舵机座对比 | 2026-10-11 | HAT 与 imu_to_dxl = JST EH 3P（2.5mm）、微雪 = 5264-3P，与飞特原线 AMP2.0-3P（2.0mm）均不配 | 舵机线适配 |
| [hd1910-amp2.0-3p-pinout.png](./hd1910-amp2.0-3p-pinout.png) | HD-1910 原线端子脚序 | 2026-10-11 | 飞特原线 AMP2.0-3P：1=Signal / 2=Vcc / 3=GND（与板座脚序不同，接线须交叉） | 舵机线适配 |
| [hd1910-dupont-adapter-wiring.png](./hd1910-dupont-adapter-wiring.png) | 杜邦过渡线接法 | 2026-10-11 | 台架过渡期 AMP2.0 ↔ 板座杜邦转接示意（仅调 ID/零位，不带载，方案见 PROGRESS） | 舵机清点/改 ID |
| [_user-back2.png](archive/hat-v1.2-white-20261010/_user-back2.png) | 用户提供的 HAT V1.2 背面照（第 2 张） | 2026-10-11（收到） | A 段实测当晚的定位底图：40P 排母在照片上缘视角，8 焊盘组与排母针序判读均基于此图（结果见 PROGRESS A2/A3 行）；工作文件名 | HAT A 段核对 |
| [_crop-pads.png](archive/hat-v1.2-white-20261010/_crop-pads.png) | ↑ 背面焊盘局部放大（照片推断） | 2026-10-11（制作） | 8 焊盘组定位裁剪图，对应 +BATT（第 3 排）/GND（第 4 排）判读；内容按文件名与生成时间推断 | HAT A2 进板口 |
| [_crop-f303.png](archive/hat-v1.2-white-20261010/_crop-f303.png) | F303 MCU 局部放大（照片推断） | 2026-10-11（制作） | 背面 GD32F3xx（兆易创新 F303 兼容）区域裁剪图，A4 粗查（48 脚不在舵机数据链）对照用 | HAT A4 |
| [_crop-chip.png](archive/hat-v1.2-white-20261010/_crop-chip.png) | 背面芯片局部放大（对象待确认） | 2026-10-11（制作） | 与 _crop-f303 同批生成，具体框选对象未记录，待复核 | HAT 背面元件核对 |
| [_crop-buck.png](./_crop-buck.png) | 降压模块局部放大（照片推断，对象待确认） | 2026-10-11（制作） | 按文件名推断为降压模块裁剪图，A 段实测下午生成，具体用途未记录 | 降压模块核对 |
| [_crop-buck2.png](./_crop-buck2.png) | 降压模块局部放大第 2 张（照片推断，对象待确认） | 2026-10-11（制作） | 同上，晚间生成，具体框选对象未记录 | 降压模块核对 |
| [imu-board-b-20261014-a.jpg](archive/imu-gd32-single-port-20261014/imu-board-b-20261014-a.jpg) | 第二块 IMU 板背面 | 2026-10-14 | 仅板厂标记（94V-0 / E469747 / HQPCB-2），无版本丝印 | IMU 版本判别 |
| [imu-board-b-20261014-b.jpg](archive/imu-gd32-single-port-20261014/imu-board-b-20261014-b.jpg) | 第二块 IMU 板正面 | 2026-10-14 | **LQFP48 主控（GigaDevice GD32F303）+ 单 3P 白座 + 降压前端（电感 L1/二极管）**；识别为 jyg9 社区成品版 imu_to_dxl；针序与供电边界已获 0.2 图纸确认（2026-10-26） | 挂 8.4V 总线前目视核对 |
| [imu-single-port-h1-location-20261026.png](archive/imu-gd32-single-port-20261014/imu-single-port-h1-location-20261026.png) | 单口 GD32 IMU H1 位置标注与局部放大 | 2026-10-26（制作） | 来源为上行 10-14 用户原图；脚本 `scripts/annotate-imu-h1-location.py`。元件面、白色 3P 朝右；红框标出左下 H1 四焊盘，标 H2/H3 供区别。仅位置识别，不标上下针序；已打开检查，原图保留 | [COM5 与 H1 定位记录](../references/舵机网页工具惯性显示/research.md#ft232h-com5-20261026) |
| [sch/page1–5.png](archive/hat-v1.0-sch-pages) | HAT V1.0 原理图 PDF 逐页导出图 | 2026-10-11（制作） | 源自 `docs/schematics/microduck-hat-v1.0-sch/` 的 5 页 SCH PDF，供屏幕对照放大查看；**图纸版本 V1.0，实物 V1.2，图物差异见 HAT 小节** | HAT A 段图物对照 |
| [ft232h-breakout-20261016.jpg](./ft232h-breakout-20261016.jpg) | FT232H 转接板 | 2026-10-16 | 紫色 Adafruit FT232H Breakout 兼容板（USB-C，D0–D7/C0–C9 两排孔，**照片上排针未焊**） | Radxa 1.5M console 接线（见下方小节） |

## 降压模块（黑色，XT60 输入）— 2026-10-10 照片识别（正面+背面）

正反面共三次视觉识别 + 像素色块校验（红端子质心与标记完全吻合）。**照片识别、实物未复测**，丝印文字以手上实物为准。

**板子身份（背面丝印）**：**BUS SERVO POWER SUPPLY V1.3**，By **造物の乐趣**（@Make & Share），带二维码（微信压缩图码点损坏，OpenCV 无法解码，**待手机扫描取作者文档**）。网检（2026-10-10）：本地三个参考库与公开网络均无此板资料——社区文章[证实电源板是 microduck 复刻需自研的关键件](https://post.m.smzdm.com/p/a70nxnqg)，此板应为某位社区作者的自研件。丝印 **OUT PWR: 5V or 7.4V MAX 6A**——"5V 或 7.4V"疑似"稳压 5V / 直通电池 7.4V"两种输出模式，待二维码文档或实测确认。

**正面元件（编号对应标注图）：**

| # | 元件 | 识别要点 |
|---|---|---|
| 1 | XT60 输入插座（母头） | Amass，丝印 PWR IN 7.2-18V +/− |
| 2 | 选压焊盘 7V/6V/5V（VOLT_SEL） | 三对焊盘焊锡桥选定输出电压，**当前桥哪档照片不可辨** |
| 3 | 功率电感 | 屏蔽方型，丝印 4R7 = 4.7µH |
| 4 | 降压主控 IC | SOIC 无散热罩，旁有 MAX: 6A 丝印，型号待实物近拍 |
| 5 | 贴片功率器件区 | MOSFET/二极管/电阻小件 |
| 6 | 输入电解电容 ×2 | 丝印 22 16V |
| 7 | 输出电解电容 | 丝印 100µF 16V（CK） |
| 8 | 3P 输出排针（白座） | 丝印 GND/VCC/NC，实测 VCC=6.00V 稳压输出 |
| 9 | PWR OUT 输出端子（红塑 2P） | 实测跟随输入=电池直通，舵机总线走它 |
| 10 | 安装孔 ×4 | 四角 |

**背面另见**：金色圆孔一颗（**2026-10-10 勘误：曾据照片误判为 DC 母座，用户实物核对板上无此件**，疑为镀铜安装孔/过孔，实物待认）、VOLT_SEL 选压焊盘（改焊处）、XT60 大焊点 ×2、3P 排针焊点（左边缘竖排）。

**现行使用边界**：空载已测 VCC 为 6V、约 6.3V 开始跌落；当前方案仅用 PWR OUT 直通口，VCC 闲置，取消为 IMU 改焊 5V 的要求。空载结果不证明整机载流合格，见[供电复核](../references/供电与扩展板实物复核/research.md)。

**实测手顺（2026-10-10 已完成空载扫描，结论见 [buck-module-test.md](../buck-module-test.md)）：** 剩余：台架带载复测。~~核 DC 母座~~（勘误：板上无此件）。~~改焊 5V 档~~（2026-10-10 v2 评审取消：AP2210K-3.3 输入上限实为 13.2V，IMU 直挂总线，本板稳压支路无负载）。**该板在整机中的角色与接线见 [power-architecture-v2.md](../power-architecture-v2.md)（历史版本 v1 同目录存档）。**

## 微雪总线转接板 — Bus Servo Adapter (A) v1.1 — 2026-10-10 照片识别

板子身份（左缘竖排丝印）：**Bus Servo Adapter (A) v1.1**，Waveshare，板 42×33mm、安装孔 φ2.5×4（孔距 37×28mm）。**2026-10-25 更正**：已取得[微雪官方 wiki](https://www.waveshare.com/wiki/Bus_Servo_Adapter_(A)) 链接的含 USB 原理图，图纸未标修订号，实物版本对应仍待逐件核对；见[原理图登记](../schematics/README.md)。照片上芯片丝印不可辨；当晚电脑识别为 CH343/COM4，不能等同总线数据通路已验证。

| 派生资料 | 来源、日期及用途 |
|---|---|
| [官方图第 1 页渲染](../references/舵机网页工具惯性显示/waveshare-bus-servo-adapter-a-schematic-page1-20261025.png) | 2026-10-25，用 pypdfium2 将[官方 PDF](../references/舵机网页工具惯性显示/waveshare-bus-servo-adapter-a-schematic-20261025.pdf)第 1 页按 2.5 倍渲染，无裁剪/标注；已打开检查。用途为 USB/DC_IN0 电源网络核对，不是实物接线图；来源与 SHA256 见[研究](../references/舵机网页工具惯性显示/research.md#waveshare-usb-20261025)。 |

**正面元件（对应标注图 [waveshare-bus-servo-adapter-a-annotated.jpg](./waveshare-bus-servo-adapter-a-annotated.jpg)）：**

| 元件 | 识别要点 |
|---|---|
| 舵机口 ×2（白座 5264-3P） | 丝印 D/V/G = 数据/电源/地；两口并联，菊链最多 253 颗 |
| UART 排针 TX/RX/GND | A 模式接 MCU；微雪 wiki 提醒 **RX-RX、TX-TX 直连**（丝印已按对端标注，勿交叉） |
| 模式跳线帽 ×2（黄色） | **A = UART 控制 / B = USB 控制**，对照板面 A/B 表格丝印 |
| USB-C 座 | B 模式接电脑（CH343 串口，微雪总线工具/LeRobot 可用） |
| DC 母座 5.5/2.1、DC+/DC- 螺丝端子（绿 2P） | 外部电源入口；官方图 DC1 接 DC_IN0，绿端子 H1 经 MOS 管 M1 接入，不粗略视为无器件的直接并联；丝印 DC 9-12.6V |
| 板载降压区 | 供板内逻辑，不给舵机稳压；旧照片“47µH”未独立读清，官方候选图 L1 为 4.7µH，图物对应待核 |
| PWR 电源指示灯 | 右下角 |
| 半双工转换与阻容区 | UART↔单线总线收发切换电路（芯片丝印未读清） |

**供电事实（2026-10-25 官方图核对，非端点实测）**：H3/H5 的 V 接外部 DC_IN0，USB 经 D4/U2 供逻辑，USB 不给 3P 的 V 提供正常电源。设备输入电压应匹配其规格；微雪本身不把外部输入稳压为舵机电压。Wiki 说明丝印 9–12.6V 针对 ST 系列、也接受 SC 匹配供电，本次正文未列具体 5–8.4V 数字，撤回旧精确引文。单口 IMU 规格 6–24V，本项目台架使用 7.4V 经微雪取电，不能仅插 USB；详见[供电/实测记录](../references/舵机网页工具惯性显示/research.md#waveshare-usb-20261025)。

**本项目用法**：HD-1910 是 7.4V 舵机 → 台架喂 **2S（6.6-8.4V）正确，严禁 12V**。角色 = 台架总线调试（舵机改 ID/零位、imu200 验收、对比飞线/FE-URT-2 方案），**不进整机供电链**（整机架构见 [power-architecture-v2.md](../power-architecture-v2.md)）。

## HAT — Microduck Controller Hat for Radxa Zero 3W（实物 V1.2）— 2026-10-10 照片识别

板子身份（正面丝印）：**Microduck Controller Hat for Radxa Zero 3W**，实物版本丝印 **V1.2**（正背面均有）。**⚠️ 此前档案记为 V1.1，以实物为准更正为 V1.2**；存档原理图（[SCH PDF](../references/白色扩展板原理图查证/SCH_Microduck-Hat-for-Radxa-Zero_2026-10-06.pdf)）仅为 **V1.0**。照片识别、未上电未复测。

**2026-11-02 用户确认来源**：这块 HAT 与 IMU 均来自 [kissqy/Microduck-kissqy hardware](https://github.com/kissqy/Microduck-kissqy/tree/main/hardware)（HAT REVA；EH2.5/AMP2.0 两版，实物版本待核），V1.0 PDF 不是它的图纸。
**本组 10-10 照片已归档**：[archive/hat-v1.2-white-20261010/](archive/hat-v1.2-white-20261010/README.md)。作者 AMP2.0 BOM 中 HAT 唯一多脚 IC 是 TLV320AIC3104（HVQFN-32），**没有 48 脚 MCU**，与本文背面照片的“F303 LQFP48”不一致；本组不能用于当前实物接线，当前板需重拍。

**关键发现（图物差异）**：

1. **背面有一颗 F303 类 MCU**（LQFP48，丝印 ?32F303CET6，品牌前缀不可辨）+ 金属壳晶振——V1.0 原理图 5 页中**没有任何 MCU**，属 V1.1/V1.2 新增，用途未知（总线卸载/电源管理/RTC 皆有可能）。
2. **正面圆柱电容可见“10 / 50V / RVT”标记**，更符合普通电解电容；撤回此前“1.0F 5.5V 超级电容/RTC 备份”的推断。
3. 背面**焊盘 ×8**的位置与排列对应正面两组 4Pin 空接口，不能作为另有独立电池入口的证据；具体网络待 V1.2 图纸或断电测量确认。
4. RS485 座（EH 4P ×2）位置为**空焊盘未焊**；本项目用 TTL 总线，不影响。

**正面元件（现行位置复核见 [hat-v1.2-port-review.png](archive/hat-v1.2-white-20261010/hat-v1.2-port-review.png)，旧综合标注不用于接线）：**

| 元件 | 识别要点 |
|---|---|
| 舵机口 ×2（JST EH 3P，左缘大白座） | 丝印 SERVOS；按 V1.0 图：1=GND 2=+BATT 直通 3=DATA（V1.2 待复核） |
| Qwiic/I2C 座 ×4（SH 1.0 4P） | 丝印 I2C3 / I2C4 / I2C5 等 |
| RS485 座焊盘 ×2（EH 4P） | 空焊盘未焊 |
| AP63205 5V 降压区 | 电感丝印 CK 6R8 = 6.8µH，与 V1.0 图 L1 一致 |
| 圆柱电容 | 标记可见 10 / 50V / RVT；无证据称其为超级电容 |
| 扬声器/麦克风座群 | 丝印 SPEAKERS、LEFT/RIGHT、Mic、MICS |
| 40P 排母焊盘（正面） | 排母本体焊在背面，插 Radxa Zero 3W |

**背面元件（位置对应关系见现行接口复核图）：**

| 元件 | 识别要点 |
|---|---|
| F303 类 MCU（LQFP48） | 丝印 ?32F303CET6；**V1.0 图无此件** |
| MCU 晶振 | 金属壳贴片 |
| PAM8406 音频功放（SOP-16） | 与 V1.0 图 U12 一致 |
| 40P 排母 | 2×20，插 Radxa Zero 3W |
| 小信号芯片区 | SOT-23-5/6 多颗（LDO/74LVC/LM5050 等，待 V1.2 图对照） |
| 焊盘 ×8 | 对应正面两组 4Pin 空接口，不是已确认的独立电池输入 |

**接口结论（2026-10-10 照片复核及旧意向）**：照片中只明确看到两个已焊接 SERVOS 3Pin 口，未识别出标注 BAT/VIN 的独立电池入口；A 两线进电、B 单链加末端 IMU、C 对插主控仅历史意向。**2026-10-26 用户确认单口 IMU 已从微雪台架接回 HAT“另一个口”**，00:11 快照显示 servo-web 运行。更新为文字口述，没有新接线照片；不把“另一个口”映射成旧图 A/B。见[当前记录](../references/舵机网页工具惯性显示/research.md#hat-debug-plan-20261026)。

**行动项**：接线/上电前向板卡来源索取 **V1.2 原理图或改动说明**（重点：MCU 功能与固件、+BATT 入口形式、舵机口供电路径是否与 V1.0 一致）。供电架构分析（[power-architecture-v2.md](../power-architecture-v2.md)）基于 V1.0 图，舵机口 +BATT 直通等结论需按 V1.2 实物复核。

## 万用表 — 德力西 6000 位数字万用表

6000 Counts（最多显示 5999），手动量程。照片状态：显示 `000 mV` + DC，直流毫伏档空载。

**档位（旋钮）**

- `V⎓` 直流电压 ×4 档：600m / 6 / 60 / 600（V）。测 3.3V/5V 用 6V 档，7.4V 电池及以上用 60V 档
- `V~` 交流电压：600V~（配 Live 火线识别档）
- `Ω` 电阻 ×5 档：600 / 6k / 60k / 600k / 6M（断电测量）
- 蜂鸣/二极管档：响=通；二极管正向约 0.5~0.7V
- `A⎓` 直流电流：60μ / 600μ / 6m / 60m / 600m（红笔在 VΩmA 孔）+ 10A 专用档（红笔换 10A 孔）
- `NCV` 非接触验电、`OFF` 关机

**插孔**

- `COM`：黑表笔，公共端，任何测量都在这
- `VΩmA`：红表笔，测电压/电阻/通断/≤600mA 电流；内部 **600mA 保险丝**
- `10ADC`：仅 10A 档用，**无保险丝（UNFUSED）**，超 10A 直接烧表

**按钮**：左=背光，右=HOLD 读数锁定。

**红线**：禁止带电测电阻；禁止电流档测电压；测完电流红笔立刻插回 VΩmA。

## 直流稳压电源 — 德力西 DLX-30V10AMF

可调线性/开关直流电源，最大 **30V / 10A**。照片状态：3.00V、0A、C.V. 灯亮（恒压、空载）。

**面板**

- `VOLTAGE` 旋钮（带 SETOUT）：调输出电压
- `CURRENT` 旋钮（带 LOCK）：调**电流上限**（限流保护值，不是输出电流）
- `ON/OFF` 按键：输出通断（按键灯亮=输出开）
- 三行显示：绿=电压 V，红=电流 A，黄=功率 W
- `C.V.` 灯=恒压正常工作；电流顶到上限时跳 `C.C.`（恒流，电压自动压下来，起保护作用）

**本项目用法**

1. 降压模块实测（PROGRESS 待办）：电源接模块输入，万用表并输出，电压 12V→6V 扫描找掉出稳压点，判定 2S 电池（带载跌 6.6V）是否可用
2. 电路板首次上电：先限流 0.1~0.2A 排短路，正常后放宽到 0.5~1A
3. 电机单独测试可直接带，但与开发板同测时分两路供电、GND 共地，不共用同一路 5V

## 第二块 IMU 板 — jyg9 社区成品版 imu_to_dxl — 2026-10-14 照片识别

用户提供正反面照片（[正面](archive/imu-gd32-single-port-20261014/imu-board-b-20261014-b.jpg) / [背面](archive/imu-gd32-single-port-20261014/imu-board-b-20261014-a.jpg)），**照片识别、未上电**。

**判别结论：jyg9 / 社区套件（microduck-community-kit）的 GD32 版 IMU 板**，依据：

| 证据 | 观察 |
|---|---|
| 主控封装 | LQFP48 四边 48 脚（STM32G031 血统为 TSSOP20，一眼排除） |
| 主控丝印 | GigaDevice GD32F303 系列（放大可辨 GigaDevice 字样，具体后缀糊） |
| 电源前端 | 电感 L1 + 二极管 + SOIC-8 降压电路，与官方 README 的 **6~24V 宽压输入、效率 >90%** 一致（社区库 `hardware/imu_to_dxl/README.md`） |
| 总线接口 | 单 3P 白座（ScrapMeta v0.3 为双 B3B-EH 并联） |
| 板面丝印 | 正面有日期类标记（约 2026/9/7x）及字样；背面仅板厂标记 94V-0 / E469747 / HQPCB-2，无版本号 |

**与之前调研的差异（2026-10-26 关闭）**：2026-10-09 调研记录称 jyg9 版"板上带 CH340 调试口"，本板照片未见——经核官方 0.2 版 BOM/原理图，**官方设计即无 CH340**，USB 调试走 GD32 原生 USB 引到排针，出入关闭（[jyg9 电源分析](../references/单口惯性单元五伏供电/research.md)）。另：当时照片判读"SOIC-8 降压电路"，官方 BOM 实为 SOT23-6 封装的 ETA2845S2G。

**2026-10-26 调试口核对**：照片上未见 USB 插座或 CH340；设计源文件却明确预留 **H1 UART 日志、H2 SWD、H3 USB 下载焊盘**，不能把“没有 USB 座”理解为“没有调试引出”。三组焊盘与手上实物的位置/版本尚待对照，未制作已确认针序图；来源与 H3 +BATT 供电边界见[接口研究](../references/惯性单元三版来源对比/research.md#usb-debug-20261026)。

**同日调试进展**：FT232H 已枚举 COM5；因用户不确定 H1 位置，已用原图生成[定位标注与放大](archive/imu-gd32-single-port-20261014/imu-single-port-h1-location-20261026.png)，红框为 H1 四焊盘。当前焊接/线序仍未现场核实，没有收到新照片；本图不将设计逻辑 pad 号当照片上下针序。下一步补此处近照确认，再接两根日志线，详见[计划](../references/舵机网页工具惯性显示/debug-plan-20261026.md)。

**2026-10-25 指示灯复核**：该单口板照片未见电源/状态 LED，对应社区 `hardware/imu_to_dxl/imu_to_dxl.kicad_sch` 也未列 LED；D1/D2 是保护器件。固件 `board.h:77` 的 PB5 灯明确只属于开发板，不用于要求该成品板必须亮灯。用户本轮口头“板一”指这块单口板（历史文档板②），烧损的是双口板；后续按接口数量区分。详见[换口与 LED 记录](../references/舵机网页工具惯性显示/research.md#hat-port2-20261025)。

**含义**：出厂即 DXL 2.0 + 飞特双协议自动识别，ID 200，**不需要刷固件**；供电按 0.2 图纸 **≥6.5V 冷启动 / ≈5.93V 维持（EN 分压设定），5V 必不启动、7.4~8.4V 正常**，可直接挂 8.4V 舵机总线末端（EH 座针序 1=GND 2=V+ 3=DATA 已获官方图纸确认，对照 [三板舵机座对比](./board-servo-socket-pinout.png)；接线前目视核对仍保留）。

## FT232H 转接板 — Adafruit FT232H Breakout 兼容板 — 2026-10-16 照片识别

用户提供照片（[原图](./ft232h-breakout-20261016.jpg)，企业微信压缩图），**照片识别、未上电**。

| 证据 | 观察 |
|---|---|
| 板面大字丝印 | FT232H（USB 转 UART/FIFO/JTAG 类转接板） |
| USB 口 | USB-C |
| 主控 | SSOP 封装 FTDI 芯片（具体后缀照片看不清），旁有小封装芯片（疑 3.3V LDO） |
| 引脚 | 两排通孔：上排 Gnd + C0–C9（ACBUS）；下排 3V / 5V / Gnd + D0–D7（ADBUS） |
| 其他 | I2C 拨码开关 + 4P I2C 专用座；官方 USB-C 原版开关连通 D1/D2，UART 前须确认 OFF/断开，兼容板实际方向待核（2026-10-26 撤回“只控制上拉”旧判断）；晶振、去耦电容若干 |

- 布局与 [Adafruit FT232H Breakout](https://learn.adafruit.com/adafruit-ft232h-breakout) 一致 → UART 模式 **D0=TX、D1=RX**，3.3V 逻辑（兼容板按同设计推断，照片未见电平跳线）。
- **10-16 照片上未见已焊排针（只有通孔焊盘）**，不代表当前仍未焊。只收 IMU 日志需 Gnd / D1 两处可靠连接，不要求焊接并连接 D0。
- 用途：此前计划用于 Radxa console（1500000 8N1）；2026-10-26 用于单口 IMU H1 日志的计划为 **115200 8N1 无流控**，两者不能混用。接线与开关勘误见 [串口桥接瑞莎调试口](../references/串口桥接瑞莎调试口/research.md)，[本轮计划](../references/舵机网页工具惯性显示/debug-plan-20261026.md)。
- 待核对：枚举 VID/PID 应为 0403:6014（兼防克隆芯片问题）；丝印细节以实物为准。

## 新增照片规则

- 文件名：`主题-型号.jpg`（英文小写连字符），收到日期写登记表
- 待收照片（拍后补入）：IMU 板 J2 焊盘面、舵机清点、打印件清点、降压模块主控 IC 近拍、**FE-URT-2 调试板正反面**（2026-10-14 用户反馈找不到板，无照片存档；官方参数：FE-URT2-C001，55.8×36.6×11.5mm，USB-C，TTL 3P×2 + RS485 4P + 电平拨码）；**二维码用手机扫（结果发给助手即可），压缩照片解不了码**
- 说明写在对应小节，重点记"照片里当时的状态"和"后续要用它核对什么"
