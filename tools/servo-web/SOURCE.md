# servo-web 工程工作副本

## 性质与来源

- **本目录是本项目 servo-web 的权威可部署工作副本**（2026-10-27 用户指示建立）：servo-web 后续会频繁修改，一律在本副本或板侧进行，**不修改只读参考库** `references/microduck-replica/tools/servo-web/`（上游 v0.15.2，保持原样）。
- 来源：主控 Radxa（radxa-zero3，`192.168.1.35`）部署目录 `~/servo-web/` 整目录打包拉取。
- 拉取时间：北京时间 2026-10-27 深夜（板钟 2026-10-26 17:13 UTC）；60 个文件 MD5 见 [source-manifest-md5.txt](source-manifest-md5.txt)。
- 同步时排除（板上仍保留）：`logs/`（运行时日志）、`__pycache__`、`*.bak-*`（板上补丁备份链）、`.idmap-backup-*/.upstream-idmap-backup-*`（idmap 交换历史快照）。

## 当前副本相对上游 v0.15.2 的状态（v0.15.3，2026-10-27 深夜更新）

完整差异审计见 [servo-web IMU 调研·续 4](../../docs/references/servo-web-imu-3d-20261024/research.md)，要点：

| 文件 | 状态 |
|---|---|
| `server.py` | `read_states_with_imu` 为**上游原始混读**（10-24 拆分补丁已于 10-27 回滚）+ **总线帧记录页面开关**（v0.15.3：`BUS_LOG_ON` 默认关，WS 命令 `{"op":"buslog","on":bool}` 控制；开=写 `logs/bus-日期.log`+推页面日志栏，关=上游默认不记；异步 writer 线程，串口锁路径零文件 IO）+ cal-fix（手动校准路径）/read_torques（页面握手路径）/零位符号/host 遥测与 MON 常驻监控/表现层补丁 |
| `index.html` | 日志栏新增「总线帧」勾选框（勾选=开启记录+显示；hello/广播同步多标签页状态）+ miss 文案、模型缓存、行内 CAL 等表现层补丁；PAGE_VERSION 0.15.3 |
| `feetech.py` | 仅 py311 f-string 语法兼容，收发逻辑与上游零行为差异 |
| `imu_bus.py` | kitbits 状态位勘误（kit v1 语义，10-27 三重证据验证正确）+ readyflag + miss 文案/滑窗统计 |
| `calib/` | 10-22~10-24 的 EEPROM 校准快照（28 份 JSON，运行时产物，留档） |
| `model/`、`poses/` | 3D 模型与姿态数据（2.8MB） |

## 更新方式

板侧修改并验证后，从主控重新打包同步到本目录：

```bash
ssh radxa "cd ~/servo-web && tar czf /tmp/servo-web-snap.tgz --exclude='./logs' --exclude='__pycache__' --exclude='*.bak-*' --exclude='./.*' ."
scp radxa:/tmp/servo-web-snap.tgz tools/servo-web/ && cd tools/servo-web && tar xzf servo-web-snap.tgz && rm servo-web-snap.tgz
find . -type f -exec md5sum {} + | sort -k2 > source-manifest-md5.txt   # 刷新清单并更新本文件时间
```

相关：`docs/references/servo-web-imu-3d-20261024/sources-board/` 为 10-27 深夜的**取证快照**（3 个源文件+2 个历史备份，SHA256 已登记），仅作历史证据，不再维护；本目录取代其"最新副本"角色。
