# 项目目录结构分析与治理建议

日期：2026-11-05（北京时间）。状态：分析建议；P0/P1 已于同日执行，P2 部分登记。

> **2026-11-05 执行状态：** 根 README 已收敛，10-31～11-02 事件移入 `docs/archive/`；PROGRESS 已加当前摘要，并把 2026-10 及以前归档到 `docs/archive/progress-2026-10.md`；docs/hardware/tools/scripts/software 索引与 `hardware/replica/` 入口已建；`docs/references/` 已改中文专题名并补索引；`software/` 迁移已完成（servo-web、robotd-recovery、robotd-v03）；HAT 版本清单与模型清单已补；根日志已移入专题，xpack 包与根残留已登记。组件脚本暂留 `scripts/` 并按索引分类。以下保留当时分析。

## 1. 项目定位

**[用户确认]** 项目是 MicroDuck 硬件复刻；部分核心硬件在复刻完成后尝试自主设计，例如 HAT；软件参考上游，训练环境自主建设。

建议以“硬件复刻与整机集成 → 核心硬件自主设计；运行软件参考适配；训练环境自主建设”为组织原则。A/B/C 保留为来源及历史路线标签，不作为整个项目永久的一级目录分类。

复刻硬件完成不等于整机行走验收通过，更不等于自主 HAT 已制造或首板通过。训练自主仍允许既有规则授权的通用框架、公开参数和显示资产复用。

本轮检查本地目录、Git 索引与文档，不联网、不连接设备、不运行训练或工程测试；只新增分析报告。未核验上游最新状态、电路正确性或板侧即时部署。本提案不代表批准迁移。

## 2. 盘点证据

使用 `git -c core.quotepath=false ls-files`、`git status --porcelain`、目录枚举、入口阅读和路径检索。索引文件数包含已跟踪但工作区删除的文件，不包括忽略/未跟踪文件，不代表磁盘总文件数或体积。拟新增文档所在 docs/、docs/references/ 未发现补充 AGENTS.md。

| 范围 | 本地核查结果 | 依据 |
|---|---|---|
| 索引主要目录 | docs 4906，references 4147，hardware 1412，flash 1143，tools 173，training 70，scripts 65，local-changes 57，根 microduck-community-kit 41 | git ls-files 按首级路径分组 |
| 根入口 | README 88 行，PROGRESS 984 行，BOM 88 行，AGENTS 180 行；README 多行为长篇事件记录 | 文件行数；README 项目定位第31行，市场调研第80行 |
| 文档 | docs 根15个文件；docs/references 67个专题，无 README 索引 | 直属目录枚举，统计在新增本专题前 |
| 业务索引缺口 | docs/README.md、hardware/README.md、tools/README.md、scripts/README.md 不存在 | Test-Path |
| 自主 HAT | release-review 有20个子目录及20个ZIP；rev_a 有38个 production* 目录 | 直属枚举；未据此认定内容重复 |
| 烧录依赖 | flash 的1143个索引文件中1132个属于 xpack-openocd-0.12.0-7 | git ls-files flash 分组；未测体积 |
| 训练资产 | training/logs 被忽略；入口说明其中含自训产物和外部策略包 | training/.gitignore；training/README.md:3、32；未逐包核验 |
| 根参考库残留 | 41个索引文件为SDK示例、IDE设置、BIN/HEX等；references 下无同相对路径文件 | 逐路径检查；最近相关提交 ec0158b |

检查时工作区已有61条修改、30条删除、295条未跟踪状态条目；未跟踪目录可能合并为一条，不能解读为295个文件。均非本轮产出，未覆盖、恢复或混合提交。迁移实施前须重新盘点。

## 3. 问题分析

### 当前状态与历史记录混杂

**[本地核查]** README 在项目定位之前堆积部署及排障事件；PROGRESS 包含硬件、软件、训练、市场调研和工具安装流水。

状态复制已有不同步实例：README 第3行指向 B.0/84362651，第35行仍写“当前86654c03/r18”；custom_hat/README.md 第11行称 B.0 为当前开发，末段仍称“本轮修订的是 rev_a”。PROGRESS 顶部已有 Y10 物料匹配预估，其他部分入口仍要求继续进入物料匹配。只记录文档差异，不重新核定报价。

**[推断]** 重复维护当前状态增加误读旧版本的风险；并发修改及历史窗口保留也是可能原因，不能把所有差异认定为工程错误。建议根 README 只保留定位与导航，PROGRESS 保留当前摘要/阻塞/下一步，历史转按月档案；组件版本只在组件入口维护。

### 复刻整机缺少统一入口

**[本地核查]** hardware 主要有 banana_pcb 和 custom_hat，装机来源、装配、接线及版本分散在 BOM、PROGRESS、照片及原理图索引。docs/schematics 是上游证据副本，hardware 是可写工程，此边界应保留。

建议增加 hardware/README.md 和 hardware/replica/README.md，汇总装机基线、来源/版本、装配、接线、验证状态与证据链接。初期只做索引，不复制原图或原理图；custom_hat 独立表示自主设计，不能冒充已装机板。banana_pcb 首轮保留路径，后续才考虑移入 replica。

### tools/scripts 已混入运行产品

**[本地核查]** software/servo-web 是可部署工作副本；robotd-recovery 是已部署适配；robotd-v03 同时包含已撤回通信补丁和仍保留的 Studio 显示/交接适配。scripts 混放服务单元、设备诊断、历史补丁、图片生成和市场报告脚本。

建议新增 software，按 servo-web、robotd、studio、deploy、policies 管理本机适配与运行资料；tools 留采购、烧录依赖和开发辅助。scripts 只留跨域维护/文档生成，组件专属脚本随组件。

robotd-v03 不得整包归档，须先区分仍用与撤回部分；补丁目录不等于完整软件源码已在仓库。custom_hat/software 的板卡专属驱动暂留组件内，由 software 入口链接。

### 自主训练与外部模型身份不够直观

**[本地核查]** training 已有 params、models、mjlab_duck、duckstand、scripts 和回放入口，基础结构可保留；logs 存放两类不同来源的模型，且默认 checkpoint 使用固定路径。

建议先增加版本化产物清单：来源（自训/外部）、哈希、配置、观测动作契约、硬件适配、验证状态、位置及恢复方法。外部候选策略长期由 software/policies 管清单，权重可放忽略的数据目录；迁移前查调用点，不顺带替换或重建训练环境。

### 硬件版本与交付包需要状态管理

**[本地核查]** custom_hat 并存历史骨架、rev_a/rev_b、候选、拼板、报价及交付包，部分已有停用提示，但目录名不能直接说明可否使用。

建议清单绑定“版本→源哈希→导出包→用途→验证证据→替代关系”，区分开发、报价候选、制造获准、历史/撤回。报价不是制造放行。后续才整理各版本内部的 source/checks/exports/archive，先不移动 KiCad 工程与库；旧 ZIP、展开目录和验证数据未经比对均保留。

### 研究证据缺少索引，旧路径不能盲删

references 与 docs/references 职责不同，前者上游只读，后者本机研究证据。建议先保留路径，补主题索引，以复刻、自主HAT、软件、训练、工具、旁支研究分组，并标现行/历史/待确认和替代关系。市场研究移出根主线入口，资料保留；不必立即另建仓库。

根 microduck-community-kit 的41个文件不是已证实的重复物：references 下无同路径副本。需查来源及其他位置副本，不能直接删除或自动写回只读库。根三份已跟踪日志应关联排障专题。OpenOCD 完整发行包可能用于离线烧录，先登记来源/版本/校验/许可，再决定保留策略，不因文件多就移除。

## 4. 目标结构草案

以下为建议，分批落实；无实际内容时不预建空目录。

```text
duck-robot/
├── README.md / AGENTS.md / PROGRESS.md / BOM.md
├── hardware/
│   ├── README.md
│   ├── replica/              复刻整机基线入口
│   ├── banana_pcb/           首轮保留工作副本位置
│   └── custom_hat/           自主HAT及板卡专属驱动
├── software/
│   ├── servo-web/
│   ├── robotd/               补丁、版本与构建依据
│   ├── studio/               本机显示及标定交接适配
│   ├── deploy/               部署说明和模板
│   └── policies/             外部策略来源和契约清单
├── training/                 自主模型、环境、训练与回放
├── flash/                    暂留烧录工作流及板型边界
├── tools/                    采购与开发辅助
├── scripts/                  跨域维护和文档生成
├── docs/
│   ├── README.md
│   ├── references/           研究证据，增加分类索引
│   ├── specs/
│   ├── photos/
│   ├── schematics/           上游图纸证据副本
│   ├── video-notes/
│   └── archive/              历史进度和过期指南
├── references/               上游快照，只读
└── local-changes/            历史提取件，暂留路径
```

无需立即引入庞大全局 data/assets/build 层次。板卡交付、训练产物和原始证据的生命周期不同，优先各组件就地管理；BOM.md 管当前复刻整机，板级自主 BOM 链接组件。

## 5. 执行优先级与验收

| 优先级 | 动作 | 判据 |
|---|---|---|
| P0 | 明确定位、补业务索引、收敛根README和PROGRESS、纠正重复当前状态 | 四条主线入口清楚，当前版本不冲突，旧证据可追溯 |
| P1 | software/servo-web → software/servo-web；robotd-recovery/v03 按仍用与撤回拆分归属 | 来源、部署版本和撤回项明确，路径与引用同步 |
| P1 | 建立装机基线、HAT版本/导出包清单、模型产物清单 | 装机/研发、自训/外部、报价/制造不混淆 |
| P2 | 整理旧路线文档、根日志和组件脚本；调查根参考库残留 | 原件保留，旧新路径可查，无未经判定的删除 |
| P2 | 决定工具发行包、重复导出及缓存的存储策略 | 有可恢复来源/校验，保留必要离线能力 |

第一批建议只治理入口与当前状态，不搬运行工程；第二批按组件迁移。每个迁移项记录旧/新路径、用途、权限边界、来源许可、现行状态、调用点、哈希和验证方式。只做必要链接、路径及清单检查；不顺带重训、标定、启动设备或运行无关测试。

## 6. 限制、失败与下一步

- 首次残留文件比较因 PowerShell 条件表达式写法失败，修正后重跑；最终确认41个同路径副本均不存在，未进行不存在文件的哈希比对。
- 首次报告写入没有在预期相对位置得到确认，随后使用仓库相对路径重新写入并确认；最终文件位置以 Resolve-Path 的现场结果为准。
- 未审计完整依赖图、Git对象大小、嵌套仓库、全量链接、所有包内容以及忽略数据的备份位置；未验证设备即时状态。
- 本轮按“先分析”请求只新增报告，入口冲突列为首批治理事项，不修改其他任务正在维护的工程和入口。本报告不改变现行部署、制造或接线许可。
- 真正实施按项目 Spec 流程确认治理范围和迁移方案。用户尚未批准上述结构；flash 是否长期独立等细节可在方案阶段确定。
- 本轮未提交或推送；已有工作区改动保持原状。

## 7. 来源入口

- [项目规则](../../../AGENTS.md)、[总览](../../../README.md)、[进度](../../../PROGRESS.md)、[BOM](../../../BOM.md)。
- [上游参考库](../../../references/README.md)、[历史迁移记录](../上游参考资料目录整理/research.md)、[本地提取件](../../../local-changes/README.md)。
- [自主HAT](../../../hardware/custom_hat/README.md)、[Rev B](../../../hardware/custom_hat/rev_b/README.md)、[图纸证据](../../schematics/README.md)。
- [训练](../../../training/README.md)、[烧录](../../../flash/README.md)、[servo-web来源](../../../software/servo-web/SOURCE.md)、[v03与Studio适配](../../../software/robotd-v03/README.md)、[恢复适配](../../../software/robotd-recovery/README.md)。

上述均为本地来源，不代表本轮在线核验的上游事实。
