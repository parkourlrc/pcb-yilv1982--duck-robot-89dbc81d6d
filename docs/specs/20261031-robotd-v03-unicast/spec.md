# Spec：控制器环境安装与 v0.3 IMU 单播适配

> **历史任务**：2026-11-01 换上新单口板后，相关通信补丁已撤回，见[当前回滚 Spec](../20261101-restore-mixed-sync-read/spec.md)。以下实验、安装与验收按原日期保留；环境及 Studio 显示适配不在撤回范围。

- 日期：2026-10-31
- 状态：已交付环境与单播接入；真机 1500 周期出现 3 次通信失败，作为遗留项明确保留。
- 提交：未提交，保留工作区。

## 需求与验收

处理用户选定的第 1、2 项：在 Radxa Zero 3W 安装 Python 3.13、Microduck Studio 和配套飞特 robotd；让当前新制 ScrapMeta v0.3、replica 0.2.0 固件、ID 200 的 IMU 使用独立单播 READ，舵机继续 SYNC_READ。第 3 项（本机标定导入、模型动作尺度及滤波）留待后续；本任务不启动模型动作。

安装验收以主控实际 Python 版本、Studio HTTP 响应、robotd 版本及所需运行库为准；单播适配验收以编译成功、关键传输分支检查及真机只读遥测为准。不用源码检查或网页可访问代替真机遥测验收。

## 现状与依据

- [实测] 六个模型已在 `/home/radxa/duck-policies/hd1910-20261031/`；ONNX SHA-256 回读一致。
- [实测] 主控 Debian 12 / AArch64，系统 Python 3.11.2；起始无 robotd、robotctl、Python 3.13；servo-web 0.15.4 占用 `/dev/ttyS2`，15 个舵机在线。
- [用户授权/实测] 用户已提供管理员认证用于安装，sudo 标准输入认证成功。凭据不进入项目文件和安装日志。
- [源码核验] Studio 固定修订 `2026.10.3101`、提交 `3952471a8394c8b720817d2160ffd95ce5a54456`；原生公开源码固定提交 `27d7921dbcb280bd7d6ba3e9937624f1e2e61d23`，配套 robotd `0791fcd-feetech-qinmo-control.47`。
- [源码核验] `duck-control/src/feetech.rs` 中 `telemetry` / `telemetry_partial` 仍将 `ImuToDxl` 加入混合 SYNC_READ。现有 DXL2 独立读路径可作为共享时限与诊断合并的参考。
- [源码核验] `ImuSample::decode` 已以 `status & 0x07 == 0` 判就绪，允许 `0x08`；与当前 replica 0.2.0 已知状态语义相容，不直接复制 servo-web 为 kit v1 添加的 bit7 分流。
- [本机历史实测] servo-web 0.15.4 已切换单播 READ，记录见 [IMU 专题](../../references/舵机网页工具惯性显示/research.md)。不能把该结果写成 robotd 已验收。
- [待确认] 新二进制尚未构建；控制环两次事务合并的实际时延和读取成功率须在本机读取窗口确认。第 3 项尚未完成，不宣称可运行策略。

## 具体方案（用户已批准）

1. 安装独立 ARM64 Python 3.13，保留系统 Python；安装固定版 Studio 和原生程序及 ONNX Runtime。Studio 使用明确的 Python 3.13 路径。robotd 配置与服务先安装为停用状态，避免抢占 servo-web 串口或套用上游另一台机器的标定。
2. 在 `software/robotd-v03/` 建带来源说明的可部署补丁工作区；固定原生源码在独立缓存/工作副本中构建。原始来源快照及 `references/` 三个上游目录保持只读。
3. 仅对 `BusImuBoard::ImuToDxl` 改遥测：先对 ID 200 单播 READ 地址 56、长度 15；成功后对原 15 颗舵机 SYNC_READ 56/15，再合并返回。FT6、Qinmo、DXL2 分支保留。
4. 两次读取共用现有遥测 deadline；单播读取保留 ID、长度、校验、状态、回显过滤与迟到帧检查。记录单播请求/应答时间，合并收包字节、校验错误、缺失 ID 等诊断，不延长控制周期掩盖超时。
5. IMU 缺答、报错或逾时仍使该帧失败；只有 IMU 有效时才允许既有 partial servo 规则。严格与 partial 两入口都接入新路径。不改 IMU 四元数、陀螺比例、安装方向、关节映射或策略参数。
6. 做有针对性的传输用例：线上请求不把 200 放入舵机 SYNC_READ、共享 deadline、IMU 缺答/异常、partial 条件及其他板型路径保持。编译后安装带本机补丁标识的版本，保留原版二进制用于回退。
7. 真机验收时串口只由一个程序持有：短暂停 servo-web，使用明确只读的原生诊断入口采数，完成后恢复 servo-web。先核源码确认诊断入口不写寄存器；若无合适入口，另列最小诊断方案再执行，不以启动控制服务替代只读诊断。

## 影响文档、风险与回退

更新本 spec、[模型/控制器研究](../../references/飞特策略模型上机核对/research.md)、根 README 和 PROGRESS，以及新增工作副本来源/部署说明；模型内容和 BOM 不因纯软件安装变更。

主要风险是两次事务增加读取耗时、失效应答污染后续请求、错误放宽 partial 条件；用共享时限和针对性传输检查约束，真机结果按实际记录。新程序安装不自动开启策略；失败时停用新运行端并恢复 servo-web 和保存的原版文件。

## 实施记录

- 用户确认方案后，已完成 `ImuToDxl` 单播读取、传输测试与 `control.47+duck-v03.1` 标识；原生代码改动完整保存在 `software/robotd-v03/patches/v03-unicast.patch`，未改只读参考库。
- 已安装独立 Python 3.13.18、Studio 2026.10.3101、补丁 robotd/robotctl、原配套 padd、ONNX Runtime 1.28.0、服务与 helper；Studio HTTP 200，模型预检固定路径指向同一补丁程序。
- 单播新增 5 项通过。相关回归首次 95/97 通过；缺 ONNX 测试资源的用例补齐同源模型后通过，时间戳精确比较用例单独复查通过。原始失败保留，不写成首次全部通过。
- ARM64 release 构建成功，最高 glibc 符号 2.30。本机只读约 30 秒：1500 周期、1497 成功、2 次 IMU 超时、1 次舵机校验失败；平均读取 6.123 ms，最终 50.0048 Hz。所有快照 `motor_writes_blocked=true`，有效 IMU 帧故障/重复为 0；不宣称零错误或完成运动验收。
- 测试结束 robotd 停止/未启用自启，原用户单元 duck-servo-web 已恢复；Studio 保持运行。本机标定与动作参数未导入/修改，未发模型动作。
- 下载连接/超时、Windows 长路径/参数转义、测试资源与补丁换行核验的过程问题见关联研究；安装产物及退回原版二进制的路径已记录。
