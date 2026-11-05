# +3V3 与地连接修复检查点（2026-10-30）

状态：本轮已验证的部分完成并更新主PCB；未连接22→1，最后U701.7的+3V3仍未完成，禁止投板。随后两个悬空过孔和U301丝印已在[warning cleanup](../warning-cleanup-20261030/result.json)中处理，普通DRC已为0。用户对继续处理供电/地回复“继续”；主会话执行，无subagent、无硬件操作、无下单。

## 本机文件依据

起点是[I2S修复检查点](../i2s-sdo-repair-20261030/research.md)，不是旧实验板。完整工程副本、源文件摘要、失败与接受记录见 [state.json](state.json)、[before-summary.json](before-summary.json)。初始+3V3有21个包含焊盘的连通组，POWER_GND有3组。两个地铜孤岛分别包含C310.2、U801.3，不是无用浮铜，不能删岛来消除提示。

## 已采用的修改

1. 删除C323 +5V电容旁重复且悬空的F.Cu短线，保留同位置正确B.Cu路径。
2. C313/C315/C320的三段旧电容短线由F.Cu改回实际焊盘所在B.Cu；每步普通warning减少且未增加未连接。不能据此断言全部旧补孔脚本的所有调用都犯同样错误。
3. 为+3V3未接焊盘规划短引线与连接现有平面的过孔，优先复用既有同网对象；0.2 mm局部引线、0.5/0.3 mm过孔，采用当前项目规则，不改规则、不移动器件。实际连接及回流仍需最终设计评审，不能把DRC连接等同载流验收。
4. C312.1通过同层引线连接已接通的同网过孔，避免再制造新的铜岛。
5. C310.2地岛的缝合位置受BCLK和MCLK短段占用，保留网络和端点做局部绕线后补地孔。U801.3地岛选择更深的岛内点，局部绕开+1V8_CODEC一段线后补地孔。不是改变整个时钟或电源接口。

共接受25个小步骤；涉及19个供电扇出/接线步骤（含复用既有过孔）和2个地岛步骤、4个旧短线修正。最终+20过孔、走线净增82段，主板615走线段/93过孔/60封装/4铜区。原理图、焊盘定义、器件位置和工艺规则未变。重铺铜缓存随候选保存，故文件行差异较大，不代表元件或网络被改写。

## 同规则检查结果（离线工具检查，非硬件实测）

| 项目 | 前 | 后 |
|---|---:|---:|
| 普通DRC | 15 warning | 11 warning |
| 未连接 | 22 error | 1 error（U701.7 +3V3） |
| 原理图一致性 | 101 warning | 101 warning |
| ERC | 0 | 0 |
| +3V3包含焊盘的连通组 | 21 | 2 |
| POWER_GND包含焊盘的连通组 | 3 | 1 |
| 走线段 / 过孔 | 533 / 73 | 615 / 93 |

逐UUID比较普通DRC和parity无新增项；193个有网络焊盘原有连接均保留。有效引脚赋网/契约未新增差异；见 [connectivity-verification.json](connectivity-verification.json) 与 [result.json](result.json)。剩余11项普通warning为2个悬空孔、1丝印重叠、8丝印压铜；四条悬空走线提示已消除。原有101项一致性提示不因本轮视为已解决。

修改先在完整副本中检查，每次报告使用新路径，拒绝的候选恢复前一版。最终审阅连通图、层图、源摘要及差异后才用apply_patch回写主PCB；主板SHA256与完整验收候选一致。前后快照 `before.kicad_pcb` / `after.kicad_pcb` 只用于追溯，单独文件缺工程规则时不能运行DRC比较。

## 失败、纠正及限制

- 初次在同一进程多次读写SWIG对象遇到类型错误，改为每步独立进程；第一个已通过检查点保留，错误阶段未更新主板。
- 旧代码模式用pad.GetLayer()判断SMD层，现场观察该值可返回F.Cu，即使焊盘实际在B.Cu；因此改用footprint.GetLayer()并核pad.IsOnLayer()。新候选中出现的悬空短线被逐项DRC拒绝并回退。记录保留，不误写为板密度问题。
- 找到“位于原填充区”的过孔不保证重铺铜后连接改善：一些候选接上目标同时分割地铜，未连接未下降，故拒绝。后续改落孔位置或复用既有过孔；不是只看新增铜数量。
- 同网铜不需要被当异网隔离；搜索先保守处理，再区分同网孔与焊盘/钻孔留量。边缘地孔候选未改善，选地岛内部位置并绕开障碍后才通过。
- C310与U801局部绕线经真实DRC和全板连通比较，没有用几何近似取代KiCad检查。
- 最后一项U701.7尝试了局部连接及SDI/SDO联动规划，随后对预留供电过孔位置的四个I2S信号24种顺序进行了有界搜索，均未获得完整方案；**没有写入主板或接受副本**。这是该候选位置/有限搜索的失败，不证明必须换层数、删音频或PCB无解。见 codec-searches.json 与相关search-failure*.json；下一步需重新设计该供电/信号扇出的局部几何。
- `plan_i2s_sdo`的失败输出原先仍指向I2S专题，发现后规划输出改为本专题；后期codec-searches保存在本目录。此前I2S通过报告和主板变更未被这些失败输出覆盖。
- native CLI与SWIG仍有重复图像handler/退出提示；实际命令返回、报告、源摘要已核，不宣称所有环境路径稳定。
- 大量行差异来自重新填充铜缓存；第一次取得整份diff超工具返回限额，未修改主文件。随后完整分块读出同一差异再apply_patch，回写后哈希与已核候选一致。

## 工具、图像和后续

- [repair_power_connections.py](../../../../hardware/custom_hat/scripts/repair_power_connections.py)：完整副本和基线清点。
- [power_repair_steps.py](../../../../hardware/custom_hat/scripts/power_repair_steps.py)：逐步DRC接受/回退。
- [power_plane_fanout.py](../../../../hardware/custom_hat/scripts/power_plane_fanout.py)：区分真实焊盘层，规划到平面/既有同网对象的引线；搜索只是候选生成。
- [stitch_ground_island.py](../../../../hardware/custom_hat/scripts/stitch_ground_island.py)、[power_local_detour.py](../../../../hardware/custom_hat/scripts/power_local_detour.py)：地岛候选及局部绕线。
- [finish_codec_power.py](../../../../hardware/custom_hat/scripts/finish_codec_power.py)：未成功的U701.7方案，仅实验；不可视为已完成步骤。
- [verify_power_repair.py](../../../../hardware/custom_hat/scripts/verify_power_repair.py)：完整DRC、网表、原有焊盘连接保持核验。
- [正式对照图](power-route-review.png)：[render-hat-power-repair.py](../../../../scripts/render-hat-power-repair.py)从前后geometry JSON生成，已打开检查；全部顶视坐标、底层未镜像，焊盘外接框近似，未画填充铜。`inspection-current.png`是中间检查草图，标题/局部边缘可能截断，仅留追溯。不是用户实物照片，不作载流、制造或上电依据，已登记照片索引。
- runs目录为本地完整副本，各步报告与接受/拒绝板保留在那里；永久归档本目录的最终报告、基线、计划、状态与快照。主板SHA256为 `d6ae5782164a3b442b1f00db9ab3a9d5f941a70bed85fb3844c39afd53eac99e`，等于最后验收候选；新完整副本检查复现11项warning、1项未连接、101项parity。没有自动提交或下单。

下一步明确为U701.7 +3V3，不再重做已通过的地岛和其他电源扇出；制造工艺/实际音频和总线功能仍未验收。
