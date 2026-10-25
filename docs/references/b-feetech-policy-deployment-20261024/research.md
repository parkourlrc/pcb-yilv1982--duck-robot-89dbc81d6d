# B 线飞特策略上机核对

- 日期：2026-10-24
- 问题与范围：确认本地方案 B 飞特训练工程是否有可部署行走模型；检查公开 HD1910 策略包、Radxa runtime、策略接口和控制软件包的安装边界。核查日期 2026-10-24。
- 验证状态：模型与 runtime 归档本地 SHA256 清单通过；当前 Radxa 缺官方控制栈，运行环境及模型执行参数不兼容项未裁决，未安装、未运行策略、未发送舵机动作。

## 结论

1. 本地 `references/microduck-replica/software/training/` 没有 `.onnx`、checkpoint 或其他训练产物。其 2026-09-24 基线文档所述 5 轮 smoke checkpoint 只是训练链路验证，不能当作已学会行走的策略。本地 B 工程有 `Mjlab-Velocity-Flat-MicroDuck-HD1910` 任务配置，但没有随只读源码树发布的权重。
2. 找到一个不同仓库公开的 HD1910 自训行走模型包：`kissqy/Microduck-kissqy` 的 `microduck-hd1910/firmware/policies/walk/`。截至核查时仓库 main 提交为 `eccc2fdbbf4c835e12abfa7ae6c93b1b1462fc51`（2026-10-23）；模型 SHA-256 为 `1cbf8730eadd75a5704332c9f3c10f60bfa9412135b907831c9dbd731ce1795f`。它不是本地 B 训练产物，也不是方案 C 仿真工程产物。
3. 包的元数据为 HD1910、61 维输入、14 维动作、50 Hz、ONNX 内含一次观测归一化，动作顺序为左腿 20–24、颈头 30–33、右腿 10–14，与 2026-10-24 对齐后的本机 ID 顺序一致。ID 对齐只解决映射，不证明零位、机械 Home、方向、IMU 安装和姿态已匹配。
4. 该包针对 `robotd` 固件 0.15.1，训练任务是 `Mjlab-VelStand-Rough-Backlash-MicroDuck`，模型说明明确 `deployment_verified=false`，且要求 HD1910/IMU 适配驱动和当前装配标定。官方导出包也声明不能把其中归档标定写回实机。
5. 2026-10-24 后续现场复查发现前一记录已过时：Radxa 为 Debian 12、内核 `6.1.84-10-rk2410-nocsf`；无 `robotd`/`robotctl` 命令，无 `/etc/robot`、`/opt/robot`，相关 systemd 服务 inactive。`servo-web` 实际在运行并持有 `/dev/ttyS2`，与此前“已关闭”状态不符；按用户先前关闭要求终止其 PID 1200，之后 `fuser` 无占用输出，robotd/servo-web 服务均 inactive。终止的是本机调试 Web 进程，没有发舵机动作或改舵机参数。
6. 下载了公开仓库的 `Microduck-Robotd-FT6-R17.tar.gz` 至被 Git 忽略的 `training/logs/b-feetech-walk-20261024/`，归档 SHA-256 为 `bcfd5c183c697b9e76d20bd563d995eda6a48331a7c49b9e76d20bd156c65cce`。已展开到同目录 `runtime-package-review/` 作静态检查；归档内 `SHA256SUMS` 中列出的文件均匹配。包声明构建 `1fa8438-feetech-ft6-control.43`，目标官方系统 0.15.1 / R17 V1.0.95；robotd/robotctl 为 AArch64，列出的 glibc 最高符号版本 2.30，内含 ONNX Runtime 1.28.0。它不是通用 Debian 安装包，配置/服务脚本涉及 `/opt/robot/feetech-ft5-r5`、`/etc/robot/feetech-ft5` 和 systemd 服务，安装入口还会停止/替换旧 robotd、写入配置并可安装包内标定。当前板上没有官方服务基线，且非交互 sudo 不可用，因此没有执行安装。
7. 此归档内 walk 模型 SHA-256 与候选模型一致，但模型合同及实际执行配置有冲突：模型目录 `deployment-profile.toml` 与训练/contract 元数据要求 `action_scale=1.0`、`head_lowpass=1.0`、`legs_lowpass=1.0`；归档 `deployment-execution.json` 却要求头部 0.5、腿部 0.7；归档全局默认 `action_scale=0.7`。包自己将 `deployment_verified` 标为 false，尚无依据判断是否有意作为补偿或配置错误。不能静默选其中一套上线。
8. 归档标定 `hd1910-calibration.robot.toml` 标注来源为 `duck-10e4`，零点含 30=2526、31=2228、33=1599，并带 IMU 四元数；这不是本机当前标定的证据。安装文档虽称保留已有有效标定，但本机没有 robotd 标定文件可供保留，不能直接部署该标定，也不能把缺失项用上游值补齐并投入运动。
9. 本地 Windows Python 3.13 环境没有 `onnx` 或 `onnxruntime` 模块；归档只带 AArch64 ONNX Runtime，未做本机模型前向推理。前次模型 SHA、元数据和维度仍是文件/合同核验，不升级为推理或真机验证。
6. 上述模型仓库的 `firmware/policies/LICENSE` 为个人非商业使用许可，允许自然人个人非商业使用，但不授予商业/组织用途；上游代码、模型、几何和其他第三方权利仍各自适用原许可。下载或部署前须按实际用途遵守许可。

## 来源与定位

- 本地 B 训练说明：`references/microduck-replica/software/training/README.md`、`docs/hd1910-baseline.md`，并检查训练树中 `.onnx`/checkpoint 文件；未发现模型文件。
- 本地接口历史核查：`docs/references/c-motion-training-20261015/research.md` 第 4 节与 `docs/references/runtime-policy-model-20261013/research.md`。
- 模型仓库：<https://github.com/kissqy/Microduck-kissqy>，main 固定核查提交 `eccc2fdbbf4c835e12abfa7ae6c93b1b1462fc51`。
- 策略包说明：<https://github.com/kissqy/Microduck-kissqy/tree/main/microduck-hd1910/firmware/policies/walk>，文件 `使用说明.md`、`README.en.md`、`manifest.json`、`deployment-profile.toml`、`deployment-runtime.json`、`model-info.json`、`deployment-contract.json` 与 `LICENSE`。
- 板上状态：SSH 别名 `radxa`（192.168.1.35）；读取 `/etc/os-release`、内核、进程、命令、systemd、目录、`servo-web /api/info`。servo-web API 显示 15/15 舵机在线、总线 timeout=0、ID 200 已进入 live；这些是停止 servo-web 前的只读快照，不代表 IMU 姿态标定或策略 Home 一致。随后终止 servo-web PID 1200 并检查串口释放。`sudo -n` 返回需要密码，无法做特权安装。
- 控制归档：`training/logs/b-feetech-walk-20261024/Microduck-Robotd-FT6-R17.tar.gz`，SHA-256 `bcfd5c183c697b9e76d20bd563d995eda6a48331a7c49b9e76d20bd156c65cce`；解包审阅位于同目录 `runtime-package-review/`，该目录及压缩包受 `training/.gitignore` 忽略。来源链接为上一节公开模型仓库路径下的 `microduck-hd1910/firmware/console/updates/`。

## 关键接口与限制

- Manifest：`obs_len=61`、`action_len=14`、`control_hz=50`、`servos=hd1910`、`action_scale=1.0`、`normalization=embedded_in_onnx_once`。
- Policy Home（弧度）及关节次序来自 `deployment-contract.json`，属于模型训练合同；不得覆盖本机 EEPROM 零点，也不能仅凭模型包推定当前机械姿势一致。
- 包声明腿/头额外滤波为直通 1.0；ONNX 没有把该过滤器嵌入图。运行端须读并落实完整合同，不能仅复制 `.onnx`。
- 模型训练合同记录总质量 0.82 kg；与本项目 B 基线的原 Microduck 质量惯量沿用方式、场景和版本不同，部署前应确认本机机械结构是否对应模型。
- 公开仓库的策略许可仅供个人非商业使用。不得把源仓其他部分默认为可复用或可商用。

## 后续条件

后续要先解决三项：①确认官方 control.43 / 0.15.1 控制栈能否在本机 Debian 12 镜像上受支持地安装（当前安装器依赖缺失的既有 systemd 服务/配置基线，sudo 需交互密码）；②由模型来源方确认执行参数冲突，尤其训练合同 1.0 直通与运行配置 0.5/0.7 的差异；③取得/重建本机 15 关节与 IMU 的有效标定，并确认 Home/方向/装配。之后才可做无动作模型加载与总线状态验证，再安排机械可靠支撑下的受控动作。servo-web 当前已关闭、串口释放；robotd 未安装，策略未加载。即使全部条件补齐，该模型 `deployment_verified=false`，首跑仅为实验，不等于步态验收。
