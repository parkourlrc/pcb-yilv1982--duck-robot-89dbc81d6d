# Spec：按参考项目接入六模型和标定数据

- 日期：2026-10-31
- 状态：已交付参考数据导入；本机标定核对和动作验收未完成。
- 授权：用户在了解标定和动作参数含义后明确指示“按参考项目的数据来”；据此采用已下载的六模型配套数据，沿用现有安装、IMU 适配和只读边界。此轮为配置/数据导入，不新增或修改运行端功能。
- 提交：未提交，保留工作区。

## 需求与依据

将已上传的六个 HD1910 普通足部模型接入现成 Studio 模型库和 robotd 槽配置。动作参数使用 kissqy R17 包及已安装 control.47 的实际解析规则；标定数值采用包内 `duck-10e4` 参考数据并标明来源，不将参考机的已验证标志视为本机实测。

已核对：本机 15 个 ID 于 2026-10-24 对齐上游；板上 robotd 配置尚无标定和模型路径。参考机零点并非本机零点记录，现有 servo-web EEPROM 文件不由本轮覆盖。walk 的 `deployment-execution.json` 是控制器明确支持的运行覆盖：幅度 1.0、头/腿滤波 0.5/0.7，优先于全局幅度 0.7；不再将这三处静态不同视为尚未裁决的加载冲突。出处见[统一研究](../../references/b-feetech-policy-deployment-20261024/research.md)。

## 执行范围

1. 归档固定参考配置和来源。原样保留模型及合同，使用现成 Studio 导入实现执行六模型的原生 `validate-policy`（含一次零输入前向计算，不访问电机）。
2. 在现有配置中接入六槽、50 Hz、配套增益/尺度、技能时长和按键。仅复制本次六个普通足部模型，不引入滑轮模型、参考机系统服务或安全设置。
3. 导入参考标定的数值：ID、零点、方向、范围、IMU 四元数；本机副本保持 `motion_enabled=false`、`imu_mount_verified=false`、各关节 `calibrated=false`。上游原件原样另存，避免伪造本机验收。
4. 配置写入前备份，保持 `policy.enabled=false` 和既有 `--read-only` 服务参数；不启动 robotd、不占串口、不写 EEPROM、不执行动作。已有 servo-web 持续运行。
5. 验收：Studio 导入记录、六个 SHA、原生模型预检结果、配置回读及服务状态；不重复上一轮总线长测。

## 回退与交付

以板侧带时间戳的配置备份回退；模型库新增记录和原始上传目录分开保留。更新研究、README、PROGRESS、training/README 和工具入口。保留此前 3/1500 通信失败遗留；动作验收及参考标定与实物是否对应仍未完成。

## 实际结果

- [实测] 六模型已导入 `/home/radxa/studio-dev/state/models/`，原生合同检查及一次零输入前向计算 6/6 通过；ONNX 和所有被导入的合同/执行文件 SHA 与原文件一致，六模型 HOME/P/关节次序签名相同。
- [实测] `/etc/robot/feetech-ft5/robotd.toml` 和 `hd1910-calibration.toml` 已写入并回读 SHA；配置备份为 `/etc/robot/feetech-ft5/backup-before-reference-20261031T151401297666Z/`。参考数值不变，动作/验证标志保持 false。
- 首次导入脚本误假定状态目录是 `/var/lib/microduck-studio`，在任何模型/配置写入前断言退出；改用已安装 Studio 的 `default_state_dir()` 后成功，实际为程序目录下 `state/`。未改 Studio 或 robotd 源码，未改变所选方案。
- [实测] 安装后 robotd inactive/disabled，原 service 仍含 `--read-only`，Studio active；本轮没有启动 robotd、读写串口或动作。证据见[研究](../../references/b-feetech-policy-deployment-20261024/research.md)中的导入、安装和最终回读 JSON。
