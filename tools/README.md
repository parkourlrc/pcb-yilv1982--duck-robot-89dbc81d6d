# tools 目录索引

采购、烧录依赖与开发辅助。运行软件适配已迁到 [software/](../software/README.md)。

| 入口 | 内容 |
|---|---|
| [jlc-order/](jlc-order/README.md) | 嘉立创开放平台 API 下单/查询 |
| [kicad-mcp-server/](kicad-mcp-server/README.md) | KiCad MCP 服务 |
| [emmc-flash/](emmc-flash/) | 瑞芯微 eMMC 烧录工具与驱动（RKDevTool/DriverAssistant） |
| [baidu-pan-mcp/](baidu-pan-mcp/README.md) | 网盘 MCP 工具；本地目录，Git 忽略 |
| 根脚本 | `list-disks.ps1`、`scan-lan.ps1`、`scan-usb.ps1`、`serial-*.py`、`抓Radxa启动日志.bat` |

## 边界

- `references/` 只读；工具需要改动时在本目录或工作副本进行。
- 真实 API 配置、调用台账、密钥不提交。
- servo-web、robotd 补丁已移至 `software/`，不在本目录继续维护。
