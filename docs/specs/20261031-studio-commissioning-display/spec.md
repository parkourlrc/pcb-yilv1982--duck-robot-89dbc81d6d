# Spec：Studio 调试模式数据显示适配

- 日期：2026-10-31
- 状态：**已交付，网页数据接口验收通过**。
- 已有授权：用户已支撑机器人并批准切换现成 commissioning 模式；此服务操作已完成。2026-10-31 用户针对已落盘的需求、现状与修复方案回复“继续”，据此执行显示适配和部署，无需重复确认。
- 提交：未提交，保留工作区。

## 需求与验收建议

解决 Studio 调试模式中“原生接口有 15 颗舵机反馈，页面总览在线数为空、舵机表 0/15 且位置为空”的显示问题。使用现有 robotd 反馈显示在线数、位置、电压、温度，并正确保留 IMU 安装方向未验证状态。

不改变串口读取、模型执行、标定数值、关节方向、EEPROM 或扭矩；不启用策略、不做点动。3D 关节姿势依赖的角度/标定接口另行核对，不用参考标定拼造已验证姿态。

验收建议：实际 `/ws` 的总览和舵机表与同次原生反馈一致；有效帧可显示 15/15，停止推进/过期帧显示未知或过期，不把旧反馈持续算在线；断连与重启不能复用旧会话状态。模型动作保持关闭。

## 现状与证据

- [实测] robotd `control.47+duck-v03.1`，API 42，`commissioning/ready`，15 颗扭矩已关闭。Studio 源包修订 `2026.10.3101`，运行目录 `/home/radxa/studio-dev`；网页自报应用内部版本 `0.1.0-dev`，不与源包修订混用。
- [实测] 实际网页接口已收到 IMU 动态重力、电压和循环频率；总览 `servos.online=null`，舵机表 `online=0`，原生 `last_sample.servos` 有 15 颗数据。
- [源码核验] `studio/state.py:191` 与 `studio/servo.py:667` 读取 `native.joints`；`state.py:239` 已单独从 commissioning 的 `last_sample.imu` 取重力。`startup_status.py` 的诊断输入主要为启动模式 `native` 观察值，不覆盖这一调试格式。
- 原始证据、安装状态与失败记录：[统一研究](../../references/飞特策略模型上机核对/research.md)、[网页接口](../../references/飞特策略模型上机核对/studio-commissioning-websocket-20261031.json)、[原生回读](../../references/飞特策略模型上机核对/studio-commissioning-final-20261031.json)。
- 受影响入口：根 README、PROGRESS、`software/robotd-v03/README.md`、本 Spec 索引与统一研究。BOM/接线/参考库无需修改。

## 已批准修改方案

1. 在本项目可写工具目录保存固定 Studio 来源、工作副本或可重放补丁；板侧修改前备份实际目标文件和 SHA。三个 `references/microduck-*` 保持只读。
2. 在 Studio 增加仅用于显示的 commissioning 反馈整理：读取 `last_sample.servos`，映射 ID、原始位置、电压、温度等；供总览和舵机表共用，保持现有 motion/startup 分支行为。预期涉及 `studio/state.py`、`studio/servo.py` 与显示数据整理模块；必要的新鲜度跟踪限定在 `studio/robotd.py` 轮询缓存，不改变 RPC 或硬件命令。
3. 通过样本周期是否推进、原生样本时间与接收时间判断新鲜度；robotd 重启或断连时清掉旧上下文。`read_error` 时保留清楚的过期/错误状态，不凭接收到相同 JSON 就把旧帧刷新为在线。
4. IMU 显示使用原生 `ready/valid/mount_verified`，明确安装方向未验证；缺少的诊断字段继续显示未知，不编造传感器状态。
5. 只部署涉及的 Studio 文件并重启 Studio，robotd 保持当前调试与卸力状态。失败时恢复此次文件备份并重启 Studio。
6. 检查限于该格式适配：有效、过期/不推进、会话切换的代表数据，再读取实际 `/ws` 核对在线数、位置和 IMU 状态；不重跑模型/总线长测。

## 阶段记录

- 前轮完成现状排障、服务切换和候选需求整理；没有修改 Studio/robotd 功能源码。
- 本轮用户明确“继续”后进入编码。IMU 页 `studio/imu.py` 的 `view()` 与总览共用显示新鲜度，属于方案第 4 项的显示适配；不改该文件的校准或控制方法。

## 实施与验收

- 持久成果：[工具目录](../../../software/robotd-v03/studio-display/README.md)，含四个上游原件、五个部署文件、补丁、SHA 清单与安装脚本。三个只读参考库未修改。
- [实测] 6 项针对性检查通过；有效反馈、过期、重复旧帧、读错/断连、会话更换及非 commissioning 分支均已覆盖。见[日志](../../references/飞特策略模型上机核对/studio-display-tests-20261031.log)。
- [实测] 23:44:52 备份后部署，23:45:16 仅重启 Studio。robotd PID 4092 保持不变、扭矩关闭、策略关闭；配置和标定 SHA 未变。备份目录 `/home/radxa/studio-display-backups/20261031T154452988692Z/`，见[安装报告](../../references/飞特策略模型上机核对/studio-display-install-20261031.json)。
- [实测] 实际 `/ws` 至少 3 帧总览与 2 帧舵机表均显示 15/15，全部位置/电压/温度有效；IMU 重力持续更新、安装方向标为未验证。见[网页验收](../../references/飞特策略模型上机核对/studio-display-websocket-20261031.json)。未发送硬件控制命令，也未做浏览器画面验收。
- 遗留边界：3D 标定关节弧度、缺少的 IMU 原生诊断字段、本机标定与动作验收仍不在此次显示修复完成声明内；原生偶发通信失败仍有记录。
- 未提交、未推送，工作区保留。
