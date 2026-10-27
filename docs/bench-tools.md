# 台架/装机工具索引（2026-10-22 更新）

按用户指示整理的现行工具清单：**能复用参考工程现成工具的不再自研**。来源分三类：本项目自研、社区 kit（`references/microduck-community-kit/`，只读，部署=拷贝不改源）、replica（只读参考）。

## 一、改号与装配校准（ID 与中位校准 2026-10-20 完成；ID 已于 2026-10-24 对齐上游）

### hls_servo_debugger（社区 kit，**主力复用**）

- 位置：`references/microduck-community-kit/software/hls_servo_debugger/`
- 形态：**浏览器交互式调试器**（Flask + pyserial，前端免构建）。上游记录使用 **HD-1910-C001（固件 3.46）×16 台**；本机 15 颗已用它完成 ID 初始化，但不能由此认定本机固件版本和全部参数行为都已核验。
- **本机现行映射（2026-10-24 对齐上游）**：`20–24=左腿、10–14=右腿、30–34=头颈（30=neck_pitch、31=head_pitch）、200=IMU`，14 号为右踝，**与上游 microduck_feetech `model.rs` 完全一致，可按上游关节表直接使用**。舵机 EEPROM 已于 2026-10-24 改号对齐（[scripts/servo-id-align-upstream.py](../scripts/servo-id-align-upstream.py)，记录见 [servo-id-align-20261024](references/servo-id-align-20261024/research.md)）；部署副本关节表已回上游原表（[scripts/swap-hls-jointmap.py](../scripts/swap-hls-jointmap.py) 再跑 + [scripts/hls-headneck-revert-upstream.py](../scripts/hls-headneck-revert-upstream.py)，备份 `provision.py.bak-20261024-132405`）；参考库未改。2026-10-17/10-22 的本机相反映射已作废。完整部署契约见[本机 ID 映射表](servo-id-mapping.md)。
- 能力（README 全表）：
  - **整机 15 台初始化**：出厂 ID 1 → 按关节表编号 **10~14 / 20~24 / 30~34**，本机左右分组以上述映射为准；提供可选初始位置校准、回读校验、写锁保护（解锁 55 号 → 改 ID → 上锁，自动流程）；本机 2026-10-17 选择“不校准只改 ID”，中位 CAL 已于 2026-10-20 装机后全部完成（15/15，见 PROGRESS 当日条目）；
  - PING/扫描、实时反馈（56~70 共 15 字节：位置/速度/负载/电压/温度/电流 + 趋势图）、位置/速度/电流/PWM 控制、全内存表参数界面（0~86）、同步读写、原始十六进制帧调试；
  - `selftest.py` 无硬件协议自检（含从站模拟，可离线验证整个初始化流程）。
- 部署（Radxa，链路即 /dev/ttyS2）——**2026-10-17 已部署完成**：
  ```bash
  # 初次从参考库拷至板上 ~/hls_servo_debugger/；后按本机映射交换部署副本关节表
  # python3-flask 2.2.2 已装（python3-serial 原有）
  cd ~/hls_servo_debugger
  nohup python3 -m hls_debugger --host 0.0.0.0 > /tmp/hls_debugger.log 2>&1 &
  # 电脑浏览器访问 http://192.168.1.35:8765（实际端口 8765，非 Flask 默认 5000）
  ```
- 安全特性：初始化带回读校验；`hw_test.py` 是真机只读连通测试（PING/READ，不产生动作）。
- **2026-10-23 本机补丁：初始化页扭矩按钮改为随动开关**（用户需求）。选中舵机后前端自动现读 40 号（0 关 / 1 开 / 2 阻尼输出）：关着显示「打开扭矩」、开着显示「关闭扭矩（卸力）」，点击按当前状态反向写入；串口未连/读不到时退回旧版「关闭扭矩（卸力）」行为。触发点：关节表加载、切换关节（点选/下一个/重置）、流程结束、串口连接成功、切到初始化页签。补丁存档 [`scripts/hls-prov-torque-toggle.patch`](../scripts/hls-prov-torque-toggle.patch)（改 `static/app.js`，`index.html` 仅加 `?v=` 防缓存；参考库未动，板上部署副本已应用并重启生效）。写路径沿用原 `/api/torque`；C 线开扭矩**不自动对齐目标**，装配态开扭矩前仍须先人工对齐（见上文 CAL 复核）。实测：ID 10/20 关扭矩状态正确显示「打开扭矩」，切换关节即触发对应 40 号读取（服务端日志留痕）。
- 关键寄存器参考：**ID=5、波特率=6（0=1Mbps）、应答级别=8、卸载条件=19（BIT3 过流）、写锁=55（0=解锁/1=上锁）**。以厂商适用版本资料为依据、工具实现作对照；本机保护位仍需在带载动作前回读。2048 对应关节角 0 以正确机械零姿态已校准为前提，方向 −1 是上游记录，不能当成本机逐关节验收。

### 装盘、CAL 与恢复扭矩（2026-10-20 复核）

- 未装盘且轴未受机构约束时，推荐先到 2048、按正确朝向选最近齿位，再支撑并关扭矩、扶到该关节机械零姿态执行 CAL。这是减少剩余修正的装配工艺，不是 CAL 的协议前提；已有未知 offset 时仅归中不保证最终偏移绝对值小，不自动清 offset。已装好的不因 offset 大就一律拆盘。
- **“转到中位”会实际运动**：社区 `provision.py:881–898` 先使能，再写限速/2048 目标，已装机构不能盲点。CAL 则是重定义当前位置；`protocol.py:629–646` 关扭矩 → 解锁 → `0x0B` → 上锁，不写目标 42，也不重新使能。
- **CAL 成功提示不能替代结果确认**：校后先确认当前位置约为 2048（本机容差未定），恢复扭矩前须以当前坐标对齐目标并回读。C 线 `/api/torque` 直接使能，没有自动对齐；B 线 servo-web 的“先对齐再使能”实现不能算作 C 工具已有功能。未确认前保持关扭矩。
- 正确零姿态不是带非零角度的 home/站姿；孔位能装上也不等于零位正确。单圈目标限制不保证反馈永远在 `0…4095` 内，异常/超窗时再排查，不自动切多圈、改相位或重启。完整厂商证据、上游反例与源码定位见[装配与 CAL 调研](references/assembly-check-20261017/research.md)。

### servo-web（B 线整机 3D 网页调试台，2026-10-22 板载真机部署）

- 位置/来源：源码自 B 线参考库 `references/microduck-replica/tools/servo-web/`（v0.15.2）**只读拷贝**至板 `~/servo-web`（约 3.3M）；参考库未改。默认轮询 ID 集合 `20-24,30-34,10-14` 与本机相同，无需 `--ids`。**映射现状（2026-10-24）：舵机 EEPROM 改号对齐上游后，板上副本已回退为上游原生映射（20–24=左腿、10–14=右腿、30=neck_pitch、31=head_pitch），`/api/info` 已验证、15/15 在线**；2026-10-22 的本机映射补丁（[scripts/servo-web-local-idmap.py](../scripts/servo-web-local-idmap.py)）已由反向补丁 [scripts/servo-web-upstream-idmap.py](../scripts/servo-web-upstream-idmap.py) 撤销（备份 `~/servo-web/.upstream-idmap-backup-20261024-131954/`），其后叠加的模型缓存/方向广播/单颗 CAL/状态同步/CAL 修复补丁全部保留；3D 模型 fetch 版本号已跳 `?v=20261024`，浏览器 Ctrl+F5 后生效。上游 `poses/站`、`缩` 仍在 `poses/upstream-2026-09-20/` 归档，不是本机姿态，勿发送；`directions.json` 15 颗全 −1 为本机 2026-10-22 逐颗核对结果，改号只换 ID 不换舵机，方向数值不变。映射核查历史见 [servo-web 数据来源与关节映射](references/servo-web-mapping-20261022/research.md) 与 [servo-id-align-20261024](references/servo-id-align-20261024/research.md)。另用 [scripts/servo-web-model-cache.py](../scripts/servo-web-model-cache.py) 给 `/model/*` 加 no-store、fetch 加版本参数，HUD 显示 30/31 实际映射，避免“数据面板更新、3D 仍用旧模型”。每颗操作行后面有 `CAL` 按钮（[scripts/servo-web-row-cal.py](../scripts/servo-web-row-cal.py)），按“一键校准”区当前基准单颗校准，完成后 300/800 ms 刷新 3D。22 号曾加软件零位 `ZERO_COUNTS={22:1198}`（[scripts/servo-web-zero-offset.py](../scripts/servo-web-zero-offset.py)），后为 CAL 测试清空；CAL 成功后也会自动清（**仅当前页面会话**，刷新按 index.html 常量复位；当前空表无实害）。注意 22 的 CAL 仍走硬件 2048（2026-10-24 已同步：viewer 硬编码 `{22:1198}` 已清空——22 号 2026-10-23 已重校、且改号后 ID 22 语义变为左髋 pitch，旧零位不再成立）。刷新/重连的状态同步：`hello` 会读一次 40 号扭矩并回传，第一帧状态到达时把滑块对齐实际读数（[scripts/servo-web-state-sync.py](../scripts/servo-web-state-sync.py)）。**CAL 修复（[scripts/servo-web-cal-fix.py](../scripts/servo-web-cal-fix.py)，2026-10-23 01:05 部署）**：根因是旧版"下垂补偿"符号错（OFFSET_SIGN 默认 +1、实际 −1）把偏移多挪一倍反向量，CAL 后读数恒为 2×pre−2048（0x0B 固件本身无辜，2026-10-23 01:16–01:20 九次无补偿校准全部一次到位证实）；修复后 0x0B 回读位置、未到目标改走写偏移兜底（两符号都试、回读验证），成功路径不再做下垂补偿——CAL 语义=**当前物理位置读数 2048，点 CAL 那一刻摆得多准零点就多准**（失电等待期间关节会垂，摆好立即校或托住；2026-10-23 01:20 左腿隔 3 分钟连校即把 12–30° 摆位误差固化进零点，导致站姿 3D/实物不一致，见调研）。部署后**尚未真机验证**；00:53–54 五次坏校准待按备份逆序撤销（21→22→21→20→22），撤销前不要点 CAL。证据与复核见 [servo-web CAL 调研](references/servo-web-cal-droop-20261023/research.md)。**用户 2026-10-22 确认 3D 与实物的方向和位置全部对上；15 颗回中位（2048）后机器人站立，方向表 15 颗全 −1**；带载前仍先小角度、托住试，官方姿势/一键校准按需使用，不要把静态对齐当成动态站立验收。
- 板上启动（**2026-10-25 起改用 systemd 用户服务，标准方式**）：
  ```bash
  systemctl --user start|stop|restart|status duck-servo-web   # 崩溃自动重启(Restart=always)
  ```
  单元 [scripts/duck-servo-web.service](../scripts/duck-servo-web.service)（`--imu-bus` 常开，IMU 未接时自动降级），已 `enable`。**工程可部署副本：[tools/servo-web/](../tools/servo-web/SOURCE.md)（2026-10-27 起，主控 `~/servo-web` 的同步版+来源差异说明；上游参考库只读不改）**。**开机自启还需一次 `sudo loginctl enable-linger radxa`**（未执行前，重启后须 SSH 登录一次服务才起）。手动应急启动仍可用 `( setsid nohup python3 server.py … & )`（注意先停服务防抢串口）。
  ⚠️ 后台作业务必用 `( … & )` 双层脱开：`ssh 'cmd & …'` 形式下本地连接被杀会经 sshd→bash 作业表把 HUP 传给服务、误杀服务（2026-10-24 实测踩过）。
  电脑/手机浏览器开 `http://192.168.1.35:8080`。停止：`pkill -f "[s]erver.py"`（方括号防 pkill 自匹配，2026-10-22 实测踩过）。
- **常驻监控（2026-10-25 部署，随服务自动开启、每秒实时落盘）**：`~/servo-web/logs/monitor-YYYYMMDD.csv` 记主机 SoC/GPU/频率/负载、每颗电压/温度/电流汇总（v_min/v_avg/t_max/i_sum）、总线统计、分 ID 丢帧 TOP、UART 驱动错误（TIOCICOUNTER）；事件行 STORM_START/STORM_END/ALL_OFFLINE/ID_SET_CHANGE 自动写入并上页面日志。顶栏显示「SoC/CPU/最低电压/监控✓行数·事件N」（悬停见丢帧 TOP 与 UART 错误）。补丁 [scripts/servo-web-full-monitor.py](../scripts/servo-web-full-monitor.py)（叠加于 [servo-web-host-monitor.py](../scripts/servo-web-host-monitor.py)）。首次部署即捕获 04:36 全掉线风暴（当时 SoC 60°C——该次非热因）与 32 号扫描缺失。
- **IMU 状态位勘误补丁 + IMU 读数隔离补丁（2026-10-24 部署；②已于 2026-10-27 回滚）**：①板②固件状态位为社区 kit v1 语义（bit0=四元数有效、bit1=计数回绕、bit3=传感器错误、bit7=融合运行中），与 `imu_bus.py` 沿用的 duck-control 旧语义相反——曾致有效帧全被判"融合没出数"，已用 [scripts/servo-web-imu-kitbits.py](../scripts/servo-web-imu-kitbits.py) 改判位（备份 `~/servo-web/imu_bus.py.bak-20261024-141102`，**仍生效**）。②板②在串口重开窗口/偶发时段缺答晚答，混帧下一次缺答拖死整条 sync_read（15 颗全部"无应答"），曾用 [scripts/servo-web-imu-separate-read.py](../scripts/servo-web-imu-separate-read.py) 把 200 拆成独立单 ID sync_read、舵机单独读——**2026-10-27 用户指示回滚**（补丁未解决问题且改变 IMU 请求的时序环境，非根因）：`read_states_with_imu` 恢复原始混读（200 排第一位、与舵机同一条 sync_read）；恢复源为板上 `server.py.bak-20261024-150443`（补丁脚本 OLD 段与之逐字一致），回滚前拆分版备份 `server.py.bak-20261026-164510`；10-25 后新增的主机遥测/常驻监控（host_stats/MON）与该段无关，保留。只读诊断 [scripts/imu200-diag.py](../scripts/imu200-diag.py)、丢帧监测 [servo-web-bus-monitor.py](../scripts/servo-web-bus-monitor.py)、三读法时序实验 [imu200-timing-test.py](../scripts/imu200-timing-test.py)（后两者/诊断均须停服独占总线，servo-web 运行时另开进程读 200 会抢应答帧出假象）。核查证据见 [servo-web IMU 调研](references/servo-web-imu-3d-20261024/research.md)。
- **IMU miss 文案勘误补丁（2026-10-26 已部署）**：板②应答率 0–27%（非断链）时面板长期显示「连接中断」，措辞失实。已用 [scripts/servo-web-miss-label.py](../scripts/servo-web-miss-label.py) 改为「IMU 应答率过低：连续 N 帧未应答，最近 60 秒成功 K 次…」（imu_bus.py 新增 60s 滑窗成功计数，状态字仍为 disconnected、前端逻辑不动），index.html 标签 `disconnected` → 「IMU 未应答」（备份 `*.bak-20261026-135651`）。依据见 [IMU 调研 round3 与补丁节](references/servo-web-imu-3d-20261024/research.md#round3-20261026)。
- **总线帧异步日志（2026-10-27 部署，v0.15.3 起为页面开关）**：原 bus_trace→log() 在**串口锁内**每行 open/write/close + print(flush)，全量记录时 eMMC 延迟尾部（几十 ms）会插进收发间隙人为制造丢帧、170 行/s 逼近 journald 限流。现实现：**日志栏新增「总线帧」勾选框**——勾选才开始记录（写 `~/servo-web/logs/bus-日期.log` 毫秒时间戳逐帧 hex + 同步推入页面日志栏，覆盖所有设备含 sync_read/sync_write 轮询流量）；不勾选=上游默认不记录。总线线程只入队（put_nowait µs 级），daemon 线程 `servo-web-buslog` 批量写盘+推页面，队列 2 万行满丢新+计数绝不反压；WS 命令 `{"op":"buslog","on":bool}` 可程序控制，hello/广播同步状态；**会话开关，服务重启后默认关**。初版无条件常开补丁 [scripts/servo-web-bus-asynclog.py](../scripts/servo-web-bus-asynclog.py)（备份 `server.py.bak-20261026-170715`），开关版部署备份 `*.bak-20261026-231214`；工程副本 [tools/servo-web/](../tools/servo-web/SOURCE.md)。
- **2026-10-22 真机实测**：15/15 在线、刷新 9.8 Hz、总线电压 7.1 V、超时/校验错 0；3D 整机模型与逐颗电压/温度/电流回读正常。启动/连接只做扫描+读相位（寄存器 18），不自动放开速度/加速度限制（0.15.2 行为）；页面滑块/姿态/校准按钮会实际发指令，**开扭矩前先「滑块对齐当前位置」**，流程见其 README。
- 板 Python 3.11 与上游 3.12 f-string 语法不兼容（`feetech.py` 一处），部署副本已打 `scripts/servo-web-py311.patch`（参考库保持原样）；依赖 `starlette`/`uvicorn`/`websockets` 已 `pip3 install --user --break-system-packages` 装在 radxa 用户目录（pyserial 3.5 系统自带）。漏装 websockets（即未按 requirements 的 `uvicorn[standard]` 装）表现为页面 WebSocket「断开，3 秒后重连」。
- **与 hls_servo_debugger 互斥占用 /dev/ttyS2**：servo-web 运行期间 :8765 无服务，`servo-mujoco-viewer.py`、`servo-trace.py` 无数据源；反之亦然。切换顺序：先 `pkill` 现占用者，再按各自部署命令启动另一个。板上重启后 hls/imu-viewer 均为用户态进程需手动拉起（systemd 单元仍待用户 `sudo systemctl enable --now`）。
- 2026-10-22 凌晨曾在参考目录内以 `--fake` 本机试跑（无串口、纯演示），运行残留（`logs/`、`__pycache__/`）已于 2026-10-22 清理，参考库恢复原样；正式使用一律走板上部署副本。

## 二、行程检查与实时可视化（2026-10-20 新增）

### servo-trace.py（本项目自研，**手掰行程记录器**）

- 位置：`scripts/servo-trace.py`；已部署板上 `~/servo-trace.py`。
- 用途：手掰关节做行程检查时，循环轮询 :8765 读 15 颗 56 号位置存 CSV（约 10 轮/s）；`touch /tmp/stop-servo-trace` 停止，自动在 `~/servo-trace.csv.summary` 输出每颗 min/max/行程（读数折回单圈后取极值，角度相对中位 2048、未含方向系数）。
- 前提：目标舵机扭矩关闭（40=0）才可手掰；产出用于回填 `training/params/microduck_geometry.json` 各关节 `range`（换算时按关节表方向）。

### servo-mujoco-viewer.py（本项目自研，**舵机实时 3D 数字孪生**）

- 位置：`scripts/servo-mujoco-viewer.py`；**Windows 本机运行**（`py scripts/servo-mujoco-viewer.py`，需 `pip install mujoco`，已装 3.16.0；本机无 WSL）。
- 用途：实时读板 :8765 的 14 颗关节位置，驱动 `training/models/duck_v0.xml`，实物手掰时桌面 MuJoCo 窗口里的鸭子同步动（mouth 34 不在模型中）。角度换算 `qpos = sign × (计数−2048) × 2π/4096`，SIGNS 表默认全 −1（duck-control 方向，**本机未逐关节核对，方向反了改 SIGNS 一行**）。
- 与 servo-trace 可同时跑（同一 :8765 数据源并发读）。

## 三、IMU 测试

### imu-viewer.py（本项目自研，**姿态实时可视化**）

- **2026-10-25 19:59 运行状态**：用户要求关闭 servo-web 并打开 IMU 工具，已停 `duck-servo-web.service`，启动板上既有查看器 :8766；当时 SSE 为“IMU 无应答”。当前单口 IMU 接 HAT 第二个 3P 口，页面旧“链末”提示不作改线要求。查看器未校验应答 checksum，适合看姿态，不替代原始帧完整性验证；详见[切换记录](references/servo-web-imu-3d-20261024/research.md#imu-viewer-20261025)。

- 位置：`scripts/imu-viewer.py`（2026-10-17 建；已部署板上 `~/imu-viewer.py`，运行于 **http://192.168.1.35:8766**）
- **浏览器打开即用：3D 立方体实时跟随 IMU 姿态**（晃动板子立方体跟着转），并显示四元数/陀螺 dps/采样计数/状态/读取率。
- 实现零新依赖：Flask（板上已有）+ SSE 推流 + CSS 3D（无 three.js/CDN，离线可用）。数据契约照 imu200.py（@56 读 15 字节：gyro i16×3 + quat half×3，w 由归一恢复）。
- 用法：`python3 imu-viewer.py [--port /dev/ttyS2] [--http 8766] [--sim]`（`--sim` 为无硬件模拟自测；经微雪板看时 `--port COM4`）。
- ⚠️ 与 hls_servo_debugger **不同时占用串口**（后连的会打不开 ttyS2，页面会显示串口错误）。

### 其他 IMU 工具

| 工具 | 来源 | 用途 | 入口 |
|---|---|---|---|
| `imu200.py` | 本项目 | **板②验收**：13 项判据（URT-2/COM 口电脑侧跑） | [flash/tools/imu200/](../flash/tools/imu200/)（双击 `flash/3-验收-imu200.bat`） |
| `sensor_probe.py` | 社区 kit `firmware/v1/host/tools/` | 深度表征：陀螺/加计统计、四元数范数、采样率、静态零偏、PASS/FAIL（只读+复位厂商命令） | 参考；`--port` 适配串口 |

## 四、舵机测试

| 工具 | 来源 | 用途 |
|---|---|---|
| hls_servo_debugger | 社区 kit | 主力（见上，反馈/控制/参数全覆盖） |
| `feetech-ping.py` | 本项目 scripts/（已部署板上 ~/） | 快速 ping/scan/回环；2026-10-17 修复 checksum 公式 bug（见排障记录） |
| `servo_probe.py` | 社区 kit host/tools | 只读排障探测：56~70 块布局、寄存器账本、READ/PING/SYNC_READ 时序、坏校验应答行为 |
| `bus_smoke.py` | 社区 kit host/tools | IMU 节点双协议（DXL/飞特）冒烟 |
| HD1910M Rust 工具 | replica `tools/FeeTech_HD1910M_Servo/` | **不做部署**：`src/protocol.rs`（FT-SCS 实现）、`src/registers.rs`（寄存器定义）、TUTORIAL.md（协议教学）作参考源码；型号/固件适用性仍以厂商资料及实际回读核对 |

## 五、已验证事实备忘（2026-10-17 联调）

- 链路：`ssh radxa` → /dev/ttyS2 → HAT 74LVC → 舵机 ID 1 ✓ / IMU ID 200 ✓（错误码均 0x00）。
- 串口权限：radxa 已入 dialout 组；ttyS2 需 fiq_debugger 已移除（`/etc/kernel/cmdline` 无 `console=ttyFIQ0`）。
- **微雪当前不能当作已知正常主机（2026-10-26 更正）**：10-25 COM4、外部 7.4V 下 IMU 与同口独立舵机均无回包，撤回旧“验证可用”现行判断。主排障已回 HAT，微雪留独立支线，见[舵机对照](references/servo-web-imu-3d-20261024/research.md#waveshare-servo-ping-20261025)。
- **IMU 日志工具（2026-10-26 计划）**：先核对本机构建与日志开关；官方 1.5.1 默认关日志，确认关闭时跳过 H1 监听。启用时用已有 FT232H 接 H1 DEBUG_TX→D1/RX 与 GND，115200 8N1 无流控；I2C 开关须使 D1/D2 断开，实物引脚/模式确认后再接。DAPLink 留作 H2 SWD 后备，本轮未连接或刷机。见[调试计划](references/servo-web-imu-3d-20261024/debug-plan-20261026.md)与[同源故障修复记录](references/microduck-imu-community-20261026/research.md)。
- HD-1910 规格：信号高电平 2–5V（3.3V 逻辑兼容）、出厂 ID 1 @1Mbps、ID 范围 0–253。
- **当前状态**：15 颗 ID 已于 2026-10-17 逐颗完成（10–14 / 20–24 / 30–34），零位待按[装配校准流程](references/assembly-check-20261017/research.md)逐关节确认；第一颗“嫌疑坏”舵机继续隔离，不在装机批内。
