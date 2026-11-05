# software 目录索引

本机运行软件适配、补丁与部署资料。上游只读参考仍在 [references](../references/README.md)，采购、烧录依赖和开发辅助在 [tools](../tools/README.md)。

| 入口 | 内容 |
|---|---|
| [servo-web/](servo-web/SOURCE.md) | servo-web 可部署工作副本（当前 0.15.3） |
| [robotd-recovery/](robotd-recovery/README.md) | 躺姿起身补丁、部署与验收 |
| [robotd-v03/](robotd-v03/README.md) | v0.3 补丁历史；通信补丁已撤回，Studio 适配保留 |
| [robotd/](robotd/README.md) | robotd 补丁与版本入口索引 |
| [studio/](studio/README.md) | Studio 显示、标定交接适配索引 |
| [deploy/](deploy/README.md) | 板侧部署约定与服务入口 |
| [policies/](policies/README.md) | 外部策略来源、契约与清单入口 |

## 边界

- 补丁目录不等于完整软件源码；部署版本、撤回项和板侧状态以各入口为准。
- 不修改 `references/` 只读参考库；需要改上游时用工作副本。
- 部署路径、密钥和真实 API 配置不写入版本库。
