# Studio 适配索引

- **3D显示来源（2026-11-06）**：[部署版本模型与加载源码快照](model-source-2026103101/README.md)，从部署固定提交恢复，包含model.json、meshes.bin、duck3d.js及worker；用于[第⑤步训练工具](../../docs/specs/20261106-训练可视化工具/spec.md)，尚未接入回放。

Studio 显示、标定交接与站姿零位适配主要在 [robotd-v03/studio-handover](../robotd-v03/studio-handover/README.md)，状态与撤回边界见 [robotd-v03 README](../robotd-v03/README.md)。

- 当前板侧为原版 robotd/Studio 运行；v0.3 通信补丁已撤回。
- 六模型导入、站姿零位对齐和标定交接记录见 [飞特策略模型上机核对](../../docs/references/飞特策略模型上机核对/research.md)。
- 显示适配不等于动作或承重验收。
