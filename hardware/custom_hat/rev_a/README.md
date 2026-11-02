# Custom HAT Rev A.1（制造/实物验收未完成）

现行见[2026-10-31 J502针序及钢网修复](../../../docs/references/hat-simulation-tools-20261029/qwiic-pinout-20261031/research.md)，PCB SHA256为90f27091017525a22f45c8818c973c317ed6262387a98fdf06bdc26337dac2a6。**A.1的J502为1=GND、2=3V3、3=SDA、4=SCL；旧Rev A不同，不能混用。** 元件/板框不变，其它连接和I2S参考铜取样保持；C307 DNP的两个锡膏开口已在导出时排除。之前codec复位、电源/补偿、规则修复继续有效。**[用户确认，2026-10-31] 尚未送厂、没有新板实物。** 制造/装配接受和供电条件待落实，实际功能留待制板后按[最短首板草案](../../../docs/specs/20261028-custom-hat/first-article-a1.md)验证。[原目标审计](../../../docs/references/hat-simulation-tools-20261029/qwiic-pinout-20261031/completion-audit.md)区分已修问题与剩余依赖，[修复方案](../../../docs/specs/20261028-custom-hat/recovery-plan.md)维护下一步。

## 当前文件事实

| 项目 | 本机文件/工具核对 |
|---|---|
| 主入口 | custom_hat_rev_a.kicad_pro / .kicad_sch / .kicad_pcb；六个功能子页 |
| PCB | 65×30mm板框、4层、72封装、1130线段、100贯通via，盲/埋/微孔0 |
| 铜区 | F/B POWER_GND、In1 POWER_GND、In2 +3V3；直流焊盘连通已核，不等于完整高频回流核准 |
| 完整工程重铺铜 DRC | 已证明DRU有效加载；普通违规0、未连接0、schematic parity 0、ERC 0、netlist mismatch 0，功能与制造未验收 |
| ERC | 0，不能替代真实电路、焊盘、PCB 和功能检查 |
| 生产审查包 | `production-20261031-qwiic-review/` 同版输出；独立PTH/NPTH、装配资料、6处POFV及默认Job隔离；C307锡膏已排除。此前包仅历史 |
| BOM | 58/58拟装器件、38/38有效分组、35唯一MPN；52贴装+6通孔；C307 DNP。分组增加仅因C309图形变体，不代表新增器件或采购核准 |
| 电源器件 | L301=5.6µH IHLP4040DZER5R6M5A；R309=WSL120600000ZEA9铜跳线，专用焊盘已匹配 |
| 安装条件 | H1/H2排母侧圆柱头M2.5外径≤4.5mm，无垫圈/六角隔离柱；长度及另一侧堆叠待核 |
| 环宽/热孔 | 99 via各铜层环宽≥0.125mm，codec限定0.35/0.15mm贯通孔为0.1mm；U301 EP内5热孔，6处filled/capped仍待接受 |
| 反馈/补偿 | FB全网6.332mm、COMP4.509mm、RC1.638mm，均F.Cu；布局检查通过，环路稳定性未验收 |
| 补偿公式 | 图27理想网络与ngspice核对一致，Eq12印刷系数未当选值依据；14kΩ/3.3nF保持，未借手册示例相位裕量宣称本板通过 |
| LDO回路 | C308/C309为2.2µF；C309输出线2.227mm，R703仅串电容回地；C311并联影响已单列，未证实旧板振荡 |
| I2S参考铜 | 原线路保持；现行5条I2S取样与c6c09b33版一致。F地3片各有地via，直流同组不证明回流阻抗或EMI合格 |
| codec复位 | J101.33/ GPIO3_C3接U701.31；R308=10kΩ、C310=100nF保持，四端同组；复位GPIO驱动和实际低脉冲/电源时序待验 |
| J502扩展口 | A.1按Qwiic/STEMMA QT针号：GND/3V3/SDA/SCL；需继续核外设电平、上拉、地址、线束与负载，非所有SH4P通用 |
| 主控软件 | 历史内核同版本官方包缺codec/BMI088驱动；[codec模块/overlay](../software/codec/README.md)、[音频路由工具](../software/codec/AUDIO-ROUTING.md)及[BMI088双端点适配器](../software/imu/README.md)已离线核查；实际主控配置、播放/录音和六轴采样仍未验收 |
| 主电流铜 | 共用输入、SERVO_VBAT及主控5V内层主干/排母入口1.2mm；F面源端、反馈和其他分支另计，35µm模型不标整板额定 |
| 供电边界 | 本自设计HAT仅单源供电，不支持带电USB源并供；官方V1.11图的GPIO5V与USB VBUS同网，不当作用户实物版本识别 |
| 输入标识 | J301右侧pin1=2S+、pin2=GND已印；全部针序与保护范围见[接口说明](../../../docs/references/hat-simulation-tools-20261029/power-acceptance-20261031/power-interface.md)，不能套到白色V1.2 |
| 功放去耦 | C323/C328位于F面，经成对VDD/GND通孔接B面U803；VDD到C328平面铜线2.947mm，另含1个通孔，非实测性能 |
| TTL去耦 | C329/C330各100nF，B面VCC线3.135/1.441mm，各经约0.8mm线接地孔；孔接F/In1/B地，完整高频回流与实际性能未验 |
| 板名/版本 | 当前DUCK HAT A.1，沿用1.0mm字高/0.15mm笔画及丝印间距规则；A.1区分J502针序，不是制造/实测标记 |
| 制造预核 | 163圆孔逐项核钻孔，652项孔铜距通过；via/PTH器件孔/NPTH规则为0.20/0.30/0.25mm，未替代加工公差与厂商接受 |
| 图纸显示/装配 | 网络类、阻容、40P及TTL标签已整理；DATA连续线与junction不改变原网；底面装配图已镜像，原生CSV不再镜像；元件值查BOM |

## 已关闭旧问题

AP64350 独立 1–9 焊盘、BMI088 标准封装及 CSB2 DNC、TTL 两缓冲器与动力分支、I2S 方向、麦克风/功放路径、1.8V LDO、TP802 位置、内层铜区均已有文件级修复。40P pin1 设计侧已有参考依据，不再要求用户重复手量；这些不等于整板或驱动实测通过。

## 已处理事项与剩余条件

- U501周边错误铜/keepout及J301/J506通孔、焊盘/courtyard冲突已修；实物装配高度未验证。
- I2S_SDO及`R308.2 ↔ U701.7 +3V3`已连通，原微孔现改为同位置`0.35/0.15mm`机械贯通孔。现行不要求激光盲孔，但小机械孔/POFV及QFN land组合仍需厂商接受，见[现行复核](../../../docs/references/hat-simulation-tools-20261029/npth-clearance-20261031/research.md)。
- 原理图/板一致性107项已逐项修正为0：库关联、显式NC、PWR_FLAG、board-only标记、DNP及字段均同步，未关闭规则；同版生产审查包已重出。
- 双面各3个fiducial已经重排，1mm圆铜、2mm阻焊开口、无锡膏、有courtyard；普通DRC为0，夹持/拼板仍需厂商确认。
- 已加入 3 个板边 `POWER_GND` 地缝合过孔；候选和主板 DRC 均保持普通违规 `0`，位置与依据见 [地缝合/EMC 复核](../../../docs/references/hat-simulation-tools-20261029/ground-stitch-20261030/research.md)。
- I2C5本板上拉、电容盘中孔已修。U301已有5个同网热孔，C303新增VIN线2.7025mm，C308位于LDO附近。codec/TO-252不套固定孔数。有效电容/稳定性、载流、真实热/回流、小孔加工与首板功能仍未完成，不能按孔数或评分放行。
- 既有 best、base-clean、fanout-check、via-work 与 ../candidates/ 均不是发布版。

## 工作流程

当前可交给用户审阅的[CAM/装配评审资料](../release-review/README.md)包含固定制造文件和更新后的制造状态说明，未发送。包内列明待工厂接受的孔/land/POFV/层叠和装配问题；它不是自动下单包或实物放行。

使用 ../scripts/pipeline.py 建立完整副本并检查；见[流程说明](../scripts/README.md)。不在主板上直接重跑旧布局、补孔或布线实验。每个电路/布局修复须有来源、同规则报告与检查点；通过后才能考虑回写主入口。

已确认功能为供电、TTL、板载 IMU、ToF、播放/录音；屏幕、摄像头、RS485、EEPROM、充电、UPS 不在范围。当前 GPIO 控制 DXL_DIR，不能写成自动换向已验证。默认不提交、不下单、不操作实物。
