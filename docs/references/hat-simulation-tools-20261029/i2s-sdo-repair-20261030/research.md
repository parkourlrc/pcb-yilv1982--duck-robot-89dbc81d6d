# I2S_SDO 连接及相邻扇出修复（2026-10-30）

> 后续[供电/地检查点](../power-repair-20261030/research.md)已将主板更新为11项普通warning、1未连接（U701.7）；本文15/22/101保留为I2S修复完成时的历史证据，不覆盖原报告。

状态：局部修复通过并更新主PCB，整板仍不可投板。用户对下一步处理I2S_SDO回复“继续”；主会话执行，无subagent、无实物操作。

## 原问题与最终改动

- 修复前 U701.4（codec DIN）与 J101.40 同为I2S_SDO，但没有走线连接。原理图方向正确，不重复改方向或器件。
- 现有B.Cu的SDI/LRCK/BCLK扇出和过孔限制了pad4出线区域。只加一条线的有限几何搜索未找到通路；这不是板面无空间的证明。
- 最终联动重布I2S_SDO、I2S_SDI、I2S_LRCK、I2S_BCLK四网，保留端点、位号、焊盘、其他网络、原理图与规则。MCLK未改。两条数据线主要走F.Cu，LRCK含In1.Cu段，BCLK走B.Cu；codec端仍从B.Cu出线。
- 新线宽0.15 mm、孔盘/钻孔0.5/0.3 mm：来自现有工程允许值（工程min_track_width=0.10、min_via_diameter=0.50、钻孔下限0.30及现行环宽规则），**没有降低规则**。当前规则允许不等于已完成供应商工艺/整板载流确认。

## 方法及失败记录

1. 用KiCad读取实际焊盘、各层走线、过孔和禁布区；按铜几何及网络间距形成约束网格，非盲试坐标。
2. 单网搜索试过0.2/0.15/0.1 mm线、0.6 mm孔盘、0.1/0.05 mm网格，均无路径；一个仅在规划数据中略移LRCK过孔的尝试也未成功，未写板。
3. 四网按有限顺序组合规划。最初BCLK端点超出局部窗口，是搜索实现缺口，扩展至实际端点后重算，不能将此失败当板故障。0.6 mm孔盘组搜索在第13个顺序后停止，未产生完整PCB候选。
4. 重新核项目规则后使用已有规则允许的0.5 mm孔盘；单网仍无路径，四网联动在第3个顺序（SDI、LRCK、SDO、BCLK）取得完整规划，见 [search-attempts.json](search-attempts.json)。
5. 将网格阶梯线简化成45/90°路径，再完整副本落板、重铺铜DRC和连通图复核。规划仅使用保守焊盘外框及铜障碍，未用其替代KiCad规则引擎。

代码：[plan_i2s_sdo.py](../../../../hardware/custom_hat/scripts/plan_i2s_sdo.py)、[simplify_i2s_plan.py](../../../../hardware/custom_hat/scripts/simplify_i2s_plan.py)、[apply_i2s_sdo.py](../../../../hardware/custom_hat/scripts/apply_i2s_sdo.py)。[route-plan.json](route-plan.json)为采用路径，grid-route-plan.json保留简化前规划，search-failure*.json为搜索诊断，不是物理不可布线证明。

## 本机离线验收（非硬件实测）

| 项目 | 修复前 | 修复后 |
|---|---:|---:|
| 普通DRC | 16 warning | 15 warning |
| 未连接 | 23 error | 22 error |
| 原理图一致性 | 101 warning | 101 warning |
| ERC | 0 | 0 |
| 走线段 / 过孔 | 538 / 73 | 533 / 73 |
| I2S_SDO端点 | 未连 | 同一连通组 |

- 同一完整工程、同一规则、重铺铜并启用原理图一致性。逐UUID比较普通DRC与parity无新增项；SDI旧悬空孔提示随重布消除，I2S_SDO未连接消除。
- 独立副本重铺铜保存后，比较193个有网络焊盘的连接分组，原有连接无丢失；U701.4与J101.40进入同一连通组。见 [connectivity-verification.json](connectivity-verification.json)。原理图导出网表与板赋网/契约无新增差异。
- 核对全部几何条目：只有四个目标I2S网络的走线/过孔变化；元件、焊盘和其他铜对象保持原值。审阅差异和路径图后，源哈希仍等于基线才回写；主板SHA256等于验收候选，见 [result.json](result.json)。
- 没有测量真实I2S时序、回波或播放/录音功能；几何/连通验收不等于音频已运行。地铜连通未退步，但完整信号完整性/回流评审仍属制造前检查，不在本轮作过度结论。

## 证据与图像

- [before-summary.json](before-summary.json)、[after-summary.json](after-summary.json)保存实际命令、版本和源摘要；对应drc/erc报告保留。
- [before.kicad_pcb](before.kicad_pcb)、[after.kicad_pcb](after.kicad_pcb)仅为差异快照，未附完整规则时不能独立跑DRC比较。完整副本路径见result.json。
- [I2S路径与扇出对照](i2s-route-review.png)由 [render-hat-i2s-repair.py](../../../../scripts/render-hat-i2s-repair.py)从前后PCB几何生成；已打开复核。全部为顶视坐标、底层未镜像，焊盘为外框近似，未画填充铜；不是实物照片，不构成制造或上电许可。
- inspection.png为早期局部检查草图，复用了旧图网格，坐标标注不完整；仅留追溯，正式图为i2s-route-review.png。图像及生成脚本已登记照片索引。
- KiCad仍输出重复图像handler和SWIG退出警告；命令返回、原始报告及几何/连接结果已核，不把它当全部环境稳定性验收。

## 后续

剩余22项未连接主要涉及+3V3与地铜区；需逐项按真实几何处理，不默认全部补孔。还剩4条悬空线、2悬空孔、1丝印重叠、8丝印压铜及101项一致性提示。旧生产包未更新；未提交/推送、未下单、未上电。
