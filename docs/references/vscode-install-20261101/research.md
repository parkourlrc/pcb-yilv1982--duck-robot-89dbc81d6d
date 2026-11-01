# Windows VS Code 安装记录

- 日期：2026-11-01（Asia/Shanghai）。
- 需求与范围：[用户确认] 安装 VS Code；属于本机工具安装，不涉及项目功能开发。
- 关联进度：[PROGRESS.md](../../../PROGRESS.md)。

## 来源与执行

- 包来源：WinGet 官方源 `winget`，精确包 ID `Microsoft.VisualStudioCode`，用户范围安装。
- 安装包 URL：<https://vscode.download.prss.microsoft.com/dbazure/download/stable/e646868227c3e3a9e3f24277c8c7220be42c0be7/VSCodeUserSetup-x64-1.143.1.exe>。
- 官方 Windows 安装说明入口：<https://code.visualstudio.com/docs/setup/windows>；本轮网页工具未返回正文，不据此声称核验了页面内容。
- 本机证据定位：安装命令输出、`code.cmd --version`、WinGet 安装清单、开始菜单快捷方式与用户 PATH，原始关键输出见 [verification.txt](verification.txt)。

```powershell
winget install --id Microsoft.VisualStudioCode --exact --source winget --scope user --silent --accept-package-agreements --accept-source-agreements --disable-interactivity
```

## 结果与验证边界

- [实测] 安装前常规用户/系统路径未找到 Code.exe，PATH 未找到 code，WinGet 精确查询未找到已安装包；未全盘搜索便携版。
- [实测] WinGet 选择 1.143.1，完成安装包哈希校验并返回 `Successfully installed`，退出码 0。
- [实测] 安装后命令行版本为 1.143.1、提交 e646868227c3e3a9e3f24277c8c7220be42c0be7、架构 x64；WinGet 清单确认当前用户版 1.143.1。
- [实测] 程序路径：`C:\Users\elvis\AppData\Local\Programs\Microsoft VS Code\Code.exe`。
- [实测] 开始菜单已存在 Visual Studio Code 快捷方式，用户 PATH 已包含安装目录的 `bin`。
- 验证范围：安装与 CLI 入口核对完成，未做 GUI 交互验收，未另行安装扩展或修改项目设置。
- 失败与待确认：安装无失败；网页正文未取得，详见来源说明。无阻碍使用的安装待办。
- 下一步：从开始菜单启动；新开终端后可使用 `code .` 打开当前目录。
- 工作区记录保留未提交、未推送。
