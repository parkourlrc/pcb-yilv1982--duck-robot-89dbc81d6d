# Radxa 上的六个 HD1910 策略模型

- 日期：2026-10-31。
- 设备：`radxa-zero3`，用户 `radxa`。
- 存放目录：`/home/radxa/duck-policies/hd1910-20261031/`。
- 状态：六个模型及各自原始配套文件已上传，ONNX SHA-256 与本地源文件逐个一致；未接入 robotd、未启用策略、未发运动指令。

| 运行槽 | 模型 | 相对路径 |
|---|---|---|
| `walk` | 行走、零速度保持与倒地恢复联合 | `models/1cbf8730eadd75a5704332c9f3c10f60/policy.onnx` |
| `sitstand` | 坐下与站起 | `models/1c94934c6421ec72ed48079cea749668/policy.onnx` |
| `ground_pick` | 地面捡取 | `models/b14e3a8b56ddbb8d2d831e727774a168/policy.onnx` |
| `roulade` | 前滚翻 | `models/59e15d7b04d0c40e9b11b8a70bdecae6/policy.onnx` |
| `kick_left` | 左脚踢球 | `models/ee0376c927044cdece056ba1d3e6eac7/policy.onnx` |
| `kick_right` | 右脚踢球 | `models/67ad09d82f4865d222a7ae06f250cf9f/policy.onnx` |

`catalog.json` 是本次六模型目录索引，`transfer-verification.json` 是真机文件哈希回读。`source-inventory.json` 是来源库的完整历史库存，含未在本次上传的滑轮和 A 线条目；板上实际范围以本表和 catalog 为准。

这些模型来自 `kissqy/Microduck-kissqy` 的 HD1910 配套包；许可见 `POLICIES-LICENSE.txt`。模型声明均为 `deployment_verified=false`，动作名称表示上游用途，不代表本机已验证的能力。

现成控制软件候选为 `fanhao375/microduck-replica` 的 Microduck Studio（网页控制台）配套飞特版 robotd（实际策略执行）。Studio 提供上述六类模型槽、模型导入/切换、网页遥控和实体手柄入口。当前板子仅有 servo-web 0.15.4，未安装此控制栈；本目录不是自动加载目录。

接入前要落实运行栈安装、本机标定和 v0.3/replica 0.2.0 IMU 的单播读取方式；原模型动作合同及运行时滤波差异也须按实际版本解析。具体证据在项目 `docs/references/b-feetech-policy-deployment-20261024/research.md` 的 2026-10-31 上传与控制器核查节。
