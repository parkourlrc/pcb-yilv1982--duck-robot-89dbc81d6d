# 来源与本机差异

> **2026-11-01 现行状态**：v0.3 通信补丁及改序实验均已从运行端和 WSL 工作源码撤回，板侧使用下述原始 control.47 binary；此目录保留来源、补丁和历史安装证据。Studio 显示适配与参考数据仍保留；见[当前验收](../../docs/references/飞特策略模型上机核对/restore-mixed-sync-read-20261101.md)。

- 原生源码：`https://github.com/fanhao375/Microduck-kissqy`，提交 `27d7921dbcb280bd7d6ba3e9937624f1e2e61d23`，目录 `microduck-hd1910/firmware/`。
- 源码归档（本轮获取）SHA-256：`45cd22a955f3ff68bfbcb2d4266352d92798b6d1abd87a559fd613fcd52817d1`。
- 原始 robotd 构建标识：`0791fcd-feetech-qinmo-control.47`；本机补丁标识：`0791fcd-feetech-qinmo-control.47+duck-v03.1`。
- 原生源码许可：Apache-2.0，原始 LICENSE 保存在来源快照；不替代模型的个人非商业许可。
- Studio：`https://github.com/fanhao375/microduck-replica`，`microduck-software-v2026.10.3101`，源码提交 `3952471a8394c8b720817d2160ffd95ce5a54456`。
- 软件包 SHA-256：`0502c452e7062aa29286f6a82c046ed4ceaaf8beecaa6d98958341a80c95ea77`。
- Python：Astral python-build-standalone `20261026`，CPython 3.13.18、AArch64 GNU；资产 SHA-256 `578d9da1983463ffb0c8c98ab0da2f18177f44069328eb0af847860c1eb05c3e`。来源 `https://github.com/astral-sh/python-build-standalone/releases/tag/20261026`。
- ONNX Runtime 1.28.0：先前已取得的 R17 发布包 `onnxruntime/`，保留 LICENSE、ThirdPartyNotices 和提交信息；不重新下载其他执行器模型。

原生补丁只包含 `ImuToDxl` 的遥测读取分离、相应传输回归测试和构建标识。保留原生 FT6、Qinmo、DXL2 路径、关节映射及标定/动作参数解析逻辑。

后续按用户“按参考项目的数据来”的指示，另导入六模型、配套动作参数及 `duck-10e4` 参考标定数值；来源原件、实际配置和差异见 [reference-data](reference-data/README.md)。本机标定验证和动作标志保持关闭，未再修改原生代码。

原始来源与逐文件证据见 [控制器来源快照](../../docs/references/飞特策略模型上机核对/controller-sources-20261031/SOURCES.md)。缓存下载包和源码位于 `training/logs/`（Git 忽略）；本目录的补丁、安装文件和研究证据是可复查的持久成果。

2026-10-31 经用户确认，另在 [studio-display](studio-display/README.md) 保存并部署同一固定 Studio 源包的显示适配。四个原件、五个安装文件和 SHA 分别留存；只整理 commissioning 遥测显示和新鲜度，不改原生控制器、标定或动作入口。
