# Custom HAT Rev A（设计未完成，不可投板）

现行状态为 [供电/地修复检查点](../../../docs/references/hat-simulation-tools-20261029/power-repair-20261030/research.md)；此前U501、J506、I2S修复和[真实性复核](../../../docs/references/hat-simulation-tools-20261029/audit-20261030/review.md)保留作为历史基线。[修复方案](../../../docs/specs/20261028-custom-hat/recovery-plan.md)维护后续任务。

## 当前文件事实

| 项目 | 本机文件/工具核对 |
|---|---|
| 主入口 | custom_hat_rev_a.kicad_pro / .kicad_sch / .kicad_pcb；六个功能子页 |
| PCB | 65×30 mm 板框、4 层、66 封装（含 6 个双面 fiducial）、615 走线段、94 过孔；709 是线段和过孔合计 |
| 铜区 | F/B POWER_GND、In1 POWER_GND、In2 +3V3，四铜区已存在；不等于全部连接完成 |
| 完整工程重铺铜 DRC | 0 项普通违规、1 项未连接（U701.7 +3V3，error）；一致性另报 107 项（含 6 个装配 fiducial）；仍未通过 |
| ERC | 0，不能替代真实电路、焊盘、PCB 和功能检查 |
| 旧生产包 | 未同步到当前设计，不可下单 |

## 已关闭旧问题

AP64350 独立 1–9 焊盘、BMI088 标准封装及 CSB2 DNC、TTL 两缓冲器与动力分支、I2S 方向、麦克风/功放路径、1.8V LDO、TP802 位置、内层铜区均已有文件级修复。40P pin1 设计侧已有参考依据，不再要求用户重复手量；这些不等于整板或驱动实测通过。

## 仍需修复

- U501周边错误铜/keepout及J301/J506通孔、焊盘/courtyard冲突已修；实物装配高度未验证。
- I2S_SDO已连通，地网包含焊盘的连通组已合一；当前唯一未连接仍是 `R308.2 [+3V3] ↔ U701.7 [+3V3]`。局部标准过孔、右侧绕行和 FreeRouting 候选均因 I2S/裸焊盘/+5V 间距冲突淘汰，详情见 [U701.7 连接复核](../../../docs/references/hat-simulation-tools-20261029/u701-power-20261030/research.md)。不能再用补孔或放宽 DRC 代替 codec 区域联动重排。
- 原理图/板一致性、供电与接口工艺边界和同版生产输出需完成。107 项一致性差异不可当作 107 个真实短路，其中新增 6 项是装配 fiducial footprint。
- 已加入 F.Cu/B.Cu 各 3 个双面 fiducial；KiCad DRC 普通违规保持 `0`，`kicad-happy` 的 `FD-001` 已消除。装配基准位置仍需结合贴片厂工艺确认。
- 已加入 3 个板边 `POWER_GND` 地缝合过孔；候选和主板 DRC 均保持普通违规 `0`，位置与依据见 [地缝合/EMC 复核](../../../docs/references/hat-simulation-tools-20261029/ground-stitch-20261030/research.md)。
- 既有 best、base-clean、fanout-check、via-work 与 ../candidates/ 均不是发布版。

## 工作流程

使用 ../scripts/pipeline.py 建立完整副本并检查；见[流程说明](../scripts/README.md)。不在主板上直接重跑旧布局、补孔或布线实验。每个电路/布局修复须有来源、同规则报告与检查点；通过后才能考虑回写主入口。

已确认功能为供电、TTL、板载 IMU、ToF、播放/录音；屏幕、摄像头、RS485、EEPROM、充电、UPS 不在范围。当前 GPIO 控制 DXL_DIR，不能写成自动换向已验证。默认不提交、不下单、不操作实物。
