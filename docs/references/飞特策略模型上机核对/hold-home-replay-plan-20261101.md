# 2026-11-01 原生站姿使能一次复现

- 问题：复刻 Studio 的站姿使能，查明原生写舵机目标前后 ID 200 单播 READ 的超时边界。
- 授权：用户明确回复“已托稳，可以执行一次”；沿用台式电源 7.4 V、限流 3 A。动作授权只用于一次 `hold-home`，不因采集失败自动重跑。
- 方法：短暂停 Studio/robotd，独占只读回读 15 颗扭矩与寄存器 9–39、40–52，保存保护相关原始字节及 IMU 诊断；恢复原生 commissioning 后，附加 control 线程 syscall 采集，调用与 Studio 相同的 `robot.busCommand`：`action=hold-home`、15 个 `direction=-1`、`duration_ms=3000`。读取/解析以对应本机固件为准，不将通用 STS 模式定义套给 HD1910。
- 原生路径：Preload 写当前反馈位置 → 下一周期遥测 → Enable 写扭矩并回读 → 3 秒 Ramping；读取失败由既有保护取消站姿并卸力。排障脚本最长等待动作 6 秒，随后显式 `robot.relax`、确认 off，再独占读扭矩寄存器和 IMU 诊断，恢复原先活动服务。
- 防重复：发送前独占创建 `.attempted` 标记；检测已有标记或输出即拒绝运行。直接 goal 写实验仍禁用。
- 保持不变：生产代码、固件、20 ms 时限、方向、零位、动作参数、既有保护。此次为用户明确请求的硬件排障复现，非功能修改。
- 限制：strace/ptrace 会改变时序；Studio 暂停以避免并发命令，因此复现的是相同原生 RPC 和控制逻辑，不能称电气时序与无采集时完全一致。保护回读只记录实值，不写保护配置；不把短时受支撑复现当作完整带载验收。
- 来源：板侧 `/home/radxa/studio-dev/studio/imu.py:463`；本项目固定控制器源码 `robotd/src/feetech_commissioning.rs:592` 及 `software/robotd-v03/patches/v03-unicast.patch`；原始脚本 [hold-home-replay-20261101.py](hold-home-replay-20261101.py)。运行结果与未解决问题补入同专题 `research.md`。
