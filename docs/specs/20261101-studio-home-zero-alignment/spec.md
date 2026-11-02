# Spec：对齐 Studio 两个站姿入口的编码器零位

- 日期：2026-11-01。
- 状态：用户已确认“已托稳，按方案修正”；已部署并完成只读验收，未试站姿，未提交。
- 需求：用户反馈舵机页站姿正确、IMU 页角度错误。修正两者使用的零位不一致，使共同 14 个关节的 HOME 原始目标相同；嘴沿用各入口原有行为。
- 依据：[板侧实际配置、源码及目标比较](../../references/b-feetech-policy-deployment-20261024/studio-home-target-mismatch-20261101.md)。Studio 已记录 15 颗中位校准、页面公式零位 2048；robotd 加载的却仍为参考机的不同零位。方向均 −1、共同 HOME 弧度相同、无另存站姿覆盖。
- 修改：将主程序标定文件的 15 个 `zero_raw` 改为 2048；保留其他所有字段，包括最新 IMU 标定、校准完成标志、动作开关、方向、限位。没有重新写舵机 EEPROM，没有改模型、P/D、读序或错误保护。
- 审阅存档：[候选 TOML](../../references/b-feetech-policy-deployment-20261024/studio-home-zero-alignment-proposed.toml)、[候选差异](../../references/b-feetech-policy-deployment-20261024/studio-home-zero-alignment-proposed.diff)。部署依据为停服后的最新文件，实际结果见[部署回读](../../references/b-feetech-policy-deployment-20261024/studio-home-zero-alignment-deployment-20261101.json)与[当前标定快照](../../references/b-feetech-policy-deployment-20261024/hd1910-calibration-zero-aligned-20261101.toml)，不能整体复制较早候选。
- 部署方案：用户确认并确保机器人有支撑后，检查实际会话/扭矩，短暂停 Studio/robotd，保存当前原件和哈希；基于停服后的最新文件仅替换零位，验证其余字段完全相同，恢复原本运行的服务。不能用较早候选整文件覆盖用户此间的新 IMU 标定。
- 验收：只读回读 `calibration-status`，确认 15 个零位为 2048、原字段和保护不变、服务正常；离线计算共同 14 个目标一致。此阶段不自动调用站姿，不把字段写入视为物理站姿或模型验收。
- 风险与回退：零位直接改变下一次动作的目标，重启 commissioning 会卸力；保留当前动作关闭/未完成状态。失败则保留服务停止或恢复安全的原配置，不自行试动作。参考机零位原件保留供追溯，不再次作为当前本机零位。
- 独立遗留：新板日志出现过 ID 200 缺答；本方案不声称解决通信故障。Studio 正式提交/模式交接仍属后续功能，不在此处设置 `motion_enabled=true` 或 `calibrated=true`。
- 提交：未提交，保留工作区。

用户批准内容：只改 15 个 zero_raw 为 2048，保留最新 IMU 标定和动作保护，重启后只读核对，不自动试站姿；用户同时确认当前已托稳。部署按停服后的最新文件生成，不整体覆盖早先候选。

## 执行与验收

- [实测] 文件仅 15 个 `zero_raw` 改为 2048，重启后原生 `calibration-status` 全部回读一致；IMU 安装四元数 `[0.047458248, -0.683087043, -0.048132479, -0.727202221]` 与 `imu_mount_verified=true` 保留，15 个 `calibrated=false`、`motion_enabled=false` 保留。
- [实测] 主配置、Studio 中位/方向记录及 robotd 二进制哈希前后一致；两服务 active/enabled，Studio HTTP 200，servo-web inactive/disabled。验收时 commissioning/ready、torque off、无运动、策略关闭。
- [实测] 首次原生回读已通过，但 HTTP 检查早于 Studio 就绪，脚本按设计停止服务并恢复原文件。首轮证据保留；部署脚本补齐有限启动等待，使用独立重试目录再次部署，第 10 次 HTTP 检查成功。此为验收脚本等待问题，不据此声称出现硬件故障。
- [源码计算／边界] 共同 14 个关节目标一致，嘴仍按两个入口各自范围处理。本轮没有动作复验，没有宣称修复通信或完成正式标定交接。
