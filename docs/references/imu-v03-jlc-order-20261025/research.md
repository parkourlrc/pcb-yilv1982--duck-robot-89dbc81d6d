# 双口 IMU 板（imu_to_dxl v0.3）嘉立创开板下单调研（2026-10-25）

## 问题与范围

用户要求把双口 IMU 板（ScrapMeta `imu_to_dxl` v0.3，实物丝印 IMU2DXL V1.0，32×22mm）送嘉立创打样下单。本轮核实：生产文件是否现成、下单工具链在本机的可用状态、可行路径与缺口。

## 核实结果（均为本轮本机实测/在线核查）

### 1. v0.3 没有 Gerber 生产文件

- 上游 GitHub `ScrapMeta/microduck-diy/tree/main/imu_to_dxl`：**只发布 `hardware/`（eprj2 工程源）+ README**，无 Gerber/制造文件（2026-10-25 在线核查）。
- 本仓库存档 `docs/schematics/imu-to-dxl-scrapmeta-v0.3/`：eprj2 真源 + 导出的原理图 PDF，无 Gerber。
- `references/microduck-community-kit/hardware/imu_to_dxl/production/imu_to_dxl_0.2_10p_gerber.zip` 是 **v0.2 KiCad 版**的 Gerber（单口/10p），**不是本板**，不能混用。
- `references/microduck-replica/hardware/imu_to_dxl/` 为 replica 版（板框 45×22-R2），也不是本板。
- `imu_to_dxl_ref_2026-08-30_18-59-47.eprj2` 文件头为 **SQLite format 3**（嘉立创EDA专业版工程库），无法脚本直出 Gerber，须在 EDA 内导出。

### 2. 关键陷阱：eprj2 工程内有两页板

- `imu_to_dxl_1` = J1+J3 **双口**（实物板对应页，下单选这页）；
- `imu_to_dxl_2` = 单 J1 变体（介于 v0.2 与 v0.3 之间，仅参考，**不能下单**）。
- 依据：`docs/schematics/imu-to-dxl-scrapmeta-v0.3/README.md`（2026-10-09 导出核对）。

### 3. jlc-order API 工具链本机状态

**2026-10-25 更新：用户已把首单环境配置放回本机（`jlc-order.toml` 密钥 + `orders.jsonl` 台账，18 条 2026-10-09 调用记录），`doctor` 自检通过（验签 ✓、IP 白名单 ✓）。以下缺口表仅留作当日历史。**

| 项 | 状态 |
|---|---|
| 代码/测试（`tools/jlc-order/`） | 在，2026-10-09 版（README 记录首单 customerOrderId 85073604 实测跑通） |
| `jlc-order.toml` 真实密钥 | ~~不在本机~~ **已放回（doctor 验签通过）** |
| `orders.jsonl` 台账 | ~~不在本机~~ **已放回（10-09 首单环境台账）** |
| `api-docs/` | 不在本机（gitignore，可从控制台重下） |
| `tools/baidu-pan-mcp/` 上传工具 | 目录不存在——**不需要了：首单 pcbFileUrl 用的就是 gitee raw 链接**（`https://gitee.com/yilv1982/duck-robot/raw/main/hardware/banana_pcb/production/banana_pcb.zip`），本轮已复验 raw 匿名可下载（README 与新推文件均 200） |
| WSL Ubuntu-24.04 | 2026-10-22 全新安装（训练用），与 10-09 首单无关 |
| 嘉立创EDA专业版（lceda-pro） | **已装**（`%LOCALAPPDATA%\Programs\lceda-pro`，10-09 导出原理图 PDF 即用它） |

### 3a. 在线计价实测（2026-10-25，本机）

`pcb quote -p examples/imu_to_dxl_v03.toml` 真实应答：**internetPayTotalMoney = ¥55.12**（32×22mm 2 层、板厚 1.6mm、5pcs、FR-4 绿色、无铅喷锡、1oz、全部测试；含 adornPutMoney 30.11 + specialMoney 20.00 + taxMoney 5.01 等）。板厚若改 0.8/1.0/1.2 需重新计价。

### 4. 下单参数（已建模板 `tools/jlc-order/examples/imu_to_dxl_v03.toml`）

板框 32×22mm、双层、5 片经济打样、绿色、无铅喷锡、全测；**板厚未量**（默认 1.6mm，可选 0.8/1.0/1.2，待用户确认或量实物板）。

## 结论：两条可行路径

- **路径 A（推荐，最省事）：嘉立创EDA专业版内置下单**。lceda-pro 打开 eprj2 → 选 `imu_to_dxl_1` 板页 → 菜单"制造/PCB制板下单"（EDA 自动上传工程数据，免 Gerber/网盘/API/密钥），订单页人工支付。不经过本项目 API 工具。
- **路径 B：本项目 jlc-order API 流（密钥已到位，仅剩 Gerber）**。① ~~密钥~~ ✅ 已放回并 doctor 验签通过；② EDA 导出 `imu_to_dxl_1` 的 Gerber zip（**唯一缺口**）；③ ~~公网托管~~ ✅ 走 gitee raw（首单同款流程）：Gerber zip 提交进仓库（仿 `hardware/banana_pcb/production/` 模式）→ 推 gitee → raw 链接填 `pcb_file_url`。随后 `pcb quote` 复核 → `pcb order`（`advance_payment=false` 默认只建单不扣款，订单生成后人工支付）。计价已实测 ¥55.12/5 片。

## 验证状态与限制

- 上游无 Gerber、本机无密钥/台账/网盘工具——均本轮实测确认；首单 85073604 的运行环境去向未深究（不影响决策）。
- 板厚、收货信息（路径 B 的 `[order]` 段）、数量是否 5 片：**待用户确认**。
- 下单未执行；完成后应更新 BOM（新增在途条目）与 PROGRESS，并回填本文件记录订单号。

## 2026-10-25 晚收官：Gerber 到手、下单完成（本机实测）

- **EDA 自动化导出（新通路，本轮打通）**：`.eprj2` 无法离线转 Gerber（见上），但桌面 lceda-pro（Electron）可 `lceda-pro.exe --remote-debugging-port=9222 <eprj2路径>` 命令行直接打开工程；经 CDP（python websocket-client，注意 `suppress_origin=True` 绕 403）驱动：真实坐标双击工程树 `PCB1_1` → 菜单「导出 → PCB制板文件(Gerber)」→ 对话框「导出Gerber」。合成 DOM 事件无效，必须 `Input.dispatchMouseEvent`。最后一键导出由用户手动完成（"我来操作吧"），产物 `Gerber_PCB1_1_2026-10-25.zip`。驱动脚本存 `%TEMP%/eda-cdp/eda-cdp.py`（临时，未入库；复用价值见下）。
- **Gerber 验证（本机解析，全部通过）**：双层全套（GTL/GBL/GTS/GBS/GTO/GBO/GTP/GKO/钻孔×2/飞针 JSON）；板框 **33.0×22.0mm**；4×φ2.2 安装孔 @间距 30×19（中心距边 1.5）；**6×φ1.0 = J1+J3 双 EH 口**（单口变体只会有 3——双口身份决定性证据）；φ0.3 过孔 24+24、其余焊盘孔齐全。**勘误口径：文档旧记 32×22、孔距 29×19，X 向差 1mm**——Y 向完全吻合，判断为旧记录测量/读图偏差，以 Gerber 实测为准（如需铁证可量实物板，不阻塞下单）。
- **下单（本机实测）**：zip 入仓 `docs/schematics/imu-to-dxl-scrapmeta-v0.3/production/imu_to_dxl_v03_gerber.zip`（commit 9636c8c）→ 推 gitee → raw 200 → `jlc-order.toml` 换指向 → **`pcb order` 建单成功：customerOrderId 85849959，orderMoney ¥50.11（低于 quote ¥55.12，下单时叠加优惠），advance_payment=false 未扣款，待用户人工支付**。收货/发票信息沿用首单（用户已填）。
- 后续：`python -m jlc_order order progress --order-no 85849959` 跟进度；到货后焊装+刷机按 [flash/README](../../../flash/README.md)；元件按上游 BOM 采购（另行任务）。

## 2026-10-25 深夜转向：裸板单取消，改 PCB+SMT 一体单

- **裸板单 85849959 用户在网页取消**（API 复核 `orderTotalMoney=0` 未支付，无扣款风险）；用户定向 **PCB+SMT 一体单**。
- **jlc-order API 无 SMT 业务线**（工具内 grep 无 smt 接口；README 明示应用仅开通 PCB 业务线）→ SMT 单走 EDA「PCB/SMT 一键下单」按钮或 JLC 网页，不经过 API。取消 API 订单也不必用 API（网页已办）。
- **BOM 导出（CDP 驱动 EDA：导出 → 物料清单(BOM) → 导出BOM）**：15 行全部带立创 C 编号（作者工程内已配好物料，上游 README 存有其立创 BOM 单号 `BOM260909006316`/`SO26090921960`）。与网表逐项吻合：U1=LSM6DSV16XTR、U2=STM32G031F8P6、U3=AP2210K-3.3TRG1、U6=SN74LVC1G125DBVR-TP、R1-R5=10k、R6=150Ω、D1 PESD/D2 5.1V、阻容 6 颗、J1/J3/J2。Y1/C7/C8（LSE）正确不在 BOM（DNP）。
- **CPL 导出（同通路：导出 → 坐标文件）**：原始 24 行 = BOM 19 件 + 3 DNP（C7/C8/Y1，SMD 但无料）+ 2 插件（J1/J3，SMD=No）。已生成 **JLC 版清理 CSV**（Designator/Mid X/Mid Y/Layer/Rotation 五列、去 mm 后缀、19 行），与 BOM 设计位号一一对应。
- **贴片范围定案**：19 件全贴（含 J2 BM07 调试座——约 ¥1，免 J2 焊线，现役两块板均未装座的历史痛点）；J1/J3 EH 插件到货自焊（6 焊点）；Y1/C7/C8 维持不装。SMT 工程费/钢网/物料以 JLC 网页计价为准。
- 三件套归档：`imu_to_dxl_v03_gerber.zip` / `imu_to_dxl_v03_bom_20261025.xlsx` / `imu_to_dxl_v03_cpl_raw_20261025.xlsx` / `imu_to_dxl_v03_cpl_jlc_20261025.csv`（[production/](../../../schematics/imu-to-dxl-scrapmeta-v0.3/production/)）。

## 来源

- 上游：https://github.com/ScrapMeta/microduck-diy/tree/main/imu_to_dxl（README 在线核查，2026-10-25）
- 本地：`docs/schematics/imu-to-dxl-scrapmeta-v0.3/`（README/原理图/eprj2）、`tools/jlc-order/README.md`、`config.example.toml`、`.goal/PROJECT_KNOWLEDGE.md` 嘉立创工具节、`docs/references/imu-to-dxl-variants-20261009/research.md`

## 2026-10-25 补充：能否不经 EDA 界面自己生成 Gerber（用户委托调研）

**结论：v0.3 的 Gerber 生成绕不开嘉立创EDA界面（桌面版已装），最短路径仍是人工两步导出；oshwhub 上发现同名功能的替代板但不是本板。** 三条自动路线均验证后排除：

1. **直解 eprj2（失败）**：`.eprj2` 为 SQLite 库，`documents` 表为空，文档正文在 `history_data`（258 条 base64 blob，16 字节对齐=分组加密），密钥疑在 `project_history_a92…` 表 key 列（16 字节 hex）。实测 AES-128（ECB/CBC/CTR/GCM/CFB/OFB、IV=0/首块/密钥、key 按 hex 与 ASCII 两解释）与 SM4（ECB/CBC 多 IV）全部不可读（可读率 ≤0.41）——密钥还有一层推导（疑与 users 表口令/设备因子有关），继续逆向不划算。
2. **KiCad 9 导入器 / epro2kicad（无净收益）**：KiCad 9 原生支持导入 EasyEDA **Pro 的 `.epro`**（改名的 ZIP，内含 `.epcb` 明文文档；[KiCad dev docs](https://dev-docs.kicad.org/en/import-formats/easyeda/index.html)），导入后 `kicad-cli pcb export gerbers` 可无界面出 Gerber；社区工具 [epro2kicad](https://github.com/enkhbold470/epro2kicad) 也是包装 KiCad 自己的解析器。**但 `.epro` 本身必须由 EasyEDA Pro 界面"文件→导出"生成**——既然要开界面，不如直接导 Gerber，KiCad 环节（已通过 winget 安装，仅备用）对 v0.3 无净收益。
3. **oshwhub 同功能板（重要发现，但不是本板）**：[avanx/MicroDuck IMU_to_DXL](https://oshwhub.com/avanx/project_whiijerp)（立创开源平台，专业版工程，Apache 2.0，创建 2026-09-17/更新 2026-10-08）。经页面 BOM 与电路说明核实，与 v0.3 **完全不同设计**：MCU=AT32F425K8U7（QFN-32，非 G031 TSSOP-20）、电源=VBUS→自恢复保险丝→HT7533→SGM2036-1.8（非 AP2210K-3.3）、缓冲=SN74LVC2G241（非 1G125）、**单口 CN1 叶子节点设计（作者明确"只设计一个接口"）**、按 power_support 21.9×14.9 孔位设计。配套固件为其自研 AT32 飞特 SCS 固件（状态：PCB/上电/飞特固件均"完成"），仓库 https://github.com/avanx/microduck_imu_to_ttl 。**不得与 v0.3 混淆下单**；若未来评估"原生飞特单口 IMU 叶子板"可另立专题。

最短可行路径维持：桌面嘉立创EDA专业版打开 eprj2 → 板页 `imu_to_dxl_1` → 导出 Gerber zip → 推 gitee 拿 raw 链接 → `pcb order`（密钥已就位、计价 ¥55.12 已实测）。
