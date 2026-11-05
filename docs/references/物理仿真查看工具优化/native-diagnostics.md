# Native 窗口针对性排查（2026-10-21）

## 范围与环境

仅查本机 `training/play_mujoco.py --viewer native` 低速与首次启动器退出码 1；没有安装软件、修改 WSL/Windows 图形设置、改依赖、重训或连接硬件。模型为 `training/models/duck_visual.xml`，策略为 `training/logs/rsl_rl/duck_walk/2026-10-19_15-02-25/model_9999.pt`，单环境、控制步长 0.02 秒。版本记录见下列 JSON。

## 本机实测

| 项目 | 结果 | 原始证据 |
|---|---|---|
| 初次 native 运行 | 3.169 秒墙钟，16 控制步，0.101×，10 次状态同步；Python 未记录异常，但 PowerShell 启动器退出 1 | [native-metrics.json](native-metrics.json) |
| 本机 GLFW 隐藏 OpenGL context | `DISPLAY=:0`，`WAYLAND_DISPLAY=wayland-0`；vendor `Mesa`；renderer `llvmpipe (LLVM 20.1.2, 256 bits)`；OpenGL `4.5 (Compatibility Profile) Mesa 25.2.8-0ubuntu0.24.04.2` | [native-diagnostics.json](native-diagnostics.json) 的 `renderer_probe` |
| 开启 `-X faulthandler` 再运行 | 3.203 秒墙钟，20 控制步，0.125×，11 次状态同步；直接捕获 Python 子进程退出码为 0，未出现 segfault/faulthandler 崩溃输出 | [native-diagnostic-metrics.json](native-diagnostic-metrics.json)、[native-diagnostic.log](native-diagnostic.log)、[native-diagnostics.json](native-diagnostics.json) 的 `native_process` |

重复运行从进程启动到退出耗时约 52.95 秒，包含模型、CUDA 和窗口初始化；上表 3.203 秒是初始化完成后的回放计时，两者不应混用。控制步骤的主机耗时中位数约 9.00 ms，不能把它当作窗口渲染时间。

2026-10-22 提交前仅清理日志一处行尾空格，日志内容及计时数据未改。

## 结论与限制

- **已验证：** 本机 WSLg 下本次 GLFW context 使用 CPU 软件渲染 `llvmpipe`；CUDA 可供策略/物理使用，不等于原生窗口也走 RTX 4080 图形渲染。native 的低速已复现，未通过实时播放验收。
- **未确认：** 首次启动器退出码 1 在本次直接捕获 Python 子进程的运行中没有复现；没有证据认定它是 GLFW segfault，也未定位退出码的具体原因。
- **范围限制：** 未分别测量每个原生渲染/同步阶段的耗时，故不能把软件渲染认定为全部低速的唯一原因。未尝试安装驱动或调整系统图形配置。
- **使用决定：** Python 参数帮助、原生入口启动提示和 PowerShell 启动器均将 native 标为“实验入口 / 本机软件渲染低速”；默认 Viser 保持日常入口。只有需要原生专有诊断时再单独处理 WSLg 图形路径。

原生 `scene_completed_hz_including_pauses` 不适用于浏览器场景任务，`native_sync_calls` 仅统计状态同步次数；两者都不代表实际窗口 FPS。`error: null` 只表示该 Python 计时对象没有捕获到异常，不能单独视作进程退出或实时验收成功。
