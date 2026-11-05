# PCB 自动化设计到回寄上机：需求驱动运行手册

日期：2026-11-05。适用：本项目自主模块的小批量 PCB（约 1–20 片，含 SMT/THT）。目标：**用户只填一张需求卡，后续按 Stage 0–10 逐步执行；只在门禁处做确认、付款、上电和验收。**

本手册是执行层；设计原则、成本口径和证据规则仍见 [自主硬件模块研发流程](hardware-module-development-workflow.md) 与 [AGENTS](../AGENTS.md)。不适用于高频/RF、强电、认证或量产项目，遇到时先扩展流程。

## 0. 怎么用

1. 复制 [PCB 项目模板](../hardware/templates/pcb-project/README.md) 到 `hardware/<模块>/`。
2. 填写 `requirements.md`；不确定项写“待确认”，不要留空。
3. 代理按 Stage 0–10 执行，自动完成设计辅助、检查、打包、报价和记录；只在 G1–G5 门禁停下来问用户。
4. 用户只需要做五类决定：需求冻结、设计放行、下单/付款、允许上电、首板验收。
5. 状态写入 `order-status.json`；源身份写入 `checkpoint.json`；测试写入 `first-article-test.md`。

**自动化边界**：代理可以改工程、跑检查、生成生产包、调用 PCB 报价/下单 API；不能替用户付款、不能替用户上电、不能把“下单成功”写成“首板通过”。

## 1. 需求卡（唯一需要用户填的输入）

字段与模板一致；只填业务/约束，不必选具体器件：

```yaml
project: 模块名/版本
host: 宿主板/系统版本
must: [必须功能]
not_do: [明确不做]
interface: 连接器/针序/观察方向/电平/通信
power: 输入电压/电流/保护/上下电顺序
mechanical: 板框/孔位/高度/插拔与线束空间
quantity: 数量
assembly: PCB only | SMT | 全焊（含 THT）
process: 层数/铜厚/表面处理/特殊工艺（未知写待确认）
budget: 整批预算，含 PCB/元件/加工/运费/税费口径
acceptance: 首板验收标准与不覆盖条件
references: 参考工程/手册/许可
unknowns: 关键未知与风险
```

## 2. 阶段与门禁总览

| Stage | 目标 | 主要自动化动作 | 产物 | 门禁 |
|---|---|---|---|---|
| 0 | 立项、复制模板 | 建立目录、记录版本 | 项目目录 | — |
| 1 | 需求冻结 | 解析需求、列缺口 | `requirements.md` | **G1 用户确认** |
| 2 | 接口与证据 | 查针序/电平/机械/来源 | 接口表、来源清单 | 关键未知有处理计划 |
| 3 | 方案/选型/成本 | 候选 MPN、库存/工艺/软件核查、粗预算 | 架构、候选 BOM、成本表 | 方案与预算可行 |
| 4 | 原理图/封装 | KiCad 工程、符号/封装核对 | 可打开工程 | 关键映射自检 |
| 5 | 布局/机械 | 板框、固定、布线、工艺基线 | PCB 候选 | 无已知机械冲突 |
| 6 | 检查/同源包 | ERC/DRC/一致性/DFM、打包、哈希 | `release/<hash>/`、`checkpoint.json` | **G2 用户放行设计包** |
| 7 | 工厂匹配/报价 | 全表核料、SMT/THT/治具/费用 | 报价记录、缺口清单 | 报价在预算内或用户例外 |
| 8 | 下单/生产 | PCB API 下单、SMT 网页下单、状态轮询 | 订单号、付款记录 | **G3 用户确认下单/付款** |
| 9 | 回寄/来料 | 收货、外观/数量/极性/关键网络检查 | 来料检查记录、照片 | **G4 用户允许上电** |
| 10 | 首板上机/验收 | 限流上电、电源/总线/IMU/舵机/功能测试 | `first-article-test.md` | **G5 用户验收；M3 才可闭环** |

## 3. Stage 0–2：立项、需求、接口

### Stage 0 立项

- 复制模板：`hardware/templates/pcb-project/` → `hardware/<模块>/`。
- 建立 `design/`、`checks/`、`release/`、`orders/`、`first-article/`。
- 记录模块名、版本、负责人、日期；不预建与当前阶段无关的空目录。

### Stage 1 需求冻结

- 代理把需求卡转成“功能/接口/机械/制造/预算/验收”六类检查表，列出缺项和冲突。
- 用户只需确认：范围、预算口径、成功标准、明确不做什么。
- 出口：`requirements.md` 标注 `frozen: YYYY-MM-DD`。

**G1**：用户确认需求冻结。未确认不进入选型。

### Stage 2 接口与证据

- 核宿主针序、观察方向、电平、通信方向、机械尺寸、线束/工具空间。
- 每条关键结论标来源：原厂规格/本机实测/上游记录/推断/待确认。
- 出口：接口表 + 来源清单；关键未知必须有验证计划或替代方案。

## 4. Stage 3–5：方案、原理图、布局

### Stage 3 方案/选型/成本

- 按功能块选拓扑；每个关键器件给精确 MPN、封装、库存时点、工艺准入、软件/驱动支持。
- 先算整批可交付成本：PCB + 元件（含备损/最低用量）+ 装配/治具/换料 + 运费/税费。
- 高价料、特殊工艺、THT、双面装配必须单列；报价前不把估算写成最终价。
- 出口：架构图、候选 BOM、成本表、未定费用。

### Stage 4 原理图/封装

- 在完整 KiCad 工程中工作；保留符号/封装库与规则。
- 核对：电源/保护/复位/时钟/引脚映射/器件方向；符号→焊盘→物理脚位逐项对应。
- 出口：可打开工程 + 关键核对表。

### Stage 5 布局/机械

- 先固定板框、孔位、宿主对插方向/高度、插拔/线束/工具空间；再排关键回路、去耦、细脚扇出。
- 制造基线（层数/铜厚/表面/最小孔/填孔/装配面/THT）先定；局部特殊工艺要评估整板费用。
- 出口：PCB 候选 + 机械/工艺约束记录。

## 5. Stage 6：检查与同源生产包

自动检查至少包括：

```bash
# 以本机 KiCad 版本为准；输出目录 checks/
kicad-cli sch erc --output checks/erc.rpt design/<project>.kicad_sch
kicad-cli pcb drc --output checks/drc.rpt design/<project>.kicad_pcb
```

- 另核：原理图/PCB 一致性、未连接、铜连通、板框/阻焊/钢网/孔层、BOM/CPL 位号与角度、DNP、THT 开窗。
- 生成同源包：Gerber/钻孔、BOM、CPL、顶底装配图、制造参数、检查报告。
- 包目录：`release/<pcb_sha256前8位>/`；`manifest.json` 记录每个文件 SHA256、工具版本、生成时间。
- `checkpoint.json` 至少写：源文件哈希、`fitted_count`、`bom_groups`、层数、装配面、检查结果、`production_ready`、`manufacturing_release`。

**G2**：用户放行设计包。放行对象是“这个哈希的生产包”，不是工作区最新改动。

## 6. Stage 7：工厂匹配与报价

- PCB：用 `tools/jlc-order` 报价/下单（仅 PCB）；命令示例：

```bash
cd tools/jlc-order
python -m jlc_order doctor
python -m jlc_order pcb quote -p <工艺配置>.toml
```

- SMT/PCBA：在嘉立创网页逐项核对全部 C 编号/MPN/位号/数量/安装面/DNP/THT/治具/换料；导出全表，不以部分标签推定全板。
- 报价必须绑定当前生产包哈希；旧报价、旧 Y 单不能冒充新源价格。
- 出口：`orders/quote-<hash>.json` + 缺口清单；超预算先给取舍方案，用户决定例外。

## 7. Stage 8：下单、付款、生产

- PCB 可用 API：

```bash
python -m jlc_order pcb order -p <工艺配置>.toml   # 需 [order] 配置；真实下单前先 dry-run/quote
python -m jlc_order order progress --order-no <customerOrderId> --watch
```

- SMT/PCBA 在网页下单；记录 `smt_order_id`、付款页面/用户确认、服务项和运费。
- **付款只能由用户执行**；代理不保存支付凭据，不把页面价写成银行到账。
- 下单后源文件变更 → 新版本、新哈希、新报价/新单，不静默改旧单。

**G3**：用户确认下单并付款。

## 8. Stage 9：回寄与来料检查

- 收货先核：包装/数量/板号/版本丝印/PCBA 位号/连接器方向/明显损伤。
- 断电检查：电源入口、极性、关键网络、短路、THT 焊点、DNP 是否符合。
- 拍照、登记、与订单/生产包哈希对应；异常先记录，不急着上电。

**G4**：用户确认允许上电。上电按 [AGENTS](../AGENTS.md) 的限流/极性/分阶段边界执行。

## 9. Stage 10：首板上机与验收

1. 限流上电，先核电压轨与静态电流；异常立即断电。
2. 核主控启动、HAT/总线、IMU、舵机通信、连接器与关键功能。
3. 记录每项的条件、结果、限制；失败项写返修/ECO，不写“基本通过”。
4. 填写 `first-article-test.md`；通过后更新 `checkpoint.json` 的 `production_ready`/`manufacturing_release` 与 `order-status.json`。

**G5**：用户验收首板；M3 才可闭环。下单、付款、收货、上电、功能通过是不同状态，不互相替代。

## 10. 状态文件与模板

- `requirements.md`：需求卡（唯一用户输入）。
- `checkpoint.json`：源哈希、检查、包、订单、制造放行。
- `order-status.json`：阶段、报价、订单、付款、物流、来料、首板。
- `first-article-test.md`：首板测试记录。
- `release/<hash>/manifest.json`：生产包逐文件哈希。

模板：[hardware/templates/pcb-project](../hardware/templates/pcb-project/README.md)。

## 11. 失败、返修与 ECO

- 工厂 DFM/缺料：冻结下单，修源→新哈希→新包→重报价；不直接改已上传文件。
- 来料/焊接缺陷：拍照、隔离、返修或重下单；记录批次与位号。
- 首板失败：保留失败数据，定位到设计/物料/焊接/装配/软件；修复后新版本、新首板记录。
- 任何源变更都要更新 `checkpoint.json` 与订单对应关系；旧包只作历史。

## 12. 自动化清单（代理执行）

| 动作 | 自动化程度 | 工具/入口 |
|---|---|---|
| 需求转检查表 | 代理生成，用户确认 | `requirements.md` |
| 原理图/PCB 编辑 | 代理辅助，用户放行 | KiCad + `tools/kicad-mcp-server` |
| ERC/DRC/一致性 | 脚本执行 | `kicad-cli` |
| 生产包/哈希 | 脚本执行 | `release/`、`checkpoint.json` |
| PCB 报价/下单 | API 执行，用户付款 | `tools/jlc-order` |
| SMT/PCBA 下单 | 网页人工，代理核对 | 嘉立创网页 |
| 来料/上电/首板 | 用户在场，代理记录 | `first-article-test.md` |

**原则**：能脚本化的检查、打包、哈希、报价、状态记录尽量自动化；涉及付款、上电、验收和不可逆外部操作的，必须由用户确认。
