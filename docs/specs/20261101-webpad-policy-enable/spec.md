# Spec：接通网页手柄所需的模型加载

- 日期：2026-11-01。
- 状态：用户已确认“已托稳，按方案接通模型”；已部署，六模型及网页绑定验收通过，保持卸力，未运行动作。
- 需求：使用现有 Studio 网页手柄，让已安装的六模型被 robotd 加载、现有五个技能绑定可识别；验收截至卸力状态的只读核对。
- 范围：只改 `/etc/robot/feetech-ft5/robotd.toml` 的 `[policy] enabled=false` 为 `true`，并重启 robotd。保留六模型路径、已写本机标定、动作参数、通信方式、保护和按键映射；不改源码、不配实体蓝牙手柄、不自动站姿/行走/执行技能、不提交推送。
- 依据：[当前实测、原生源码与网页状态](../../references/b-feetech-policy-deployment-20261024/webpad-models-check-20261101.md)。模型文件六个 SHA 全部一致；配置禁用使加载函数提前返回、技能列表为空。当前原生热加载命令因进程内启动字段 false 被拒绝。

## 修改与回退

1. 确认机器人当前已托稳／固定，可在重启时卸力。现有回读是上力保持；旧任务支撑确认不等于这次即时状态。
2. 再读当前配置及标定，若用户同时改了参数则以新的文件为基准，只定位修改 `[policy] enabled`，不回写本轮整份快照。
3. 使用原生 helper 同一配置锁避免与 Studio 提交冲突，备份当前配置、元数据和受保护文件 SHA。锁路径按当前 helper 现场读取。保存本项目候选 diff 和实际部署差异。
4. 原子写入单字段修改，保持 owner/mode，重启 robotd 一次；不重启 Studio、不关闭保护、不发送 enable/init/skill/twist。
5. 等待有限时间，读取加载结果和启动状态。若因这次修改导致加载/启动失败，保存失败日志，恢复此前配置并恢复服务；不以重复动作验证，也不覆写并发的新标定。
6. 成功只表示模型已加载、技能已注册且网页链路识别；真实行走和技能效果留待用户操作确认。

## 验收

- 原生 `motion/control`；`robot.policies.enabled=true`，六模型路径保持，槽位及整体加载无错误；预期三自定义技能 `roulade/kick_left/kick_right`，内置 `ground_pick/sit_toggle`。
- `pad.bindings` 五项不再报“没有这个技能”；网页只读状态不再有该绑定错误。卸力时技能仍因未开始走而不可按，这是正常前置条件。
- 启动后扭矩关闭、动态 `policy_enabled=false`，不自动运动。标定与模型哈希不变，实际配置差异只有一项布尔值；robotd/Studio active/enabled。
- 记录频率与主控温度/降频，已测 85°C／816 MHz，不能把没有推理动作的回读频率当作运行模型的实时性能验收。
- 更新研究、PROGRESS 与入口；默认不 commit/push。

## 确认原因

本任务的用户指令已授权配置网页手柄和核对模型。额外确认针对实际发现的加载配置修改和重启卸力：依据 [AGENTS.md](../../../AGENTS.md) 第四节第 8 条“修改方案经用户批准后方可编码”，以及原版 `main.rs:1608` 的 `confirm_startup_limp()`。不要求重复确认已完成的只读检查。

确认记录：用户于 2026-11-01 明确回复“已托稳，按方案接通模型”，授权单字段修改、重启卸力及只读验收，不自动站起、行走或执行技能。

## 实际交付

- 只将现行 robotd.toml 的 policy.enabled 改为 true，实际 diff 与方案相同；原生六模型加载成功、五绑定无错，实际网页状态同样通过。标定、模型及配套文件、基础服务和二进制 SHA 未变。
- robotd PID 1567、Studio PID 973 均 active/enabled；Studio未重启。原生 motion/control、动态动作关闭，15颗已确认卸力；未发送站姿、行走或技能命令。
- 首次验收错误地把 `torque_state_confirmed=false` 当成未确认，触发自动回退；源码实际定义 false=已确认关闭、null=未知。已严格按原生定义修正验收，在独立 attempt2 目录部署成功，保留首轮脚本和完整日志。两次安装及回退均在本次已确认的重启卸力范围内，无上力动作。
- 最终备份 `/etc/robot/feetech-ft5/backup-before-webpad-policy-20261101T080359146909Z/`。证据见[完整研究](../../references/b-feetech-policy-deployment-20261024/webpad-models-check-20261101.md)，实施见[工作副本](../../../tools/robotd-v03/webpad-control/README.md)。动作效果和推理实时性能未验收。

提交：未提交，保留工作区。
