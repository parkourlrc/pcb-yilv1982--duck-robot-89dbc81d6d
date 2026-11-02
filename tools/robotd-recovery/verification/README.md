# 离线验收（2026-11-01）

本页保留部署前离线阶段的条件与结果；之后已完成[部署只读验收](../../../docs/references/b-feetech-policy-deployment-20261024/webpad-recovery-deployment-20261101.md)，物理起身仍未测试。

**[实测／离线] 候选代码已构建和验证，未部署、未触发真机动作。**
测试不连接串口：真实 ONNX 测试使用假关节／IMU 输入及假扭矩接口，不能代替机器人起身、承重或时序验收。

## 最终结果

| 项目 | 结果与原始日志 |
|---|---|
| 恢复状态机 | 4/4，超时、失效反馈、旧租约、连续姿态及取消屏障：[test-final.log](test-final.log) |
| IPC 协议 | 55/55，含新增动作参数 roundtrip：[guards-final.log](guards-final.log) |
| HOME 与普通起步保护 | 7/7 + 8/8；另有一项确认在原始源码同样失败，见下方：[guards-final.log](guards-final.log) |
| 完整控制流程 | 真实 ONNX 1.28.0＋假 IO，4/4，分别独立进程：[integration-final.log](integration-final.log) |
| Studio 后端 | 7/7，所有权、迟到回执、失效页面、模型匹配、旧 daemon 与停止放行：[studio-tests-final.log](studio-tests-final.log) |
| 浏览器逻辑 | 7/7，运行实际 RecoveryCard 函数并注入假计时器／RPC：[browser-logic-final.log](browser-logic-final.log) |
| 配套源码解析 | Python AST、JS syntax：[syntax-final.log](syntax-final.log) |
| ARM64 构建 | 成功，仅既有 linker 优化参数弃用警告：[build-final.log](build-final.log) |
| 补丁重放 | 原始包重建后，15 个修改／新增文件 SHA256 一致：[patch-replay-final.log](patch-replay-final.log) |
| ELF | AArch64、ELF64，未执行二进制：[elf-final.log](elf-final.log) |

完整流程分别验证：

1. 正确加载既有 walk SHA，实际生效的 scale、头／腿滤波为 1.0／0.5／0.7；扭矩开启后先读新反馈再写策略目标；租约过期卸力。
2. 上力后的反馈失败时执行卸力，不写策略目标。
3. 恢复中 INIT 取消后，不因已排队请求再次上力。
4. 连续姿态判据后保持零输入，拒绝普通移动，显式 enable 才交接，模型不重置。

## 失败、修正及保留项

- 初次离线构建发现旧 Windows 解压目录缺 xtask 等 195 个文件，从已验证 SHA 的原始 tar **仅补入新工作副本**；原件未改。
- Windows 内联 shell PATH 因含空格而解析失败；改用已保存的固定 PATH 构建脚本。
- 锁定测试依赖最初缺 `async-trait v0.1.92`，按现有 Cargo.lock 补齐；锁文件哈希未变。
- 新 RPC 引发 updater IPC 的穷尽匹配编译错误，补非本服务分支，不改更新行为。
- IPC `every_call` 原要求每方法仅一例，误将三种 action 当三方法并保留旧总数；已改为 68 个独立方法，参数变化另测。首次 [guards-initial.log](guards-initial.log) 留存。
- 最初四项完整 daemon 测试在同一进程运行，后三项触发既有全局 HOME OnceLock。改为每项独立进程，不改生产初始化约束；首次 [integration-initial.log](integration-initial.log) 留存。
- `tests::r17_empty_snapshot_and_warming_imu_do_not_accept_home` 在候选和完全未改的固定原始源码均报 `loop did not tick`。原始源码对照见 [baseline-existing-test.log](baseline-existing-test.log)。属于本次发现的现有失败；未擅改上游测试或启动行为，不能宣称整个 robotd 测试集全绿。
- 原始对照首次共用本任务主机 target，随后发现 Cargo 可能复用旧测试二进制。已使候选文件失效、明确重新编译，最终日志为 **332 个候选 robotd 测试中的指定项**，四项新增完整流程每项实际运行 1 个测试，没有“过滤后零项”的假通过。脚本现已分开两套 target。
- 第一次 Windows 补丁重放被全局 `core.autocrlf=true` 转成 CRLF，文本等价但字节哈希不同；重放命令显式 `core.autocrlf=false`，通过逐文件核对。未更改用户全局 Git 配置。
- 代码复核补齐恢复取消在 Studio 更新／标定保护中的急停放行；start 和 keepalive 不获此例外。

## 尚未验证

未进行真实浏览器渲染／交互验收、物理仿真、ARM64 程序运行、板侧服务切换或真机动作。
本机模型能否从某种躺姿起身、是否稳定承重、实际推理周期能否满足新鲜度条件，均须后续独立验收。
8 秒与连续 1 秒只是已批准的首轮参数，不能由离线测试写成实物效果已验证。
