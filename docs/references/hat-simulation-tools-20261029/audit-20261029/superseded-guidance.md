# 已废弃指导存档（2026-10-29）

仅用于追溯，不可用于制作、装配或上电。现行见 review.md 和 recovery-plan.md。


## hardware/custom_hat/README.md

# custom_hat KiCad 工程骨架

本目录是 HAT 首版方案的原理图阶段工作副本。当前仅建立 KiCad 工程文件和功能页占位，**没有 PCB、没有最终器件封装、没有投板生产文件**。

## 文件

- `custom_hat.kicad_pro`：KiCad 工程配置。
- `custom_hat.kicad_sch`：主原理图入口（当前为可打开的骨架页）。
- `power.kicad_sch`、`radxa_40p.kicad_sch`、`servo_ttl.kicad_sch`、`head_imu_tof.kicad_sch`、`screen_spi.kicad_sch`、`camera_csi.kicad_sch`、`audio.kicad_sch`、`testpoints.kicad_sch`：功能页工作副本。电源/TTL/头部传感器/Radxa/CSI/屏幕页分别注明来源和核验边界；尚未组成新板最终层级网表。
- `DESIGN_NOTES.md`：本轮信号分配、占位和未决项。

当前骨架沿用本项目已有 KiCad 10 可读的 `.kicad_sch` 语法样例，仅用于先固定工程目录和模块边界；复制的示例符号不代表已经选定香蕉座、封装或电路连接。


## hardware/custom_hat/rev_a/README.md

# Custom HAT Rev A（功能页接口草案）

这是一个独立的 KiCad 10 工程，用于把已确认的 HAT 需求拆成可审查的扁平功能页。

## 已生成

- `radxa_40p.kicad_sch`：Radxa ZERO 3W 40P 与 SPI/I2C/I2S/UART 网络契约。
- `power.kicad_sch`、`servo_ttl.kicad_sch`、`imu_tof.kicad_sch`、`audio.kicad_sch`、`testpoints.kicad_sch`：电源、飞特 TTL、BMI088/ToF、音频和测试点接口草案。
- `net-contract.json`：所有页的 pin-to-net 契约。
- `rev_a.pdf`：原理图 PDF 导出。
- `erc.rpt`：当前 Rev A ERC 报告。
- `simulation/`：电源反馈/负载预算与 TTL RC 参数扫描的可运行前置仿真（方程级，不是 SPICE）；AP64350 的等效开关仿真见 `docs/references/hat-simulation-tools-20261029/ap64350_equivalent.cir`。

## 当前状态

2026-10-29：**摄像头与屏幕已去掉**，工程从 8 页减到 6 页、器件 28→25；CSI 直通与屏幕排线口不再实施。

2026-10-29 更新：电源页已按 **AP64350** 重画引脚契约（1 BST / 2 VIN / 3 EN / 4 RT/CLK / 5 FB / 6 COMP / 7 GND / 8 SW），并加入 RT=200k、FB 52.3k/10k、COMP 14k+3.3nF、BOOT 100nF、5.5µH、2×10µF 输入、2×22µF 输出（`C307` 22µF 留位 DNP）、EN 100k 上拉和 **已确定贴装的 SMBJ12A 输入 TVS**。

**ERC 违规为 0**。此前 171 条 off-grid 由 1.27 mm 网格吸附消除；剩余 7 条单脚标签也已在 2026-10-29 处理：codec 的 `DVDD1V8`/`AVDD3V3` 改接 `+1V8_CODEC`/`+3V3`，BMI088 的 INT2/CSB2/INT4 改显式 no-connect，INT1/INT3 接到新增 `J802` 测试点。**ERC 清零不等于电路正确**，功能页仍是引脚契约级草案。

功能页中仍有器件级占位：TTL 半双工收发器、BMI088 去耦、音频 codec/功放、测试点封装均未完成（屏幕与 CSI 已去掉）。

## PCB 骨架（2026-10-29）

- `custom_hat_rev_a.kicad_pcb`：65 × 30 mm 板框（与 Radxa Zero 3W 同尺寸）+ 4 个 M2.5 安装孔（Pi Zero 标准）；电源区 17 个器件在板内，其余 11 个暂存在板上方三行。由 `scripts/build_pcb_rev_a.py` 生成。
- `drc.rpt`：**116 条 = 113 条 `unconnected_items`（未布线）+ 3 条丝印**；无短路、间距、孔距或外框重叠。
- 封装：TTL EH 3P、ToF SH 4P、codec VQFN-32、测试点均已分配；**BMI088 已按 Bosch 手册自建 `duck:Bosch_LGA-16_3x4.5mm_P0.5mm`**（4.5×3 mm、0.5 mm 间距、0.30×0.25 焊盘），工程内有 `fp-lib-table` 与 `duck.pretty`。
- 未布线、未铺铜、未出 Gerber/BOM/CPL。`U301` 用 PowerPAK SO-8 近似；安装孔与 `J101` 已按 Radxa 官方 2D 图纸（`radxa_zero_3w_2d_dxf.zip`）直接采用 Radxa DXF 原值：2.05/4.59 mm 两排、8.32…56.58 mm 列（板高同为 30 mm）；**图纸无引脚编号，pin 1 端仍是假设**，首板前须用实物通断确认。

2026-10-29 勘误：旧方程脚本的电源预算漏计 Radxa、TTL 参数未核验，不能作为 HAT 通过结论或 33Ω 选型依据。厂商 AP64350 PSpice 模型无法在 ngspice 47 运行，已改用等效开关模型；详见[工具记录](../../../docs/references/hat-simulation-tools-20261029/research.md)。

## 生成

`python hardware/custom_hat/scripts/generate_rev_a.py`

RS485、识别 EEPROM、充电和 UPS 已明确排除。


## hardware/custom_hat/rev_a/production/README.md

# Rev A 生产文件（链路试跑，不可下单）

本目录是一次**文件链路验证**：证明从 KiCad 工程能导出嘉立创需要的格式。**当前板子未布线、器件未装完，不能发给嘉立创。**

2026-10-29 范围变更：摄像头与屏幕已去掉；随后补了 6 个贴片测试点与 1.8 V LDO，器件总数 **33**。

## 文件清单

| 文件 | 内容 | 说明 |
|---|---|---|
| `custom_hat_rev_a-F_Cu.gtl` | 顶层铜 | 4 层板 |
| `custom_hat_rev_a-In1_Cu.g1` | 内层 1 | 目前为空（未铺铜） |
| `custom_hat_rev_a-In2_Cu.g2` | 内层 2 | 目前为空（未铺铜） |
| `custom_hat_rev_a-B_Cu.gbl` | 底层铜 | |
| `custom_hat_rev_a-F_Mask.gts` / `-B_Mask.gbs` | 阻焊 | |
| `custom_hat_rev_a-F_Silkscreen.gto` / `-B_Silkscreen.gbo` | 丝印 | 含 40P 的 “1” 标记 |
| `custom_hat_rev_a-Edge_Cuts.gm1` | 板框 | 65 × 30 mm |
| `custom_hat_rev_a.drl` | 钻孔 | Excellon，公制，绝对原点 |
| `custom_hat_rev_a-cpl.csv` | 贴片坐标 | 原点 = 钻孔原点，Y 为负（KiCad 约定） |
| `custom_hat_rev_a-bom.csv` | 物料表 | 只到 value/footprint，**LCSC 列空** |
| `custom_hat_rev_a-job.gbrjob` | Gerber 作业文件 | 包含层映射 |
| `custom_hat_rev_a-gerber.zip` | **上传用打包** | 11 个层/钻孔文件 |

## 生成方式

```text
kicad-cli pcb export gerbers --layers F.Cu,In1.Cu,In2.Cu,B.Cu,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts ...
kicad-cli pcb export drill --format excellon --drill-origin absolute ...
kicad-cli pcb export pos --format csv --units mm --use-drill-file-origin ...
python hardware/custom_hat/scripts/bom_from_netlist.py
```

## 现在不能下单的原因

1. **地网缝合未收尾**：DRC 5 条，全部是地铺铜连通判定；无短路/间距/线宽问题。
2. **器件**：33 个全部落板（正 28、背 5），双面贴装。
3. **BMI088 封装是错的**：现在用 `LGA-16_3x3mm`，实际是 3 × 4.5 mm。
4. **无铺铜**：内层两层是空的，电源/地平面还没做。
5. **`U301` 用 PowerPAK SO-8 近似**：未与 Diodes 官方 SO-8EP 焊盘图比对。
6. **BOM 没有立创编号**：物料未选型，价格与库存未核。

## 下单前需要补齐

- 补 5 处缝合过孔让 DRC 归零；
- **外层铜指定 2 oz**：0.6 mm 线宽在 1 oz 只有 1.64 A，不足以支撑 5 V 轨；
- 铺铜（至少 GND 平面）与电源载流核算；
- 全部器件封装核对（尤其 BMI088、SO-8EP、连接器方向）；
- BOM 补 LCSC 编号、确认库存；
- 板厚、表面处理、阻抗要求写进下单备注。

## CPL 原点提醒

坐标用的是“钻孔原点”，坐标为负值属于 KiCad 导出惯例。上传嘉立创前要在平台里核对方向与原点，必要时把 Y 取反或选“以板左下角为原点”。**不同平台对 CPL 的约定不一致，这一步必须人工确认，不能照传。**


## docs/specs/20261028-custom-hat/order-checklist.md

# Rev A 嘉立创下单检查单

> 状态：**不能直接下单**。文中标注了必须人工收尾的项。本文件是流程清单，不是放行许可。

## 1. 当前设计状态

| 项 | 状态 |
|---|---|
| 原理图 | 6 页，ERC 0 |
| PCB | 4 层，65 × 30 mm，33 个器件（正 28 / 背 5） |
| 布线 | 已自动布线；电源 0.6 mm、信号 0.25 mm |
| DRC | **5 条，全部是地铺铜连通判定**（无短路/间距/线宽/孔问题） |
| 生产文件 | Gerber 10 层文件 + 钻孔 + CPL + BOM 已生成 |
| BOM | 29 行 / 32 件，**LCSC 编号为空** |

## 2. 下单前必须完成的四件事

1. **补缝合过孔**：在 KiCad 里给 F.Cu/B.Cu 地铺铜之间的 5 处判定补过孔，直到 DRC 归零。
   自动流程试过空位打孔、网格打孔、加 In1 地平面，都不能消除（板面被 0.6 mm 电源线占满）。
2. **核对 BMI088 封装**：`duck:Bosch_LGA-16_3x4.5mm_P0.5mm` 是按数据手册建的，但焊盘宽度取了 0.30 mm（手册推荐值未明确），首板前建议对照 Bosch landing pattern 再确认一次。
3. **BOM 补 LCSC 编号**：按 `production/custom_hat_rev_a-bom.csv` 逐项选型，确认库存与价格。
   关键器件：AP64350（SO-8EP）、LP38693DT-1.8（TO-252）、TLV320AIC3104（VQFN-32）、BMI088（LGA-16）、SMBJ12A、JST EH 3P、JST SH 4P、22P FPC 座。
4. **确认 2 oz 铜**：见下方参数表——0.6 mm 线宽配 1 oz 只有 1.64 A，不够 5 V 轨的 2–2.5 A。

## 3. 上传文件

| 文件 | 用途 |
|---|---|
| `production/custom_hat_rev_a-*.g*` + `.drl` + `.gbrjob` | 打样（打包成 zip 上传） |
| `production/custom_hat_rev_a-bom.csv` | SMT 物料 |
| `production/custom_hat_rev_a-cpl.csv` | SMT 坐标（含 `Side=bottom` 的 5 行） |

## 4. 板参数

| 参数 | 值 | 说明 |
|---|---|---|
| 层数 | **4** | 内层目前无走线，仅作参考平面 |
| 尺寸 | 65 × 30 mm | 与 Radxa Zero 3W 一致 |
| 板厚 | 1.6 mm | 与 40P 座高度匹配 |
| 外层铜 | **2 oz** | 5 V 轨载流需要；务必在备注注明 |
| 内层铜 | 1 oz | |
| 表面处理 | 有铅/无铅喷锡（HASL） | 无阻抗要求 |
| 最小线宽/间距 | 0.15 / 0.15 mm | 设计值；个别 0.10 mm 短段 |
| 过孔 | 0.3 mm 钻 / 0.6 mm 盘 | |
| 阻焊/丝印 | 绿色/白色 | 无特殊要求 |
| 特殊 | **双面贴装** | 背面有 codec、LDO、ToF 座、电容 |

## 5. 下单步骤（嘉立创）

1. 进入 PCB 下单页，上传 Gerber zip，确认层数识别为 4 层、尺寸 65 × 30。
2. 选 2 oz 外层铜、1.6 mm、HASL、绿色阻焊。
3. 勾选 SMT，上传 BOM 与 CPL；**核对平台识别出的元件位号、封装与方向**。
4. 查看 3D 预览：重点看背面 5 个器件是否与正面焊盘冲突、40P 座方向。
5. 确认价格与交期后**再付款**（本流程不代付）。

## 6. 收到板后的首轮检查

1. 目视：40P 座方向、丝印 “1” 标记、屏幕/CSI 已取消无需检查。
2. 万用表：pin1↔pin17 通（3.3 V）、pin2↔pin4 通（5 V）、GND 与各电源不短。
3. 限流上电（建议 100 mA 起），先测 5 V 轨，再测 3.3 V/1.8 V。
4. 通过后再插 Radxa，逐项验证 IMU、ToF、音频、舵机总线。

## 7. 已知风险

- **5 处地网缝合未收尾**：不补过孔，地平面可能被分割，EMI 与回流变差（功能通常仍能工作）。
- **载流**：0.6 mm 在 2 oz 下约 3.3 A；若实际电流超 2.5 A，需重新评估。
- **自动布线质量**：线宽/间距按规则通过，但未做阻抗、电源完整性、回流路径优化。
- **BMI088 焊盘宽度**：0.30 mm 为保守取值，未与官方 landing pattern 逐项比对。


## 原 PROGRESS 自设计 HAT 流水

## 自设计 HAT：参考盘点与需求草案（2026-10-28）

- **[Radxa 图纸核对，2026-10-29]** 从 Radxa 官方 `dl2.radxa.com/zero3/docs/hw/3w/` 下载 `radxa_zero_3w_2d_dxf.zip` 并解析：安装孔在 (3.6,3.6)/(61.4,3.6)/(3.6,26.5)/(61.4,26.5)，40P 焊盘两排距上边 **2.05/4.59 mm**、列 **8.32…56.58 mm**。并用官方 HAT 的 `J4` 通孔阵列（8.4…56.66、3.16/5.70）交叉校核：两板以下边对齐时相差 0.16 mm。用户确认本板与 Radxa 同尺寸对插，板框改为 **65×30**，40P 直接采用图纸原值 **row 2.05/4.59**，`J101` pad1=(8.32,2.05)；DRC 118 条 = 113 未布线 + 5 丝印。**图纸无引脚编号，pin 1 端仍是假设**，首板前须用实物通断确认。详见[第 16 节](docs/references/hat-simulation-tools-20261029/research.md)。

- **[恢复音频输出 + 四种收敛尝试，2026-10-29]** 用 JST SH 1.0mm 3P（J504）+ 0402 耦合电容恢复音频输出，测试点减到 3 个，ERC 0。四种尝试均未收敛：6 层叠层无差别、电源扇出更差（31）、GND 走线最差（64）、多次取优最优 24 本次 36。判断瓶颈是**电源焊盘到平面的连接**。剩余项已导出[清单](docs/specs/20261028-custom-hat/remaining-fixes.md)。详见[第 45 节](docs/references/hat-simulation-tools-20261029/research.md)。

- **[+3V3 铺铜与音频输出取舍，2026-10-29]** 背面加 +3V3 铺铜后未连接 26→20；删除音频输出（J503/C317/C318）后器件 44→41。IMU 的 4 个地脚经**路径检查**证实 3 个无干净出路，盘中孔又会触发环宽/短路，已回退。当前 DRC **23（19 未连接 + 3 悬空 + 1 间距）**。**注意：codec 只剩数字侧，听不到声音**——要真正输出需 6 层板或移出连接器。详见[第 43 节](docs/references/hat-simulation-tools-20261029/research.md)。

- **[44 器件布线未收敛，2026-10-29]** 补全 codec 后器件 33→44，布线明显恶化。试过 0402 阻容、电源线 0.4mm、间距 0.15（回退）、DRC 驱动自动补孔（产生 211 条违规，回退）。未连接集中在**背面 +3V3/GND 电源脚**（布线器没打孔）。当前 28 条（24 未连接 + 4 悬空过孔），无短路/间距/线宽问题。判断为容量上限，下一轮考虑改布局或上 6 层板（需用户确认成本）。详见[第 42 节](docs/references/hat-simulation-tools-20261029/research.md)。

- **[codec 换真实符号，2026-10-29]** 复核发现 U701 是 12 脚通用占位符号，33 个焊盘只有 12 个有网——**音频此前根本没接**。按 TI IBIS 的 [Pin] 表重建 32 脚符号（`duck.kicad_sym`），补 R308/C310–C318/J503 共 9 件；同时修 BMI088 的 CSB2 悬空。ERC 归 0。代价：44 器件塞进 65×30 后自动布线退化（未连接 20–26、track_width 40+），**PCB 暂不可交付**，下一轮重做布局。详见[第 41 节](docs/references/hat-simulation-tools-20261029/research.md)。

- **[装配说明 + 首板测试计划，2026-10-29]** 新增 [assembly-notes](docs/specs/20261028-custom-hat/assembly-notes.md)（贴装顺序、J101/D301/U501 方向检查、C307 DNP、与旧板差异）与 [first-article-test](docs/specs/20261028-custom-hat/first-article-test.md)（四阶段：空板限流→插 Radxa→总线→整机，含“不可同时 USB-C 与 HAT 双供电”的安全规则）。spec 索引状态已更新。详见[第 40 节](docs/references/hat-simulation-tools-20261029/research.md)。

- **[打包与制造说明，2026-10-29]** 生产目录新增 `custom_hat_rev_a-gerber.zip`（11 文件，可直传），PCB 内写入制造说明（4 层 / 65×30 / 1.6 mm / **外层 2 oz** / HASL / 双面贴装）。地网缝合最后尝试：F 层仅 1 个岛、B 层 2 个，补 1 个过孔后 DRC 仍 5 条，确认需人工收尾。详见[第 39 节](docs/references/hat-simulation-tools-20261029/research.md)。

- **[BOM 选型表，2026-10-29]** LCSC 无可稳定调用的公开接口（404 / Access Denied / 前端渲染），未编造编号。改为新增[BOM 选型建议](docs/specs/20261028-custom-hat/bom-selection.md)：按位号列出制造商型号、封装、参数与三条硬约束（C303/C304 50 V、L301 饱和 ≥5 A、U301 焊盘需复核）。详见[第 38 节](docs/references/hat-simulation-tools-20261029/research.md)。

- **[地网收尾尝试 + 下单检查单，2026-10-29]** 试了“GND 走线”和“加 In1 地平面”两种方案消除剩下 5 条地网判定，均无效——只能人工补缝合过孔。当前 DRC **5 条全是地网连通**，短路/间距/线宽/孔为 0。新增[下单检查单](docs/specs/20261028-custom-hat/order-checklist.md)：4 层、65×30、1.6mm、**外层 2 oz 铜**、HASL、双面贴装，并列明下单前必须完成的 4 件事。详见[第 37 节](docs/references/hat-simulation-tools-20261029/research.md)。

- **[载流核算 + 0.6mm 电源线，2026-10-29]** 按 IPC-2221 算：0.6 mm 在 1 oz 只有 1.64 A、2 oz 有 3.3 A。本板 5 V 轨 2–2.5 A，因此**必须外层 2 oz 铜**（下单要注明），线宽定 **0.6 mm**；0.8 mm 在四层板上路由不下（12–13 个未连接）。最终 DRC **5 条，全是地铺铜连通判定**，短路/间距/线宽/孔为 0。详见[第 36 节](docs/references/hat-simulation-tools-20261029/research.md)。

- **[电源网络加宽到 0.5mm，2026-10-29]** 发现自动布线把所有线都按 0.25 mm 走（netclass 存在工程文件，pcbnew 导 DSN 时不带）。改为在 DSN 里注入 `kicad_power` 类（500 µm），电源网实测 **0.50 mm**；配合 50 轮与三次取优，**DRC 3 条**（全为地铺铜连通判定）。0.8 mm 时因板面过密导致 13 个未连接，退到 0.5 mm。详见[第 35 节](docs/references/hat-simulation-tools-20261029/research.md)。

- **[自动布线跑通，2026-10-29]** 用 **FreeRouting 2.5.0 jar + Temurin JRE 25**（便携解压）跑通自动布线，流程封装为 `scripts/pipeline.py`（重建→导出 DSN→布线→导入 SES→放宽规则与铺铜）。布线结果随机，用“多跑取最优”选最好一次：**DRC 从 73 降到 1 条**（仅剩 F/B 地铺铜连通判定，需人工加一个缝合过孔）。隐藏安装孔/测试点/IMU 位号后丝印违规归零。生产文件已重出，Gerber 含实际走线。详见[第 34 节](docs/references/hat-simulation-tools-20261029/research.md)。

- **[补 1.8V LDO + 电源标志，2026-10-29]** 新增 `U702` LP38693DT-1.8（+3V3→+1V8_CODEC，TO-252，背面）+ C308/C309 1µF，补上 codec 1.8 V 供电缺口。加 4 个 `PWR_FLAG` 消除 `power_pin_not_driven`，ERC 归 0。BOM 脚本排除 PWR_FLAG 与 DNP 预留位，现 **29 行 / 32 件**。DRC 69→**73**（新增 3 器件 8 个待连点），未连接 59→**63**，无短路/间距/重叠。详见[第 33 节](docs/references/hat-simulation-tools-20261029/research.md)。

- **[地网合并 + 贴片测试点，2026-10-29]** 发现并修正两处连接错误：Radxa 的 `GND` 与板上 `POWER_GND` 是两个地网、`+3V3_HAT` 与 Radxa `+3V3` 是两个孤立 3.3 V 轨——已统一。`J801` 改 6 个贴片测试点（TP801–TP806），**30 个器件全部落板、板外暂存 0**。DRC 73→**69**，未连接 66→**59**。同时发现 `+1V8_CODEC` 无供电来源，下一轮补 XC6206 LDO。详见[第 32 节](docs/references/hat-simulation-tools-20261029/research.md)。

- **[测试点改 2×3 + 地铺铜，2026-10-29]** J801 从 2×4 改 **2×3**（6 个关键点），并清掉已无源端的 `CAM_3V3_IN`。F.Cu/B.Cu 各加整板 **GND 铺铜**（实心连接），`unconnected_items` 82→**66**，DRC 89→**73**。J801 仍放不下（通孔件不能上背面，正面无空位），下一轮改贴片测试焊盘。详见[第 31 节](docs/references/hat-simulation-tools-20261029/research.md)。

- **[双面贴装布局，2026-10-29]** 正面排满后，把 **J502（ToF）与 U701（codec）移到背面 B.Cu**，正面 22 件、背面 2 件、板外暂存 1 件（J801）。CPL 已验证输出 `Side=bottom`。DRC **89 = 82 未布线 + 7 丝印**，无短路/间距/孔距/重叠。修了三个 bug：通孔器件误翻面、通孔禁布区用旧快照、批量替换导致缩进错误。详见[第 30 节](docs/references/hat-simulation-tools-20261029/research.md)。

- **[连接器自动布局，2026-10-29]** 手工摆放反复踩坑（短路/压孔/外框重叠），改为脚本化：固定电源块 16 件，其余按期望位置在 1.27 mm 网格搜索并校验板内、孔禁布、courtyard 不重叠。结果板内 **22 件**、板外暂存 3 件（J801/J502/U701），DRC **88 = 82 未布线 + 6 丝印**，无短路/间距/孔距/重叠。无源器件位号不再上丝印，噪声从 13 降到 6。详见[第 29 节](docs/references/hat-simulation-tools-20261029/research.md)。

- **[BMI088 封装修正，2026-10-29]** 从 Bosch 官方手册（BST-BMI088-DS000-19）取 landing pattern，自建 `duck:Bosch_LGA-16_3x4.5mm_P0.5mm`（0.30×0.25 焊盘、0.5 间距），加工程 `fp-lib-table`（必须无 BOM）。ERC 回到 **0**。一次性摆全部连接器的尝试产生 174 条 DRC（重叠/孔距/阻焊桥），已回退到电源块状态（89 条），连接器布局改为分组迭代。详见[第 28 节](docs/references/hat-simulation-tools-20261029/research.md)。

- **[需求收缩：去掉摄像头与屏幕，2026-10-29]** 删除 `screen_spi`、`camera_csi` 两页，功能页 8→**6**，器件 28→**25**；40P 的 11/15/22/24（LCD）与 19/21/23（SPI）改为不连接。ERC 仍 0，DRC 120→**89（82 未布线）**。CSI 直通与屏幕 FPC 避让不再需要，生产文件已重出（25 器件 / 23 行 BOM）。详见[第 27 节](docs/references/hat-simulation-tools-20261029/research.md)。

- **[生产文件链路试跑，2026-10-29]** 板层数改为 **4 层**，导出 Gerber（10 层文件 + job）、钻孔、贴片坐标、BOM（26 行/28 器件，LCSC 留空）。命令全部成功，说明导出链路通；但**不可下单**：未布线 113 条、12 个器件仍在暂存区、BMI088 封装错误、无铺铜。详见[第 23 节](docs/references/hat-simulation-tools-20261029/research.md)与[production/README](hardware/custom_hat/rev_a/production/README.md)。

- **[PCB 第二轮，2026-10-29]** 补齐全部功能页封装（屏幕 14P、TTL EH 3P、ToF SH 4P、CSI FH12 22P、codec VQFN-32、测试点）；加 4 个 M2.5 安装孔（Pi Zero 标准）与 40P 定位；其余 11 个器件放暂存区。DRC **116 条 = 113 条未布线 + 3 条丝印**，无短路/间距/孔距问题。BMI088 仍用 3×3 占位封装，40P 坐标未按 Radxa 图纸核对。详见[第 15 节](docs/references/hat-simulation-tools-20261029/research.md)。

- **[PCB 骨架，2026-10-29]** 给电源页分配真实封装（SO-8EP 近似、SMB、0805/1206、12×12 电感），用 KiCad `pcbnew` 生成 65×30.9 mm 板框与电源区布局：`custom_hat_rev_a.kicad_pcb`。DRC 从 54/72/44 收敛到 **33 条，全部是未布线（unconnected_items）**，无短路/间距/重叠。仅放置 16 个器件，屏幕/TTL/IMU/CSI/音频尚未进板，未布线、未出 Gerber。详见[第 14 节](docs/references/hat-simulation-tools-20261029/research.md)。

- **[三项决定落实，2026-10-29]** 用户授权决定：① 输入 TVS **贴** SMBJ12A（防御性，插拔峰值 14–16V 未超 35V 绝对最大）；② 输出电容 **2×22µF 贴装 + C307 22µF 留位 DNP**；③ codec 的 `DVDD1V8`/`AVDD3V3` 接到实体轨（`+1V8_CODEC`、`+3V3`）；④ BMI088 的 INT2/CSB2/INT4 改显式 NC，INT1/INT3 接新增 `J802` 测试点。结果：**ERC 违规归零**，已重出 PDF/网表并渲染核对。详见[第 13 节](docs/references/hat-simulation-tools-20261029/research.md)。

- **[电源页改 AP64350 + ERC 复跑，2026-10-29]** 电源页按 AP64350 重画（1 BST/2 VIN/3 EN/4 RT/CLK/5 FB/6 COMP/7 GND/8 SW），加入 RT 200k、FB 52.3k/10k、COMP 14k+3.3nF、5.5µH、2×10µF 输入、2×22µF 输出、EN 上拉与 SMBJ12A TVS 候选；生成器加 1.27mm 网格吸附后 **ERC 从 171 条降到 7 条**，全部是单脚 NC 网络。插拔瞬态检查：1–10µH 电缆下峰值 14–16V，低于 35V 绝对最大，TVS 属防御性。已重出 `rev_a.pdf` 与网表。详见[第 12 节](docs/references/hat-simulation-tools-20261029/research.md)。

- **[电源选型改 AP64350 + 等效仿真跑通，2026-10-29]** 用户决定改用 AP64350。厂商 PSpice 模型在 ngspice 47 **实测无法运行**（8 组配置全失败；RT/CLK 已按手册改为 200k=500kHz）；本会话无桌面，LTspice 已装但 `-b` 跑不起来。改用按手册参数搭的等效开关模型，8.4 V/6.0 V 输入均稳在 4.97 V，3.5 A 阶跃触发 5 A 峰值限流、跌到约 4.1 V。注意 SO-8EP 同封装但第 4 脚定义不同（SS vs RT/CLK），不能直接换脚。详见[仿真攻关记录](docs/references/hat-simulation-tools-20261029/research.md)。

- **[AP63205 第三方模型搜索，2026-10-29]** 按用户要求不只查官网：通用搜索、GitHub、SnapEDA、SamacSys、Ultra Librarian、立创、Würth、Diodes 官方页与官方仿真器示例全部查过，**没有公开 SPICE/IBIS 模型**，只有符号与封装（[推断]）。顺带查到 Voron-Tap Issue #42 报告 AP63205 上电 VIN 浪涌可致稳压器击穿短路，手册绝对最大 VIN 为 35 V(DC)/40 V(400 ms)。详见[第三方搜索与可靠性记录](docs/references/hat-simulation-tools-20261029/research.md)。

- **[电源选型核对，2026-10-29]** 参考方案实际用的是 **AP63205（2 A，TSOT-26）**：官方 C1 的 U9（LCSC C2071056）与 kissqy REVA 的 AP63205WU 均是它；**AP64501 不出现在任何参考 HAT 中**，是 Rev A 生成脚本的候选。同族 AP64350（3.5 A，SO-8EP）有官方 PSpice 模型，但文件有子电路名笔误、打完补丁仍在 ngspice 不收敛。详见[电源芯片对比](docs/references/hat-simulation-tools-20261029/research.md)。

- **[模型第三轮，2026-10-29]** 核对 Diodes 官方器件页与数据手册：AP64501/PAM8406 未发布公开 SPICE 模型（[推断]，对照 1N4148W 页面同一读取方式可见模型条目）；官方另有 SIMetrix 内核仿真器，未验证是否含这两个型号。TPS565201 备选模型在 ngspice 47 下六种策略均不收敛，属引擎兼容问题。同轮发现 `duck-robot-tools` 被清空，已按原地址重下 ngspice 与 TI 包，哈希与上轮记录一致。详见[第三轮查找](docs/references/hat-simulation-tools-20261029/research.md)。

- **[模型续查，2026-10-29]** 下载 TPS565201 的官方未加密 PSpice 电源模型（SLVMC88，已试跑但不收敛），作为不同型号备选；TPA2012D2/TPA3136D2 音频模型也已下载，但为 PSpice/TINA 加密格式，不能直接当作 ngspice 明文模型。AP64501/PAM8406 原型号仍未取得模型，选型/原理图未更改。详见[第二轮查找](docs/references/hat-simulation-tools-20261029/research.md#第二轮查找电源音频缺口与备选模型2026-10-29)。

- **[模型资料/本机仿真，2026-10-29]** 已取得 TI SN74LVC1G125 两版 PSpice、IBIS/HSPICE 和 TLV320AIC3104 IBIS。两版缓冲器 PSpice 模型在 ngspice 47 完成基本电平/禁用兼容性检查，未验证 HAT 总线；Diodes AP64501/PAM8406 页面受限，模型未取得，BMI088 官方产品页未找到模型链接。下载位置、不同子电路引脚顺序和验证边界见[模型记录](docs/references/hat-simulation-tools-20261029/research.md#真实器件模型查找与下载2026-10-29)。

- **[用户确认] 需求汇总已确认**：首版明确不做 RS485、识别 EEPROM、充电和 UPS；基础功能及头部 IMU、摄像头、屏幕纳入需求。具体设计方案草案已落盘于 [design-plan](docs/specs/20261028-custom-hat/design-plan.md)，待用户批准，尚未进入画板阶段。

- **[用户确认] 屏幕需求**：3.5 寸、显示简单表情、无触摸；具体型号、分辨率和接口待定，已更新需求 R13。

- 用户希望使用已有 KiCad 自设计 HAT、走通嘉立创制板流程；本轮要求先整理参考设计与需求。
- **[原始资料核对]** 已盘点官方 C1/D1、社区 Radxa V1.0 原理图与 kissqy REVA 两层工程；community-kit 本地硬件目录无独立 HAT，replica 引用官方设计。见[功能与资料对照](docs/references/hat-design-inventory-20261028/research.md)。
- [需求草案](docs/specs/20261028-custom-hat/spec.md)已落盘；**用户已确认需要头部 IMU、摄像头排线口 ×1、屏幕排线口 ×1**。摄像头/屏幕型号、协议、主控信号来源与具体实现待核，其余功能范围继续确认。RS485 与识别 EEPROM 用途见[补充说明](docs/references/hat-design-inventory-20261028/research.md#rs485-eeprom)。未画板、未下单、不改变当前供电路线。白色 V1.2 全套工程及现有 IMU 缺答根因仍待核；新板不作为已验证修复。
- **[用户批准方案]** 已在 `hardware/custom_hat/rev_a/` 建立独立 KiCad 10.0.7 原理图工程，生成 Radxa、屏幕、电源、TTL、BMI088/ToF、CSI、音频、测试点八个功能页；未画 PCB、未下单、未操作硬件。功能页仍含器件级接口契约，不能视为已确认可制造网表。
- **[编码进展]** 用户再次确认继续后，已补入 Radxa、头部传感器、CSI 与屏幕参考页工作副本；这些页面仍不是本项目最终网表，主层级尚未接入，目标器件针序、FPC 接触面、地址、电平和 GPIO 仍待逐网核对。当前工程仍停留在原理图准备阶段，不进入 PCB。
- **[编码进展]** Rev A 顶层已挂入 8 个功能页并导出 `rev_a.pdf`、`net-contract.json`。KiCad CLI ERC 报告 171 条违规，主要来自生成页坐标/连接器占位和孤立接口标签；工程仍不可投板，需替换真实器件/网络并重跑 ERC。Rev A 当前没有 PCB、BOM、CPL、DRC 或 Gerber。
- **[仿真勘误，2026-10-29]** 旧 Python 脚本仅计算假设参数，电源预算漏计 Radxa，TTL 参数未核验，撤回整板预算通过和 33Ω 推荐。已下载 ngspice 47 并用独立 RC 电路确认引擎运行；尚未验证 HAT。工具位置、来源与日志见[工具调研](docs/references/hat-simulation-tools-20261029/research.md)。
