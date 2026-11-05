# 部署约定与入口

- 板侧主控：Radxa Zero 3W，部署目录 `/home/radxa/`；servo-web 在 `~/servo-web/`。
- systemd 单元在 [scripts](../../scripts/README.md)：`duck-servo-web.service`、`duck-hls.service`、`duck-imuview.service`。
- 台架/装机工具清单见 [docs/bench-tools.md](../../docs/bench-tools.md)。
- 起身补丁部署与回滚见 [robotd-recovery](../robotd-recovery/README.md)；v0.3 撤回边界见 [robotd-v03](../robotd-v03/README.md)。

## 边界

- 部署前确认板型、串口占用和服务状态；不把仓库路径当作板侧路径。
- 真实凭据、API 配置和未脱敏日志不提交。
