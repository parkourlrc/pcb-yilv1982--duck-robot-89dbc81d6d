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

### 3. jlc-order API 工具链本机状态（缺口）

| 项 | 状态 |
|---|---|
| 代码/测试（`tools/jlc-order/`） | 在，2026-10-09 版（README 记录首单 customerOrderId 85073604 实测跑通） |
| `jlc-order.toml` 真实密钥 | **不在本机**（全仓库 find 无；环境变量无 JLC_*） |
| `orders.jsonl` 台账 | **不在本机** → 10-09 首单不是在本机当前工作区跑的（当时凭据/环境去向不明，.goal 知识库 2026-10-08 记"用户已有密钥但未在本会话提供"） |
| `api-docs/` | 不在本机（gitignore，可从控制台重下） |
| `tools/baidu-pan-mcp/` 上传工具 | **目录不存在**（AGENTS.md 提及，但本机缺失；API 下单需公网 pcbFileUrl） |
| WSL Ubuntu-24.04 | 2026-10-22 全新安装（训练用），与 10-09 首单无关 |
| 嘉立创EDA专业版（lceda-pro） | **已装**（`%LOCALAPPDATA%\Programs\lceda-pro`，10-09 导出原理图 PDF 即用它） |

### 4. 下单参数（已建模板 `tools/jlc-order/examples/imu_to_dxl_v03.toml`）

板框 32×22mm、双层、5 片经济打样、绿色、无铅喷锡、全测；**板厚未量**（默认 1.6mm，可选 0.8/1.0/1.2，待用户确认或量实物板）。

## 结论：两条可行路径

- **路径 A（推荐，最省事）：嘉立创EDA专业版内置下单**。lceda-pro 打开 eprj2 → 选 `imu_to_dxl_1` 板页 → 菜单"制造/PCB制板下单"（EDA 自动上传工程数据，免 Gerber/网盘/API/密钥），订单页人工支付。不经过本项目 API 工具。
- **路径 B：本项目 jlc-order API 流**。需用户补齐三样：①appid/access_key/secret_key（重建 `tools/jlc-order/jlc-order.toml`，密钥来自 open.jlc.com 控制台）；②EDA 导出 `imu_to_dxl_1` 的 Gerber zip；③Gerber 公网托管 URL（网盘分享链接，百度网盘工具本机缺失，需用户手动上传分享）。然后 `pcb quote` 计价 → `pcb order`（`advance_payment=false` 默认只建单不扣款，订单生成后人工支付）。

## 验证状态与限制

- 上游无 Gerber、本机无密钥/台账/网盘工具——均本轮实测确认；首单 85073604 的运行环境去向未深究（不影响决策）。
- 板厚、收货信息（路径 B 的 `[order]` 段）、数量是否 5 片：**待用户确认**。
- 下单未执行；完成后应更新 BOM（新增在途条目）与 PROGRESS，并回填本文件记录订单号。

## 来源

- 上游：https://github.com/ScrapMeta/microduck-diy/tree/main/imu_to_dxl（README 在线核查，2026-10-25）
- 本地：`docs/schematics/imu-to-dxl-scrapmeta-v0.3/`（README/原理图/eprj2）、`tools/jlc-order/README.md`、`config.example.toml`、`.goal/PROJECT_KNOWLEDGE.md` 嘉立创工具节、`docs/references/imu-to-dxl-variants-20261009/research.md`
