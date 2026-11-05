# 网页躺姿恢复（已部署，基本完成；M5 完善）

> **2026-11-05 状态（用户确认）**：起身恢复入口已达到基本完成要求；不完美（稳定性、承重、异常处理）转 M5 完善，不作为 M2 阻断。以下 11-01/11-02 故障记录保留。

**2026-11-02 01:11 第二次事件**：主控未重启，普通行走期间大量IMU/总线反馈异常，最终由网页“停下”关闭策略；本次没有调用显式恢复入口。只读快照显示扭矩仍开、机身未直立。见[第二次日志分析](../../docs/references/飞特策略模型上机核对/walk-fall-second-20261102.md)，不将上一事件的低压关机推断套用到本次。

**2026-11-02 排障更新**：用户在部署后尝试过恢复与行走，报告摔倒自动翻身后停机。
日志显示四次显式恢复很快结束，随后普通行走约17.45秒后Studio停止；已有低电压遥测和默认自动关机配置线索，缺故障系统日志，尚未定因。
用户重启后两服务已自启、策略与扭矩关闭。见[调查与原始证据](../../docs/references/飞特策略模型上机核对/walk-crash-investigation-20261101.md)。
下述“未动作”仅描述此前部署验收；本功能已达到基本完成要求（用户确认 2026-11-05），完整稳定性/承重验收与不完美项在 M5 处理。

2026-11-01：完成代码、隔离 ARM64 构建及无动作验证后，用户明确要求“部署”。
23:49已安装 `control.47+duck-recovery.1` 与配套Studio，网页新入口可用。
两服务保持自启、六模型加载、标定与模型哈希未变；只读验收后策略及扭矩仍关闭，未执行起身或行走。
详见[部署记录](../../docs/references/飞特策略模型上机核对/webpad-recovery-deployment-20261101.md)与[当前部署清单](deployment-status.json)。

新增独立“躺姿起身”按钮，复用已装联合 walk 模型，最长尝试 8 秒。
姿态连续符合判据后继续零速度保持，用户点“开始走”才交给普通驾驶。
超时、失效反馈、断连或停止请求取消恢复并请求卸力；卸力回读失败会明确报告。
**[实测／离线]** 下述测试验证了代码路径；没有物理仿真或真机承重成功数据。

## 交付与复查

| 文件 | 用途 |
|---|---|
| [来源说明](SOURCE.md)、[源码哈希](source-manifest.json) | 固定原件、修改范围及逐文件 SHA256 |
| [原生补丁](patches/firmware.patch) | 10 个文件，含新增状态机、API 43、设计文档及假 IO 测试 |
| [Studio 补丁](patches/studio.patch) | 5 个文件，含网页、会话所有权和急停放行配套 |
| [候选产物清单](candidate-manifest.json) | ARM64 二进制、候选包和基线回退包的 SHA256 |
| [当前部署清单](deployment-status.json) | 实际安装版本、服务状态、现场备份与网页验收 |
| [验收记录](verification/README.md) | 已通过项、原始日志和已确认的上游测试失败 |
| [实现 Spec](../../docs/specs/20261101-webpad-walk-recovery/spec.md) | 授权、完整行为、判据和真机验收边界 |

二进制和两个压缩包位于本目录 `artifacts/`（忽略构建产物）；补丁、清单、脚本及日志纳入可跟踪文件。
`.work/` 是可再生源码和测试缓存，不是唯一交付。没有修改只读参考库；2026-11-02 用户要求全量提交并推送，见[同步检查](../../docs/references/全量提交与托管同步/research.md)与 Git 历史。

## 控制边界

- `robot.recover` 使用编号及递增序号；网页每 100 ms 续期，原生租约 500 ms。后台不代发心跳。
- 原生独占总线；上力使用现有预载实测位置及扭矩回读，并额外读取一帧新反馈后推理。
- 固定使用 `Net::Walk` 与已装 SHA `1cbf8730…795f`，scale 1.0、头低通 0.5、腿低通 0.7。未添加旧 `stand_test`。
- 恢复中速度、头、身体和嘴中性；其他动作受限。停止和 HOME 请求先取消并卸力，新 HOME 必须另行请求。
- HOME 关节误差≤5°（不含嘴）、倾角≤10°且新鲜数据连续 1 秒才进入保持；再次失稳持续 1 秒退出。
- 普通起步保护、新单 3P IMU 的原版混合 SYNC_READ、标定及模型文件均未改。

姿态判据只表示传感器符合条件，不能独立判断脚底接触或稳定承重。8 秒上限和 1 秒窗口尚未真机验收。
原生机制详见固件补丁内 `docs/design/robotd-design.md` 的本项目恢复章节。

## 本地重建

需要来源清单列出的两个已缓存包和已归档 Studio 快照；脚本先验证哈希，缺件则停止，不联网取替代版本。
在本机 PowerShell、仓库根目录：

```powershell
python -X utf8 -B software/robotd-recovery/prepare-source.py --dest software/robotd-recovery/.work
```

目标必须不存在；已有 `.work` 时用新的目录名。最终已在 `.work/replay-final` 验证重放，15 个修改／新增文件哈希完全一致。
构建脚本固定读取 `.work/firmware`，在 WSL 新目录 `/root/duck-robot-recovery-20261101` 构建：

```powershell
wsl.exe -d Ubuntu-24.04 -- sh /mnt/c/Projects/duck-robot/software/robotd-recovery/build-local.sh build
```

本地检查入口为 `test`（状态机）、`guards`（协议和起步保护）、`integration`（真实模型＋假 IO）。
`baseline-check` 单独验证已存在的上游失败，预期退出非零；不与候选共享测试目录。
Python 后端测试用 `python -X utf8 -B software/robotd-recovery/tests/test_pad_recovery.py`；
浏览器心跳逻辑测试用 `node --test software/robotd-recovery/tests/test_pad_recovery.mjs`。
所需工具版本与 ONNX Runtime 路径见 [SOURCE.md](SOURCE.md)，不涉及机器人串口。

## 安装与回退

用户先授权实现、后明确授权部署，已完成安装；没有起身动作授权。
实际使用的[安装脚本](deploy/install.py)只接受显式`--apply`，要求基线匹配和实时确认卸力，并保留现场备份。
本机备份为`/etc/robot/feetech-ft5/backup-before-duck-recovery-20261101T154921811536Z/`。
以下为复用或回退时的核对范围；不能重放历史安装去覆盖后续用户改动：

1. 核对当时状态及板侧版本，现场备份实际运行的robotd、4个Studio原文件、服务配置、标定和模型哈希。本次`updates.py`等全部基线文件均已核对匹配。
2. 候选仅替换 robotd 和 Studio 的 `studio/pad.py`、`studio/pad_drive.py`、`studio/updates.py`、`web/pad.js`，新增 `studio/pad_recovery.py`；保持配置、六模型、标定、自动启动及混读方式。
3. 沿用现场配置锁、原子切换和服务管理。本次重启前已确认卸力，重启后只读确认新能力、模型和标定；没有动作测试。
4. 失败时恢复该次现场备份。附带的 `baseline-rollback` 是固定基线材料，**不是将来安装前的现场备份**；只在文件哈希一致时使用。回退新增文件仅在其哈希仍为候选值时移除，保留后续用户改动。
5. 真机起身仍须用户另行授权，记录初始躺姿、支撑、实际承重、耗时、反馈新鲜度和退出原因。上游升级可能覆盖本项目补丁，需要按新基线重新评估。

`candidate-manifest.json`、`source-manifest.json`及压缩包内清单保留构建时快照，`deployed=false`表示生成当时；当前实机状态以`deployment-status.json`为准，避免修改已核验产物的哈希。
