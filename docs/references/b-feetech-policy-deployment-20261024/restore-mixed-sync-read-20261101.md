# 单口替换板：恢复混合 SYNC_READ

日期：2026-11-01。用户已确认换上新的单 3P 口 IMU，并明确要求撤回 v0.3 通信适配，先用 servo-web 测试。旧板损伤和新板身份分别记录；没有刷写新板。

> **后续服务切换／当前状态**：用户随后要求关闭 servo-web、启动 robotd 和 Studio，并确认机器人已托稳。现 servo-web inactive，robotd/Studio active，Studio HTTP 200；原版 robotd 为 commissioning/ready，torque off，策略关闭，无动作。见[切换结果](robot-studio-switch-result-20261101.json)。下文“保留 servo-web 运行”属于此前只读验收结束时的状态，自启配置始终未改。

## 回滚前发现

- [用户确认] 新单口板已经到货并装上，原“准备购买/未换装”状态作废。
- [实测] 回滚前 robotd PID 367，commissioning/ready/off、策略关闭，650 周期成功 650、通信失败 0；识别块为 `[6,0,0,0,242]`，原生识别为 `ft6/legacy_identity`。这是本次软件身份读取，不据此推定新板厂商/硬件修订或所有出厂固件细节。
- [源码核验] 本机 v0.3 补丁只针对 `BusImuBoard::ImuToDxl` 分拆读取，`Ft6` 路径原本仍为混合 SYNC_READ。因此新板在现有补丁 binary 中并不一定走 v0.3 单播分支；本轮仍按用户要求移除整个 v0.3 主机适配。
- 原始状态保存在 [部署记录](mixed-sync-deployment-20261101.json)。Radxa 时钟与工作机时钟不同，原始记录保留各自时钟；统计耗时使用 monotonic，不按板钟推断事件之间的绝对间隔。

## 实施与限制

方案与范围见 [回滚 Spec](../../specs/20261101-restore-mixed-sync-read/spec.md)。已恢复原件，停止 Studio/robotd 后启动 servo-web，由其独占串口；保留校验、等待和互斥锁，未发电机动作、未启动模型、未刷固件。本轮未提交/推送。

| 对象 | 完成状态 |
|---|---|
| servo-web `server.py` / `index.html` | 恢复已存 0.15.3：`[200]+servo_ids` 一条 SYNC_READ，撤回 0.15.4 的 READ 分拆；原 `_io` 锁、20 ms 单次读取及缺席降级机制保留 |
| servo-web `imu_bus.py` | 撤回 v0.3 自动分流后，首测发现还残留旧板 kitbits，继而恢复上游 legacy 状态判据和 Fake 数据；保留 ready/configured、统计与日志 |
| 板侧 robotd | `control.47+duck-v03.1` → 原件 `0791fcd-feetech-qinmo-control.47`；SHA256 `725b74cd93660a312970a44879abe5b75e8becf108499a1b8798961e48ca5f00`；当前未启动 |
| WSL 源码 | 三个被改源文件恢复原始 SHA，v0.3 独有测试文件移出构建树；未重编译，使用留存原版 binary |
| 参数与应用 | robotd 配置、标定、directions、feetech.py、robotctl 前后 SHA 一致；Studio 显示适配及六模型保留 |

备份与核对：[本地回滚](mixed-sync-local-rollback-20261101.json)、[板侧部署](mixed-sync-deployment-20261101.json)、[WSL 回滚](mixed-sync-wsl-rollback-20261101.json)、[legacy 判据部署](mixed-sync-legacy-parser-deployment-20261101.json)。本地备份在 `mixed-sync-rollback-before-20261101/`；板侧备份在 `/home/radxa/restore-mixed-sync-20261101/before/`；WSL 备份在 `/root/duck-robot-control47-before-mixed-20261101/`。WSL `target/` 的旧实验 binary 未删除，已放 `DO-NOT-DEPLOY-OLD-V03-BINARIES.txt`，不能把它们当作恢复后的源码产物。

## 两次真实 servo-web 只读验收

通过真实 WebSocket `/ws` 进入原有轮询，只发送原有 `buslog` 开关；hello 回读 15 颗扭矩均为 0。每次采集约 30 秒，再用 1 秒结束日志。没有执行 WRITE/SYNC_WRITE、电机目标或使能命令。

| 项目 | 第一窗口：仅撤回 v0.3 补丁 | 第二窗口：再撤回旧 kitbits |
|---|---|---|
| 舵机 state 完整帧 | 296/296（15/15 在线） | 296/296（15/15 在线） |
| 原始混合请求 | 297 | 297 |
| 日志完整 16 应答周期 | 296；末尾周期关闭日志时截断 | 296；末尾周期关闭日志时截断 |
| 总线统计增量 | TX 307 / RX_OK 4911 | TX 308 / RX_OK 4927 |
| timeout / bad_checksum / bad_id | 0 / 0 / 0 | 0 / 0 / 0 |
| IMU 网页消息 | 1 条首次等待、561 条 error | 2 条首次等待、562 条 live，末帧约 9.9 Hz |
| 原始 IMU 应答 | 297，状态字节均 0x08 | 297，状态字节均 0x08 |
| 首 12 字节不同块数 | 235 | 225 |

**统计边界**：WebSocket 会重复广播同一 IMU 样本，562 条 live 不是 562 次独立读取。日志开关边界与 HTTP 统计窗口不同；HTTP 增量含 hello 扭矩读取（一次 15 ID 的 SYNC_READ）以及开/关日志前后的轮询，不能用 TX 总数作 30 秒遥测周期分母。最后一组日志未全收录是关日志边界，应用 timeout/校验/错 ID 计数均无增量，不能把它记成设备缺答。

两窗口抓包请求均为：

```text
ff ff fe 14 82 38 0f c8 14 15 16 17 18 1e 1f 20 21 22 0a 0b 0c 0d 0e 12
```

含义为广播 `0x82`、地址 56、长度 15，ID 顺序 `200,20,21,22,23,24,30,31,32,33,34,10,11,12,13,14`。完整周期也按这一顺序收到 16 个合法状态包。日志窗口内没有 ID 200 的单播 READ。两次逐包校验分别 5034/5034、5037/5037 合法。

**[源码核验／实测] 页面 error 原因**：第一窗口进入本地 `BIT_SENSOR_ERR=0x08` 分支。该分支来自 10-24 旧板 kitbits 补丁；上游原 `imu_bus.py` 的 bit3 为读取慢提示、bit0 为未就绪，bit1/2 才报错误。恢复这些原有分支后，同一首轮原始 297 块离线回放全部 live，真实第二窗口也持续 live。原始四元数和陀螺有变化，保留字节为 0。这里确认的是“旧判据触发了 error，恢复原判据后页面可读”；新板厂商、出厂固件源码以及 bit3 的内部置位条件未独立核准，不以板型外观推断全部固件语义，也不据此保证安装方向或动作安全。

来源定位：`tools/servo-web/server.py:read_states_with_imu`、`tools/servo-web/imu_bus.py:BusImuService.feed`；只读原判据 `references/microduck-replica/tools/servo-web/imu_bus.py`；固定 robotd 源 `duck-control/src/feetech.rs:IMU_IDENTITY/BusImuBoard::from_identity/telemetry_ids`（提交 `27d7921dbcb280bd7d6ba3e9937624f1e2e61d23`）。没有修改参考库。

原始证据与解析：

- [首轮网页数据](mixed-sync-servo-web-capture-20261101.json)、[首轮总线帧](mixed-sync-servo-web-bus-20261101.log)、[首轮解析](mixed-sync-before-legacy-analysis-20261101.json)。
- [最终网页数据](mixed-sync-servo-web-capture-legacy-20261101.json)、[最终总线帧](mixed-sync-servo-web-bus-legacy-20261101.log)、[最终解析](mixed-sync-legacy-analysis-20261101.json)。
- [真实采集脚本](mixed-sync-servo-web-capture-20261101.py)、[离线分析脚本](analyze-mixed-sync-capture-20261101.py)、[最终部署核对](mixed-sync-final-audit-20261101.json)。

## 最终运行状态与未完成项

- [实测] `duck-servo-web.service` active，PID 819 唯一持有 `/dev/ttyS2`；页面 `http://192.168.1.35:8080/`。robotd、`microduck-studio.service` 均 inactive。
- 自启配置保持原值：robotd/Studio enabled、servo-web disabled。重启系统后仍按原配置进入 robotd/Studio；本轮没有把 servo-web 改成自启。
- 当前交付为新单口板的混合读取通过，未做新板站姿、模型动作或安装方向验证；双口 v0.3 起身坏帧根因依然未查明，波形/SWD 任务仍暂缓。
- 原 `test_imu_bus` 套件未能启动：Windows 缺 uvicorn；Radxa 缺测试依赖的相邻 `imu200` 模块。未为此安装额外依赖，也不记作测试通过；验收依据是两次真实网页/总线采集和原始块回放。

## 交付检查

本地 4 个运行文件与板侧 SHA 一致；9 份本次 JSON 可解析，采集/分析脚本语法、回滚文档本地链接与 `git diff --check` 通过。只读参考目录无修改；运行源码已回滚，历史备份保留，工作区未提交。

## 2026-11-01 用户再次要求启动服务

[实测] 请求时 servo-web inactive，robotd/Studio active，8080 无 HTTP 响应；原版 control.47 回报 commissioning、torque off、policy_motion_enabled=false。确认卸力后停止 Studio/robotd，启动用户 `duck-servo-web.service`。最终页面 HTTP 200、0.15.3、非 fake、15/15 舵机在线，启动扫描 16 次成功、0 超时/坏校验/错 ID。未追加动作或重复 30 秒验收，自启配置不变。此后的进程状态以该次记录为准，前文 PID 819 属此前验收窗口。见[启动与回读记录](servo-web-service-start-20261101.json)。

## 2026-11-01 用户随后切回 robotd 和 Studio

[实测] 切换前 servo-web 运行，15 颗扭矩均为 1；原版 `feetech_commissioning.rs::run` 启动调用 `torque_off` 后识别 IMU。用户确认已托稳后，停止 servo-web，再启动 robotd 与 Studio。最终 robotd/Studio active、servo-web inactive、Studio 首页 HTTP 200；robotd `control.47`、commissioning/ready、torque off、torque_off_pending=null、policy_motion_enabled=false、motion=null。没有发送 hold-home 或模型动作命令。自启、程序及标定配置均未改，本轮只切换服务；记录未提交。见[切换前回读](robot-studio-switch-preflight-20261101.json)及[最终回读](robot-studio-switch-result-20261101.json)。

## 2026-11-01 断电后再次确认开机自启

用户报告刚才断电，要求两服务自动启动。[实测] 检查时 robotd 和 microduck-studio 已为 enabled/active，servo-web 为 disabled/inactive。已再次执行 `systemctl enable robotd.service microduck-studio.service`，两个 multi-user.target.wants 链接有效；本次启动的 ExecMainStartTimestampMonotonic 分别为 8,292,638 / 9,796,425 微秒（开机后约 8.3/9.8 秒），Studio 页面 HTTP 200。本轮没有重启服务、再次断电或启动模型，现有 commissioning 模式与自启配置保持。见[完整核对](robot-studio-autostart-confirmed-20261101.json)。本次记录保留工作区，未提交。
