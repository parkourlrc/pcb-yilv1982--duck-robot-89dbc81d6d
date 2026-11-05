# T110｜2026 年原生文本模型使能：Qwen3.5 小模型系列

- 研究窗口：**2026-01-01 至 2026-10-10**；来源访问日期：**2026-10-10（Asia/Shanghai）**。
- 状态：只读分析已获主会话确认，本文件按确认内容落盘；写入阶段没有新增联网搜索或抓取。
- 范围：只记录 **Qwen3.5 0.8B／2B／4B／9B** 这一条官方证据链，以 **Qwen3.5-2B 与 2025 年 Qwen3-1.7B 的同表文本指标**为主要质量证据，不扩展模型榜。
- 验证层级：官方仓库、官方模型卡、许可证正文；**不是本机实测、独立复现或商业玩具采纳证据**。
- 写入边界：仅新增本文件，不改既有分片及主入口，不执行 Git；后续集成由主会话处理。

## 一、结论：补足原生文本能力，不能概称全面提升

**T110 支持：2026 年新增了一组可自托管的开放视文模型，能直接进行纯文本生成；其中 2B 在官方同表中，相比 2025 年 Qwen3-1.7B 的部分知识及 Thinking 模式指令遵循指标提高，但默认 Non-Thinking 模式 IFEval 从 68.2 降至 61.2。**

因此，这条证据既不应降格为只有上下文压缩等工程功能，也不能升格为“文字生成全面提升”“所有小尺寸更强”或“同效果成本已下降”。能够证明的是：**新的原生文本部署选项，以及有任务、模式和型号限定的官方自报能力变化**。

与 [T101 文本／记忆基础设施](./enablers-software-2026.md) 的分工：T101 说明长会话上下文管理工程；T110 说明模型本身的文本生成接口及语言评测表现。两者都不单独证明长期人格、故事文学性或儿童回答准确率。

## 二、完整来源登记

以下均为前序只读分析已实际取得的正文，**访问结果均为 HTTP 200**。未将搜索摘要、URL 中的日期、模型名称中的数字或未打开的博客当作日期证据。仓库与模型卡的 main 路径会继续变化；本文件记录访问日所读内容，不把动态页面的整体修改日期当作模型发布日。

### T110-A｜Qwen3.5 官方仓库：小模型发布事件与下载路线

- 来源主体：QwenLM 官方仓库。
- 实际读取 URL：<https://raw.githubusercontent.com/QwenLM/Qwen3.5/main/README.md>
- 定位：News／Models。
- 事件日：**2026-03-02**，News 原文：
  > 2026-03-02: Qwen3.5-9B, Qwen3.5-4B, Qwen3.5-2B, and Qwen3.5-0.8B are now available on [Hugging Face Hub] and [ModelScope]!
- 方括号中为原文链接文字，链接目标分别为 <https://huggingface.co/collections/Qwen/qwen35>、<https://www.modelscope.cn/collections/Qwen/Qwen35>；本轮确认的是 README 中的官方发布及链接，**未另外打开集合页或下载权重**。
- 同一 News 记载 **2026-02-16** 首批 Qwen3.5 为 397B-A17B；不能把家族首发日当作小模型系列的发布日期。
- Models 段说明对无法访问 Hugging Face 的用户推荐 ModelScope，并列出下载及框架环境变量路线；支持作为中国市场自托管候选，不等于已经核验某账号或设备下载、运行成功。
- 访问结果：HTTP 200，取得 README 正文。

### T110-B｜Qwen3.5-2B：本条主模型卡

- 来源主体：Hugging Face 上的 Qwen 官方账号。
- 实际读取 URL：<https://huggingface.co/Qwen/Qwen3.5-2B/raw/main/README.md>
- 日期：未单独核定模型卡首次发布日期；模型发布事件由 T110-A 的 **2026-03-02** 支持。
- 定位：YAML 元数据／Model Overview／Benchmark Results → Language／Quickstart／Serving Qwen3.5／Text-Only Input／Thinking Mode／Best Practices。
- 关键原文：
  - `license: apache-2.0`。
  - “Type: Causal Language Model with Vision Encoder”。
  - “Number of Parameters: 2B”（位于 Language Model 项下）。
  - “Qwen3.5-2B operates in non-thinking mode by default”。
  - Text-Only Input 示例请求：“Give me a short introduction to large language models.”
- 可证内容：模型卡明确提供后训练模型权重与配置、纯文本生成用法、本地推理服务及 Thinking／Non-Thinking 两种模式；第五节的五项正反指标全部取自此卡同一 Language 表。
- 访问结果：HTTP 200，取得完整模型卡正文。

### T110-C｜Qwen3.5-9B：尺寸、许可与默认模式边界

- 实际读取 URL：<https://huggingface.co/Qwen/Qwen3.5-9B/raw/main/README.md>
- 日期：模型卡独立首发日未核；小模型发布事件按 T110-A。
- 定位：YAML／Model Overview／Quickstart。
- 关键原文／字段：`license: apache-2.0`；Language Model 的 Number of Parameters 为 9B；“Qwen3.5 models operate in thinking mode by default”。
- 范围：9B 模型卡的默认 Thinking 说明，**不能直接套给 2B／0.8B**；本文件不把 9B 的评测分数转记到小尺寸型号。
- 访问结果：HTTP 200，取得完整模型卡正文。

### T110-D｜Qwen3.5-4B：尺寸、许可与默认模式边界

- 实际读取 URL：<https://huggingface.co/Qwen/Qwen3.5-4B/raw/main/README.md>
- 日期：模型卡独立首发日未核；小模型发布事件按 T110-A。
- 定位：YAML／Model Overview／Quickstart。
- 关键原文／字段：`license: apache-2.0`；Language Model 的 Number of Parameters 为 4B；“Qwen3.5 models operate in thinking mode by default”。
- 访问结果：HTTP 200，取得完整模型卡正文；写入前从已取得正文核对默认模式，没有再次联网。

### T110-E｜Qwen3.5-0.8B：尺寸、许可与默认模式边界

- 实际读取 URL：<https://huggingface.co/Qwen/Qwen3.5-0.8B/raw/main/README.md>
- 日期：模型卡独立首发日未核；小模型发布事件按 T110-A。
- 定位：YAML／Model Overview／Quickstart。
- 关键原文／字段：`license: apache-2.0`；Language Model 的 Number of Parameters 为 0.8B；“Qwen3.5-0.8B operates in non-thinking mode by default”。
- 访问结果：HTTP 200，取得完整模型卡正文；写入前从已取得正文核对默认模式，没有再次联网。

### T110-F｜Qwen3.5-2B 许可正文

- 实际读取 URL：<https://huggingface.co/Qwen/Qwen3.5-2B/raw/main/LICENSE>
- 定位／短引：“Apache License / Version 2.0, January 2004”；“TERMS AND CONDITIONS FOR USE, REPRODUCTION, AND DISTRIBUTION”。
- 日期边界：January 2004 是许可证文本版本，不是模型发布日。
- 访问结果：HTTP 200，取得许可证正文；与 T110-B 的 Apache-2.0 元数据一致。

### T110-G｜Qwen3.5-9B 许可正文

- 实际读取 URL：<https://huggingface.co/Qwen/Qwen3.5-9B/raw/main/LICENSE>
- 定位／短引：“Apache License / Version 2.0, January 2004”。
- 日期边界：许可证版本日期不等于模型发布日。
- 访问结果：HTTP 200，取得许可证正文；与 T110-C 的 Apache-2.0 元数据一致。
- 许可核验范围：四张模型卡均已核元数据；另外完整读取了 **2B 和 9B** 的 LICENSE。未声称已经逐份读取 0.8B／4B 的 LICENSE 或审计全部依赖。

### T110-H｜Qwen3 官方仓库：2025 年旧基线

- 实际读取 URL：<https://raw.githubusercontent.com/QwenLM/Qwen3/main/README.md>
- 定位：模型尺寸介绍／News。
- 旧基线系列发布日：**2025-04-29**。
- 原文：
  > 2025.04.29: We released the Qwen3 series. Check our [blog] for more details!
- 同一 README 的模型尺寸介绍明确包括 **1.7B**。此处依据系列发布记录界定旧基线年份，没有另核单个权重文件的上传时刻。
- 对照分数取自 T110-B 的同表，不是从旧仓库的另一张榜单拼接而来；模型名 **Qwen3-1.7B** 不替换为其他型号。
- 访问结果：HTTP 200，取得 README 正文。

## 三、尺寸、模式及接入状态必须分别记录

| 型号 | 模型卡 Language Model 标称参数 | 该卡记载的默认模式 | 已核许可层级 |
|---|---:|---|---|
| Qwen3.5-0.8B | 0.8B | Non-Thinking | 模型卡 Apache-2.0 元数据 |
| Qwen3.5-2B | 2B | **Non-Thinking** | 模型卡元数据＋LICENSE 正文 |
| Qwen3.5-4B | 4B | Thinking | 模型卡 Apache-2.0 元数据 |
| Qwen3.5-9B | 9B | Thinking | 模型卡元数据＋LICENSE 正文 |

- **交付形态**：官方已发布开放权重与配置，可通过支持框架自托管；不是仅存在宣传演示。这里不使用云服务的 GA／Preview 标签代替权重发布状态。
- **原生文本**：2B 卡将模型定义为带视觉编码器的因果语言模型，并提供 Text-Only Input 及本地服务 `--language-model-only` 用法。文本能力不依赖用户先提交图片，也不是把上下文压缩功能当作模型推理能力。
- **架构边界**：家族 Highlights 中的概括性架构宣传不能自动替代每个小尺寸的 Model Overview，更不能仅凭家族措辞把各尺寸都认定为同一种 MoE 结构。
- **本地服务与云 API 分开**：模型卡的兼容 API 示例可以面向本地推理服务；兼容某种 API 格式不等于使用该 API 格式所属厂商的云或模型。本条没有核验阿里云等托管接口的区域、价格、SLA 或儿童产品条款。
- **商用边界**：Apache-2.0 是模型许可证据，不是全部软件、托管服务、输入数据、第三方内容或生成物权利的统一授权。商业集成仍须按实际分发方式履行许可义务并审查依赖与数据权利。
- **中国市场候选**：官方 ModelScope 下载路线和自托管说明支持开展境内后端评估；没有验证账号准入、网络可达性、目标硬件、实际下载或部署结果。

## 四、能生成文本与能做好产品是两层事实

T110-B 的纯文本示例直接发送自然语言请求并生成回答；模型卡还给出 SGLang、vLLM、KTransformers、Transformers 等推理服务路线。因此可确认存在原生文本推理与生成的可实施接口，而非只有压缩、缓存或状态管理。

但示例可运行的说明和接口存在，不等于本项目已经运行成功。模型卡还提示：

- 推理效率与吞吐因框架而显著不同；生产负载需选择、配置及验证服务引擎。
- 默认长上下文可能造成 OOM，必要时降低上下文窗口；标称支持长上下文不等于目标设备有足够内存。
- 2B 默认 Non-Thinking；Thinking 需要明确启用。不能把 Thinking 评测成绩用于承诺默认模式体验。
- Best Practices 建议大多数请求保留 32,768 tokens 输出空间，复杂数学／编程评测可设至 81,920 tokens。这是推荐配置，**不是本轮已核定每个榜单单元使用的实际预算，更不是玩具实时响应的耗时测量**。

## 五、同表五项正反指标：严格保留模式与退步项

**唯一分数来源：T110-B 的 Benchmark Results → Language。** 以下两个型号在该官方表内比较，模式按行组保留；所有数值均为该表分数，越高越好，不拼成综合百分比，也不表述为儿童场景实测准确率。

| 基准／同表模式 | 旧基线 Qwen3-1.7B | 新模型 Qwen3.5-2B | 证据允许的结论 |
|---|---:|---:|---|
| MMLU-Pro／Instruct（Non-Thinking） | 40.2 | 55.3 | 该知识与推理基准分数提高 |
| C-Eval／Instruct（Non-Thinking） | 61.0 | 65.2 | 该中文知识评测分数提高 |
| **IFEval／Instruct（Non-Thinking）** | **68.2** | **61.2** | **退步：默认非思考模式的该指令遵循指标下降，不能删除或隐藏** |
| IFEval／Thinking | 72.5 | 78.6 | 开启思考后的该指令遵循指标提高 |
| IFBench／Thinking | 26.7 | 41.3 | 开启思考后的另一指令遵循指标提高 |

### 比较条件与不能外推的内容

1. **官方自报，不是独立复现。** 同一模型卡、同一任务名称与模式分组提供有限比较依据，但本项目没有取得并复现全部评测输入、逐模型采样设置、实际输出预算及评分执行过程。
2. **参数量不等：1.7B 对 2B。** 这不是同参数规模的严格升级试验；参数量、模型结构、算力、运行内存、激活／缓存、输出长度与推理耗时也不是同一个量。
3. **算力与成本未归一化。** 没有相同硬件、相同推理预算、相同延迟或相同费用下的对照，不能把分数变化写成单位算力／单位成本提高了某个比例。
4. **Thinking／Non-Thinking 不混算。** 尤其不能用 2B 的 Thinking IFEval 78.6 代替默认 Non-Thinking 的 61.2；同名 IFEval 的两组比较必须分开。
5. **默认 IFEval 退步是实质反证。** 可以说知识与部分思考模式任务表现提高，不能概称指令遵循全部改善或文字模型全面提升。
6. **不跨尺寸迁移成绩。** 本表只比较 Qwen3-1.7B 与 Qwen3.5-2B；0.8B、4B、9B 的存在和许可不意味着它们具有相同成绩或相同默认模式。
7. 这些基准不是角色故事文学质量、长期人设一致性、儿童中文准确率或家庭多轮交互体验的测量；没有这些目标用例的证据时不得补出结论。

## 六、实体玩具映射：能力已证，产品效果仍是推断

| 环节 | 本证据能提供什么 | 尚不能证明什么 |
|---|---|---|
| 文本问答与规则解释 | 原生文本生成与知识／指令评测基础，可作为后端候选 | 儿童问题准确率、幻觉率、年龄适配、规则解释一定正确 |
| 台词和内容草稿 | 能根据文本请求生成内容；可设计约束提示并人工审核 | 故事更好、文笔更好、角色更稳定、版权与内容安全已解决 |
| 多步骤文本任务 | Thinking 模式的部分指令遵循指标提高，可评估复杂请求处理 | 实时响应更快、默认模式同样提高、模型口头回答可直接控制机械动作 |
| 自托管与服务选择 | 0.8B—9B 开放权重及官方 ModelScope 路线增加后端选择 | 永久免费、运维成本为零、商业云条款自然满足、数据处理自动合规 |
| 硬件部署 | 可依据型号与推理框架开展内存／吞吐测试 | ESP32／低价 MCU 可运行、本项目板卡已达实时水平、整机 BOM 已下降 |

**具体消费玩具采用 Qwen3.5 的证据：本条未取得。** 产品卡仅可引用 T110 解释可选能力；不得据此填入某品牌已采用某型号。端云边界与整机成本继续参照 [硬件使能片](./enablers-hardware-2026.md)，不因“小模型”标签取消内存、功耗、网络、声学和安全工程要求。

## 七、访问审计、未验证项与交接

- 前序只读分析实际读取了本文件登记的 **8 个官方 URL**：两个仓库 README、四个型号模型卡、两个 LICENSE；全部 HTTP 200，**本条证据链没有读取失败项**。
- 发布日期来自官方 News 的明确事件记录；没有将模型卡的当前内容、许可证版本日或 Qwen3.5 家族首发日冒充小模型首发日。
- 没有打开并核验所链接的 Qwen 发布博客、ModelScope 集合页或托管 API 正文；没有凭这些链接补写未读事实。
- 写入阶段仅复用前序已取得正文，并从保留正文核对四个型号的默认模式；没有追加搜索或联网抓取。
- 没有下载权重、安装框架、运行模型、调用付费服务、上传家庭数据或进行实物测试。
- 未验证：目标硬件内存／吞吐／功耗、首 token 与整链 p95、Thinking 额外等待时间、目标产品问答与创作质量、儿童适龄和隐私要求、同效果成本、实际玩具采纳。
- 必须保留的收敛结论：**原生文本能力与可部署性有直接证据；部分官方基准改善、默认 IFEval 退步同时成立；参数与算力不等，不能概称全面提升。**
- 本轮只新增本文件；既有分片与主入口未改，未运行 Git。
