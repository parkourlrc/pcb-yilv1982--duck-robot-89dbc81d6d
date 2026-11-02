# 网页手柄模型加载配置

2026-11-01 用户要求先用网页手柄并核对六模型；确认托稳后，已将主控 `/etc/robot/feetech-ft5/robotd.toml` 中 `[policy] enabled` 从 false 改为 true。没有修改模型、参数、标定、按键映射、通信或源码。此目录是本项目部署工具，不是上游改版。

- `enable-policy-loading.py`：在 helper 同一锁下备份配置、原子修改一个字段、重启 robotd、读取加载/绑定及卸力状态。源码验证 `torque_state_confirmed=false` 表示已确认扭矩关闭，null 才是未知。记录存在时拒绝重复运行。
- 当前已部署至 `/home/radxa/webpad-policy-enable-20261101-attempt2/`；`deployment.json` 为成功记录，仓库对应证据见下方。
- 首次实现误读上述三态字段，导致成功加载后自动回退；原脚本及证据已保留，不删除或伪称第一次即通过。修正版未放松卸力要求，也没有修改任何原生保护。
- 当前加载开关 true；动态动作开关仍 false、确认卸力，六模型已加载、五绑定无错。robotd/Studio active/enabled。重启始终先卸力，用户需显式站起/开始走；本工具不代执行。
- 最终配置备份：`/etc/robot/feetech-ft5/backup-before-webpad-policy-20261101T080359146909Z/`。若将来回退，须先查当时用户动作/支撑、并发参数与标定，不能直接覆盖整份旧文件。

网页入口 `http://192.168.1.35:8000/#/pad` 无需蓝牙配对。图中 A=地面捡取、X=前滚翻、LB/RB=左右脚踢、十字键下=起坐。键盘 W/S 前后、A/D 平移、Q/E 转向；Esc 松开速度输入，空格／Select 为卸力。

- [需求、授权与方案](../../../docs/specs/20261101-webpad-policy-enable/spec.md)
- [研究、来源与全部证据](../../../docs/references/b-feetech-policy-deployment-20261024/webpad-models-check-20261101.md)
- [成功部署记录](../../../docs/references/b-feetech-policy-deployment-20261024/webpad-policy-enable-final-20261101.json)
- [网页最终回读](../../../docs/references/b-feetech-policy-deployment-20261024/webpad-page-final-20261101.json)

仅完成模型加载和控制入口验收，尚未进行模型动作及其实时性能验收。未提交或推送。
