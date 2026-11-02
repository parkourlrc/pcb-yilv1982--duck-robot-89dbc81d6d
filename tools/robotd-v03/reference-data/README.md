# 六模型参考数据与本机配置

> **2026-11-01 本机适用性更新**：此目录的参考机零位不能继续作为本机已做 2048 中位校准后的动作零位。经用户批准，真机 15 个 `zero_raw` 已改为 2048，原生回读通过；最新 IMU 标定及动作保护保留。共同14个站姿目标计算一致；用户随后已正式写入本机标定并有保持回读，六模型也已加载，实际模型动作未测试。见[对比、部署和限制](../../../docs/references/b-feetech-policy-deployment-20261024/studio-home-target-mismatch-20261101.md)。下文文件与标志仅为 10-31 导入快照，不是当前实时值，不能整体覆盖回真机。

2026-10-31 用户明确要求“按参考项目的数据来”。原件来自已下载的 kissqy R17 包；来源、压缩包及逐文件 SHA 见 [source.json](source.json)。原生代码 Apache-2.0，模型个人非商业许可沿用板上原始模型目录的 `POLICIES-LICENSE.txt`。

| 文件 | 用途 |
|---|---|
| `robotd-profile.toml` | 配套运行配置原件，含六个普通足部模型和一个额外滑轮技能；不整体执行 |
| `hd1910-calibration.robot.toml` | `duck-10e4` 标定原件，不能将其中验证标志当作本机验收 |
| `robot-calibration-source.json` | 作者标定来源记录原件 |
| `robotd.local.toml` | 本次实际写入 Radxa 的六模型配置快照，模型路径为 Studio 导入后的路径 |
| `hd1910-calibration.local.toml` | 本次写入的参考标定副本；数值保留，动作和本机验证标志关闭 |

walk 基础运行幅度为 1.0、头/腿滤波为 0.5/0.7，来自原模型 `deployment-execution.json`；控制器优先读取该覆盖，不再叠乘全局 0.7。训练合同本身仍是 1.0/1.0/1.0。电压补偿等实时倍率属于另一步，不能把基础幅度写成所有工况最终倍率。其他模型沿用各自合同、技能配置；全局头腿滤波明确为 1.0。

本机与原件的区别：六槽路径改为 Studio 模型库；删除额外滑轮技能；不复制原件 `[safety]`；保留 feetech/legacy 数据配置和 audio 关闭；该配置名不规定 READ 次序，2026-11-01 通信 binary 已恢复原版，对当前 Ft6 使用混合 SYNC_READ。`policy.enabled=false`，标定 `motion_enabled=false`、`imu_mount_verified=false`，15 个 `calibrated=false`。这是参考数值导入，不是本机完成标定或动作验收；没有写 EEPROM。

导入脚本：[import-reference-data.py](../deploy/import-reference-data.py) 使用现成 Studio 解包/验证实现；[install-reference-data.py](../deploy/install-reference-data.py) 备份后写入配置，不启动服务。实际模型身份、SHA、预检结果和备份路径见[统一研究](../../../docs/references/b-feetech-policy-deployment-20261024/research.md)。原始上传目录仍在 `/home/radxa/duck-policies/hd1910-20261031/`。

回退：保持 robotd 停止，从 `/etc/robot/feetech-ft5/backup-before-reference-20261031T151401297666Z/robotd.toml` 恢复旧配置。本次此前没有标定文件，旧配置不引用新增标定；原件和导入的模型可保留追溯，不需要删除。
