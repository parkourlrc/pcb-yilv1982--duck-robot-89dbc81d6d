# 训练档案实施记录

日期：2026-11-09（Asia/Shanghai）。用户明确授权实施；默认不提交、不推送，不启动正式策略优化。

## 已实现

- `experiment_config.py`统一67字段及奖励目录，前后端同源；锁定物理、接口、网络、终止与验收规则。阶段覆盖后应用分段常数进度配方，原状态续训沿用已消费更新。
- `experiment_archive.py`和dashboard统一启动前登记；受管档案位于Git忽略的`training/artifacts/`，SQLite从耐久记录重建。`training/records/`另留脱敏任务、配置、完整流程及结果摘要。
- 从零派生保留来源冻结运行时；旧v1用外置适配器。接权重严格比较transfer合同并继承rank0 actor/normalizer；恢复使用原实验账本。旧版本缺合同明确限制能力。
- 平台与CLI提供任务/实验/运行档案、参数差异、奖励与历史原文、曲线、产物、回放及三类训练入口。失败、中断、断连、同步失败和缺项分别记录；终态部分缓存继续重试，不提前封存完整。
- 历史导入保留源文件、按路径稳定ID幂等，镜像关联；本地训练目录、专题、相关Spec和实施验证证据已盘点。远端尚未完整扫描，记录数不是独立实验数。

## 验证证据

[本机实测] `checks/backend-contract.json`：12项纯合同检查、0训练，覆盖登记先于启动、锁定/非法参数、父档案不改、接权重合同、续训账本、文件白名单、封存篡改阻断训练/回放、终态待同步不封存及CLI重试、SQLite重建。

[本机实测] `checks/runtime-fixed-input.json`：基础奖励最大绝对误差约1.19e-7，四组足部配方误差小于1e-9；9类非法配置拒绝。物理/接口来源不因奖励配置化修改。

[本机实测] `checks/gpu-96-verification.json`：预登记4环境×8步，scratch1更新32转换、原状态续训1更新32转换、warm新实验1更新32转换，总96转换。actor/normalizer继承、critic/optimizer/探索重置及预算核验通过；未执行dev9、未追加正式策略优化。短回放输出49帧，51控制步约1.02秒触发failed=true/reason1，进程退出0；这仅验证管线，不是行为达标。

真实HTTP检查、历史盘点见`checks/http-contract.json`与`checks/history-inventory.json`。CLI catalog/validate和直接API锁定字段拒绝检查未启动训练。

最终8766真实HTTP独立验收：67字段、3任务去重、8个档案、23份历史奖励来源归属及实际GET非空；legacy为partial（10缺项、0完整性错误），允许scratch/replay，不允许原预算续训。盘点56条加既有legacy为57条平台记录，其中4条启动登记、1条已识别镜像；不是57次独立训练。56条中32条有配置、7条具备可识别冻结运行时，状态19 completed、5 failed、4 stopped、28 unknown。

随后只读遍历全部57个档案：browse57、replay4、scratch4、warm3、resume0；完整性均为partial，来源材料缺项没有因导入而升级为完整，详见`checks/history-capabilities.json`。这是当前材料能力分级，不代表上述历史全部可原状态续训。

96转换GPU验收使用当时冻结版本。此后startup归档和评估奖励配方修补只执行0更新检查，未重新运行GPU训练，不能称最终每行代码均经过真实训练。最终v3任务登记42个来源文件哈希；8766保留运行，本轮8770/8771/8772验证服务已停止。

[本机实测] `checks/startup-failure-zero.json`：故意触发初始化失败，训练更新与转换均为0，启动登记、冻结源、运行环境、日志与failure记录保留。MuJoCo本轮警告日志副本保留于`training/artifacts/implementation-checks/mujoco-warning-log.txt`，根目录日志已仅移除本轮追加。

## 限制与失败尝试

- Windows FastAPI TestClient因缺httpx不能运行，未安装新依赖；改用真实本地HTTP服务验证。
- 浏览器视觉自动化被策略阻止，未继续绕过，不能报告视觉验收通过。
- 双Spark真实新版本续训、网络断连/重连端到端没有额外真实训练验证；合成检查与真实GPU单节点检查分别标记。
- 历史缺失日志、预算、依赖、奖励结构和冻结源文件时如实partial，不用当前源码或零值补旧事实。旧v1保留原奖励来源文档与源码供读取，不伪造为新结构化配置。
- 不保证GPU逐位复现，最小验证不代表正式策略质量或实物可部署。

所有修改留工作区，未commit/push；未删历史产物。
