# 舵机 ID 对齐上游 microduck_feetech（EEPROM 改号 + 软件层回退，2026-10-24）

## 问题与范围

用户指示：「id 做一次对齐，和方案 B 的飞特版一致，你来操作」。即把本机 15 颗 HD-1910 的
ID 排布从 2026-10-17/10-22 的本机定案改回上游（方案 B 飞特版 microduck_feetech /
`model.rs` / hls `provision.py` 原表），消除"本机与上游左右腿整组相反、头颈 30/31 相反"
这一长期差异。

范围：舵机 EEPROM 改号（12 颗实际换号）+ 受影响软件层回退（板上 servo-web、板上 hls
provision.py、本机 servo-mujoco-viewer.py）+ 现行文档更新。不改零位/偏移/方向/增益，
不动 IMU（ID 200），不动 references/ 只读库。

## 改号前后映射（腿组整组互换、头颈 30/31 互换）

| 部位 | 改号前（2026-10-17/10-22 定案） | 改号后（= 上游 microduck_feetech） |
|---|---|---|
| 左腿（hip_yaw/roll/pitch、knee、ankle 顺序） | 10-14 | **20-24** |
| 右腿（同序） | 20-24 | **10-14** |
| 颈俯仰 neck_pitch | 31 | **30** |
| 头俯仰 head_pitch | 30 | **31** |
| head_yaw / head_roll / mouth | 32 / 33 / 34 | 32 / 33 / 34（不变） |
| IMU | 200 | 200（不动） |

组内关节顺序（髋→踝、名称对应）两侧一致，故腿组是"整组平移"而非逐关节重排；
头颈仅 30/31 两颗互换；32/33/34 与 IMU 不动。

## 实施过程与证据

### 1. 改号脚本（本项目自研）

- [scripts/servo-id-align-upstream.py](../../../scripts/servo-id-align-upstream.py)：自包含
  飞特 SCS 协议（帧格式/校验和照 [scripts/feetech-ping.py](../../../scripts/feetech-ping.py)
  2026-10-17 实测修正版），单颗流程复刻 hls `provision._write_eeprom` / duck-control
  `bus.rs::write_eeprom`（本机 2026-10-17 给 15 颗改号用过的同一路径）：
  `ping(旧) → 写 55=[0]（关写保护）→ 写 5=[新] → 50ms → 写 新/55=[1]（上锁）→ 回读 5 号/55 号校验 + 旧 ID 静默确认`。
- 防撞号顺序（临时 ID 40-45，执行前 ping 确认空闲）：左腿 10-14→40-44；右腿
  20-24→10-14；临时 40-44→20-24；头颈 30→45、31→30、45→31。共 18 步覆盖 12 颗。
- 状态文件 `~/id-align-20261024.state.json` 防重复执行（**改号前后 ID 集合相同，扫描无法
  自检"已完成"，重复执行等于再换一次方向**）；快照 `~/id-align-20261024-snapshot.json`
  记录每颗改号前 reg5/reg55/位置；运行日志 `~/id-align-20261024-run.log`（均在板上）。
- 勘误（脚本自身，已修复入库）：初版 `final_verify` 拿中间临时号对位置指纹，12 条假超差；
  修正为按"原始 ID→最终 ID"合成映射折叠核对后 12/12 全对。板上快照的 `fingerprint_bad`
  已由复核脚本更正并附 `fingerprint_note`。

### 2. EEPROM 改号实测（2026-10-24 13:1x，板上执行）

- 前置：servo-web 15/15 在线（`/api/info` present 全 15、`fake:false`、timeout 0）后
  `kill` 停服务释放 /dev/ttyS2；hls / imu-viewer 未运行。
- 预检（dry-run）：扫描 0-60 恰为 10-14/20-24/30-34，无额外 ID，临时号 40-45 空闲，IMU 200 在线。
- 执行：18 步全部一次成功，每步回读 `5 号=新 ID、55 号=1`，旧 ID 即刻静默；无超时、无校验错。
- 终扫：恰为 10-14/20-24/30-34，临时号全部释放。
- 位置指纹（合成映射）：12 颗改号舵机改号前后读数**全部零偏差**（例：旧 10 pre=2046 →
  新 20 now=2046；旧 12 pre=2344 → 新 22 now=2344；旧 30 pre=1818 → 新 31 now=1818），
  证明只改了 ID、每颗舵机物理不动、零位/偏移随原舵机保留。
- 安全边界遵守：只写 5/55 两个寄存器，未发任何位置/速度/扭矩指令，未触碰 200 号。

### 3. 软件层回退

| 层 | 动作 | 备份（板上） |
|---|---|---|
| servo-web `~/servo-web` | [scripts/servo-web-upstream-idmap.py](../../../scripts/servo-web-upstream-idmap.py) 反向补丁：`JOINT_NAMES`、`OFFICIAL_FOLD`、页面分组/容器、`DEFAULT_POSITION`、SIT/FOLD、膝发送角、中文关节名、`ORDER`/`order`/注释、`model.json` 关节 id 与顶层 `joint_ids`、`build_model.py JOINT_IDS` 全部换回上游；3D 模型 fetch 版本号 `?v=20261022-2`→`?v=20261024`；`directions.json` `_note` 追加改号说明（数值仍全 −1）。后续叠加的 model-cache/dirs-sync/row-cal/zero-offset/cal-fix/state-sync 补丁全部保留 | `~/servo-web/.upstream-idmap-backup-20261024-131954/` |
| servo-web 重启验证 | `/api/info`：`20=left_*、10=right_*、30=neck_pitch、31=head_pitch`，15/15 在线、`fake:false`、timeout 0；启动日志只有扫描+读相位，无动作指令 | — |
| hls `~/hls_servo_debugger` | `provision.py` 关节表回上游：先重跑 [scripts/swap-hls-jointmap.py](../../../scripts/swap-hls-jointmap.py)（对称交换，换回 left=20-24/right=10-14）；30/31 因 [scripts/swap-hls-headneck.py](../../../scripts/swap-hls-headneck.py) 带单向幂等保护拒绝换回，另写 [scripts/hls-headneck-revert-upstream.py](../../../scripts/hls-headneck-revert-upstream.py) 两行精确替换为 `30=neck_pitch、31=head_pitch`；`py_compile` 通过。hls 当前未运行，下次启动生效 | `provision.py.bak-20261024-132405`（30/31）；jointmap 脚本自带备份 |
| 本机 viewer | [scripts/servo-mujoco-viewer.py](../../../scripts/servo-mujoco-viewer.py) `JOINTS` 表换回上游；顺带清掉过期硬编码 `ZERO_COUNTS={22:1198}`（那是 2026-10-23 #22 当右髋 pitch 时的临时零位，22 号当日已重校，且改号后 22 号语义变为左髋 pitch，硬编码会错挂关节；servo-web 页面侧本就是空表） | git 工作区 |
| servo-trace.py | 不改：纯按 ID 记录，ID 集合未变 | — |

上游姿态 `poses/upstream-2026-09-20/`（站/缩）维持归档，不恢复到姿态列表——它们绑定
上游机器的零位，仍不是本机姿态。

## 验证状态与限制

- EEPROM：18 步全过回读校验 + 终扫 + 位置指纹 12/12 零偏差。**改号结论可信**。
- servo-web：API 映射已验证为上游；3D 归属/方向**待用户浏览器 Ctrl+F5 后目视复核**
  （`model.json` 已换 id 且 fetch 版本号已跳版，正常硬刷新即可拿到新模型；HUD 会显示
  `30→neck_pitch、31→head_pitch`）。
- hls：表已回上游并编译通过，未启动实测（下次用时启动即按上游表）。
- 方向表 `directions.json` 仍 15 颗全 −1：改号只换 ID 不换物理舵机，方向系数属于
  （物理舵机、关节）对，理论不变；但**左右腿镜像关节的语义换了组，建议用户下次开 3D
  时顺手扫一眼左右是否仍一致**。
- 零位：各舵机 EEPROM 偏移随原舵机原样保留（位置指纹零偏差即证据）；2026-10-23 遗留的
  左腿（现 ID 20-24）摆位误差固化问题与本次无关，仍未处理。
- 带载动作边界不变：本次全程未发动作指令；后续带载仍按"先小角度、托住"流程。

## 回滚方式（如需）

反向执行同一脚本把 MOVES 换向即可（20-24↔10-14、30↔31），或直接手掰 `~/id-align-20261024-snapshot.json`
里记录的原 ID。软件层用板上 `.upstream-idmap-backup-20261024-131954/` 与 `provision.py.bak-*`
恢复。改号脚本有状态文件防呆，反向执行需先清 `~/id-align-20261024.state.json` 并理解风险。

## 下一步

1. 用户浏览器 Ctrl+F5 复核 3D 与实物（左右腿、30/31 归属与方向）。
2. 后续所有控制软件（robotd 补丁或自研、策略部署）**直接按上游 `model.rs` 映射使用**，
   不再需要本机差异表；`robotd.toml` 方向表顺序恢复上游顺序（左腿 20-24、颈头嘴 30-34、
   右腿 10-14）。
3. 左腿（现 20-24）2026-10-23 校准摆位误差的矫正仍待做（见
   [servo-web CAL 调研](../servo-web-cal-droop-20261023/research.md)）。

## 追加核查：用户怀疑 hls_servo_debugger 把 ID 改回去了（2026-10-25 凌晨，未改动）

用户报"左右脚又反了"，怀疑刚打开过一次 hls 导致 ID 被改回。**三重证据证明 hls 没有任何
写入、ID 未变**：

1. hls 完整日志（3766 行，覆盖 01:43–01:49 会话）端点普查：仅 `/api/feedback` 轮询 ×3470、
   `GET /api/{logs,status,ports,joints,fields}`、`POST /api/read` ×5、`POST /api/connect` ×1——
   **没有任何 write/init/provision/torque 类请求**；它只是连上串口读了几次。
2. 逐颗直读 5 号寄存器：15/15 `reg5 == 自身 ID`（10=10 … 34=34），EEPROM 仍是上游排布。
3. 板上 `provision.py` mtime 13:24:05（即 2026-10-24 回退上游后未被再改）；servo-web 各文件
   mtime 也都在补丁时间点后未变。

附带发现（当时状态，非 ID 问题）：①15 颗位置全部 ≈2045–2057——自 2026-10-24 下午的
参考指纹（多处 ±20–26°）之后有人把全部关节回中/重校过零位；②servo-web 曾被人以不带
`--imu-bus` 的裸命令重启（IMU 面板会消失），本次核查后已按标准命令带 `--imu-bus` 拉起。
用户若仍见"左右反"：先对正在看的页面 Ctrl+F5（尤其昨 13:20 前开过的旧标签页，其
JS/model.json 还是本机映射旧版），并注意 hls 关节表现在按上游分组（左腿 20-24/右腿 10-14、
30=neck/31=head）显示属正常，不是被改回去。

**同日续：用户确认 servo-web 里动左脚 3D 动右脚且踝方向反。实测服务器端一切正确**
（`/api/info` 20=left_*/10=right_*/30=neck/31=head；页面分组「左腿 20–24/右腿 10–14」；
model.json left_ankle=24/right_ankle=14；`Cache-Control: no-store`）——该症状与"旧标签页
仍跑本机映射旧版 JS/模型"完全吻合（物理左腿现挂 20-24，旧页把 20-24 画成右腿、镜像踝
方向看着就是反的）。判定为客户端旧页面，处置：硬刷新或关掉重开标签页，用分组标题自检
（新页显示「左腿 20–24」，旧页显示「左腿 10–14」）。

---

# 第四阶段：腿组再次被换回 + 只换腿修复（2026-10-25 凌晨，已修复）

## 现象与定案

用户硬刷新并重开标签页后仍"动左脚 3D 动右脚、踝方向反"。服务器端已验证为上游映射
（/api/info、页面分组、model.json 均 20-24=左），reg5 校验 ID 寄存器一致——结合用户
实测，**定案：物理左腿又被挂回了 10-14**，即 2026-10-24 13:12 全机对齐之后腿组再次被
反向换号。注意 reg5 校验只能证"应答 ID 与寄存器一致"，证不了"哪条腿在哪组号"。

## 时间线证据（板上日志考古）

- **15:24（10-24）总线上仍正确**：灵动中心快照 `30:1812/31:1815` 与改号后上游状态吻合
  （改号前 30=头 1818/31=颈 1817，改号后物理颈在 30）。
- **15:24–15:45 总线风暴**：累计超时 232→7500+（总线长时间整体无应答，疑似物理操作）；
  另一会话记录（[b-feetech-policy-deployment](../b-feetech-policy-deployment-20261024/research.md)）
  在此窗口杀掉 servo-web（其记录 PID 1200，声称未发动作/未改参数）。
- **15:45:25** servo-web 日志写到一半被硬杀（截断在句中）；**01:37（10-25）板子重启**
  （uptime 证实），重启后用户手动起 hls（bash 历史：换 WiFi + hls 启动命令）。
- **01:43 hls 会话纯只读**（3766 行端点普查：仅 feedback 轮询 + 5 次 read + connect）——
  **不是这次 hls 干的**；但 10-24 晚间若有更早的 hls 会话，其 /tmp 日志已被覆盖，无从查证。
- 期间 15 颗位置全部变为 ≈2048（15:24 时 30/31 还在 ~1812）——存在 servo-web 日志之外的
  回中/重校操作，与换号来源同属未解（无日志留存）。

## 修复（2026-10-25 02:4x 执行）

- [scripts/servo-id-legs-reswap-20261025.py](../../../scripts/servo-id-legs-reswap-20261025.py)：
  **只换腿组**（左 10-14→20-24、右 20-24→10-14，临时号 40-44；30/31/32/33/34 与 200 不动
  ——15:24 证据表明头颈当时仍正确，且用户仅报脚反）。15 步全部回读校验一次通过，
  终扫正确；快照/状态文件/运行日志 `~/id-legs-reswap-20261025*`。
- servo-web 已带 `--imu-bus` 重启（此前被人裸启动过），15/15 在线。
- 待用户验证：动左脚 3D 应动左脚；并**点头测试**（低头时 3D 应是头在点头而非脖子）——
  若头颈也反了说明那次换号是全量换（含 30/31），需再补一次 30↔31 互换。

## 遗留

- 10-24 15:45 后的换号执行者无日志可考（嫌疑：被覆盖的 hls 会话或未记录的物理/工具操作）。
  **再次提醒：改号只允许经本项目脚本（带回读校验与状态文件防呆），hls 初始化页不要
  对已编号整机使用。**
- 板上裸启动 servo-web（丢 --imu-bus）的问题两次出现，已在 bench-tools 强调标准命令。
