# servo-web 工程工作副本

> **2026-11-01 当前版本：0.15.3，混合 SYNC_READ＋原版 legacy 状态判据。** 用户已换上新单 3P 口板；v0.3 的读取分拆、状态自动分流以及旧单口板的 kitbits 补丁已撤回。真实 30 秒只读采集 296/296 帧舵机完整，IMU 约 9.9 Hz，0 超时/坏校验/错 ID。见[回滚与验收](../../docs/references/b-feetech-policy-deployment-20261024/restore-mixed-sync-read-20261101.md)。新板厂商/批次未独立核准，不把旧 GD32 的状态语义作为新板依据。

## 性质与来源

- **本目录是本项目 servo-web 的权威可部署工作副本**（2026-10-27 用户指示建立）：servo-web 后续会频繁修改，一律在本副本或板侧进行，**不修改只读参考库** `references/microduck-replica/tools/servo-web/`（上游 v0.15.2，保持原样）。
- 来源：主控 Radxa（radxa-zero3，`192.168.1.35`）部署目录 `~/servo-web/` 整目录打包拉取。
- 初次拉取时间：北京时间 2026-10-27 深夜（板钟 2026-10-26 17:13 UTC）；当前文件 MD5 见 [source-manifest-md5.txt](source-manifest-md5.txt)，已于 2026-11-01 按版本库文件重建，不含清单本身、缓存或日志。历史拉取数不作为当前清单数。
- 同步时排除（板上仍保留）：`logs/`（运行时日志）、`__pycache__`、`*.bak-*`（板上补丁备份链）、`.idmap-backup-*/.upstream-idmap-backup-*`（idmap 交换历史快照）。

## 当前副本相对上游 v0.15.2 的状态（v0.15.3，2026-11-01 回滚更新）

完整差异审计见 [servo-web IMU 调研·续 4](../../docs/references/servo-web-imu-3d-20261024/research.md)，要点：

| 文件 | 状态 |
|---|---|
| `server.py` | `read_states_with_imu` 为**上游原始混读**（10-24 拆分补丁已于 10-27 回滚）+ **总线帧记录页面开关**（v0.15.3：`BUS_LOG_ON` 默认关，WS 命令 `{"op":"buslog","on":bool}` 控制；开=写 `logs/bus-日期.log`+推页面日志栏，关=上游默认不记；异步 writer 线程，串口锁路径零文件 IO）+ cal-fix（手动校准路径）/read_torques（页面握手路径）/零位符号/host 遥测与 MON 常驻监控/表现层补丁 |
| `index.html` | 日志栏新增「总线帧」勾选框（勾选=开启记录+显示；hello/广播同步多标签页状态）+ miss 文案、模型缓存、行内 CAL 等表现层补丁；PAGE_VERSION 0.15.3 |
| `feetech.py` | 仅 py311 f-string 语法兼容，收发逻辑与上游零行为差异 |
| `imu_bus.py` | 原版 legacy 状态判据：bit0 未就绪、bit1/2 故障、bit3 读取慢；旧板 kitbits 与 v0.3 自动分流均已撤回，readyflag、miss 文案/滑窗统计保留 |
| `calib/` | 10-22~10-24 的 EEPROM 校准快照（28 份 JSON，运行时产物，留档） |
| `model/`、`poses/` | 3D 模型与姿态数据（2.8MB） |

## 更新方式

板侧修改并验证后，从主控重新打包同步到本目录：

```bash
ssh radxa "cd ~/servo-web && tar czf /tmp/servo-web-snap.tgz --exclude='./logs' --exclude='__pycache__' --exclude='*.bak-*' --exclude='./.*' ."
scp radxa:/tmp/servo-web-snap.tgz tools/servo-web/ && cd tools/servo-web && tar xzf servo-web-snap.tgz && rm servo-web-snap.tgz
```

清单仅对本目录版本库中的权威文件计算，排除 `source-manifest-md5.txt` 自身，不把本地 `__pycache__`、日志或备份加入。不能使用不加过滤的整目录 `find` 重建清单。

相关：`docs/references/servo-web-imu-3d-20261024/sources-board/` 为 10-27 深夜的**取证快照**（3 个源文件+2 个历史备份，SHA256 已登记），仅作历史证据，不再维护；本目录取代其"最新副本"角色。
