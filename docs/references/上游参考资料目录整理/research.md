# 上游参考资料目录整理

日期：2026-10-10。用户要求：将根目录三个 `microduck-*` 目录放入英文命名的参考资料目录。本次采用 **`references/`**，区别于本项目调研记录目录 `docs/references/`。

## 目录映射

| 原根目录路径 | 当前路径 | 保持不变的文件数 |
|---|---|---:|
| `microduck-build-tutorial/` | `references/microduck-build-tutorial/` | 141 |
| `microduck-replica/` | `references/microduck-replica/` | 518 |
| `microduck-community-kit/` | `references/microduck-community-kit/` | 3580 |

上表原路径仅为迁移历史，不是当前入口。新总入口：[references/README.md](../../../references/README.md)。

## 执行与边界

- 移动前核验全部源/目标的绝对路径位于当前工作区，目标不存在；检查源树无符号链接/目录联接，然后用 PowerShell `Move-Item -LiteralPath` 整体移动。
- 三个参考库**内部文件不编辑**，原目录结构、许可证和本地已有忽略文件一并保留；本机脚本、目录导航与链接在参考库外更新。
- `local-changes/` 的历史提取件没有移动；其中的文件内容不改。仅其 README 更新上游所在位置和恢复边界。
- 更新根 `AGENTS.md`、README、BOM、PROGRESS、知识入口、相关文档/固件校验说明和训练脚本中的参考目录定位。
- 历史 `a-training-validation.json` 的机器路径保留为原始证据，不虚构当前训练已运行。源库导入清单保留原 `destination` 与哈希，另外补充 `current_destination` 和迁移日期。
- A 训练文档中的已提取源码入口改指向实际存在的 `local-changes/` 存档；训练环境和旧机器路径仍须另行配置。

## 验证

- 4239 个迁移文件逐一比较相对路径、大小和 SHA-256，内容全部一致（包括原目录中的本地忽略文件）。摘要见 [verification.json](./verification.json)。
- 比较 Git 索引中旧路径与新路径的 mode/blob 标识，4146 个已跟踪文件均为纯路径移动；其余 93 个本地忽略文件随目录保留，但未顺带提交。
- 本次新增/修改 Markdown 的 152 个本地链接全部有效；另检查参考库内部 420 个链接，未引入新断链。工具许可证副本及历史提取源码有 32 处既有断链，保持原件，不在本次重写。
- 两个 Bash 脚本的独立 `bash -n` 与 `--help` 均通过；固件 HEX 离线长度（10724 bytes）与 SHA-256 校验通过。未启动训练、未连接或刷写硬件。
- 执行 `git diff --check`；按项目规则提交并推送当前分支的上游。

## 限制

本次只整理目录，不代表上游缺失源码已经补齐，也不证明历史 WSL、训练日志、虚拟环境或硬件状态在当前机器存在。上游库内硬编码路径保持原样，运行前应在获授权的工作副本中按环境处理。
