# 现成控制器来源快照

- 获取日期：2026-10-31（北京时间）。
- 用途：核实能调用六个 HD1910 模型的现成网页控制器、模型导入协议、安装要求和 IMU 读取方式。
- 证据等级：原作者仓库/Release 源码与说明；不是本机控制器运行验收。

## 发布身份

- `replica-releases.json`：GitHub `GET https://api.github.com/repos/fanhao375/microduck-replica/releases?per_page=5` 返回的发布记录。
- 已查询到的软件修订 `microduck-software-v2026.10.3101`，发布时间 `2026-10-31T10:57:26Z`（北京时间 18:57:26）；源码提交 `3952471a8394c8b720817d2160ffd95ce5a54456`，见 `replica-release-commit.json`。
- `latest-release.json`：GitHub `releases/latest` 指向的是 `microduck-replica-image-20261027` 整机镜像。这与最新软件修订是两类发布，不能用该端点把 10-31 软件更新误判为不存在。
- Release 来源：`https://github.com/fanhao375/microduck-replica/releases/tag/microduck-software-v2026.10.3101`。
- `bootstrap-README.txt`、`README.txt`、`runtime-provenance.json`：来自上述 Release 同名附件；SHA-256 均与 GitHub 资产 digest 一致。
- 配套原生程序：robotd 构建 `0791fcd-feetech-qinmo-control.47`；公开源码导出提交 `27d7921dbcb280bd7d6ba3e9937624f1e2e61d23`，来源 `https://github.com/fanhao375/Microduck-kissqy`。公开导出与原嵌入构建提交不是同一个 Git 身份，边界见 provenance。

## 文件来源与定位

Studio 文件通过 GitHub Contents API 的 `ref=3952471a8394c8b720817d2160ffd95ce5a54456` 获取并原样解码保存；原生源码的 ref 为 `27d7921dbcb280bd7d6ba3e9937624f1e2e61d23`。

| 本地文件 | 原仓路径／关键定位 |
|---|---|
| `studio-README.md` | `software/studio/README.md`；网页端口 8000、模型管理、运行方式、Python 3.13 |
| `studio-model_package.py` | `software/studio/studio/model_package.py`；`REQUIRED`、`_contract_basics`、`_recommended_slot`、`extract_package` |
| `studio-models.py` | `software/studio/studio/models.py`；`SLOTS/SKILLS/DEFAULT_KEYS`、`_check_compatibility`、`_wait_loaded`、`_select` |
| `studio-imu.py` | `software/studio/studio/imu.py`；legacy/qinmo 与协议、安装方向绑定 |
| `studio-INSTALL-api.md` | `software/studio/deploy/INSTALL.md`；“镜像里 vs 手动装”、root helper 安装、固定目录和服务 |
| `studio-install-api.sh` | `software/studio/deploy/install.sh`；只安装 helper/drop-in/sudoers，不创建完整 robotd 基线 |
| `microduck-studio-api.service` | `software/studio/deploy/microduck-studio.service`；用户 radxa、端口 8000、服务入口 |
| `controller-feetech.rs` | `microduck-hd1910/firmware/duck-control/src/feetech.rs`；`telemetry`/`telemetry_partial`（约 870–904 行）：Feetech IMU 走混合 SYNC_READ，DXL2 分支另走单播读 |
| `controller-feetech_imu_observation.rs` | 同目录 `feetech_imu_observation.rs`；IMU 观测元数据 |
| `controller-imu.rs` | 同目录 `imu.rs`；原始 IMU 块与姿态解析 |
| `controller-bus.rs` | 同目录 `bus.rs`；这是 XL330/Dynamixel 后端，不能据此判断本机飞特读取方式；本轮已改查 feetech.rs |
| `replica-release-tree.json` / `controller-source-tree.json` | 两个固定提交的 Git tree API 原始索引；用于定位文件 |
| `replica-LICENSE` / `controller-LICENSE` | 两仓对应固定提交的根 LICENSE / firmware/LICENSE；源码许可不替代模型个人非商业许可 |

精确逐文件 SHA-256 见 `source-files-sha256.json`。

## 未成功的请求与限制

- web 工具的搜索、网页打开未返回可用正文；改用 GitHub 官方 API 和 Release 附件取得原始资料，未用搜索摘要补造内容。
- raw.githubusercontent.com 批量直读长时间无响应，已中止该命令；空的 `studio-INSTALL.md` 未作为证据保留，使用 API 取得的 `studio-INSTALL-api.md`。没有继续执行下载命令或安装脚本。
- 本轮未下载/安装新镜像、bootstrap 大包或新 robotd 二进制，未修改任何原生运行程序，未验证该控制器在本机上的推理或动作。上传行为与控制器适配分开记载。
