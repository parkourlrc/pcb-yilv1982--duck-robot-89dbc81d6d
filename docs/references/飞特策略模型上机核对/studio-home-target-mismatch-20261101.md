# Studio 两个“站姿”目标不一致

日期：2026-11-01。范围：核对真机 Studio 与原版 control.47，并按用户批准仅修正标定文件的 15 个零位；已部署、只读验收通过，本轮未触发站姿或模型。

## 结论与证据等级

- [用户反馈] 舵机页面点“站姿”能站住，IMU 页点“站姿”关节角度不对。当前新单口板已有人工作用验证，不能继续笼统写“新板站姿从未试过”；本轮助手没有触发动作。
- [实测／修正前文件与 RPC 回读] 主程序原先加载的 15 个 `zero_raw` 与此前导入的参考机数值一致，并未随 Studio 的中位校准变为 2048。Studio `servo-centered.json` 已有 15 个 ID 的完成记录；`servo-directions.json` 不存在，舵机页采用全 −1，主程序文件也全 −1。`state/servo-poses/` 没有保存姿态，因此舵机页按钮落到内置 `stand`。
- [源码核验／数值计算] 共同的 14 关节 HOME 弧度一致、方向一致、顺序一致，目标原始计数因零位不同而不同。下表为软件目标的计算差值，**不是量角器测得的实际姿态差**。
- [推断] 参考机零位被用于本机已归中后的编码器，是修正前两按钮产生不同关节目标的直接配置原因，能解释错姿。没有据此排除机械装配、中位校准误差、带载跟随不足或另有通信失败；没有做本轮动作复现，因此不宣称物理站姿已修复。
- [实测／已部署] 经用户确认托稳并批准，仅将 15 个 `zero_raw` 改为 2048，主程序原生回读一致；最新 IMU 标定和全部其他字段保留。两服务已恢复，验收时已卸力，未触发站姿。

## 两条调用路径

1. 舵机页 `web/servo.js:230–246`：优先查找名字含“站姿”的保存姿态，没有则发 `official/stand`。当前无保存姿态。`studio/servo_ops.py:655–663` 生成 `round(2048 + direction × angle × 4096 / 2π)`；`OFFICIAL['stand']` 在 44–45 行，含 14 个关节，不命令嘴。
2. IMU 页 `studio/imu.py:464–498`：调用 `hold-home`，传入 15 个方向和 3000 ms。`studio/commit.py:847–862` 只提供方向，**不把 Studio 的 2048 零位传给主程序**。
3. 原版 `robotd/src/feetech_commissioning.rs:543–570`：`home_targets` 使用 `round(joint.zero_raw + direction × HOME × 4096 / 2π)`。调试模式不加载模型 HOME，使用 `duck-control/src/model.rs:284–289` 的默认值，与舵机页 14 个目标弧度相同；`main.rs:1370–1390` 进入 commissioning 后返回，不进入策略控制分支。
4. Studio 正常提交实现 `studio/commit.py:150–168` 会把 `zero_raw` 写为 2048，但同时设置 `calibrated=true`、`motion_enabled=true` 等；本轮未调用这一流程，只修改零位，未顺带启用模型或改写完成状态。

## 修正前的主要目标差值

| 关节 | ID | robotd 零位 | 舵机页目标 | IMU 页目标 | 目标差绝对值 |
|---|---:|---:|---:|---:|---:|
| 左膝 | 23 | 1392 | 2051 | 1395 | 57.66° |
| 颈部俯仰 | 30 | 2526 | 1820 | 2298 | 42.01° |
| 头部横滚 | 33 | 1599 | 2048 | 1599 | 39.46° |
| 右踝 | 14 | 1611 | 2343 | 1906 | 38.41° |
| 右髋横滚 | 11 | 1760 | 1991 | 1703 | 25.31° |

计数换算：`abs(raw_imu - raw_servo) × 360 / 4096`。完整 15 行见[修正前比较结果](studio-home-target-comparison-20261101.json)。嘴是另一个行为差异：舵机页内置站姿不命令嘴，IMU 的 HOME 则将嘴送到零角度；原参考零位使其目标为 1372。现已对齐零位，IMU 嘴目标为 2048，仍不等于舵机页开始命令嘴。

## 已批准并部署的修正

仅将 `/etc/robot/feetech-ft5/hd1910-calibration.toml` 的 15 个 `zero_raw` 对齐为 2048。保留最新 IMU 姿态/验证值、方向、限位、`calibrated`、`motion_enabled`、P/D、模型和通信代码。依据为 Studio 已记录全部中位校准，且用户反馈其站姿可用；不是把任意编码器中心自动等同于未标定机器的关节零位。

用户已批准“已托稳，按方案修正”。审阅时的[候选 TOML](studio-home-zero-alignment-proposed.toml)、[候选差异](studio-home-zero-alignment-proposed.diff)和[方案 Spec](../../specs/20261101-studio-home-zero-alignment/spec.md)保留为过程记录；实际部署重新读取停服后的最新标定文件，仅替换零位，未用旧候选整体覆盖。共同 14 个关节目标计算一致，仅验证数值，不是实机动作验证。

### 部署证据与有限验收

- [实测] [部署结果](studio-home-zero-alignment-deployment-20261101.json)含修改前后 TOML 数据、备份位置、受保护文件哈希和重启后的原生 RPC 回读。15 个零位均为 2048，其他 TOML 字段完全一致；主配置、Studio 中位/方向记录、robotd 二进制哈希前后一致。
- [实测] 保留用户最新 `imu_mount_quat=[0.047458248, -0.683087043, -0.048132479, -0.727202221]`、`imu_mount_verified=true`；仍为 15 个 `calibrated=false`、`motion_enabled=false`、策略关闭，没有把零位对齐当作正式标定全部完成。
- [实测] robotd/Studio 为 active，Studio HTTP 200；额外只读核对自启均 enabled，servo-web inactive/disabled。原生状态 commissioning/ready、torque off、motion null。未调用站姿、模型或 EEPROM 校准。
- [实测] 首次部署已通过零位回读，但网页检查早于 Studio 监听就绪，触发停止服务并恢复原件；[首轮记录](studio-home-zero-alignment-attempt1-20261101.json)和[首轮脚本](install-studio-home-zero-alignment-attempt1-20261101.py)保留。[修正后的部署脚本](install-studio-home-zero-alignment-20261101.py)增加有限启动等待并使用独立重试目录，第 10 次 HTTP 检查成功，已恢复两服务。首轮结果不算安装成功，也不据此归因硬件故障。
- [实测] 最终备份为 `/etc/robot/feetech-ft5/backup-before-zero-alignment-20261101T072604011237Z/hd1910-calibration.toml`。本地留存[部署前原件](hd1910-calibration-before-zero-alignment-20261101.toml)和[部署后原件](hd1910-calibration-zero-aligned-20261101.toml)，SHA256 分别为 `0a96eb322c03632995832584a5582f9e28a69c2474c2fc5bc240e37f95dd3e3e`、`6e4b13c1a4d47775f06347d9b72c7d27f65ed4dd355d87dfd7390383a9f04e2e`。
- [实测／源码计算] [最终核对](studio-home-zero-alignment-verification-20261101.json)确认两份本地原件与部署哈希一致、文本仅改 15 行零位；共同 14 个目标按已部署零位重新计算一致。完整[实际部署差异](studio-home-zero-alignment-installed.diff)已保存；自启、停用 servo-web 的状态再次只读核对一致。`git diff --check` 通过；参考库未修改，本轮记录未提交。

物理站姿效果仍待用户后续验证；本次不主动试站姿。新板通信缺答、跟随误差和 Studio 正式标定交接均未在本次扩展处理。

## 独立问题与采集限制

- 本次日志另有新板 `Feetech Sync Read timeout; missing IDs [200]`（板钟 07:11:57 UTC）及 `a joint is still 20° from HOME`（板钟 07:15:26 UTC）。前者是另一个通信失败，后者是相对主程序自己目标的跟随误差，不能用本表目标差直接替代。板钟可能漂移，不将这些时间当作工作机精确墙钟。
- 07:13:20 的日志写“站住了”，原生回包 `holding=true`、`max_error_deg=20.21484375`。这说明该次接口报过保持，不等于正确物理姿态或通过 ≤5° 校准门限；本次零位修正未调低相关门限。
- 首次完整采集恰遇 `/run/robotd.sock` 消失，后续快照捕获 robotd 暂停；可能与 Studio 舵机会话接管有关，未为取证强行交还或重启服务。最终快照已成功读到实时 `calibration-status`，且加载关节与文件逐项一致。
- 第一份经 PowerShell 非 ASCII 管道转存的 `studio-home-targets-snapshot-20261101.json` 有文字编码损失，只保留过程记录；权威证据为下面的 ASCII 转义完整快照，6 个源码文本还原后的 SHA 均与板侧原文件一致。

## 来源和原件

- [权威板侧快照](studio-home-targets-snapshot-final-20261101.json)：当前 `/home/radxa/studio-dev` 的六个源码、标定/参数文件、Studio 状态、过滤日志、RPC 与 binary SHA。
- [采集脚本](collect-studio-home-targets-20261101.py)、[离线对比和候选生成](analyze-studio-home-targets-20261101.py)。均不发送舵机动作。
- 原 robotd 固定来源：`fanhao375/Microduck-kissqy` 提交 `27d7921dbcb280bd7d6ba3e9937624f1e2e61d23`；当前 binary SHA 与 control.47 原件一致。参考机标定来源见[先前导入说明](../../../software/robotd-v03/reference-data/README.md)。本轮没有修改只读参考库，记录未提交。
