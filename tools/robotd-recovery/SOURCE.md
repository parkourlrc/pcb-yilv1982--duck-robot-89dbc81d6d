# 固定来源与隔离环境

日期：2026-11-01。适用本机 C 线、HD-1910-C001、已换新单 3P IMU；非 v0.3 单播补丁。

本页记录构建来源；候选随后已按用户授权部署，当前状态见[部署清单](deployment-status.json)。

## robotd

- 来源仓库：`https://github.com/fanhao375/Microduck-kissqy`。
- 固定源码提交：`27d7921dbcb280bd7d6ba3e9937624f1e2e61d23`，子目录 `microduck-hd1910/firmware`。
- 来源内嵌构建名：`0791fcd-feetech-qinmo-control.47`；该构建身份与公开导出提交不同，不写成同一个 Git 提交。
- 原包：`training/logs/b-feetech-walk-20261024/controller-preparation-20261031/controller-source.tar.gz`。
- SHA256：`45cd22a955f3ff68bfbcb2d4266352d92798b6d1abd87a559fd613fcd52817d1`。
- 候选增加后缀 `+duck-recovery.1`、API_VERSION 42→43。通信实现、Cargo.lock 与原包相同，核验值见 [source-manifest.json](source-manifest.json)。

## Studio

- 来源：`https://github.com/fanhao375/microduck-replica/releases/tag/microduck-software-v2026.10.3101`。
- 固定提交：`3952471a8394c8b720817d2160ffd95ce5a54456`，发布于 2026-10-31。
- 本地运行源包：上述准备目录的 `studio-runtime.tar.gz`，SHA256 `fd4753ba11619607d36852f35080c62dc845fdffd005ef37aac74f61157b55ef`。
- `pad.py`、`pad_drive.py`、`pad.js` 原件与 [本机快照](../../docs/references/b-feetech-policy-deployment-20261024/webpad-models-snapshot-20261101.json) 及包内原件哈希相同；本轮又通过 SSH 只读核对这三个文件。
- `updates.py` 原件为固定包，SHA256 `b33a4953e23e3fe96a084b9be31f410d5551dae9003ff7a0fcc794155cbc312d`；随后部署前已只读核对板侧同值。
- 修改已保存在工作副本、补丁和候选包，按后续授权安装到板侧；安装清单与现场备份见部署记录。

完整发布证据与许可原件见 [来源快照](../../docs/references/b-feetech-policy-deployment-20261024/controller-sources-20261031/SOURCES.md)。本项目补丁不改变源码及模型的原许可边界。

## 模型与构建

复用联合 walk 导出，SHA256 `1cbf8730eadd75a5704332c9f3c10f60bfa9412135b907831c9dbd731ce1795f`。
测试路径为 `training/logs/b-feetech-walk-20261024/runtime-package-review/Microduck-Robotd-FT6-R17/models/1cbf8730eadd75a5704332c9f3c10f60/policy.onnx`。
只读使用，未重新训练或打包模型；其 `deployment_verified=false` 声明不变。

- Windows Python 3.13；Node 用于真实网页函数的假时钟与假 RPC 验证。
- WSL `Ubuntu-24.04`，Rust 1.99、cargo-zigbuild 0.23.4、Zig 0.15.1，目标 `aarch64-unknown-linux-gnu.2.31`。
- 候选构建根 `/root/duck-robot-recovery-20261101`；不复用历史 v0.3 target。
- 原始源码对照根 `/root/duck-robot-recovery-baseline-20261101`。首次对照曾共用本任务主机测试缓存，随后已使候选源文件失效并重新编译全部相关测试；当前脚本基线与候选分开 target，最终日志确认执行了新增测试。
- 真实 ONNX 假 IO 测试用 x86_64 `onnxruntime==1.28.0`，仅安装于 WSL `/opt/duck-robot/recovery-ort/`，加载 `onnxruntime/capi/libonnxruntime.so.1.28.0`。
- ARM64产物随后已安装运行，沿用现有兼容ARM64 ONNX动态库及Studio Python3.13，六模型加载通过；未测试物理动作。

## 实现阶段只读设备基线

robotd SHA256 `725b74cd93660a312970a44879abe5b75e8becf108499a1b8798961e48ca5f00`，PID 374；`microduck-studio.service` PID 494，两者 active。
这是实现阶段开始核对时的状态，不代表当前进程。该阶段未改设备；后续已按授权部署并重启服务，当前记录见部署清单。
