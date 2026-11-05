# HAT 22个热焊盘修复正式回写

> 本页b369f9fc…为热焊盘采用检查点。后续[U701分层via盘](../归档扩展板音频芯片焊盘/research.md)进一步回写，当前主源3b1d903c…；热焊盘改动继续保留，包与拼板以现行入口为准。

日期2026-11-02。用户目标为继续核SMT标准并解决已知问题，前轮为[SMT专项候选](../归档扩展板贴片规范复查/research.md)。本轮已有可独立采用的22焊盘修改，按原生检查、原连接/I2S参考铜核对及视觉检查通过后回写主板；未下单、未上电、未提交Git。

## 现行源与实际修改

主PCB SHA256：`b369f9fc2cfbe7ff64dc2a4aa62fac9a6fa7a2c2f6c7bce5a0347e3479dbf738`，仍为A.1内部制造修订。旧90f27091…源作为before-metadata原始快照保留。位号、值、封装、MPN、针网、器件位置、走线/via几何与规则不变，仅22个阻容地焊盘的zone连接改为thermal、连接臂0.25mm/隔离0.2mm，C306连接臂45°；其余默认参数没有因结果而全局降低。

依据为嘉立创SMT 62751热阻焊盘细则及64042目录P1-4；原始文档在[来源清单](../归档扩展板嘉立创规则自查/sources-manifest.json)。全24焊盘版虽然最终DRC为0，但I2S参考铜采样退步，所以已拒绝。C305.2和C310.2仍直接接地铜，保留为具体热/回流权衡待办，不能宣称全部热平衡解决。

本轮未把器件端子的电气热需求与焊接热平衡混为一谈；如后续原厂电源布局/高频回流要求与工艺建议冲突，需结合实际路径与工艺限制分别处理。

## 回写证据

- [geometry-connectivity-check.json](geometry-connectivity-check.json)：候选DRC/未连接/parity/ERC/网表全0；所有原焊盘几何、网络、走线及连接保持；I2S相同采样位置覆盖零损失。
- [promotion.json](promotion.json)：只回写`custom_hat_rev_a.kicad_pcb`，原源及差异有备份；回写工具核当前源与候选指纹、DRU加载证明。
- [post-promotion-summary.json](post-promotion-summary.json)：回写后重新检查完整工程，仍全0，规则哨兵有效。
- [checkpoint.json](checkpoint.json)与`hardware/custom_hat/current-review.json`绑定b369f9fc…，不再用90f27091作为当前SHA。
- 正反铜图thermal-top.svg/png、thermal-bottom.svg/png已打开，统一顶视坐标，B图未镜像。它们只用于检查真实热焊盘图形，不是装配图或实物。

内部同源输出为[production-20261102-thermal-review](../../../hardware/custom_hat/rev_a/production-20261102-thermal-review/README.md)；原有C307 DNP锡膏策略和独立PTH/NPTH、装配/BOM保持。国内RS-274-X和双联拼板需要与此源同步，现行入口统一看[release-review](../../../hardware/custom_hat/release-review/README.md)及[panels](../../../hardware/custom_hat/panels/README.md)，不从旧文件名猜当前版本。

## kicad-happy同版复审

固定版本2fd9aa0fe2d620f36627d9221e8b1393987ae38e已重新跑schematic、PCB full、cross、EMC、thermal、Gerber、SPICE及prior delta；35个相同MPN生命周期仅复用原unknown结果。

| 项目 | 本轮结果 | 解释范围 |
|---|---|---|
| 原生完整工程 | DRC/未连接/parity/ERC/网表全0 | 规则已验证加载，不能代替电气实测 |
| schematic | 44项，0error/3warning/41info | 参数/器件未变 |
| PCB full | 59项，3error/15warning/41info | 同源判断沿既有误报/风险分类，不把原始计数写全通过 |
| cross | 2warning | 近似平面识别限制保留 |
| EMC | 53项，7error/33warning/13info | 风险提示，非EMI测试 |
| thermal | 0告警，模型0.028W/只评2器件 | 不是整板热验收或额定 |
| Gerber | 2warning | Paste/铜flash比例口径，C307策略以语义审计为准 |
| SPICE | 12理想子电路pass | 不覆盖完整稳压环/负载/现场功能 |

本轮真实新事实是22个热焊盘改动已进入主工程及同源产物。U701完整扇出尚未通过；单板极性、物料工艺、实际层叠/铜厚及实物功能仍未全部完成。原“所有问题解决”目标保持active，不以本轮局部通过缩减目标。

## 本轮后续局部探索

escape-09～14在旧90f27091几何基线上继续局部扇出：逐步把SDI增加换层连接、重新排列SDO/BCLK通道，但未形成全部完整可接受路径，未回写。后续发现C305原F面位置覆盖codec换层可用区域，另建C305搬移候选：c305-relocate-01有悬空端未采用；02移至(138.5,108.5)并接L301输出，原生全0但支路9.188mm、回流/整体布局尚未完成核对；03试图更靠近输出，有铜/庭院冲突，拒绝。不能把局部搜索失败证明为物理不可布线，也不能采用有短接的候选来“清零目标”。

本轮公开资料补查TI via-in-pad示例发现其他电源QFN可用填孔，但不是AIC3104该信号焊盘的直接证据，因此不用于撤销U701具体待办。通用填孔可解决吸锡，不自动核准所有铜盘/Mask/孔几何组合。

后续已完成[codec焊接面分层铜盘](../归档扩展板音频芯片焊盘/research.md)修复，不再将失败扇出作为唯一解法。escape-15在C305候选基础上仍未得到BCLK完整路径，未采用；此失败不影响已回写的22热焊盘。该轮局部实验没有改动其它未授权硬件。
