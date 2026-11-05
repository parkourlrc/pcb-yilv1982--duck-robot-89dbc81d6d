# 舵机 ID 对照表：A 线视频（XL330） vs C 线本机（HD-1910）

> **⚠️ 2026-10-24 重大更新：应用户指示，本机已通过 EEPROM 改号对齐上游 microduck_feetech（方案 B 飞特版）映射，左右腿整组互换、头颈 30/31 互换。以下"本机 C 线"列为最终生效版。** 改号执行记录见 [舵机编号对齐上游 调研](references/舵机编号对齐上游/research.md)；2026-10-17/10-22 的"本机与上游相反"定案已成为历史。

## 本机现行映射（部署契约，2026-10-24 定案；与上游 microduck_feetech 一致）

舵机 EEPROM 已按此改号完毕（12 颗换号，18 步全部回读校验通过，位置指纹 12/12 零偏差）：

| ID 段 | 部位 | 关节（按 ID 从小到大） |
|---|---|---|
| **10~14** | **右腿** | right_hip_yaw / right_hip_roll / right_hip_pitch / right_knee / right_ankle |
| **20~24** | **左腿** | left_hip_yaw / left_hip_roll / left_hip_pitch / left_knee / left_ankle |
| 30~34 | 头颈 | neck_pitch / head_pitch / head_yaw / head_roll / mouth |
| 200 | IMU | 链末 |

与上游 microduck_feetech `model.rs` / hls `provision.py` 原表**完全一致**，控制软件可直接照上游关节表使用。home 角随关节名（left_ankle=+25.96°、right_ankle=−25.96°，头颈 +20°）。

**执行记录（2026-10-24）**：
- 舵机端：[scripts/servo-id-align-upstream.py](../scripts/servo-id-align-upstream.py) 板上执行 EEPROM 改号（55 号解锁→写 5 号→上锁→回读校验；防撞号经临时 ID 40-45）；快照与状态文件在板 `~/id-align-20261024-*`；
- servo-web：[scripts/servo-web-upstream-idmap.py](../scripts/servo-web-upstream-idmap.py) 把板上部署副本从本机映射回退为上游映射并重启，`/api/info` 已验证 `20=left_*、10=right_*、30=neck_pitch、31=head_pitch`、15/15 在线；
- hls：板上 `~/hls_servo_debugger/hls_debugger/provision.py` 关节表已回上游原表（[scripts/swap-hls-jointmap.py](../scripts/swap-hls-jointmap.py) 再跑一次 + [scripts/hls-headneck-revert-upstream.py](../scripts/hls-headneck-revert-upstream.py)），下次启动生效；
- 本机 viewer：[scripts/servo-mujoco-viewer.py](../scripts/servo-mujoco-viewer.py) 关节表同步为上游映射；
- 改号只动 ID：各舵机 EEPROM 偏移/零位随原舵机保留；方向表仍 15 颗全 −1。

## A 线视频对照（XL330，仅参考机械动作）

- **A 线**（视频所示，官方 microduck / Dynamixel XL330）：ID 1~15 连续分配，用 Dynamixel Wizard 设置；
- **C 线**（本机已初始化，microduck_feetech / HD-1910）：10~14 / 20~24 / 30~34 分组分配，用 hls_servo_debugger（:8765）设置；**ID 1 保留**（总线上出现 ID 1 = 有未编号的出厂舵机），**200 = IMU 专用**。

## 按关节对照（装配时按关节名对号；C 线列为 2026-10-24 本机最终映射）

| 关节 | 部位 | A 线 ID（视频） | 本机 ID |
|---|---|---:|---:|
| left_hip_yaw 左髋偏航 | 左腿 | 10 | **20** |
| left_hip_roll 左髋侧摆 | 左腿 | 9 | **21** |
| left_hip_pitch 左髋俯仰 | 左腿 | 8 | **22** |
| left_knee 左膝 | 左腿 | 7 | **23** |
| left_ankle 左踝 | 左腿 | 6 | **24** |
| right_hip_yaw 右髋偏航 | 右腿 | 5 | **10** |
| right_hip_roll 右髋侧摆 | 右腿 | 4 | **11** |
| right_hip_pitch 右髋俯仰 | 右腿 | 3 | **12** |
| right_knee 右膝 | 右腿 | 2 | **13** |
| right_ankle 右踝 | 右腿 | 1 | **14** |
| neck_pitch 颈部俯仰 | 头颈 | 12 | **30** |
| head_pitch 头部俯仰 | 头颈 | 11 | **31** |
| head_yaw 头部偏航 | 头颈 | 13 | **32** |
| head_roll 头部侧摆 | 头颈 | 14 | **33** |
| mouth 嘴 | 头颈 | 15 | **34** |
| （IMU） | 链末 | — | **200** |

## ⚠️ 高危撞号（跟视频最容易装错的地方）

| ID | A 线含义 | 本机含义 |
|---:|---|---|
| **1~9** | 右腿五关节＋左踝/左膝 | **1 = 未编号出厂舵机标志；2~9 不使用** |
| **10~14** | 头颈四关节＋左髋偏航（A 线 11~14 为头颈） | **右腿五关节** |
| **20~24** | （不存在） | **左腿五关节** |

跟视频装配时**不要听 ID 只看位置**；A 线与本机没有数字对应关系（编号方向相反：A 从踝往髋编，本机从髋往踝编；A 左右与本机左右仅在各自体系内自洽）。

## 其他差异（同样别照搬视频）

- A 线视频用 Dynamixel Wizard 设 ID/参数——本机用 :8765 调试器（参数含义也不同，如 A 的 PWM Slope/Shutdown 是 Dynamixel 概念）；
- A 线电气（OpenRB-150/USB）与 本机（HAT/UART2）不同，接线一切以本机 [HAT 接线意向](photos/archive/hat-v1.2-white-20261010/hat-v1.2-wiring-plan.png) 为准；
- A 线嘴部舵机"行走策略不使用"——本机 15 颗全编（34=mouth），上游飞特版包含嘴。

## 历史记录（勿用于现行部署，仅追溯）

- **2026-10-17 定案（已作废）**：实物装配后发现左右腿与上游相反（当时定 10-14=左腿、20-24=右腿），舵机按此改号；`scripts/swap-hls-jointmap.py` 交换板上 hls 关节表。
- **2026-10-22 补充（已作废）**：实物确认 30=head_pitch、31=neck_pitch（也与上游相反），按实物编号在软件层映射（未改 EEPROM）；`scripts/swap-hls-headneck.py`、`scripts/servo-web-local-idmap.py` 等把 servo-web/hls/viewer 改为本机映射。当日用户确认 3D 与实物方向位置全部对上（15 颗全 −1、回 2048 站立）。
- **2026-10-24（现行）**：用户指示"ID 做一次对齐，和方案 B 的飞特版一致"，EEPROM 改号回上游排布，软件层全部回退。此后控制软件不再需要本机差异表。

来源：A 线表 = [build-tutorial README「舵机 ID」](../references/microduck-build-tutorial/README.md)；上游关节表 = [hls_servo_debugger provision.py](../references/microduck-community-kit/software/hls_servo_debugger/hls_debugger/provision.py)（源自 microduck_feetech `model.rs`）；**本机现行映射 = 2026-10-24 EEPROM 改号对齐上游（执行记录见 [舵机编号对齐上游](references/舵机编号对齐上游/research.md)）**。
