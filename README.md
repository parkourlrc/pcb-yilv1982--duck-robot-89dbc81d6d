# duck-robot

MicroDuck 小型双足机器人的个人复刻项目。当前主线为**方案 C（社区套件，飞特 HD-1910-C001）**；组织原则是“硬件复刻与整机集成 → 核心硬件自主设计；运行软件参考适配；训练环境自主建设”。A/B 仅作来源与回退标签，不作为整个项目的一级分类。

**当前状态（2026-11-05）**
- **整机**：M1 已完成（用户确认 2026-11-05）：新单 3P 口 IMU 已换装、15 颗舵机标定完成；IMU 间歇缺答/行走摔倒转可靠性跟踪。
- **自主 HAT**：B.0 / `84362651` 已付款5片；[工厂MK701/Y701方向确认](docs/references/扩展板乙版降本/engineering-feedback/research.md)已核对，待用户回复；**研发继续暂停**，未确认发货，首板未验收，原750元目标未达成。
- **PCB 全流程**：M3 进行中，B.0 / `84362651`、Y10／SMT2611051346 已付款，等待回寄与上机测试。
- **训练**：M2 已完成（官方模型上机+基本动作，用户确认）；M4 自训进行中，自训策略尚未上机。
- **里程碑**：M1/M2 已闭环；M3 PCB 全流程进行中（已下单，待回寄/上机）；M4 自训进行中；见 [MILESTONES](MILESTONES.md)。

详见 [PROGRESS](PROGRESS.md)；物料与缺口见 [BOM](BOM.md)。

## 入口

| 文档 | 用途 |
|---|---|
| [AGENTS.md](AGENTS.md) | 项目规则、目录边界与协作要求；开始前先读 |
| [PROGRESS.md](PROGRESS.md) | 当前状态、阻塞、待办与按时间倒序的记录 |
| [BOM.md](BOM.md) | C 线物料、数量与采购状态 |
| [MILESTONES.md](MILESTONES.md) | 8 个里程碑、验收标准与当前状态 |
| [docs/pcb-production-runbook.md](docs/pcb-production-runbook.md) | PCB 从需求到回寄上机的逐步运行手册 |
| [docs/README.md](docs/README.md) | 方案、测试单、图纸、照片与研究索引 |
| [hardware/README.md](hardware/README.md) | 复刻整机、取电板与自主 HAT |
| [software/README.md](software/README.md) | 本机软件适配、robotd/Studio 与部署索引 |
| [tools/README.md](tools/README.md) | 嘉立创下单、烧录依赖与开发辅助 |
| [scripts/README.md](scripts/README.md) | 跨域维护与诊断脚本 |
| [duck-robot-training](https://gitee.com/yilv1982/duck-robot-training) | 自建 real2sim2real 训练工程与资料（2026-11-10 拆分） |
| [flash/README.md](flash/README.md) | IMU 固件与烧录 |
| [references/README.md](references/README.md) | 三个上游参考库（只读） |

## 三条主线

### 1. 硬件复刻与整机集成

整机基线、装配与接线以 [hardware/replica](hardware/replica/README.md)、[BOM](BOM.md) 和 [PROGRESS](PROGRESS.md) 为准。当前 C 线为 kissqy HAT（REVA）＋新单 3P 口 IMU＋15 颗 HD-1910-C001；白色 HAT V1.2 与旧 GD32/v0.3 板仅作历史。供电按 [v2 架构](docs/power-architecture-v2.md) 的讨论基线，实物复核见[供电与扩展板实物复核](docs/references/供电与扩展板实物复核/research.md)；旧的 [HAT V1.2 测试单](docs/hat-v1.2-test.md) 不自动套用到当前板。

### 2. 核心硬件自主设计

自主 HAT 工作区在 [hardware/custom_hat](hardware/custom_hat/README.md)：现行 B.0 源 `84362651`，2026-11-05 已付款 5 片、线路暂停，首板未验收；A.1 与旧检查点在 `rev_a`、`归档` 前缀中保留。方法与复盘见[研发流程](docs/hardware-module-development-workflow.md)、[阶段复盘](docs/references/自主扩展板阶段复盘/research.md)。报价、制造放行与实物验收分开记录。

### 3. 软件适配与训练

servo-web 工作副本在 [software/servo-web](software/servo-web/SOURCE.md)；robotd 补丁见 [software/robotd-recovery](software/robotd-recovery/README.md) 与 [software/robotd-v03](software/robotd-v03/README.md)（通信补丁已撤回，Studio 适配保留）。训练工程见 [training](training/README.md)，阶段计划见 [real2sim2real 工具链](docs/real2sim2real-toolchain-plan.md)。

## 并行参考库（只读）

三套开源资料统一存放在 [references/](references/README.md)，本项目调研结论放在 [docs/references/](docs/references/README.md)。三套库只读，不修改、不合并代码、硬件配置或采购清单；历史混入的本地修改已提取到 [local-changes/](local-changes/README.md)。

| 方案 | 本地入口 | 参考内容 |
| :--- | :--- | :--- |
| A：帆哥教程 | [microduck-build-tutorial](references/microduck-build-tutorial/README.md) | Pi Zero 2 W / OpenRB / XL330 路线（回退线，基线已存档） |
| B：fanhao375 复刻研究 | [microduck-replica](references/microduck-replica/README.md) | 机械装配、电控与调试资料；兼论 XL330 与飞特路线 |
| C：jyg9 社区套件 | [microduck-community-kit](references/microduck-community-kit/README.md) | **主参考**：imu_to_dxl / banana_pcb / dxl_hub 三块板、GD32 固件与升级工具、robotd 飞特补丁、HLS 舵机调试器 |

- 方案 B 遵循其 [LICENSE](references/microduck-replica/LICENSE) 与 [NOTICE](references/microduck-replica/NOTICE.md)：不同文件许可不同，不能整目录视为 Apache-2.0 或可商用；打印 CAD 已迁往上游独立仓 [microduck-replica-cad](https://github.com/fanhao375/microduck-replica-cad)。
- 方案 C 缺口（`software/microduck_feetech/` 完整源码上游未推送、真机整定值仅可参考等）见 [PROGRESS](PROGRESS.md)「方案方向」。

## 回退线与旁支

- **A 线回退**：[阶段基线](docs/route-a-baseline-20260928.md)、[A 线 BOM](docs/bom-route-a-20260928.md)、[A 训练](https://gitee.com/yilv1982/duck-robot-training/blob/main/docs/a-training.md)、[A 验收数据](docs/a-training-validation.json)、[B 训练](docs/b-training.md)。仅回退时使用。
- **旁支研究**：[消费电子玩具市场研究](docs/references/消费电子玩具市场研究/research.md)；资料保留，不列入硬件主线。
- **历史事件**：[2026-10-31～11-02 事件摘录](docs/archive/readme-events-2026-11.md)；完整记录见 PROGRESS 与各专题。

## 致谢

感谢 [AI-FanGe/Microduck-build-tutorial](https://github.com/AI-FanGe/Microduck-build-tutorial)、[Rhoban/microban](https://github.com/Rhoban/microban)、[pollen-robotics/microduck](https://github.com/pollen-robotics/microduck) 及方案 B/C 上游作者的开源工作；各参考库内容以其自带许可为准。
