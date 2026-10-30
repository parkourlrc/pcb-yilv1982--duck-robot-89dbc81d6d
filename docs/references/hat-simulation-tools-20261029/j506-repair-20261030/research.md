# J301/J506 局部布局修复（2026-10-30）

> 后续已完成[I2S_SDO修复](../i2s-sdo-repair-20261030/research.md)。本文16项普通warning及23未连接为J506检查点结果；当前主板为15项普通warning及22未连接。前后原始报告不覆盖。

状态：D02 局部冲突已修并更新主PCB；仍不可投板。用户对继续处理J301/J506冲突回复“继续”，本轮主会话执行，不使用subagent。

## 几何依据及范围

- 来源：现行Rev A PCB和本地KiCad封装。J506为 `JST_SH_BM02B-SRSS-TB_1x02-1MP_P1.00mm_Vertical`，位于B.Cu、0°，不是横向出线座。本轮保留型号、朝向、针序、其他器件与制造规则。
- J301正面通孔排的courtyard为(106.535,125.505)–(127.945,129.135)，其贯穿焊盘与原J506的MP固定焊盘重叠；原J506中心(113.43,126.05)。
- 新J506中心(113.0,122.3)，移动Δ=(-0.43,-3.75) mm；courtyard为(110.055,119.655)–(115.945,124.945)。相邻R309的courtyard从x=116.065开始，相隔0.12 mm；J301 courtyard上边y=125.505，与新J506下边相隔0.56 mm。
- J402位于F.Cu，其器件外形不能整个视为B.Cu实体障碍；检查其贯穿焊盘、钻孔和安装孔，保持两面元件区分。完整DRC未报告新的贯穿孔/底面courtyard冲突。
- 这些是布局文件几何，不是整机装配高度或实物插拔验收；SH座及线束的最终供货、装配空间仍按交付条件核查。没有因本轮局部通过而宣称整板可制造。

## 实施与第一次失败

1. 用新pipeline生成完整副本并核基线24违规+23未连接+101一致性项。
2. 只移动J506并重接两条喇叭线端点。第一候选机械冲突消失，但SPK_N斜线穿过新位置的MP焊盘，产生短路与阻焊桥，**未接受、未回写**。
3. SPK_N改为经插座焊盘之间的通道：(113.5,120.975)→(113.5,124.5)→(113.725,124.725)→(117.0853,124.725)，保持0.25 mm与B.Cu；SPK_P保留其原有网络路径，仅延长接座端段。
4. 同规则重铺铜验证、焊盘连通图复核、对照图及精确文件差异审阅后，源指纹仍等于基线才回写主PCB。实际差异仅J506中心、两条端线及两段新增折线（19行新增、3行替换删除）。

脚本：[repair_j506.py](../../../../hardware/custom_hat/scripts/repair_j506.py)、[finish_j506.py](../../../../hardware/custom_hat/scripts/finish_j506.py)。它们操作完整候选，主会话最后审阅后用apply_patch同步主板，不自动覆盖主板。第一次失败数据在 `attempt1-*` 中保留。

## 验证（本机离线工具检查，非硬件实测）

| 项目 | 修改前 | 修改后 |
|---|---:|---:|
| 普通DRC | 24（7 error/17 warning） | 16（全warning） |
| 间距 / PTH侵入courtyard / 阻焊桥 | 2 / 3 / 2 | 0 / 0 / 0 |
| 短路 / 新courtyard冲突 | 0 / 0 | 0 / 0 |
| 丝印压铜 | 9 | 8 |
| 未连接 | 23 | 23 |
| 原理图一致性项 | 101 | 101 |
| ERC | 0 | 0 |
| 走线段 / 过孔 | 536 / 73 | 538 / 73 |

按UUID逐项比较，未新增普通DRC或原理图一致性项。两份完整工程副本重铺铜保存后，用KiCad连通图比较193个有网络焊盘，原有连接无丢失；实际导出网表与板焊盘/契约无新差异。详见 [connectivity-verification.json](connectivity-verification.json)、[after-summary.json](after-summary.json)、[result.json](result.json)。回写后主PCB的SHA256与已验证候选完全相同。

## 证据、图片及限制

- [before.kicad_pcb](before.kicad_pcb) / [after.kicad_pcb](after.kicad_pcb)仅为前后差异快照；单独快照缺工程规则，不据此运行DRC比较。完整副本路径与哈希见result.json，规则/原理图/库均未修改。
- [before-drc.json](before-drc.json) / [after-drc.json](after-drc.json)与对应summary/erc保存实际命令及结果。16项普通警告仍为4条悬空线、3悬空孔、1丝印重叠、8丝印压铜；23项未连接仍是error。不能把“普通几何error为0”写成“DRC已通过”。
- [前后底层对照图](j506-before-after.png)由 [render-hat-j506-repair.py](../../../../scripts/render-hat-j506-repair.py)从geometry-before/after.json生成，已打开检查。两幅均采用顶视坐标，底层未镜像，焊盘外接框近似，未显示铺铜，非实物照片。已登记照片索引。
- `before-inspection.png`是此前使用U501图形函数临时生成的宽视野检查草图，坐标标注不完整，不作正式对照或接线依据；正式图为上方j506-before-after.png。
- 封装描述含JST手册链接 `https://www.jst-mfg.com/product/pdf/eng/eSH.pdf`；本轮web打开未返回可用正文，未声称重新核验厂商尺寸。几何数据取自当前KiCad封装与DRC。
- KiCad进程有重复图像handler提示；命令和报告完成，未据此宣称所有运行路径稳定。
- 未新增功能、未改变原理图、未更新旧生产文件、未提交/推送、未下单或操作实物。下一步处理剩余23项未连接，不能盲目全量补孔。
