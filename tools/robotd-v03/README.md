# 本机 robotd v0.3 单播适配

> **2026-11-01 通信补丁已撤回，当前为历史档案。** 新单口板已换上；板侧恢复原 `control.47`，WSL 三个源码恢复原件、独有 v0.3 测试文件移出。旧 `target/` 已标记禁止部署，以下 v0.3 构建/安装命令仅供历史追溯。Studio 显示适配、已导入模型及参数保留。完成 servo-web 验收后，现已按用户要求停止 servo-web、启动 robotd/Studio；用户确认托稳，原生启动卸力已回读，自启设置未改。见[回滚验收](../../docs/references/b-feetech-policy-deployment-20261024/restore-mixed-sync-read-20261101.md)。

**2026-11-01 12:31 三次复现及改序对照完成，尚未修复**：[实测] 三次原生 `hold-home` 均在 Ramping 收到 21 字节坏校验候选帧，失败前插值写次数为 2／3／2。先舵机后 IMU 实验在第一次插值后仍复现（8C 应有、0C 实收），该周期先收齐了 15 颗有效舵机反馈；原生等待截止后卸力。四次均确认 15 颗卸力，已恢复板上 `control.47+duck-v03.1`。该历史窗口为 IMU READ（0x02）56/15＋15 舵机 SYNC_READ（0x82），共用 20 ms；起身单次错误卸力、Holding 连续 25 次保护未改。两服务 active/enabled，后台通信仍有失败；坏帧产生位置待查，不能归因于限流、取消回复或缺少线程锁。见[时序、等待判错对比及恢复证据](../../docs/references/b-feetech-policy-deployment-20261024/research.md)。

**2026-11-01 早期自启与连接记录**：robotd 和 Studio 均已启用系统自启，旧 `duck-servo-web` 用户服务已停止并 disabled，避免开机占用 `/dev/ttyS2`。10:53 最终回读 robotd/Studio active、原生 commissioning/ready、15 颗卸力、IMU 数据有效，策略关闭。进入 Studio 舵机页会接管总线并暂停 robotd；有舵机保持时离页不会交还，做 IMU 粗校前需托稳后点“交还主程序”。用户确认后已验证该正常交还流程成功，见[最终回读](../../docs/references/b-feetech-policy-deployment-20261024/studio-connect-restored-20261101.json)。

**2026-11-01 标定交接配置已修正**：用户批准后已完成[启动配置迁移](studio-handover/README.md)：基础服务移除 `--read-only`，commissioning 使用 helper 正式管理的覆盖文件，旧 30 文件归档。helper 已识别 commissioning，原生及网页实际预览均通过、页面 `ready=true`。只 daemon-reload，两个服务 PID 不变、自启保留；标定、模型与保护文件 SHA 未变。用户随后已正式提交，15 个 calibrated=true、motion_enabled=true，原生 motion/control；此前迁移工具仅做预览，未替用户提交。见[Spec](../../docs/specs/20261101-studio-calibration-handover/spec.md)和[完整证据](../../docs/references/b-feetech-policy-deployment-20261024/studio-commit-mode-error-20261101.md)。下文 10-31 的安装、显示验收与备份记录为历史。

原 v0.3 补丁仅用于本项目 C 线 HD1910 + 新制 ScrapMeta v0.3 / replica 0.2.0 IMU；已撤回，不能部署到现行新单口板。保留的 Studio 显示和交接适配适用于上文当前部署。用户于 2026-10-31 先确认处理运行环境与 IMU 读取，随后明确要求按参考项目数据接入标定与动作参数。

- [Spec](../../docs/specs/20261031-robotd-v03-unicast/spec.md)
- [研究与安装记录](../../docs/references/b-feetech-policy-deployment-20261024/research.md)
- [来源](SOURCE.md)
- `patches/v03-unicast.patch`：对固定原生源码的完整改动（含传输测试与本机 build 标识）。
- `deploy/`：10-31 初次安装存档；其中服务模板不是现行启动配置，现行文件见 [studio-handover](studio-handover/README.md)。

**2026-10-31 已安装并完成一次只读运行**：Python 3.13.18、Studio 2026.10.3101、robotd `control.47+duck-v03.1`。30 秒 1500 周期中 1497 成功、2 次 IMU 超时、1 次舵机校验失败；这不是零错误或动作验收。原始六模型在 `/home/radxa/duck-policies/hd1910-20261031/`，随后已导入 Studio 模型库并通过 6/6 无电机前向预检，配套动作参数和参考标定数值已接入；本机匹配尚未实测，动作保持关闭。参见 [reference-data](reference-data/README.md) 和[数据导入 Spec](../../docs/specs/20261031-reference-policy-data/spec.md)。

Studio 地址：`http://192.168.1.35:8000/`。2026-10-31 23:32:36（北京时间）用户确认支撑后，robotd 已由只读切换为 `--commissioning`；当时 Studio 保持运行、`duck-servo-web` 停止释放串口，robotd 尚未启用自启（11-01 已补齐，见上）。启动卸力已由原生回读确认，策略动作仍关闭；10-31 快照约 50 Hz、40406 周期中 34 次通信失败，详见[当时回读](../../docs/references/b-feetech-policy-deployment-20261024/studio-display-final-20261031.json)。模型预检固定路径 `/opt/robot/feetech-ft5-r5/robotd` 指向同一部署文件（11-01 已恢复原版二进制）。

**Studio 显示适配已部署（实测）**：用户批准后应用 [studio-display](studio-display/README.md) 并于 23:45:16 仅重启 Studio；真实网页 WebSocket 的总览/舵机表均为 15/15，位置、电压、温度有效，IMU 姿态更新、方向验证状态保留。当时 robotd 由 `30-studio-commissioning.conf` 运行调试模式，扭矩关闭；该覆盖现已按上节迁移。已消除 `native.joints` 与 `last_sample.servos` 的显示格式缺口；3D 标定关节姿势、缺少的原生 IMU 诊断字段及偶发通信失败仍保留边界。见[交付 Spec](../../docs/specs/20261031-studio-commissioning-display/spec.md)。

## 历史构建（当前单口板不得应用此补丁）

源码为 `Microduck-kissqy` 固定提交的 `microduck-hd1910/firmware/`。在独立可写副本应用补丁，不改 `references/` 参考库。Linux/WSL 使用 Rust 1.99.0、cargo-zigbuild 0.23.4 和 Zig 0.15.1：

```sh
git apply /path/to/tools/robotd-v03/patches/v03-unicast.patch
cargo test --locked -p duck-control v03_transport_tests -- --test-threads=1
cargo zigbuild --locked --release --target aarch64-unknown-linux-gnu.2.31 -p robotd -p robotctl
```

不执行原仓整机安装、自动更新或模型种子脚本；它们包含本任务以外的系统设置和官方其他执行器模型。

本轮 WSL 构建目录 `/root/duck-robot-control47`，工具位于 `/opt/duck-robot/rust-1.99`、`/opt/duck-robot/build-env`，Cargo 缓存为 `/opt/duck-robot/cargo`。原生源码按上游说明不含部分打包模型；相关回归的 ONNX 资源从同 SHA 原模型补入，未修改测试判断。逐文件原始/补丁 SHA 见 `source-manifest.json`，构建 SHA 与测试日志在关联研究目录。

## 机载文件与回退

**2026-11-01 顺序实验产物，未采用为当前运行版**：[增量补丁](patches/v03-servo-first-experiment.patch) 必须在 `v03-unicast.patch` 之后应用；只改变 commissioning／read-only 的严格完整反馈路径，允许部分反馈的策略入口保持原顺序。对应 [准备脚本](deploy/prepare-servo-first-experiment.py)、[构建脚本](deploy/build-servo-first-experiment.sh)、[一次性部署采集脚本](deploy/run-servo-first-experiment.py)及 [Spec](../../docs/specs/20261101-servo-first-imu-read/spec.md)。7/7 传输测试及 arm64 构建通过，但真机一次对照仍失败，不能当作修复交付。板上原单播版备份为同目录 `robotd.pre-servo-first-20261101`（SHA256 `9f9fa71723339b80f97d7be065dec04855bb0d31a3ed7c5978e8605c22db3e5b`），已自动恢复；原始配置、标定未变。WSL `/root/duck-robot-control47` 源码现已恢复 control.47 原件，旧 target 产物保留并标记不可部署；一次性采集器标记保留，不删除后重跑。

- 程序：`/opt/robot/daemon/releases/duck-v03-20261031/bin/`，`/opt/robot/daemon/current` 和 `/usr/local/bin/{robotd,robotctl,padd}` 指向它。
- Python：`/opt/duck-robot/python-3.13.18/`；系统 Python 3.11 保留。
- ONNX Runtime：`/opt/robot/onnxruntime/1.28.0/`，服务明确设置 `ORT_DYLIB_PATH`。
- 配置：`/etc/robot/feetech-ft5/robotd.toml`；已接入并加载六模型，`policy.enabled=true`，audio 关闭。基础服务为正常入口，正式 commissioning 覆盖已在用户提交后删除；本机标定15个零位2048、calibrated=true、motion_enabled=true、IMU已验证。启动仍卸力、动态策略关闭，需用户显式开始。见[网页手柄部署](webpad-control/README.md)。
- 原版备份：同一 `bin/` 下 `robotd.upstream-control47`、`robotctl.baseline-r17`；2026-11-01 已恢复该 robotd 原件，对当前 Ft6 混读；不代表双口 v0.3 问题修复。
- 只读采集：`deploy/read-only-acceptance.py` 短暂停用户 `duck-servo-web` 单元，用原生服务采集 30 秒并在 finally 中恢复；运行结果保存在板侧暂存目录，并已回收进研究专题。

需要回退程序时，保持 robotd 停止，从上述备份安装回 `bin/robotd` 和 `bin/robotctl`；不启动策略。需要切回 servo-web 时先停止 robotd，再启动用户单元 `duck-servo-web.service`，确保串口只有一个持有者；不改模型和标定。

只撤回本次调试模式时，移除 `30-studio-commissioning.conf`，重载 systemd 后重启 robotd，即恢复基础单元的只读参数；不删除其他 drop-in。此操作不会恢复已卸力的舵机扭矩或原姿态。
