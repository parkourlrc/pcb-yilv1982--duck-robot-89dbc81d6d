# KiCad PCB 设计 Agent Skill / MCP 调研

## 调用方式补充（2026-10-30）

- 本轮回读 `codex mcp get kicad --json` 为 enabled=true，但当前聊天可调用工具目录未发现 KiCad 工具；配置存在不等于本会话已经接入。
- 建议重新打开 Codex 后检查 MCP 连接，再直接用自然语言指定 `kicad` MCP、目标工程和只读范围，例如：“使用 kicad MCP 读取本项目 HAT Rev A 工程，列出 PCB 统计和电源页器件，只读不修改。”
- CLI `codex mcp get kicad --json` 查看本服务配置；已在本机执行回读。官方配置入口：<https://developers.openai.com/codex/mcp>（本次 web 调用未返回可引用正文；安装轮已通过 HTTPS 读取官方页面）。
- 如果重开后仍未加载，继续检查 MCP 启动错误；不把已注册或独立验证通过当作桌面会话连接成功。

- 日期：2026-10-30
- 问题与范围：为本项目 KiCad 10 自主 HAT/PCB 设计寻找可由 AI agent 调用的 GitHub skill 或 MCP 自动化工具。优先实际的原理图/PCB 编辑、布局、布线、DRC 和制造输出能力；不把仅能做静态分析的 skill 当作完整设计工具。
- 当前状态：首轮只检索；用户随后确认“继续”安装。2026-10-30 已安装 Seeed MCP 并注册到 Codex，具体版本、验证范围和限制见文末安装记录。未修改 `references/` 只读库。

## 候选

### 1. Seeed-Studio/kicad-mcp-server

- GitHub：<https://github.com/Seeed-Studio/kicad-mcp-server>
- 定位：MCP server，支持原理图分析、PCB 分析、网络追踪、ERC/DRC、项目模板、器件/封装获取和代码生成。
- KiCad 兼容性：README 标注 KiCad 8.0+，推荐 9.0/10.0；提供 Windows KiCad 10 Python 路径和配置示例。
- 证据状态：[已核对仓库 README/API 元数据]；GitHub stars：174（2026-10-30 查询）。
- 局限：README 的重点是分析/验证和项目辅助，未把完整的交互式布局/布线编辑工作流作为主要卖点；采用前应先验证本项目所需的板级写操作工具。
- 安装参考：
  ```powershell
  git clone https://github.com/Seeed-Studio/kicad-mcp-server
  & 'C:\Program Files\KiCad\10.0\bin\python.exe' -m pip install fastmcp
  & 'C:\Program Files\KiCad\10.0\bin\python.exe' -m pip install -e .
  ```

### 2. MJP-Sys/kicad-mcp-server

- GitHub：<https://github.com/MJP-Sys/kicad-mcp-server>
- 定位：较完整的 KiCad MCP，README 声称 122 个工具、16 类、动态项目资源、原理图工作流、Freerouting、JLCPCB/LCSC 集成和实验性的 KiCad IPC 实时集成。
- Windows：README 提供 Windows 10/11 自动设置脚本和故障排查文档；KiCad 9/Windows 修复记录明确存在。
- 证据状态：[已核对仓库 README/API 元数据]；GitHub stars：1（2026-10-30 查询），项目成熟度和 KiCad 10 兼容性仍需本机验证。
- 局限：社区验证量较低，README 主要以 KiCad 9 为例；不应直接用于 HAT 上电或生产下单前的唯一验证依据。
- 安装入口：<https://github.com/MJP-Sys/kicad-mcp-server/blob/main/docs/WINDOWS_SETUP.md>

### 3. blwfish/kicad-mcp

- GitHub：<https://github.com/blwfish/kicad-mcp>
- 定位：端到端 PCB 设计 MCP，包含原理图、布局、网络、布线、铜区、丝印、DRC、自动布线、BOM、Gerber、面板化和 LCSC 器件搜索等工具；README 列出 18 个工具/路由。
- 证据状态：[已核对仓库 README/API 元数据]；GitHub stars：27（2026-10-30 查询）。
- 局限：作者说明主要在 macOS + Claude Code 上使用，Windows/Linux 代码路径存在但未充分测试；KiCad 10 兼容性不能仅凭 README 推断。
- 适合度：如果目标是“让 agent 实际画板、布局、布线并导出生产文件”，功能覆盖最接近需求，但应先在副本工程做小板回归。

## Agent skill 候选

### aklofas/kicad-happy

- GitHub：<https://github.com/aklofas/kicad-happy>
- 技能入口：`skills/kicad/SKILL.md`，可通过 `npx skills add aklofas/kicad-happy@kicad` 安装。
- 定位：KiCad 项目/原理图/PCB/Gerber 的结构化分析和设计审查，覆盖 DRC/ERC、BOM、电源树、DFM、网络追踪和置信度/证据标注；README 明确列出 OpenAI Codex 支持。
- 证据状态：[已核对仓库 README、SKILL.md/API 元数据]；GitHub stars：1542；skills.sh 安装量：约 1.1K（检索时显示）。
- 局限：这是分析/审查 skill，不是 MCP 级别的交互式布局布线执行器；适合与 MCP 搭配，而不是替代 MCP。
- 安装命令：
  ```powershell
  npx skills add aklofas/kicad-happy@kicad -g -y
  ```

### backplaneworks/kistack

- GitHub：<https://github.com/backplaneworks/kistack>
- 技能入口：`skills/pcb/SKILL.md`、`skills/layout/SKILL.md` 等，可通过 `npx skills add backplaneworks/kistack@kicad-pcb` 或 `@kicad-layout` 安装。
- 定位：人工编写的 KiCad 工作流 skill，覆盖 PCB 审查、布局布线、封装、Gerber、面板化和 BOM；强调保存 canonical board、备份、DRC 和图层渲染检查。
- 证据状态：[已核对仓库 README、SKILL.md/API 元数据]；GitHub stars：415；skills.sh 安装量：`kicad-pcb` 约 380、`kicad-layout` 约 175（检索时显示）。
- 局限：部分布局说明依赖 KiStack/IPC/`backplane.json` 等配套环境，不能假设在当前 Codex 环境中直接可用；先作为流程知识 skill 评估。
- 安装命令：
  ```powershell
  npx skills add backplaneworks/kistack@kicad-pcb -g -y
  npx skills add backplaneworks/kistack@kicad-layout -g -y
  ```

## 结论与下一步

- [推断] 对本项目 KiCad 10，优先试 `Seeed-Studio/kicad-mcp-server` 做兼容性和分析/验证基线，再评估 `MJP-Sys/kicad-mcp-server` 的写操作覆盖；两者都应在 HAT 副本工程上验证，不直接改现行生产文件。
- [推断] 若核心需求是端到端“从描述到 PCB 布线/导出”，`blwfish/kicad-mcp` 的功能覆盖最完整，但 Windows/KiCad 10 风险最高，应排在兼容性基线之后。
- [推断] `aklofas/kicad-happy@kicad` 最适合作为 Codex 的设计审查 companion skill；它不能单独替代板级编辑 MCP。
- [本机工具检查] 已注册 Codex `kicad` MCP；实际 KiCad 路径为用户目录 `AppData/Local/Programs/KiCad/10.0/`，版本 10.0.7；不是前文安装示例中的 Program Files。当前聊天是否能热加载新工具尚未验证。
- 复核建议：先复制 `hardware/custom_hat/` 工程到临时目录，执行只读解析、DRC 和板框/网络统计，再尝试单个可回滚的布局修改；不因工具能写文件就视为电气连接或载流能力已验证。

## 来源

- <https://github.com/Seeed-Studio/kicad-mcp-server>
- <https://github.com/MJP-Sys/kicad-mcp-server>
- <https://github.com/blwfish/kicad-mcp>
- <https://github.com/aklofas/kicad-happy>
- <https://github.com/backplaneworks/kistack>
- <https://skills.sh/aklofas/kicad-happy/kicad>
- <https://skills.sh/backplaneworks/kistack/kicad-pcb>

## 2026-10-30 安装与验证记录

## 2026-10-30 既有问题复核（修订版）

此前回看只集中在早期审计，遗漏第46–56节修复及第22节pin1澄清，导致重新列出已解决问题。现行逐项证据见[真实性复核](../hat-simulation-tools-20261029/audit-20261030/review.md)。

- 旧AP64350/BMI088封装、TTL/动力缺口、I2S方向、录音功放、1.8V来源、TP802位置、内层铜区删除均已有后续文件级修复，不能继续笼统写成未解决。
- 第53节修正绝对/相对坐标错误，推翻据此得出的“完全无位置”。第55节已有逐孔验证器，不再把它写成尚未尝试方案。有限候选失败不证明必须六层、删功能或从零重排。
- pin1已有参考工程设计依据，屏幕/CSI已取消；不再要求用户补这几项旧输入。V1.2完整工程未取得，不阻塞已授权自设计。
- 当前是60封装、538走线段、74过孔、四铜区，板框65×30 mm。完整工程DRC重铺铜前后均29违规+23未连接，一致性另101；213来自缺失工程规则的副本，不能用它证明重铺铜退化。
- 仍需修U501周边错误铜/keepout、J301/J506机械铜冲突、23项未连接（含I2S_SDO）、悬空线/孔及丝印，并解决源板关联和生产包同步。
- 旧生成流程的主文件覆盖、旧SES复用、事后放宽规则及报告口径混淆有代码证据；本轮已经按[改进流程](../../specs/20261028-custom-hat/workflow-improvement.md)实施隔离检查。不是换一个MCP就能完成设计。
- 此前候选增加违规，未回写主板。清理目录命令曾被自动审批以blocked by policy拒绝，候选仍保留并明确标为未通过；旧试探脚本已撤下，不声称目录已清空。
- 无相关提交历史，无法定位最后一次覆盖主板的历史命令；风险依据与具体历史归因分开。

### 安装结果（本机工具检查，非硬件实测）

- 用户授权：在提出“安装 Seeed MCP，并用 HAT 副本只读验证”后，用户回复“继续”。
- 来源：`Seeed-Studio/kicad-mcp-server`，提交 `0b445be8668c00b0d71315e74fa2f180bca686c2`；工作副本在 `tools/kicad-mcp-server/`。通过本仓库 `.git/info/exclude` 排除该第三方克隆及环境，不将嵌套 Git 仓库和依赖提交。
- KiCad：实际执行 `kicad-cli --version` 及 `pcbnew.GetBuildVersion()` 均返回 **10.0.7**。路径 `C:/Users/yilv/AppData/Local/Programs/KiCad/10.0/bin/`，自带 Python 3.11.5。
- 运行环境：用 KiCad Python 创建 `tools/kicad-mcp-server/.venv-kicad/`，启用 `--system-site-packages` 复用 `pcbnew`，在此环境 editable 安装 MCP。KiCad 安装目录本身未安装新依赖。
- Codex：使用 `codex mcp add kicad` 注册用户级 stdio 服务，命令为 `.venv-kicad/Scripts/python.exe -m kicad_mcp_server`，环境变量明确指定 `KICAD_PYTHON`、`KICAD_CLI`、`PYTHONUTF8=1`。回读配置确认 enabled=true，三条可执行文件路径均存在。未修改 Claude Desktop 配置。
- 配置备份：用户目录 `.codex/config.toml.before-kicad-20261030-111454.bak`，仅本地保存，不进入版本库。
- Codex 配置依据：<https://developers.openai.com/codex/mcp>，核对 `config.toml`/`mcp_servers` 与本机 `codex mcp add --help`。本轮 web 工具未返回可引用内容，改用 HTTPS 直接取得官方页面正文核对。

### 最小验证与限制

- 使用 [verify_mcp.py](verify_mcp.py) 经真实 stdio MCP 客户端执行 initialize、list_tools 和两次只读调用，**枚举 47 个工具**。读取临时 HAT Rev A 副本：`get_pcb_statistics`、`list_schematic_components` 均返回内容、is_error=false。
- 原始返回和源 PCB SHA256 见 [mcp-verification.json](mcp-verification.json)。调用前后源 PCB SHA256 一致；临时副本在验证结束后移除。
- 本轮读取到的源文件统计为 4 铜层、60 个封装、538 条线段、74 个过孔、4 个铜区；它与 10-29 审计快照不同，**只表示此次读取的文件状态**，本任务未生成这些布局/布线，不据此宣称既有电路问题已修复。工具尺寸统计包括边框线宽，不替代机械尺寸定义。
- 关闭连接时输出 Windows asyncio `Overlapped ... still has pending operation at deallocation` 警告；进程返回 0，握手及两次调用完成。尚未排查是客户端、服务器退出路径还是 KiCad Python 的异步运行时所致，不能声称长期运行稳定性已通过。
- 本轮只验证安装链路；未重跑完整 ERC/DRC、未做写入/布局操作、未修改 HAT 设计、未进行实物操作或制造放行。当前聊天原有工具列表未确认热加载；如界面没有出现 `kicad`，需重新打开 Codex 后检查。

### 失败与纠正

- 起初只检查 Program Files、PATH 和 C 盘搜索，错误地将未发现解释为未安装；后从本项目脚本取得用户安装路径并实际运行，已纠正。不能再把本机“未安装 KiCad”列为缺口。
- 初次 venv 命令相对路径重复，生成 `tools/kicad-mcp-server/tools/kicad-mcp-server/.venv/`；随后另建 `.venv/`，最终实际注册使用 `.venv-kicad/`。前两个环境未注册为 MCP。
- 曾尝试合并环境修正与递归清理，自动审批以 `blocked by policy` 拒绝（未提供更细原因），未执行该次清理。改为明确绝对路径创建正确环境完成安装，遗留环境保留本地。
- 注册初次环境变量有重复路径分隔符，已改为 PowerShell `Join-Path` 生成并重新注册，最终回读路径存在。
- 安装记录和验证数据留在工作区；未 commit/push。
