# Studio 第 3 步 foreign_commissioning 修正与正式交接完成

日期：2026-11-01。对象：Radxa `192.168.1.35`、Studio 当前部署版、原版 control.47、新单 3P 口 IMU。先只读定位，随后经用户批准迁移启动配置；只 daemon-reload，未重启、未卸力、未正式提交标定或运行模型。

## 后续正式写入已完成

[用户确认／实测] 用户已自行完成“写进主程序”；后续回读为 motion/control、15 个 calibrated=true、motion_enabled=true、zero_raw=2048，IMU 已验证。正式 commissioning 覆盖已由 helper 删除，不应恢复。本轮后续又已接通六模型加载，动作仍关闭；见[最新网页手柄与模型记录](webpad-models-check-20261101.md)。以下记录限定为此前安装/预览阶段，不再作为待提交指导。

## 此前安装与预览执行结果

- **[实测]** 已将基础服务去掉 `--read-only`，原 commissioning 覆盖迁入 helper 正式管理的文件名，旧覆盖已备份并移出生效目录；helper `calib-read` 为 commissioning，foreign 条件已消除。实施与原件见[工作副本](../../../tools/robotd-v03/studio-handover/README.md)。
- **[实测]** 原生 helper 预览成功；另通过实际 Studio WebSocket 的 `calib.op` / `op=preview` 验证页面入口，回 `ok=true`，准备状态 `ready=true`、HTTP 200。没有发送 `op=commit`。
- **[实测]** 只 daemon-reload；robotd PID 1067 和 Studio PID 973、进程启动时刻、有效启动参数均未变，两服务 active/enabled。迁移前已是 commissioning/ready/off，结束仍相同；未由助手卸力。此前截图中的 holding 是修正前采集时的状态，不当作迁移开始状态。
- **[实测]** 标定、主配置、中位/方向记录、最新 pending、总线交接覆盖、helper、robotd 二进制和 Studio commit 源码的哈希均前后一致。预览采用当时最新 pending `[0.03257974300004262, -0.7032482290009199, -0.020598759000026945, -0.7098987110009286]`，没有写入正式标定；`motion_enabled` 和 15 个 `calibrated` 仍保持原来的 false。
- **证据**：[完整部署](studio-handover-deployment-20261101.json)、[实际网页预览](studio-handover-page-preview-20261101.json)、[网页核对脚本](verify-studio-handover-page-20261101.py)。备份目录 `/etc/robot/feetech-ft5/backup-before-studio-handover-20261101T074627191148Z/`。该次预览没有完成正式写入；后续用户已完成交接，见上节。

## 修正前的定位结论

- **[实测]** 定位时主程序在线，原生状态为 `commissioning/holding`、`torque_state=all_enabled`，最大 HOME 跟随误差回报 `1.669921875°`。15 个 `zero_raw` 仍为 2048。说明该时刻确有用户触发的站姿保持和较小的编码器目标误差；不是实物量角或无支撑平衡验收。助手没有发动作。
- **[实测]** `sudo -n /usr/local/sbin/microduck-helper calib-read` 返回 `mode=foreign`、`commissioning_present=false`、`exec_has_commissioning=true`，与截图红字一致。
- **[源码核验]** helper 只认识 `/etc/systemd/system/robotd.service.d/zzzz-zz-microduck-commissioning.conf`。本机现用 `30-studio-commissioning.conf`，它不是 helper 可自动管理的文件；看到启动参数含 `--commissioning` 而正式文件缺失，就拒绝预览/提交。这是安装时遗留的交接配置缺口，与舵机零位数值是否正确是两件事。
- **[源码核验]** 基础 `/etc/systemd/system/robotd.service` 仍带 `--read-only`。仅将旧覆盖文件改名，会使正式提交删除覆盖文件后回到只读模式；helper 要求 `motion/control`，因此还需同时修正基础启动方式。
- **[实测／截图及源码]** 截图黄色“鸭子姿势”是另一个门槛：目前标定站姿保持未解除，Studio 阻止正式写入，因为写入会重启并卸力。修好模式识别后仍须先托稳，再由用户在 IMU 页点“失能”或顶部“卸力”；不能靠勾选“已完成”绕过。

上述修正前确定项分别由配置文件、只读 helper 和原生回读支持，不归因于硬件。配置已按上节修正，但仍不能排除正式交接时出现其他校验或通信故障；迁移当轮没有执行真实提交；后续用户完成交接的实测见顶部。

## 原生交接行为和边界

1. `studio/commit.py:930–946` 的预览调用 helper `calib-commit`、`dry_run=true`。helper 在生成预览前同样执行严格的 `calib_mode` 检查，因此点“去做”展开预览也可能出现这条红字，不意味着已经写坏文件。
2. helper `1245–1258` 判定正式 commissioning 覆盖文件，缺失且有效 ExecStart 含 `--commissioning` 时返回/抛出 foreign；`1717–1773` 在预览分支返回前不会写标定或重启。
3. helper 正式提交 `1792–1806` 写标定及 saved、删除其认识的 commissioning 覆盖文件、daemon-reload、重启；随后等待 `motion/control` 和逐项标定回读。失败按原生备份回滚。此路径不能通过只重命名覆盖文件完成适配。
4. `studio/commit.py:111–205` / helper `750–844` 正式构造标定时会设置 15 个 `calibrated=true`、`motion_enabled=true`，按标准限位写文件并采用本次 IMU 方向。这超出上一轮“只对齐 15 个零位”的授权范围，本轮没有执行。
5. `studio/commit.py:readiness` 在 commissioning 有 hold 时显示截图中的黄色姿态项；上一轮仅修正零位没有绕过这一检查。
6. 原版 robotd `main.rs:1608–1635` 的运动模式启动先 `confirm_startup_limp()`，保持显式启用机制。服务迁移方案本身仅 daemon-reload，继续当前 commissioning 进程，不进入这段启动流程。

定位快照中的已写 IMU 标定为 `[0.031768001, -0.713162338, -0.029238557, -0.69966805]`，与零位部署时保留值不同；当时另有上节记录的待正式写入 pending。后续始终读取当时文件/Studio pending；不把本记录中的数值写回覆盖最新标定。

## 已批准并执行的方案

启动配置已接入 Studio 的原生交接约定：基础服务去掉 `--read-only`；commissioning 参数迁入 helper 认识的正式覆盖文件，归档旧 `30-studio-commissioning.conf`。在互斥锁保护下备份与调整，仅执行 daemon-reload，保留当前 commissioning 进程、标定文件、模型参数和全部动作保护。

验收已核对有效 ExecStart 与 PID 不变、helper 从 foreign 变为 commissioning，并运行原生 `dry_run=true` 与实际网页预览，确认标定/主配置等受保护文件未被改写。预览成功不等于完成真实提交。该次正式写入留给用户操作，用户随后已完成；迁移工具没有代点提交、站姿或启用模型。见[批准及交付记录](../../specs/20261101-studio-calibration-handover/spec.md)。

## 图片、来源与证据

| 文件 | 来源／收到日期 | 内容与验证状态 |
|---|---|---|
| [用户截图原件](studio-commit-mode-error-user-20261101.png) | 用户提供，2026-11-01 收到；原名 `codex-clipboard-77de9eae-50f7-415c-b87c-d188483275bb.png` | 第 3 步“写进主程序”的 foreign 红字和站姿未解除提示；原字节已保存、与临时附件一致；截图拍摄时间未核 |
| [真机完整快照](studio-commit-handover-snapshot-20261101.json) | 本机只读采集 | 当前 helper/Studio 源码、systemd 文件、标定与 pending、RPC、过滤日志；文本 SHA 回验通过 |
| [结论数据与图片 SHA](studio-commit-mode-error-findings-20261101.json) | 本次快照派生 | 模式、零位、保持状态、图片来源；板钟单独标注，不当作工作机精确时钟 |
| [采集脚本](collect-studio-commit-handover-20261101.py) | 本项目 | 只读文件和接口，不发送 UART 目标、扭矩、提交或服务重启命令 |

早期同类缺口见 [helper 初次检查](studio-calibration-helper-20261101.json)；前一项零位修正已完成，见[零位部署记录](studio-home-target-mismatch-20261101.md)。本次启动/交接适配和预览验收已完成，不需要因此重做全部中位校准。参考库未改；记录未提交。
