# 网页手柄与六模型核对

日期：2026-11-01。对象：Radxa `192.168.1.35`、原版 robotd control.47、当前 Studio、新单 3P IMU。用户已完成“写进主程序”，要求先使用网页手柄并确认模型已安装。先只读核对，再经用户确认托稳后修改单字段并重启；随后只读验收。重启按原生流程卸力，没有发送站姿、模型运行、速度或技能命令。

## 部署验收结果：六模型已加载，网页绑定已接通

- **[实测]** `/etc/robot/feetech-ft5/robotd.toml` 实际差异只有 `[policy] enabled=false → true`。原生 `loaded_models` 回报六个路径、任务名及对应 SHA256，与原上传件一致；`stand=null` 是有意关闭的独立站立槽，行走模型本身包含零速保持，不是漏装第七个模型。
- **[实测]** `robot.policies.enabled=true`；三个自定义技能 `roulade/kick_left/kick_right`、两个内置技能 `ground_pick/sit_toggle` 已注册，五项 `pad.bindings` 均无错误。实际网页 WebSocket 也已显示相同无错映射，技能置灰原因已变为“先站起来、点开始走”，不再是“没有这个技能”。
- **[实测]** robotd PID 1567、Studio PID 973 均 active/enabled，Studio 未重启；原生 motion/control、动态 `policy_enabled=false`、`torque_enabled=false`、`torque_state_confirmed=false`。最后一项含义是“已确认扭矩关闭”，不是未确认。没有自动站起或动作。
- **[实测]** 标定、基础 service、robotd 二进制、六个 ONNX 和目录内 JSON 配套文件 SHA 前后完全一致。最终备份 `/etc/robot/feetech-ft5/backup-before-webpad-policy-20261101T080359146909Z/`。只读加载/绑定验收通过，不代表实际行走、技能或推理时的 50 Hz 达标。
- 入口 `http://192.168.1.35:8000/#/pad`：用户操作次序为“站起来”→站稳后“开始走”→网页摇杆或键盘；本轮未代按。Esc 松开速度输入；Select／空格是卸力，操作前应区分。

### 首次验收脚本错误与恢复

第一次实际加载成功、五绑定无错，但助手编写的验收脚本错误地要求 `torque_state_confirmed=true`，因此触发恢复原配置及重启。源码 `duck-control/src/feetech.rs:2058–2070` 明确该字段为 `Option<bool>`：`Some(false)` 是成功写卸力并通过逐舵机回读，`None` 才是未知。助手核对后将验收改为严格要求 false；保留第一次脚本、回读和回退日志，在另一部署目录完成第二次安装且通过。不归因于模型或硬件；全程没有上力命令。

后续用户询问躺姿起身时，只读回包已变为上力保持、动态策略关闭；详见[后续能力核对](getup-availability-20261101.md)。本节卸力仅描述部署验收时刻。

## 接通前的核对与故障原因（已解决）

- **[用户确认／实测] 标定已正式写入。** 15 个 `calibrated=true`、`zero_raw=2048`，`motion_enabled=true`，IMU 已验证；原生 `motion/control`。helper 正式 commissioning 覆盖已不存在，这是成功交接后的状态，不应恢复旧覆盖。robotd PID 1361、Studio PID 973，均 active/enabled。
- **[实测] 六个模型文件都已安装并配置。** 下表每个 ONNX 的 SHA256 与 10-31 原上传索引一致；Studio `/api/models` HTTP 200，原生 `robot.policies` 六槽路径均有配置且 `error=null`。文件完整、路径已识别不等于当前推理控制器已加载，更不等于真机动作通过。
- **[实测／源码核验] 接通前模型加载被配置关闭。** `/etc/robot/feetech-ft5/robotd.toml` 的 `[policy] enabled=false`；`robot.policies.enabled=false`，网页与原生 `pad.bindings` 的五个技能映射均报 `this robot has no skill called ...`。源码在关闭时返回空策略名表并跳过 `Policy::load`。`robot.skills` 能列出磁盘上的三个自定义技能，不表示它们已注册在运行控制器中。
- **[实测] 接通前有用户触发的站姿保持。** 网页状态为 `holding`，`homed=true`、扭矩有效、动态 `policy_enabled=false`；助手没有触发这一站姿。不可把页面“开始走”按钮可点当作策略可运行：它调用 `robot.enable`，原生还会检查已加载的行走策略。
- **[源码核验] 加载开关与动作开关不同。** 修改文件为 `enabled=true` 后须重启才能更新进程内 `state.policy_enabled`；当前原生 `robot.reloadPolicies` 在该字段为 false 时拒绝，不能靠热加载绕过。启动默认意图仍为关闭且先执行 `confirm_startup_limp()`；故重启会卸力，但不自动上力或执行策略。具体修改方案见 [Spec](../../specs/20261101-webpad-policy-enable/spec.md)。

## 六模型及现有映射

所有路径均在 `/home/radxa/studio-dev/state/models/<目录 ID>/policy.onnx`；原始备份在 `/home/radxa/duck-policies/hd1910-20261031/`。

| 模型槽 | 内容 | Studio 目录 ID | 现有网页手柄绑定 |
|---|---|---|---|
| `walk` | 行走、零速保持与倒地恢复联合策略 | `316b92cd3d4f42babda055a804e73b03` | “开始走”后摇杆／键盘速度输入 |
| `sitstand` | 起坐 | `777c1b28fe47420b9180a4298e04b0bb` | 十字键下，`sit_toggle` |
| `ground_pick` | 地面捡取 | `33bb2637cdc947809511af1985397e26` | 图中 A |
| `kick_left` | 左脚踢球 | `08f3ea309a604a79a1989d5a1fa87622` | LB |
| `kick_right` | 右脚踢球 | `ea26b97e6a054e558e9f295c94634670` | RB |
| `roulade` | 前滚翻 | `4bcb5891434a43eeaf19842ae9444520` | 图中 X |

映射已经在 `[pad]` 中，无需重写按键；接通前五个技能因加载关闭而不可执行，现已消除该原因。10-31 的 6/6 无电机前向预检是历史证据，本轮未重复该预检；原生启动实际加载并预热模型，但未执行这些动作。

## 网页入口和操作边界

- 入口：`http://192.168.1.35:8000/#/pad`。已向 Codex 浏览器发出打开请求，工具返回 queued；没有宣称亲眼看到页面显示。
- 实际 WebSocket `pad.op/watch` 与 `pad.op/drive open=true` 均返回成功，`virtual.mirror=false`、`pad_unknown=null`、`driver=null`。`drive open` 只打开该页面的输入资格，不抢驾驶权、不发速度；诊断连接随后关闭。
- 网页手柄无需蓝牙配对。实体配置/映射服务 socket 缺失会使实体映射区域不可用，不构成网页手柄需要另装 padd/configd 的证据；本轮没有安装这些服务或伪造实体手柄测试完成标志。
- 点手柄图使其接收键盘：W/S 前后，A/D 左右平移，Q/E 转向。此处键盘 A 与图中的 A 动作按钮不同。
- Esc 松开网页输入、速度归零，不卸力；空格／Select／顶部卸力会卸力。模型现在已加载，当前是卸力状态，真实运动由用户另行操作。

## 其他实测与限制

- **[实测／最终回读]** 部署后 6418 周期，卸力循环约 49.97 Hz、`consecutive_errors=0`、IMU ready；CPU 85°C、408 MHz、降频 level=6。当前六模型已加载但不执行动作，不能将卸力循环频率当作模型运行性能。正式行走前建议先处理主控散热，未在本轮改风扇/频率设置。见[最终健康和HTTP回包](webpad-policy-final-health-20261101.json)。

- 后续只读健康回包：控制频率约 50.04 Hz、`consecutive_errors=0`、IMU ready；主控 `cpu_temp_c=85`、当前 816 MHz，最高 1800 MHz，`cpu_throttle.level=4`。这是本次温度/降频快照，尚未验证加载模型后的实时性能；不归因为某个未查明的散热原因。
- 电压回包约 6.825 V，来自程序遥测，不是独立电表测量，不据此擅自调整电源。
- 读取诊断 JSON 后 Windows SSH stderr 曾输出 `IO is still pending on closed socket`，stdout JSON 完整且解析成功、RPC及HTTP回包齐全；没有因此重跑或触发任何动作。
- 接通前对技能不可用已有直接配置和源码证据，不需要先假设模型损坏或更改 Studio 版本。后续仍可能出现通信、实时性能或动作参数问题，需在相应实际阶段判断；本轮没有动作验收。

## 来源与原始证据

| 来源 | 定位与用途 |
|---|---|
| [真机与模型快照](webpad-models-snapshot-20261101.json) | 配置原文、标定、服务状态、六文件大小及 SHA、部署 Studio 源码；含独立标注的板侧 UTC 时刻 |
| [只读采集脚本](collect-webpad-models-20261101.py) | 上述快照生成方式 |
| [网页状态及发送列表](webpad-page-status-20261101.json) / [脚本](check-webpad-page-20261101.py) | 原始 WebSocket 状态、五个绑定错误、无控制租约 |
| [原生加载门槛及模型库回包](webpad-policy-gate-20261101.json) / [脚本](check-webpad-policy-gate-20261101.py) | `robot.policies`、`robot.skills`、`pad.bindings`、`robot.health`、`robot.busStatus`，Studio `/api/models` |
| 固定原版源码 | `training/logs/b-feetech-walk-20261024/controller-preparation-20261031/controller-source/fanhao375-Microduck-kissqy-27d7921/microduck-hd1910/firmware/robotd/src/main.rs`：392 禁用时空名表；1608 启动卸力；2097–2155 控制器加载；5192–5216 绑定校验；5768–5780 禁用时拒绝热加载；5878–5960 原生 enable 前置检查 |
| 启动动作默认值 | 同目录 `intents.rs:278–297`：`enabled=0`、`POWER_NONE`；不是配置 enabled=true 就立即运行动作 |
| 已部署网页源码 | 快照 `sources` 中 `web/pad.js`、`studio/pad.py`、`studio/pad_drive.py`；pad.py:937–960 获取原生绑定；pad_drive.py:1415–1427 从策略回包构建技能 |

补充证据：[单字段候选差异](webpad-policy-enable-proposed.diff)、[首次脚本](webpad-policy-enable-attempt1-20261101.py)、[首次加载及误判回退](webpad-policy-enable-deployment-20261101.json)、[回退后的只读状态](webpad-policy-after-rollback-20261101.json)、[最终成功部署](webpad-policy-enable-final-20261101.json)、[实际网页最终状态](webpad-page-final-20261101.json)。可维护安装脚本和说明见[工作副本](../../../tools/robotd-v03/webpad-control/README.md)。

本轮板侧只修改加载开关；已记录首次错误、回退和最终成功。代码和记录保留工作区，未提交。
