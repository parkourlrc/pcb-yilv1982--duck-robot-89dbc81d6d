# Spec：把 robotd 启动配置接入 Studio 标定交接

- 日期：2026-11-01。
- 状态：已交付，原生和网页预览通过；迁移当轮未重启或卸力。用户随后自行正式提交成功，原生 motion/control、15个calibrated=true、motion_enabled=true，见[后续回读](../../references/b-feetech-policy-deployment-20261024/webpad-models-check-20261101.md)。
- 需求：解决第 3 步“去做”后“主程序的标定模式不是镜像设的，不敢自动切”，让当前部署可使用 Studio 原生预览及后续正式交接。
- 负面范围：不改 robotd/Studio/helper 源码，不绕过姿态和错误保护，不重启当前服务、不卸力、不重新写舵机 EEPROM、不自动正式提交标定、不开模型、不试站姿。本轮迁移后继续 commissioning；正常提交由用户托稳卸力后在网页完成。
- 依据：[真机快照、报错路径和截图](../../references/b-feetech-policy-deployment-20261024/studio-commit-mode-error-20261101.md)。正式覆盖文件缺失，旧 30 文件开启 commissioning，基础服务有 `--read-only`；上一轮 15 个零位修正已生效。

## 文件方案

1. `/etc/systemd/system/robotd.service`：只从基础 ExecStart 删除 `--read-only`；保留参数路径、socket、ONNX 环境、用户组、服务安全配置与自启关系。描述改为匹配现行用途。
2. `/etc/systemd/system/robotd.service.d/zzzz-zz-microduck-commissioning.conf`：采用当前 commissioning 覆盖内容，保留完全相同的有效 ExecStart；这是 helper 正式管理的文件名。
3. `/etc/systemd/system/robotd.service.d/30-studio-commissioning.conf`：备份至独立备份目录后移出生效目录，避免将来正式提交仅删除新文件后，旧文件继续强制 commissioning。
4. `zzzz-studio-bus.conf`、其他服务/启动项、模型和标定不改。原始来源和修改说明保存在本项目 `tools/robotd-v03/`，参考库只读。

## 部署与回退

- 在 helper 的互斥锁保护下再次检查现行文件、当前进程和会话状态；若有正在运行的提交或 IMU 重做会话，先停止迁移，不干扰用户操作。
- 先保存原服务、全部相关覆盖文件和元数据，再依次写正式 commissioning 覆盖、调整基础服务、移出旧覆盖；迁移期间始终保留至少一份有效 commissioning 覆盖。
- 只 `systemctl daemon-reload`，不 restart/start/stop。核对最终 ExecStart 与迁移前相同、robotd 和 Studio PID 不变、两个服务与自启状态维持。失败恢复原文件并再次 reload，不通过重启来掩盖错误。
- 备份前后读取标定、pending、主配置哈希；迁移工具不写这些数据。并发的用户新标定需如实单独记录，不能覆盖回旧值。

## 验收与交付

- helper `calib-read` 为 `commissioning`、正式覆盖存在，foreign 提示条件消失。
- 用当前 15 个方向和最新已验证/待写 IMU 数据调用原生 `calib-commit` 的 `dry_run=true`，只生成预览；检查成功且无标定文件写入和服务重启。
- 预览的完成标志/动作允许状态属于用户后续正式提交内容，不在本次提前写入；原生模型 `policy.enabled` 不改。
- 若当前仍站姿保持，页面的黄色“先失能/卸力”提示应继续存在；这是预期保护，不删除。正式提交会重启并卸力，须由用户托稳后在网页完成。
- 记录实际变更、备份、原生预览和状态，更新 README、PROGRESS、研究入口、tools/robotd-v03/README 与 Spec 索引。不得把预览成功写作已进运动模式或动作验收。
- 默认未提交，保留工作区；用户明确要求后才 commit/push。

确认记录：用户于 2026-11-01 对本方案回复“按方案修正”。授权启动/交接配置迁移、仅 daemon-reload 和原生预览；正式“写进主程序”由用户托稳卸力后在页面操作。

## 实际交付

- [实测] 按上述 3 个文件方案迁移，使用 helper 的同一 flock 互斥锁；基础服务与所有旧覆盖原件备份至 `/etc/robot/feetech-ft5/backup-before-studio-handover-20261101T074627191148Z/`。只执行一次 daemon-reload，无服务重启或正式提交命令。
- [实测] helper `calib-read` 为 commissioning；原生 `dry_run=true` 和 Studio WebSocket `calib.op/preview` 均成功，网页准备状态 `ready=true`，HTTP 200。
- [实测] robotd PID 1067、Studio PID 973 前后不变、active/enabled；有效启动参数及进程启动时刻不变。迁移前已卸力，后仍 commissioning/ready/off；本工具没有卸力操作。
- [实测] 标定文件、最新 IMU pending、中位/方向数据、主配置、总线交接覆盖、helper、binary、Studio commit 源码 SHA 前后一致。正式标定完成标志仍未写入。
- 原件与实现见[工作副本](../../../tools/robotd-v03/studio-handover/README.md)，执行证据见[部署 JSON](../../references/b-feetech-policy-deployment-20261024/studio-handover-deployment-20261101.json)和[网页预览 JSON](../../references/b-feetech-policy-deployment-20261024/studio-handover-page-preview-20261101.json)。用户随后已自行正式提交，后续回读已归档；不把后续交接归为本迁移工具的动作。
- 未偏离批准方案。修改保留工作区，未 commit/push。
