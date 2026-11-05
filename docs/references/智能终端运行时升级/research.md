# DSH 运行时更新：0.1.6-alpha.1 → 0.2.1-alpha.2（2026-10-14）

## 问题与范围

用户指示「更新 dsh」。范围是本机（WSL、Ubuntu、用户 `yilv`）的 DeepSeek Harness 运行时及其 `~/.dsh` profile 插件，不涉及 duck-robot 项目本身的物料/接线结论。本文记录更新前的受限条件、用户决定、已执行动作、验证证据、尚未完成项与回退路径。

## 结论速览

| 项 | 结果 | 证据等级 |
|---|---|---|
| 更新前版本 | `0.1.6-alpha.1`，装在 `/usr/local/lib/node_modules/@deepseek-ai/dsh`（属主 `root:root`，不可写） | 本机实测 |
| 原地升级可行性 | **不可行**：`sudo` 被 `no new privileges` 拦截，无法取得 root | 本机实测 |
| 选定方案 | 用户级安装 `~/.local`（用户确认），版本 `0.2.1-alpha.2`（用户确认，alpha 通道） | 用户确认 |
| 更新结果 | `~/.local/bin/dsh --version` = `0.2.1-alpha.2`；`which -a dsh` 首选 `~/.local/bin/dsh` | 本机实测 |
| 旧版保留 | `/usr/local/bin/dsh`（0.1.6）原样未动，可作回退 | 本机实测 |
| 生效条件 | **需重启 `dsh web`**；本次未自动重启，以免中断当前会话 | 本机实测 |
| 插件兼容 | `dsh-routing-suite@0.1.2` 正常；`dsh-watcher@0.4.0-insights.1` 被判定不兼容并跳过，已按其上游 npm `0.8.0` 升级（用户确认） | 本机实测 |

## 更新前的现状与约束

- **运行实例**：PID 916 `node /usr/local/bin/dsh web`，父进程 723 为交互 `-bash`（本次对话即由该实例托管）。
- **权限**：`/usr/local/lib/node_modules` 属主 `ubuntu:lxd`、`@deepseek-ai/dsh` 属主 `root:root`，均为 `drwxr-xr-x`；当前用户 `yilv`(uid 1001, gid 1002, 属 sudo 组) 无写权限，且 `sudo` 报 `The "no new privileges" flag is set` 不可用。
- **可更新到**：`latest`/`next` = `0.2.0-rc.2`（2026-09-29 发布）；`alpha` = `0.2.1-alpha.2`（2026-10-09 发布）。
- **npm 缓存故障**：`~/.npm/_cacache` 混有 root 属主文件，任何 npm 操作报 EACCES；本次改用 `--cache /tmp/npm-cache-dsh` 绕过，**根因未修**（需 root `chown`）。
- **PATH**：`/home/yilv/.local/bin` 位于 PATH 首位，且原先没有 `dsh`，因此用户级安装可直接接管命令解析，无需改动 shell 配置。

## 用户决定（2026-10-14）

1. 更新到 `0.2.1-alpha.2`（alpha 通道，而非 latest 的 `0.2.0-rc.2`）。
2. 安装到用户级 `~/.local`，不尝试取得 root。
3. `dsh-watcher` 升级到 npm 上的 `0.8.0`。

## 已执行动作与验证

1. **安装**：`npm install -g --prefix ~/.local @deepseek-ai/dsh@0.2.1-alpha.2`（临时缓存）→ 新增 561 个包，退出码 0。
   - 验证：`~/.local/bin/dsh --version` → `0.2.1-alpha.2`；`which -a dsh` → `~/.local/bin/dsh` 优先，`/usr/local/bin/dsh` 仍在。
2. **原生模块**：npm 11.17 的 `allow-scripts` 拦下 5 个包的安装脚本（`@deepseek-ai/dsh-subprocess-local`、`koffi`、`node-pty`、`@google/genai`、`protobufjs`）。
   - 核实（本机实测）：`node-pty` 自带 `prebuilds/linux-x64/pty.node`，`koffi` 走 `@koromix/koffi-linux-x64` 预编译件，二者在 Node v24.19.0 下 `require` 成功；`dsh-subprocess-local` 的 postinstall 只是给 `node-pty` 的 `spawn-helper` 补可执行位，而新旧两份安装都不存在该文件 → **判定无功能回归**，未重装。
3. **隔离验证**：在 `DSH_HOME=/tmp/dsh-verify-home`（复制真实 `web` profile）用新 CLI 实测：
   - `--profile web --dump-config` 退出码 0，配置 1227 行；
   - 真实启动成功并打印 `dsh web: http://127.0.0.1:37759/?token=…`，HTTP 请求返回 303，页面正常响应。
4. **模块解析机制变化（重要）**：0.1.6 会在 `~/.dsh/profiles/node_modules` 建立指向全局安装的符号链接农场；0.2.1 不再依赖它——把 `@deepseek-ai/dsh-base` 链接改成**悬空路径**后仍能正常启动。
   - 结论：真实 `~/.dsh` 中遗留的、指向 `/usr/local` 旧包的链接**无害，无需手工清理**。
   - 另：新版启动会删除 `~/.dsh/profiles/web/.dsh-module-fallback`（旧版投影目录），该动作在隔离副本中已按其设计完成。
5. **插件兼容与处置**：
   - `dsh-routing-suite@0.1.2`：正常组装进配置。
   - `dsh-watcher@0.4.0-insights.1`（本地定制 tarball，sha512 与 npm 同名版本**不同**，即非 npm 同名产物）：因 peerDependencies 要求 `^0.1.2-rc.1` 的 `@deepseek-ai/dsh-client-ui-*` / `dsh-session*` 系列，被 0.2.1-alpha.2 判定不兼容并**跳过**（仅警告，不阻断启动）。
   - 实测 npm `dsh-watcher@0.8.0`（2026-10-08 发布，上游 `github.com/aa2246740/dsh-watcher`）被 `0.2.1-alpha.2` **接受**（无跳过提示）。
   - 已对真实 profile 执行 `dsh plugin --profile web add dsh-watcher@0.8.0`：`~/.dsh/profiles/web/package.json` 中 `file:/home/yilv/.dsh/plugins-src/…0.4.0-insights.1.tgz` → `0.8.0`，`node_modules/dsh-watcher` 版本为 `0.8.0`。

## 尚未完成 / 限制

- **真实实例尚未重启**：新版本要生效，需停止 PID 916（其终端 Ctrl+C）后重新运行 `dsh web`。本次未自动重启，以免中断正在进行的会话。
- 真实 `~/.dsh` 的 `--dump-config` 未在沙箱内跑完：被本机文件沙箱拦在删除 `.dsh-module-fallback` 上（EACCES，非真实权限问题）。该清理会在重启时由新 CLI 自动完成。
- `0.2.1-alpha.2` 属 alpha 通道，未做长时运行验证。
- `~/.npm` 的 root 属主缓存未修，今后 npm 操作仍需临时缓存或 root `chown`。
- 未改动 `/usr/local` 下任何文件；`references/` 三个只读参考库未动。

## 回退路径

- 回到旧运行时：显式运行 `/usr/local/bin/dsh web`（0.1.6-alpha.1 完整保留），或 `rm ~/.local/bin/dsh` 让命令解析回到 `/usr/local/bin`。
- 回到旧插件：`dsh plugin --profile web add file:/home/yilv/.dsh/plugins-src/dsh-watcher/dsh-watcher-0.4.0-insights.1.tgz`（旧 tarball 已原样保留）。注意该定制版在 0.2.1 下会被跳过，若要在 0.2.1 上强跑需按官方提示授权豁免：`dsh plugin --profile web allow-version dsh-watcher@0.4.0-insights.1 --dsh-version 0.2.1-alpha.2 --accept-risk`（官方警告可能崩溃或数据丢失）。
- 变更前 profile 清单快照：`/tmp/web-package.before.json`（临时目录，重启即失；需要时按上面命令重建）。

## 来源

- 本机命令输出（2026-10-14）：`npm view`、`which -a`、`ps`、`ls -l`、`node -e require` 冒烟、隔离 `DSH_HOME` 的启动日志与 HTTP 响应、`diff` profile 清单。
- npm registry：`@deepseek-ai/dsh` dist-tags（`latest`/`next` = 0.2.0-rc.2、`alpha` = 0.2.1-alpha.2）与发布时间；`dsh-watcher` versions / dist-tags（`latest` = 0.8.0）与 peerDependencies。
- 上游仓库：`github.com/aa2246740/dsh-watcher`（插件来源）、`github.com/deepseek-ai/deepseek-harness`（CLI `package.json` 的 repository 字段）。
- 包内文档：`@deepseek-ai/dsh-plugin-manager/README.md` 第 72–75 行（版本豁免与组合生效语义）。
