# 2026 年软件能力对实体 AI 玩具的加持：T101—T109 证据片

- 研究窗口：**2026-01-01 至 2026-10-10**；来源访问日期：**2026-10-10**。
- 分工：T1 分析已确认，本文件为 Coder T1 的唯一写入成果；沿用本轮已经读取的来源，未补做联网检索。
- 范围：生成式文本、图像、音频、视频及实时多模态的产品使能能力；不重复销售研究，不改写产品侧既有四组 40 卡。
- 验证层级：官方发布／官方文档／官方仓库证据；没有调用付费模型、测试玩具、测量端到端性能或验证实际账户权限。
- **T101—T108 是能力证据，T109 是地区／年龄接入限制证据，均不是具体玩具采用某模型的证据。** 产品卡可关联这些编号说明技术可能性；只有产品自己的披露才能证明实际采用。

## 结论与措辞边界

部分支持“2026 年软件能力明显进步”，但应具体化为：**连续对话更自然、后台任务不必阻塞交流、语音自部署选择增加，以及内容生产更灵活**。不能据此宣称长期人格记忆已解决、多模态模型已能在低成本玩具端运行、整链延迟等于宣传数字，或所有成本均大幅下降。

今年“新增”有三种不同含义，正文不得混写：

1. 新模型／新接口能力，例如 GPT-Live 的全双工会话与后端分工。
2. 既有能力的工程化改进，例如服务端上下文压缩、异步函数调用。
3. 原有能力变得可下载或可部署，例如 Qwen TTS／ASR 权重与工具链开放；不意味着声音克隆或语音识别在 2026 年才出现。

面向中国市场，不能只把国际云 API 当默认可用选项。**Qwen 的开放权重及官方 ModelScope 下载路线是本片已核实的本地／自托管候选**，但尚未证明能够在本项目板卡或低价玩具芯片上实时运行。云端 Qwen API 的具体型号、国内外部署区域和商用条款仍需按实际产品核验。OpenAI／Gemini Developer API 的中国大陆地区限制，以及 Gemini 的未成年人客户端限制，见 T109。

## 一、产品映射优先表

下表“可以加持”均为产品推断，不是部署完成、成本已降低或已有玩具采用的事实。

| 编号 | 2026 新增／改进及基线 | 可加持的实体玩具体验 | 可用接口／限制 | 实际玩具采纳证据 |
|---|---|---|---|---|
| **T101 文本／记忆基础设施** | 02-10 发布服务端 context compaction；Conversations API 和客户端 compaction 已在 2025 年存在 | 连续故事玩偶、长期养成宠物：接续故事进度，减少长对话塞满上下文；配合应用记忆库保留称呼与偏好 | Responses API；压缩项不透明，不等于可编辑、准确且可删除的长期记忆；角色与关键事实仍需应用管理 | **未证实**，不能由 API 能力推定具体玩具实现了长期记忆 |
| **T102 全双工语音** | 09-10 GPT-Live 1 GA，可同时听说，后端处理任务时继续交流；Realtime API 早在 2025 年 GA | 可插话陪伴毛绒、问答机器人：说“不是这个故事”时让出话轮；查询内容时仍能简短回应 | `v1/live/sessions`；音频／文本，不支持图像／视频；Free tier 不支持；打断讲话不自动取消后端动作 | **未证实**；儿童产品另核适用条款，不能拿语音演示当玩具验收 |
| **T103 实时视听与异步任务** | 09-15 Gemini 3.8 Live／Extended Thinking 发布，实时视觉输入、异步函数调用与持续对话 | 带摄像头的探索玩具、桌面棋类伙伴：围绕正在摆放的实物说明规则，执行工具时不断掉交流 | Gemini Live API／AI Studio；开发者 API 可用不等于所有企业通道 GA，企业产品部分是 private preview；T109 对儿童客户端及大陆地区构成接入约束 | **未证实**；官方棋类／办公演示不是实体玩具量产采用 |
| **T104 TTS／角色声音** | 官方仓库记录 01-22 开放 Qwen3-TTS 0.6B／1.7B；部分型号支持声音设计与自然语言风格控制 | 稳定声线角色玩偶、多人角色故事机：睡前轻声、游戏兴奋反馈、动态或预生成台词 | 开放权重／本地代码，已核 1.7B CustomVoice 模型卡 Apache-2.0；托管 API 需另核型号和区域；97ms 是合成首包相关声明，不是问答整链 | **未证实**；可作国产／自托管候选，不能指定某品牌已采用 |
| **T105 STT／方言与识别部署** | 官方仓库记录 01-29 开放 Qwen3-ASR 0.6B／1.7B，30 种语言＋22 种中文方言；06-26 原生 Transformers 支持 | 中文家庭故事机、祖孙语音游戏：增加方言覆盖与自托管选择 | 开放权重；所查文档的流式推理依赖 vLLM，不支持 batch／返回时间戳；儿童发音、远场和舵机噪声未测 | **未证实**；支持语言清单不等于目标家庭环境的识别率 |
| **T106 图像／内容生产** | 04-21 GPT Image 2；09-08 GPT Image 2.5 Sunburst／Flare，新增质量档位与编辑选项 | 带屏故事玩具、配套 App、打印任务卡：插图、奖励卡、场景与角色素材 | Images API／Responses 工具；可能要求组织验证；复杂请求可达约 2 分钟，连续角色一致性及文字排版仍有限制 | **未证实**；主要是内容供给与个性化潜力，不是毫秒级表情动画 |
| **T107 视频／异步创作** | 03-31 Veo 3.1 Lite：偏成本效率的文生／图生视频，4／6／8 秒、720p／1080p | 配套短剧、角色宣传片、App 故事回顾；提前制作分支剧情片段 | `veo-3.1-lite-generate-preview`，付费 Preview；视频带音频，不支持 4K／Extension；片长不等于生成耗时 | **未证实**；仅支持创作／异步内容推断，不能冒称玩具实时视频交互 |
| **T108 视频／实时 Avatar** | 09-24 Gemini 3.8 Live with Live Avatar，near-real-time 视频生成与语音、口型、表情结合 | 带屏桌面伙伴、机器人面部屏幕：角色持续听说并呈现表情 | 公告称 Gemini Enterprise 可用；自定义 Avatar 仅 enterprise allowlisting；普通账号权限、并发价格、整链时延、端侧条件未核 | **未证实**；酒店等企业演示不是消费玩具采用 |
| **T109 接入条件，不是模型采用** | 归档本轮已读 OpenAI／Gemini 地区和年龄条款，不宣称这些限制均于今年首次出现 | 用于筛掉不能直接面向目标中国市场／儿童用户交付的接入路线 | 大陆未列入所查两家 Developer API 支持地区；Gemini 禁止面向或可能由未满 18 岁者访问的 API Client；企业合同另核 | **不适用**，只证明接入限制，不证明任何玩具采用 |

## 二、逐条证据登记

### T101｜文本角色与记忆：新增管理机制，不是“永不遗忘”

**来源 T101-A**

- 题名：Changelog | OpenAI API。
- URL：<https://developers.openai.com/api/docs/changelog>
- 日期：事件／日志日 **2026-02-10**；动态页面本身无单一发布日期。
- 定位：February, 2026 → Feb 10 → server-side compaction。
- 短引：“Launched server-side compaction in the Responses API.”
- 访问：浏览器正文成功。第一次通过页面提供的 WebMCP lookup_page 读取返回“Page exists in the route map, but local content was not found.”；随后直接打开官网正文成功。前一次失败不作为“没有此能力”的证据。

**来源 T101-B**

- 题名：Compaction。
- 页面 URL：<https://developers.openai.com/api/docs/guides/compaction>
- 实际读取 URL：<https://developers.openai.com/api/docs/guides/compaction.md>
- 日期：无独立发布日期；2026-10-10 读取的当前指南，新增事件日由 T101-A 证明。
- 定位：Overview／Server-side compaction。
- 短引：“reduce context size while preserving state needed for subsequent turns”；压缩项“opaque and not intended to be human-interpretable”。
- 访问：官方 Markdown HTTP 200。

**基线、产品价值与缺口**

- 同一发布日志记载：Conversations API 为 **2025-08-20**；client-side compaction 为 **2025-12-11**。因此不得说长期会话状态或压缩是 2026 年首次出现。
- 当前接口：Responses create 请求的 `context_management`／`compact_threshold`；超过阈值后产生压缩项。官方称可平衡长对话的质量、成本、延迟，没有承诺所有事实无损保存。
- 产品推断：故事进度与上下文更易延续；角色设定、用户授权后的关键偏好、事实来源和删除操作仍宜由应用的结构化记忆库管理。缓存命中与压缩不是人格一致性本身。
- 可影响成本环节：后续请求上下文长度；须同时计入压缩、检索和存储成本，**没有本轮同口径历史成本实测，不给降幅**。
- 接入状态：已发布 API 功能；所查材料未单列该功能的 GA 标签，未提供开放权重交付证据。国际云使用边界见 T109。
- 未证实：跨月偏好准确率、关键事实保留率、角色不漂移率、儿童隐私合规、真实玩具采用。

### T102｜GPT-Live：全双工、后端分工及明确的会话计费

**来源 T102-A**

- 题名：Changelog | OpenAI API。
- URL：<https://developers.openai.com/api/docs/changelog>
- 发布／GA 事件日：**2026-09-10**。
- 定位：Sep 10 → gpt-live-1 → v1/live/sessions。
- 短引：“GPT-Live 1 is now generally available in the API.”
- 访问：官方浏览器正文成功。

**来源 T102-B**

- 题名：GPT-Live 1。
- 页面 URL：<https://developers.openai.com/api/docs/models/gpt-live-1>
- 实际读取 URL：<https://developers.openai.com/api/docs/models/gpt-live-1.md>
- 日期：模型页无独立发布日；GA 日按 T102-A。
- 定位：Model details／Pricing／Rate limits。
- 短引：“It can listen and speak at the same time”；“Voice sessions cost $0.05 per minute”；“Backend model and tool usage is billed separately.”
- 访问：官方 Markdown HTTP 200。
- 明确边界：输入／输出为 audio、text；image、video 不支持；`v1/live/sessions` 是对应接口，不能把它写成 `v1/realtime` 的同一个端点；Free tier 不支持。所查页按并发会话列出 Build 50／Launch 300／Grow 500，这不是本账户已获配额。

**来源 T102-C**

- 题名：Getting started with GPT-Live。
- 页面 URL：<https://developers.openai.com/api/docs/guides/live>
- 实际读取 URL：<https://developers.openai.com/api/docs/guides/live.md>
- 日期：未标独立发布日期。
- 定位：Understand the two parts／Choose a connection。
- 短引：“Backend work can continue when the caller interrupts the assistant; your application decides whether to finish or cancel it.”
- 访问：官方 Markdown HTTP 200。
- 接口：WebRTC、WebSockets、SIP 等；后端可以 Responses delegation 或 client delegation 接入。应用负责权限确认、工具执行及任务状态，密钥应保留在可信服务端。

**来源 T102-D**

- 题名：Prompting GPT-Live。
- 页面 URL：<https://developers.openai.com/api/docs/guides/live-prompting>
- 实际读取 URL：<https://developers.openai.com/api/docs/guides/live-prompting.md>
- 日期：未标独立发布日期。
- 定位：Personality／Backchannels／Interruptions。
- 短引：“Describe the assistant’s role, tone, and speaking pace”；“When the user interrupts, the assistant should stop its answer and listen.”
- 访问：官方 Markdown HTTP 200。

**基线、产品价值与缺口**

- 基线：同一日志记载 Realtime API 于 **2025-08-28 GA**；2026 年不是第一次存在实时语音。2026-07-06 的 GPT-Realtime-2.1 条目还记载打断、静音、噪声处理改进，但没有本轮可比的玩具场景指标。
- 产品推断：用户改口、插话和后端查资料时，玩具不必等整个任务结束才再次发声；可以用短促听者反馈维持交流。
- **说话让出话轮不等于后端动作已取消**。涉及实体动作时必须由应用分别处理取消、重复执行与状态确认；模型口头确认不是硬件安全联锁。
- 情绪边界：语气、人格提示与表达力有官方接口依据；不能升级成准确识别心理状态、提供治疗或“真正理解情绪”的证据。
- 当前成本示例：**300 个会话分钟 × $0.05／分钟 = $15，仅 voice session 费用**；按秒计费，不向整分钟取整。后台模型和工具、网络及硬件另计。会话分钟不是用户开口分钟；这不是历史降价比较，也不是玩具整机月成本。
- 未证实：真实儿童语音、回声、远场、电机噪声中的打断成功率；首声与停声 p95；开放权重、端侧部署、具体玩具采用。儿童部署适用条款未在本片得到完整核准。

### T103｜Gemini 3.8 Live：实时视觉与异步工具，不把企业 Preview 写成 GA

**来源 T103-A**

- 题名：Build real-time voice applications with Gemini 3.8 Live and 3.5 Transcribe。
- URL：<https://blog.google/innovation-and-ai/technology/developers-tools/build-real-time-voice-applications-gemini-audio/>
- 发布／事件日：**2026-09-15**。
- 定位：Gemini 3.8 Live & 3.8 Live Extended Thinking → Key capabilities。
- 短引：“Execute API and tool calls in the background while continuing to stream audio responses”；“Ground dialogue in live visual inputs”。
- 访问：浏览器官方正文成功。

**来源 T103-B**

- 题名：Introducing Gemini 3.8 Live and 3.8 Live Extended Thinking。
- URL：<https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-3-8-live-gemini-3-8-live-extended-thinking/>
- 发布／事件日：**2026-09-15**；正文注明更新 **2026-09-17**。
- 定位：Experience more fluid, intelligent conversations／Start using our latest Gemini Audio models。
- 短引：“reasons and speaks simultaneously”；开发者“In the Gemini API and Google AI Studio”；企业产品部分“In private preview”。
- 访问：浏览器官方正文成功。
- 可用性：开发者 API／AI Studio 已提供，不能因发布文章存在就自动写成全部服务 GA。Gemini Enterprise 与 Enterprise for Customer Experience、Workspace 等不同通道的发布状态不能相互替代。

**来源 T103-C（通用接口边界，不代替具体型号卡）**

- 题名：Live API 官方概览。
- URL：<https://ai.google.dev/gemini-api/docs/live>
- 日期：本轮未核定其独立发布日期。
- 定位：能力及输入格式概览。
- 短引：“processes continuous streams of audio, images, and text”；输入说明含“images (JPEG <= 1FPS)”对应的页面文字。
- 访问：HTTP 200，读取 HTML 正文。
- 限制：通用指南语言覆盖等条目与 3.8 专属公告不是同一口径，不能机械合并；“视觉输入”不是输出视频，更不证明高速运动控制闭环。

**基线、产品价值与缺口**

- 官方宣称相较此前 Live 模型改进，列举若干语音／任务评测；本片没有同一实体玩具用例的前后对照。不同榜单、WER、任务完成率、延迟不能拼成“玩具综合提升百分比”。
- 产品推断：带摄像头探索、桌面棋类、看物问答；摄像头、采样频率、用户同意、家庭图像隐私和网络上行均是独立前提，不表示本项目已配置或验证。
- 当前价文章给出音频输入／输出每分钟估算，并注明基于各自 token 单价；**不得与 GPT-Live 的会话分钟价格直接相除**，本片不做“便宜多少”的比较。
- 未发现开放权重依据；不能推定端侧运行。**中国大陆及儿童客户端限制见 T109，尤其不能因开发者成人注册而认为儿童产品可以上线。**
- 实际采用：官方棋类、办公等演示不是实体玩具；四组 40 卡中如未披露模型，不得补写已用 Gemini。

### T104｜Qwen3-TTS：国产开放权重候选与可控角色声音

**来源 T104-A**

- 题名：Qwen3-TTS，QwenLM 官方仓库 README。
- 页面 URL：<https://github.com/QwenLM/Qwen3-TTS>
- 实际读取 URL：<https://raw.githubusercontent.com/QwenLM/Qwen3-TTS/main/README.md>
- 发布事件日：README News 明记 **2026-01-22**。
- 定位：News／Introduction／Released Models Description and Download／Evaluation。
- 短引：“adaptive control of tone, speaking rate, and emotional expression”；“latency as low as 97ms”。
- 访问：官方仓库 raw README HTTP 200；未下载权重或运行代码。

**来源 T104-B**

- 题名：Qwen3-TTS-12Hz-1.7B-CustomVoice 模型卡，Qwen 官方账号。
- 页面 URL：<https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice>
- 实际读取 URL：<https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice/raw/main/README.md>
- 日期：本轮未单独核定模型卡首次发布日期；事件日仍按官方仓库。
- 定位：模型卡 YAML 元数据。
- 短引：`license: apache-2.0`。
- 访问：HTTP 200。许可结论直接覆盖这个已读模型卡；不据此推定所有云服务及所有型号许可完全相同。

**失败来源／日期差异**

- Qwen 博客题名（搜索结果显示）：Qwen3-TTS Family is Now Open Sourced: Voice Design…。
- URL：<https://qwen.ai/blog?id=qwen3tts-0115>
- 访问：从 Google 结果点击后浏览器正文读取超时，后续状态读取也超时；**未取得正文**。
- 搜索摘要显示 2026-01-21，不作为已核发布日期；本片使用仓库明确记载的 **2026-01-22 发布事件**，不猜测一天差异的原因，也不把 URL 中 `0115` 当发布日期。

**接口与型号边界**

- 开放系列包括 0.6B／1.7B、12Hz tokenizer；覆盖十种语言及部分方言声线。
- 1.7B VoiceDesign／CustomVoice 表中支持 instruction control；0.6B CustomVoice 不可直接继承该结论。Base 的声音克隆／微调功能与 VoiceDesign 是不同能力。
- README 提供 ModelScope 路线并注明推荐中国大陆用户使用；开放权重和本地加载是本轮已核实的中国市场候选基础，而不是必须走国际云。
- README 链接国内托管 API <https://help.aliyun.com/zh/model-studio/qwen-tts-realtime> 及国际文档 <https://www.alibabacloud.com/help/en/model-studio/qwen-tts-realtime>。**本轮仅读到仓库链接，未打开这两份 API 正文**；因此不证明托管型号、账户可用区域、定价、SLA、许可与开放权重完全相同。
- 所查 README 推荐 GPU／FlashAttention 2 等推理条件，并称其 vLLM-Omni 示例当时仅支持 offline inference；不能将模型支持 streaming 与任意部署框架已支持在线流式服务混为一谈。

**基线、价值与缺口**

- “声音克隆在今年才诞生”不成立；此处可证事件是 2026 年权重、型号与工具发布。
- 官方同页 Seed-TTS test-zh／test-en 的对比中，2025 年 CosyVoice 3 为 0.71／1.45，Qwen3-TTS-12Hz-1.7B-Base 为 0.77／1.24，均为该表的 WER、越低越好。只说明此表中文／英文结果有取舍，**不是全面领先，也不是 STT 效果**；不能与其他数据集混比。官方自报评测未由本项目复现。
- 产品推断：固定角色声线、睡前轻声、游戏反馈、多人角色台词；也可预生成并审核后缓存，摊销多次播放的生成成本。
- 97ms 是官方合成链路／首音频包相关声明，未包含玩具采音、识别、LLM、网络及播放缓冲。本轮没有核定其完整硬件／负载条件，不据此承诺整链低延迟。
- 未证实：低价玩具 CPU／NPU 或本项目板卡实时运行；儿童中文韵律与长文本稳定性；合法授权的声音资产准备；托管 API 在国内实际可用；实际玩具采用。
- 自托管只是把部分服务商成本转为推理硬件、运维、能耗与许可管理，**不是免费、不是已经降价**。

### T105｜Qwen3-ASR：方言、开放部署及流式限制

**来源 T105-A**

- 题名：Qwen3-ASR，QwenLM 官方仓库 README。
- 页面 URL：<https://github.com/QwenLM/Qwen3-ASR>
- 实际读取 URL：<https://raw.githubusercontent.com/QwenLM/Qwen3-ASR/main/README.md>
- 事件日：**2026-01-29** 开放 0.6B／1.7B ASR 与 ForcedAligner；**2026-06-26** 原生 Transformers 支持。
- 定位：News／Introduction／Streaming Inference。
- 短引：“30 languages and 22 Chinese dialects”；“streaming inference is only available with the vLLM backend”；“does not support batch inference or returning timestamps”。
- 访问：官方 raw README HTTP 200。

**来源 T105-B／T105-C｜官方模型卡许可补核**

- 题名／型号：Qwen3-ASR-1.7B；Qwen3-ASR-0.6B（Qwen官方账号）。
- 完整读取 URL：<https://huggingface.co/Qwen/Qwen3-ASR-1.7B/raw/main/README.md>；<https://huggingface.co/Qwen/Qwen3-ASR-0.6B/raw/main/README.md>。
- 日期：模型卡首次发布日期未单核；本次独立复核访问日为**2026-10-10**，不代替T105-A的01-29事件日。
- 定位／短引：两份模型卡YAML元数据均为 `license: apache-2.0`。
- 访问结果／主体：Reviewer TECH本轮实际打开上述两份官方raw模型卡并确认；由主会话回传，Coder INTEGRATE据追加授权归档，**不是集成者重新联网核验**。
- 许可边界：只直接支持这两份已读模型卡所标许可，不自动覆盖托管API、其它变体、第三方依赖、训练数据或音频／声音权利；也不证明低功耗硬件可实时运行或具体玩具已采用。

**日期与访问边界**

- 仓库关联博客 URL：<https://qwen.ai/blog?id=qwen3asr>。
- 本轮搜索摘要显示 2026-01-28，但未打开博客正文，不将其作为已核日期；事件按仓库 **01-29**。未核定差异原因。
- 仓库列出国内实时 API 文档 <https://help.aliyun.com/zh/model-studio/qwen-real-time-speech-recognition>、国内文件识别文档 <https://help.aliyun.com/zh/model-studio/qwen-speech-recognition>，以及国际对应文档 <https://www.alibabacloud.com/help/en/model-studio/qwen-real-time-speech-recognition>、<https://www.alibabacloud.com/help/en/model-studio/qwen-speech-recognition>。**仅确认仓库链接存在，未读取这些 API 正文，不确认账户／区域／云端型号或价格。**

**基线、产品价值与缺口**

- 2026 可证事件是开放权重及工具链完善，不是语音识别或流式 ASR 首次出现；未取得目标玩具任务的历史同口径识别率和成本。
- 已核：开放架构／权重、ModelScope 下载说明、自托管推理工具；30 种语言与 22 种中文方言覆盖列表；流式／离线统一模型。
- “2000 times throughput at a concurrency of 128”是官方服务器吞吐描述，**不是单个玩具 2000 倍加速，也不是端到端时延**。没有运行其硬件条件和负载复现。
- 产品推断：中文家庭、祖孙游戏的方言适配及服务商替代选择。需另测儿童发音、口语改口、多人重叠、远场、电视背景声和舵机噪声。
- ForcedAligner 的时间戳是单独能力，不可忽略当前流式推理“不返回时间戳”的限制；不能直接据此承诺在线口型／动作同步。
- 未证实：本机端侧性能、低功耗预算、云 API 与开源版本相同、全面优于所有上一年 ASR、具体实体玩具采用。开放权重不等于不存在商业合规与运行成本。

### T106｜图像生成：内容供给与编辑能力，不是实时玩具动画

**来源 T106-A**

- 题名：Changelog | OpenAI API。
- URL：<https://developers.openai.com/api/docs/changelog>
- 事件日：**2026-04-21** GPT Image 2；**2026-09-08** GPT Image 2.5 Sunburst／Flare。
- 定位：Apr 21／Sep 8 对应模型条目。
- 短引：“Released GPT Image 2.5 Sunburst and GPT Image 2.5 Flare for image generation and editing”。
- 访问：官方正文成功。

**来源 T106-B**

- 题名：Image generation。
- 页面 URL：<https://developers.openai.com/api/docs/guides/image-generation>
- 实际读取 URL：<https://developers.openai.com/api/docs/guides/image-generation.md>
- 日期：无独立发布日期；事件日由日志提供。
- 定位：模型／输出设置、Limitations、Cost and latency。
- 短引：“Complex prompts may take up to 2 minutes”；“may occasionally struggle to maintain visual consistency for recurring characters”；“The models can use different token counts for the same quality setting”。
- 访问：官方 Markdown HTTP 200。

**状态、基线、成本与缺口**

- 接口：Images API 和 Responses API image generation tool；2.5 模型支持 `xhigh`、`max`。日志为已发布 API 模型，不把未明确的 GA 标签补写出来；较高分辨率部分标为 experimental。组织可能须先完成 verification，本轮没有实际验证账户资格。
- 基线：同一日志显示 GPT Image 1.5 于 **2025-12-16** 已发布；2026 不是第一次能生成插图。04-21 日志还记载 Batch API 支持，但异步折扣不是历史模型降价，也不能用于估算实时体验。
- 当前文档的 2.5 费率为每百万 image input tokens $8、cached image input $2、image output $30、text input $5、cached text input $1.25。这里只记录**不同输入／输出单位各自的当前价**，不跨单位比较、不推出单张固定价格或年内降幅。
- 缓存限制：文档说 GPT Image 2／2.5 缓存输入价只适用于 Responses 图像工具，不适用于直接 Images API；不能给所有图片调用统一套缓存折扣。
- 产品推断：任务卡、奖励卡、插图和角色资产，可先生成、人工审核并缓存；改善内容生产与个性化的可能性，不是素材团队总成本已经下降的实证。
- 未证实：人物跨集一致性、版权与儿童图像授权、内容审核通过率、重复生成率、每张合格素材成本、端侧权重及具体玩具采用。分钟级生成不是毫秒级面部表情动画。

### T107｜视频生成：Veo 3.1 Lite 的创作／异步路线

**来源 T107-A**

- 题名：Build with Veo 3.1 Lite, our most cost-effective video generation model。
- URL：<https://blog.google/innovation-and-ai/technology/ai/veo-3-1-lite/>
- 发布／事件日：**2026-03-31**。
- 定位：Efficiency for builders／Get started。
- 短引：“Text-to-Video and Image-to-Video”；“duration at 4s, 6s or 8s”；“paid tier on the Gemini API and Google AI Studio”。
- 访问：官方浏览器正文成功。

**来源 T107-B**

- 题名：Veo 3.1 Lite preview。
- URL：<https://ai.google.dev/gemini-api/docs/models/veo-3.1-lite-generate-preview>
- 日期：模型 Latest update 为 **March 2026**；页面 Last updated **2026-10-08 UTC**，不是首次发布日期。
- 定位：模型代码、输入输出、功能限制。
- 短引：“Output: Video with audio”；“does not support 4K outputs or Extension”。
- 访问：HTTP 200。

**状态、基线、产品价值与缺口**

- 确定接口型号为 `veo-3.1-lite-generate-preview`，因此标为 **付费 Preview，非已证 GA**。正文的“available”不取消模型页的 Preview 状态。
- 输入 Text／Image，输出含音频视频；公告提供 16:9／9:16、720p／1080p、4／6／8 秒。输出片长与生成耗时是两个变量。
- 基线：公告与 Veo 3.1 Fast 作价格／速度比较，并预告 04-07 Fast 价格变化。这不是同模型同参数历史降价实测；本轮未核准分辨率、音频、质量、时长及后续价格执行的完整对照，**不把宣传比例写成玩具成本降幅**。
- 产品推断：配套短剧、IP 内容、宣传片、App 回顾视频，以及预制分支故事素材。属于离线／异步内容供给，不证明持续会话中能即时生成视频。
- 未证实：用户发话至首帧的端到端延迟、端侧执行、生成视频变成可安全执行机械动作、儿童交付许可、具体玩具采用。直接 Developer API 接入须检查 T109；预制内容的再分发及目标受众条款也不能凭本片视为已放行。

### T108｜实时 Avatar：与短片生成不同，企业接入仍有限制

**来源 T108-A**

- 题名：Introducing Gemini 3.8 Live with Live Avatar。
- URL：<https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-3-8-live-with-live-avatar/>
- 发布／事件日：**2026-09-24**。
- 定位：开篇／Asynchronous tool execution with continuous presence／A Live Avatar to fit your brand needs／Get started。
- 短引：“pairing near real-time video generation with speech”；“Custom avatar creation is currently available only through enterprise allowlisting.”
- 访问：官方 HTTP 正文 200；非仅搜索摘要。

**状态、基线、产品价值与缺口**

- 正文称 Gemini Enterprise 可用，具有视觉与音频输入、表达性视频与音频输出、口型和表情、异步工具期间持续交流；本片按文章原词记为 near-real-time，不将其改写为经过测量的固定毫秒值。
- **自定义 Avatar 的 enterprise allowlist 不可丢失**。普通 AI Studio／Gemini Developer API 账户是否可用、是否有自助接口、企业合同与地区条件，未取得独立接口正文核验；不推定与 T103 完全相同。
- 基线：公告承接 09-15 Live 模型发布，将实时可视形象作为新增功能；本轮没有与 2025 Avatar 产品的同口径质量／延迟／成本对照。
- 产品推断：有屏桌面伙伴或机器人面部屏的持续形象，比“生成完整短片后再播放”的 T107 更贴近即时会话；无屏毛绒或机械鸭并不会自动因此获得额外体验收益。
- 未证实：价格、网络带宽、功耗、并发配额、声画同步 p95、低成本硬件部署、角色定制准入与儿童服务许可；官方酒店等服务演示不是消费玩具采用。
- 未提供可据以判断端侧可用的权重／算力资料；多模态输出不等于玩具本地推理。

### T109｜仅归档已读的地区与年龄条款（三个来源）

**用途：正文可正式引用的接入条件证据。不是模型能力跃迁、不是玩具采用证据，不扩张为对所有国际云或所有企业合同的一刀切判断。**

#### T109-A｜OpenAI 支持地区

- 题名：Supported countries and territories。
- URL：<https://developers.openai.com/api/docs/supported-countries>
- 日期：正文无单一发布日期／生效日；**2026-10-10** 读取的名单快照。
- 定位：开篇警告及完整国家／地区列表。
- 短引：“Accessing or offering access to our services outside of the countries and territories listed below may result in your account being blocked or suspended.”
- 访问：官方 Markdown 形式读取成功，HTTP 200。
- 可证结论：所查名单**未列中国大陆**；不能默认直接为大陆玩具用户提供此服务。网页可打开、代理网络可连通、成人有账号都不等于获得对目标地区提供服务的许可。
- 限制：这是该来源覆盖的服务支持名单，不是中国法律结论；不证明特定第三方托管或企业协议一定同样可用／不可用。本条不提供儿童适用性放行。

#### T109-B｜Gemini Developer API 年龄及客户端条款

- 题名：Gemini API Additional Terms of Service。
- URL：<https://ai.google.dev/gemini-api/terms?hl=en>
- 日期：正文生效日 **2026-03-23**；页面显示最后更新 **2026-04-28 UTC**；访问 **2026-10-10**。
- 定位：Age Requirements／Use Restrictions／Unpaid Services／Paid Services。
- 短引：“You must be 18 years of age or older to use the APIs.”
- 关键短引：“You also will not use the Services as part of a website, application, or other service ... that is directed towards or is likely to be accessed by individuals under the age of 18.”
- 地区短引：“You may only access the Services (or make API Clients available to users) within an available region.”
- 访问：HTTP 200，英文正文读取成功。首次无语言参数响应为葡萄牙语，随后用本 URL 读取英文确认；未靠翻译摘要下结论。
- 可证结论：**不仅开发者本人要满 18 岁，面向或可能由未满 18 岁者访问的 API Client 也受禁止性限制。家长注册／成人持有 API key 不能自动消除此限制。** 不得直接将 T103／T107 写成可上线儿童玩具的推荐接入方案。
- 其他已读边界：EEA、英国、瑞士面向用户的 API Client 必须使用 Paid Services；Unpaid Services 可能用于服务改进且可有人类审阅，正文提示不要提交敏感、保密或个人信息。不能把免费试验通道用于真实儿童家庭数据而声称隐私已核准。
- 限制：本条针对引用这些条款的 Gemini Developer API／AI Studio 等服务。Gemini Enterprise、其他企业合同和潜在许可例外**本轮未核实**；既不自动套用为全部企业服务禁令，也不假定其必然允许儿童使用。

#### T109-C｜Gemini API／AI Studio 地区及年龄验证

- 题名：Available regions for Google AI Studio and Gemini API。
- URL：<https://ai.google.dev/gemini-api/docs/available-regions>
- 日期：页面 Last updated **2026-04-28 UTC**；不是地区政策首次生效日期；访问 **2026-10-10**。
- 定位：访问失败原因／Available regions 列表。
- 短引：“Age requirements ... (18+)”；“you haven't yet verified your age on your Google Account”。
- 访问：HTTP 200，官方正文成功。
- 可证结论：所查列表**未列中国大陆**；除地区外，账号可能需要年龄验证。不能将网页可以访问、某演示可以运行或成人账号可登陆当成大陆产品交付许可。
- 限制：页面指向其他企业平台选项，但本轮未核验那些通道的合同、地区、具体模型及用户年龄许可；不把导航链接当作已获准替代方案。

## 三、面向四组 40 卡的引用与方案筛选规则

1. 产品卡已有真实披露时，分别写“产品采用证据”和“技术使能证据 Txxx”；两栏不互相替代。
2. 未披露模型时，只写“该体验可与 T102／T104 等能力形成映射，具体采用未披露／未证实”，不得填入供应商型号。
3. 中国市场先区分儿童玩具、成人桌面伙伴、企业展陈，再检查地区和用户年龄。T109 是接入门槛，不是市场销量或产品竞争力证据。
4. 中国市场候选顺序可先评估 **Qwen 开放 ASR／TTS＋本地或境内自托管后端**；这只是原型候选，尚未核验中文儿童体验、商用接口条款和成本，不等于本片已交付可上线完整架构。
5. 角色和记忆：T101 对上下文管理，T104 对声线／语气；需要应用自己的授权、遗忘、纠错、角色边界及家长管理，不能由模型型号代替产品设计。
6. 实时互动：T102／T103 分别核打断、后端状态和视觉输入；T108 仅对有显示需求、满足企业准入的方案有直接意义。
7. 内容供给：T106／T107 优先按后台生成、审核、缓存、复用理解。**原型更容易制作／内容成本可能被摊销是推断，不是已发生降价或已取得正毛利。**
8. 实体动作必须经确定性的权限、状态和安全边界执行；语音模型、视频模型的工具输出或流畅口头确认，均不构成硬件动作安全证明。

## 四、成本与整链延迟：允许写什么，不允许写什么

### 成本

- 已核算术示例：`300 session-minutes × $0.05/minute = $15`，**仅 GPT-Live voice session，后台模型／工具不含在内**；不是每月无限陪伴套餐，也不是 300 分钟用户开口的固定计费。
- 禁止把不同模型、不同质量档位、不同评测、token／字符／输入分钟／输出分钟／会话分钟／视频秒数直接相除比较成本。
- 当前价格没有历史同参数基线时，不写年内降价百分比。异步 Batch 相对同步费率、另一个 Lite 型号相对 Fast、缓存命中价相对非缓存价，均不能自动视为同一玩具体验的历史降价。
- 开放权重须计推理硬件折旧、显存、并发利用率、电费、运维、网络、授权资产、审核及失败重试；不是零成本。
- 内容生产应统计“每张／每段审核通过且角色一致的可用素材成本”，而非只取一次模型调用标价。素材缓存的价值取决于复用次数。

### 延迟与可靠性

完整路径至少包括：

`采音与回声消除 → 网络上行 → 识别或原生语音模型 → 记忆检索／工具 → 合成或原生音频输出 → 下行与播放缓冲`

- 分别测首声、完整回复、用户插话到停声、任务取消／动作停止；报告 p50／p95、网络地区、硬件、并发、儿童／成人语音及噪声条件。
- TTS 的 97ms、服务器 128 并发吞吐、视频 4／6／8 秒片长，以及 near-real-time 宣传，都不是这条完整链路的结果。
- 多模态输出不等于开放权重；开放权重不等于低价玩具芯片可运行；实时理解视频不等于实时生成视频；实时生成脸部视频不等于实时安全控制机器人。
- 所有“更自然”“更便宜”“更快”若没有目标任务同口径对照，应标为官方定性声明或产品推断，并保留验证缺口。

## 五、已读反证与访问审计（不新增模型采用结论）

### 服务供给不一定单向增加：Sora API 停服记录

- 题名：Deprecations | OpenAI API。
- URL：<https://developers.openai.com/api/docs/deprecations>
- 定位：2026-03-24: Sora 2 video generation models and Videos API。
- 日期：通知 **2026-03-24**；页面列的 API 移除日 **2026-09-24**。
- 短引：“deprecation and removal from the API on September 24, 2026”。
- 访问：由最初官方域搜索结果打开，官方浏览器正文成功；没有实际发 API 请求测试停服。
- 同一 Changelog 的 **2026-03-12** 还记录 Sora 的角色参考、延长、1080p 等 API 扩充。说明“今年曾经升级”不等于截至研究日仍可用于新产品。
- 结论：本片不将 Sora 2／Videos API 作为 2026-10-10 的现行推荐方案；生命周期与迁移成本必须独立核验。这不构成另一条玩具采用证据。

### 已完成的来源顺序与失败处理

- 涉及 OpenAI 前完整读取本地 OpenAI Docs skill；第一实质检索为 `site:developers.openai.com 2026 Realtime audio release`，随后实际打开 Deprecations 官方正文，再沿官方文档读取。OpenAI 来源只使用获准的官方文档域，未用记忆猜型号。
- Google 搜索结果仅作定位，不将摘要当正文。Qwen 博客未取到正文的日期均未升格为已验证日期。
- Qwen TTS 博客浏览器超时后，转向 Qwen 官方仓库原文；没有绕过验证码、登录或 HTTPS 安全警告。
- Google 条款首个响应语言不便核对后，读取英文正文确认未成年人客户端限制；未跳过该限制。
- 官方仓库 raw／模型卡／文档 Markdown 均只读；未下载权重、未部署、未调用付费生成或上传家庭数据。
- 未搜索或核验全部行业型号；本文件选择八项可产品化映射的能力，加三份已读条款构成 T109，保留强证据与缺口，而非模型大全。

## 六、仍需后续主任务裁决／验证

- 哪些产品卡实际披露了模型或供应商；目前 T101—T108 的具体玩具采纳均为“未证实”。
- 中国市场儿童／成人目标用户如何划分；境内托管接口和企业合同的年龄、数据、模型、区域、许可与价格是否满足要求。
- Qwen 本地／自托管候选能否在目标硬件、功耗、并发与网络条件下达到儿童普通话／方言体验门槛。
- 长期记忆的删除、纠错、角色一致性，及跨月准确率；原生语音和串联 STT→文本→TTS 两种架构的同场景对照。
- 相同体验下每活跃用户成本，包括会话空闲、后台模型、工具、审核、重试与内容缓存；目前没有历史同口径总成本降幅。
- T108 的企业定制准入、显示形态收益、合同和端到端声画同步；不以发布公告替代上线许可或实物验收。

**交接状态：本片已归档 T101—T108 的能力、产品映射、来源、基线和未证实项，以及 T109 的三个地区／年龄条款来源。所有采纳、性能与成本边界保留；未改动其他文件，未执行 Git。**
## 七、主会话独立抽查记录（2026-10-10）

- 复核主体：主会话；本记录依据用户当轮转达的独立复核结果归档，**不是 Coder T1 再次联网核验**。
- 来源顺序：主会话按 OpenAI Docs 要求，先作官方域搜索，再实际打开模型页。
- 题名：GPT-Live 1。
- URL：<https://developers.openai.com/api/docs/models/gpt-live-1>
- 访问结果：主会话独立打开官方正文成功。
- 定位：模型说明、Model details、Pricing、Rate limits。
- 核对的短引／字段：full-duplex／“listen and speak at the same time”；backend agent 分离；“$0.05 per minute”；按秒计费、不向整分钟取整；backend model／tools 另计；Audio／Text 输入输出；Image／Video unsupported；Free not supported。
- 独立复核结论：确认 T102 的当前能力、模态限制、免费层不支持及计费口径。`300 会话分钟 × $0.05／分钟 = $15` 算术成立，**仅 voice，不含后台模型和工具等费用**。
- 日期证据边界：本模型页抽查**不单独证明 GA 日期**；T102 的 **2026-09-10 GA** 仍由已经归档的官方 Changelog 条目支持。当前价格不证明历史降价；本复核不新增具体玩具采用、端侧运行或实测延迟证据。