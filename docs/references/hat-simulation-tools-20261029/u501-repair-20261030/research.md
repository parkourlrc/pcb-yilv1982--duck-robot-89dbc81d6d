# U501 局部铜修复（2026-10-30）

> 后续检查点：[J301/J506局部冲突已修](../j506-repair-20261030/research.md)。本文24违规及536线段/73孔是U501修复完成当时的结果；当前主板为16项普通warning、23未连接，原始证据不覆盖。

状态：D01 局部修复已验证并更新主 PCB；其他问题仍未解决，禁止投板。用户在确认下一步为 U501 局部修复后回复“继续”；本轮由主会话执行，无 subagent、无硬件操作。

## 依据与修改

按 [真实性复核](../audit-20261030/review.md)的 D01 建立完整副本。KiCad 10.0.7 读取实际焊盘、层和路径，定位后只删除以下对象，未修改原理图、封装、网络、板框、制造规则或其他器件位置。

| 对象 | 坐标 mm（PCB绝对坐标） | 问题与处理 |
|---|---|---|
| POWER_GND F.Cu 短线 | (162.48,108.27)→(162.48,109.12)，宽0.25 | 跨入U501 keepout并逼近pin5；删除 |
| POWER_GND 过孔 | (162.48,109.12)，孔0.3/盘0.6 | 位于U501 keepout；删除 |
| +1V8_CODEC F.Cu 短线 | (159.94,108.27)→(159.55,108.66)，宽0.25 | 碰到U501无网pin1，且顶层末端悬空；删除 |

+1V8_CODEC 的 B.Cu 电容连接、过孔及 In2.Cu 路径保留；不是把1.8V电源断开。U501 的NC焊盘定义保持不变。

修改脚本：[repair_u501.py](../../../../hardware/custom_hat/scripts/repair_u501.py)；连通性核验：[verify_u501_connectivity.py](../../../../hardware/custom_hat/scripts/verify_u501_connectivity.py)。脚本通过UUID、网络、层、区域校验后修改隔离副本；只生成候选，不自动回写。主会话通过完整复核后审阅24行删除差异，用apply_patch同步主板，并比对源指纹。

## 本机离线验证（非硬件实测）

| 检查 | 修复前 | 修复后 |
|---|---:|---:|
| 普通DRC违规 | 29（11 error/18 warning） | 24（7 error/17 warning） |
| 短路 | 1 | 0 |
| 禁布违规 | 2 | 0 |
| 间距违规 | 3 | 2（剩余属于J301/J506） |
| 悬空走线 | 5 | 4 |
| 未连接 | 23 | 23 |
| 原理图一致性项 | 101 | 101 |
| ERC | 0 | 0 |
| 走线段/过孔 | 538/74 | 536/73 |

检查使用同一完整工程、同一规则，重铺铜并启用原理图一致性。不根据总数下降单独判断通过：逐UUID比较违规无新增；有效引脚赋网/契约无新增差异。

初次严格比较发现1对未连接端点UUID变化，候选因此暂未接受。随后在独立完整副本中 `--refill-zones --save-board` 后用 KiCad 连通图核对：193个有网络焊盘原来的同网连接均保留。该变化是U802.5指向同一个+3V3连通组中的短线或其端部过孔，两者修复前后属于同一组；没有据端点换名虚构新增或已修复的连接。验证见 [connectivity-verification.json](connectivity-verification.json)。

## 检查点与回写

- [before.kicad_pcb](before.kicad_pcb)、[after.kicad_pcb](after.kicad_pcb)是精确前后PCB快照，仅用于差异追溯；单独打开不带工程规则，不可独立拿它们跑DRC比较。
- 完整副本路径、源/候选SHA256、删除UUID、回写状态见 [result.json](result.json)。验证主板更新后SHA256与检查过的候选完全一致；现行规则、原理图和库保留原值。
- 原始报告：[before-drc.json](before-drc.json)、[after-drc.json](after-drc.json)、[before-summary.json](before-summary.json)、[after-summary.json](after-summary.json)；快照后的报告不冒充新板功能验收。
- 不同步旧 best、旧实验板或旧生产文件为现行；下一步以主入口继续处理 J301/J506 冲突及23项未连接。

## 图像

[修复前后铜几何对照](u501-before-after.png)由 [render-hat-u501-repair.py](../../../../scripts/render-hat-u501-repair.py)从 geometry-before/after.json 生成，已打开核对。四面板按同一顶视坐标呈现F/B层，底层未镜像，焊盘按外接框近似显示，未显示填充铜/内层；用于局部变化说明，不代替KiCad DRC或实物验收。来源是本项目Rev A源文件，非用户实物照片；已登记照片索引。

## 失败与限制

- 首次采集过孔宽度用无参数GetWidth触发KiCad断言，读取阶段停住；只停止本任务进程，主板未变。改用GetFrontWidth后继续。相关旧运行目录保留，不拿其未完成输出当成功记录。
- KiCad进程输出重复图像handler及SWIG退出警告；已检查源差异、工具返回值和新报告，未将警告描述为所有运行路径稳定。
- 未新增布线、未消除23项未连接、未修J301/J506或全部一致性项；未重新导出生产文件、未提交/推送、未下单/上电。
