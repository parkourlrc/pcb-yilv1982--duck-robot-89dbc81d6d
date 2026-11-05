# Studio 标定交接启动配置

2026-11-01 经用户确认部署，仅 `daemon-reload` 与原生预览；不是 v0.3 通信补丁，适用于本机已恢复原版 control.47 的现行部署。

原先基础 `robotd.service` 使用 `--read-only`，临时 `30-studio-commissioning.conf` 开启调试模式；helper 不认识该临时文件，报 `foreign_commissioning`。本副本将基础服务改为正常入口，并以 helper 正式管理的 `zzzz-zz-microduck-commissioning.conf` 保持迁移当时的标定模式。用户随后已正式提交成功：helper 删除正式覆盖并重启，进入 motion/control；此处覆盖文件现仅存档，不应重新部署。

| 文件 | 作用 |
|---|---|
| `robotd.service` | 已部署基础服务，去掉 `--read-only`，其余运行环境和保护保留 |
| `zzzz-zz-microduck-commissioning.conf` | 迁移时与原临时覆盖一致；正式交接后板上已删除，本副本只留档 |
| `install.py` | 一次性迁移，按原件哈希检查、加 helper 锁、备份、重载、核对 PID 和保护文件、原生 dry-run；不 restart/stop/start、不发扭矩或正式提交 |
| `source-manifest.json` | 本机原始服务内容、SHA、helper SHA 和候选 SHA；来源为板侧实读，不冒充上游发布文件 |

**[实测]** 板侧目录 `/home/radxa/robotd-studio-handover-20261101`。部署前后 robotd PID 1067、Studio PID 973 不变，两服务 active/enabled；helper 从 foreign 改为 commissioning，命令行与网页实际预览均通过，网页准备状态 `ready=true`。迁移开始前已是 `ready/off`，迁移后仍相同；本工具未卸力。标定、pending、中位/方向记录、主配置、总线交接覆盖、helper 和二进制哈希均未变。

备份：`/etc/robot/feetech-ft5/backup-before-studio-handover-20261101T074627191148Z/`，包含基础服务及当时全部覆盖文件。回退时必须先恢复旧 commissioning 覆盖再恢复基础服务，核对目标后移出本次正式覆盖并 daemon-reload；不重启。后续如用户已完成正式提交，不应直接重放本次安装或回退，须先检查新的状态和备份。

**正式“写进主程序”现已由用户完成**：15 个 calibrated=true、motion_enabled=true、零位2048和IMU已验证，原生 motion/control。此前预览只生成内容，不写完成标志；当前应以[后续回读](../../../docs/references/飞特策略模型上机核对/webpad-models-check-20261101.md)为准。没有修改源程序、通信判错、模型参数、保护或舵机 EEPROM。

- [Spec 与用户授权](../../../docs/specs/20261101-studio-calibration-handover/spec.md)
- [原因、截图与执行记录](../../../docs/references/飞特策略模型上机核对/studio-commit-mode-error-20261101.md)
- [部署原始证据](../../../docs/references/飞特策略模型上机核对/studio-handover-deployment-20261101.json)
- [网页真实预览与状态](../../../docs/references/飞特策略模型上机核对/studio-handover-page-preview-20261101.json)

`../deploy/robotd.service` 是 10-31 初次只读安装存档，不是当前服务文件。参考库未修改；本任务文件未提交。
