# T2｜2026 年消费电子玩具的硬件与集成使能证据

> 研究区间：2026-01-01 至 2026-10-10。访问日：2026-10-10（Asia/Shanghai）。
> 状态：T2 分析已获主会话确认；本文件是 Coder 按确认内容落盘的完整证据分片，尚待集成与独立复核。此次落盘不再扩搜。
> 范围：低价 MCU、开源云客户端、语音模组、集成开发平台、端侧小模型与资源限制、云服务计费、生产测试可复用性。不是 AI 玩具销量榜、产品采用清单，也不承担其他分片的生成模型音视频能力研究。
> 修改边界：只写本文件；不修改其他分片、根入口、render 或只读参考库；不运行 Git。用户当轮授权覆盖项目默认自动提交规则。

## 1. 可直接用于集成的判断

**证据支持：2026 年，联网 AI 硬件的原型开发、语音前端集成和软件复用路径继续增加；部分生产测试经验也更加公开。没有取得同型号、同配置、同地区、同数量条件的跨年度价格对比，因此不能量化“今年整机成本下降”。**

更具体地说，新低价硬件是“新能力可获得”，在线构建器和统一框架是“更多步骤被工具覆盖或组件化”，新声学模组是“集成路径更完整”。这些都不等于已经证明实际项目工期减少某个百分比，更不等于完整玩具的 BOM、认证、售后和长期云成本同步下降。

### 1.1 证据用语分级

- **D｜2026 有日期的增量**：有 release、官方文章或明确日期 News 支持。今年新增的对象、版本或支持范围可以确认。
- **A｜访问日可获得**：商品价格、服务条款或功能在访问日可读，但不能据此确定今年新增或今年降价。
- **P｜计划或合作公告**：能够证明宣布了合作/计划，不能证明已供货、量产或采用。
- **B｜边界或限制证据**：许可证、资源表、计费、官方未验收声明等，用于限制结论。
- **推断**：依据上述事实判断可能减少的工程步骤；不是本机实测或独立项目工期对照。

### 1.2 五环节映射总表

| 环节 | 可支持的 2026 变化 | 主要证据 | 明确不能推出 |
|---|---|---|---|
| 原型 | 新低价联网板、在线固件构建入口、更多板卡适配、自然语言工作台与成套音频前端 | T201、T202、T205、T206、T207 | 开发板单价就是整机 BOM；无需工程知识即可交付玩具 |
| 内容 | 故事/音乐播放、角色与 UI 配置、内容资源装配路径更可复用 | T202、T205、T206 | 内容生成质量、版权、儿童适龄及审核已经解决；不替代模型分片 |
| 实时交互 | 稳定媒体框架、量化唤醒模型、声学前端、打断/混音及更多外设适配 | T203、T204、T205、T207 | MCU 已本地运行完整聊天大模型；开发板表现等于玩具壳体内表现 |
| 量产 | 模组结构适配与定制入口、公开的 PCBA 测试计划和工作流参考 | T207、T209；T206提供量产边界反证 | 已通过整机认证、可靠性验收，或已证明制造成本下降 |
| 长期服务 | 设备授权、AI 按量计费与商用责任更容易核对 | T208、T202、T205、T206 | 开源客户端意味着永久免费云、无限额度、无运维或售后成本 |

### 1.3 与产品卡的关系

T201—T209 只作为**可选使能**引用。任何具体产品是否采用 ESP32、小智、Tuya、reSpeaker 或某个模型，均需该产品自己的直接证据；本分片不为任何产品生成“已采用”标签。平台适配清单也不等于所有适配板都完成同等质量的量产验收。

---

## T201｜Seeed XIAO ESP32-C5：2026 新增廉价双频联网原型选项，不是年度降价

### 来源、标题、日期与访问

1. **标题**：Meet XIAO ESP32-C5: The First XIAO Dev Board with Dual-Band Wi-Fi 6\
   **URL**：https://www.seeedstudio.com/blog/2026/01/16/xiao-esp32-c5-5ghz-dual-band-wifi6/\
   **发布日**：2026-01-16。页面公开 `article:published_time` 为 `2026-01-16T01:55:45+00:00`。\
   **更新日**：2026-01-20。`article:modified_time` 为 `2026-01-20T09:29:26+00:00`；正文也显示 Last Updated on: January 20, 2026。\
   **事件日**：文章发布/更新时宣布产品上市、官方渠道可购；第一笔订单或实际首批出货日未独立核验，不能把文章时间当出货验收时间。\
   **访问结果**：CUA 后台 iab 成功读取全文与上述公开日期元数据。另一次直接 HTTP 请求返回 403/“Just a moment...”，该次未取得正文；正常浏览器路径成功，不使用绕过验证码的方法。
2. **标题**：Seeed Studio XIAO ESP32-C5\
   **URL**：https://www.seeedstudio.com/Seeed-Studio-XIAO-ESP32C5-p-6609.html\
   **发布日期/变价日**：商品页未给出可用于年度比价的独立日期。\
   **访问结果**：HTTP 200，读取商品标题、SKU、报价、数量阶梯、仓库和规格资料；未下单、未登录、未结算。

### 正文定位与短引

- 文章 **What Makes XIAO ESP32-C5 Stand Out?**：`“the first board in the XIAO series to support 5 GHz Wi-Fi”`。这是 XIAO 系列内的首次，不能扩大为世界首款或 ESP32 首次。
- 文章 **Join the XIAO ESP32-C5 Revolution**：`“at MRSP $6.9”`，并列官方 Bazaar 和 AliExpress 销售渠道。
- 文章 **High-Performance Processing** 及商品资料：240 MHz 单核 RISC-V、384 KB SRAM；商品资料列 8 MB Flash 和 8 MB PSRAM。

### 版本、价格与许可

- **版本/型号**：XIAO ESP32-C5，商品 SKU `100010048`。2.4 GHz/5 GHz Wi-Fi 6，另支持 Bluetooth LE、IEEE 802.15.4 等连接能力。
- **发布介绍文当前正文记载**：US$6.90。文章2026-01-16发布、01-20修改，本轮未取得发布当日历史快照；这是访问日所读当前正文，不简称“已核首发价”。
- **访问日商品展示价格**：US$6.90；`10+: $6.50`。这两个价格属于不同数量条件，不是时间上的降价。
- **币种/地区/数量/税运条件**：国际商店美元展示价；页面列中国、美国、德国仓选项，存在 1pcs/3pcs、排针等选项。本轮未逐一选择地区与配置结算，不能保证所有仓库和变体均同价或有现货。税费、运费及进口费用没有形成指定收货地的落地报价；不能写成含税包邮整机价。
- **开放或商用状态**：商业销售开发板。支持 Arduino、ESP-IDF 等开发生态，不自动说明 PCB、无线栈、固件、全部第三方依赖都采用同一开源许可；本轮未完成该硬件工程全部许可审计。

### 2026 增量、环节与限制

- **分级**：D（新板/新连接选项）+ A（访问日报价）+ B（非整机成本）。
- **主要映射**：原型；次要为联网集成与实时交互的网络基础。
- **能支持**：今年在 XIAO 尺寸和开发生态内增加了 US$6.90 的双频联网选项，开发者不一定需要为 5 GHz 网络更换到另一套主控开发体系。
- **推断而非实测**：复用既有 XIAO/ESP-IDF 经验可能减少原型迁移工作；本轮没有测量实际工期、丢包或延迟改善。
- **不能支持**：MCU 今年整体降价、相同 MCU 降价百分比、所有 AI 玩具可以用此板、更不能支持“US$6.90 就是一台 AI 玩具”。
- **仍需工程**：麦克风、音频输入输出、供电、结构与电池、天线净空和整机 RF、配网/掉线重连、续航、OTA、安全处理。它本身不是完整语音开发板，也不是本地 LLM 模组。
- **缺口**：首批实际发货日、指定收货地含税含运价格、同口径旧产品价格、完整硬件许可、目标玩具实测均未取得。

---

## T202｜小智 v2.4.2：新增 Firmware Builder，降低固件定制和板卡适配准备

### 来源、标题、日期与访问

1. **标题**：Release v2.4.2 · 78/xiaozhi-esp32\
   **URL**：https://github.com/78/xiaozhi-esp32/releases/tag/v2.4.2\
   **实际读取的官方 API**：https://api.github.com/repos/78/xiaozhi-esp32/releases?per_page=12\
   **发布日/事件日**：`2026-08-06T01:03:05Z`（UTC），当日 release 公布新构建器。构建器更早的实际上线日未另证。\
   **访问结果**：官方 API HTTP 200，实际读取 tag、`published_at` 和 release body；不是只依赖搜索摘要。
2. **标题**：XiaoZhi AI Chatbot — v2.4.2 README（仓库说明）\
   **URL**：https://github.com/78/xiaozhi-esp32/blob/v2.4.2/README.md\
   **读取地址**：https://raw.githubusercontent.com/78/xiaozhi-esp32/v2.4.2/README.md\
   **版本日期**：固定在 v2.4.2；README 未另设独立发布日期。\
   **访问结果**：HTTP 200，实际读取 Firmware Flashing、Features Implemented、About the Project 等段落。
3. **标题**：MIT License — v2.4.2 LICENSE\
   **URL**：https://github.com/78/xiaozhi-esp32/blob/v2.4.2/LICENSE\
   **读取地址**：https://raw.githubusercontent.com/78/xiaozhi-esp32/v2.4.2/LICENSE\
   **访问结果**：HTTP 200，实际读取授权及版权保留条件。
4. **标题**：Release v2.5.0 · 78/xiaozhi-esp32\
   **URL**：https://github.com/78/xiaozhi-esp32/releases/tag/v2.5.0\
   **发布日/事件日**：`2026-09-10T18:38:00Z`；换算中国时间为 09-11，引用时须标时区。\
   **访问结果**：同一官方 release API 成功取得完整 body，用作后续资源约束反证，不替代 v2.4.2 的功能发布日期。

### 正文定位与短引

- v2.4.2 release 开头 **Firmware Builder (New)**：`“A new firmware builder is available”`，指向 https://xiaozhi.me/console/firmware-builder 。本轮只核验官方发布记录，未登录构建器创建项目或执行烧录。
- v2.4.2 **What's Changed**：新增 ESP32-S31 Function CoreBoard 等板卡支持，同时 `“remove unreliable acoustic provisioning”`。
- 固定版 README **Firmware Flashing**：默认连官方服务器，免费 Qwen 实时模型说明针对 `“Personal users”`。
- v2.5.0 **What's Changed**：`“keep ESP32-S31 firmware in the 4MB OTA slot”`；还有板卡配置校验、显示和驱动修复。

### 版本、价格与许可

- **版本**：客户端 v2.4.2；v2.5.0 仅用于证明后续仍有工程约束。
- **许可**：客户端 MIT，可商用；需保留版权和许可声明，软件按 AS IS 提供。该许可不自动覆盖在线构建服务、官方托管服务器、接入模型、音色、资源素材或全部依赖。
- **商用依赖**：默认云服务及其免费使用描述有个人用户范围。不能把客户端代码的商用许可外推为商业玩具永久、无限量免费接入官方云。
- **价格条件**：本证据没有硬件价格，也没有得到构建器商业订阅价、官方云的完整商业配额/SLA；软件代码无许可费不等于部署总成本为零。币种、地区、税运、采购数量不适用于代码授权；云服务条件待单独确认。

### 2026 增量、环节与限制

- **分级**：D（新构建入口与适配）+ B（许可、内存、云服务边界）。
- **主要映射**：原型；次要为内容资产装配、固件复用、长期服务责任。
- **能支持**：2026 增加在线固件构建入口和更多板卡配置，可减少本地开发环境与手工适配准备。官方新入口的存在已证实，实际节省小时数未测试。
- **旧基线**：预编译固件、免搭建开发环境刷机早于 2026 已存在；不能把“无需本地编译即可刷固件”本身称为今年首次。
- **不能支持**：所有板卡验收通过；所有用户均免费商用；本地聊天大模型。README 描述的是包含云端 ASR/LLM/TTS 或实时服务接入的客户端，本地语音唤醒是另一层能力。
- **仍需工程**：正确板卡/驱动/引脚、Flash 分区、资源包、音频缓冲、AEC 硬件、配网、OTA、鉴权与密钥保护、断网/超时/异常恢复。
- **缺口**：未实操在线构建器，未做声学或设备测试，未取得官方服务器完整商用价格与 SLA；v2.5.0 的 4 MB OTA 修复反而提醒空间预算仍需管理。

---

## T203｜ESP-GMF v1.0：稳定 API 和统一组件提高跨产品媒体软件复用性

### 来源、标题、日期与访问

1. **标题**：ESP-GMF v1.0: General Multimedia Framework, First Official Release\
   **URL**：https://developer.espressif.com/blog/2026/07/esp-gmf-v1-0-release/\
   **文章发布日**：2026-07-21，正文时间显示 21 July 2026。\
   **访问结果**：CUA 成功读取全文、Overview、组件表与 release 链接。
2. **标题**：Release v1.0 · espressif/esp-gmf\
   **URL**：https://github.com/espressif/esp-gmf/releases/tag/v1.0\
   **读取 API**：https://api.github.com/repos/espressif/esp-gmf/releases/tags/v1.0\
   **事件日**：`2026-06-23T01:23:17Z`，是 release 发布日，早于介绍文章。\
   **访问结果**：API HTTP 200，核验 tag 与 `published_at`。
3. **标题**：Espressif Modified MIT License — v1.0 LICENSE\
   **URL**：https://github.com/espressif/esp-gmf/blob/v1.0/LICENSE\
   **读取地址**：https://raw.githubusercontent.com/espressif/esp-gmf/v1.0/LICENSE\
   **访问结果**：HTTP 200，实际读取完整许可。

### 正文定位与短引

- 文章 **Overview**：`“the first official, API-stable release”`。
- **Introduction**：解释此前不同媒体框架具有各自开发模型、接口和运行机制，限制代码复用；本框架统一音频、视频及 AI 媒体应用架构。
- **Overview / ESP-GMF components summary**：官方组件提升至 1.0.x 基线，新模块包括 `esp_player`、`esp_asrc`、`esp_video_render`、`gmf_fft`；AI 音频新增 VAD/NS/DOA 等元素，板级管理迁出为独立组件。
- LICENSE：`“EXCLUSIVELY with Espressif Systems products”`，并明确禁止面向非 Espressif 产品的再分发。

### 版本、价格与许可

- **版本**：ESP-GMF v1.0；文章表中具体组件各有 1.0.0/1.0.1 等版本，不把全部组件当作同一二进制。
- **许可**：`LicenseRef-Espressif-Modified-MIT`，不是无限制普通 MIT。用于 Espressif 产品的权限与向其他平台移植、再分发的权限不同。
- **依赖边界**：媒体编解码器、算法库和第三方依赖须逐项审查，不能由主仓库许可证推断所有依赖开放。
- **价格条件**：无硬件报价、云调用价或历史工时数据。代码许可不产生可计算的整机降价；币种、地区、税运和采购数量不适用于此框架 release。

### 2026 增量、环节与限制

- **分级**：D（API 稳定基线、组件整合）+ B（平台限定许可）。
- **主要映射**：实时交互；次要为原型和后续维护复用。
- **能支持**：从多套媒体开发模型转向统一组件和稳定 API，减少重复拼接和跨项目重新组织代码的必要性。这是架构与组件复用证据，不是实际工期对照实验。
- **旧基线**：ESP-ADF 等已有音频能力，本次不是“ESP32 今年才可以播放、录音”。
- **仍需工程**：音频驱动、并发、内存与 DMA 对齐、任务调度、缓冲、资源泄漏和错误恢复、硬件适配、升级回归。
- **不能支持/缺口**：框架稳定不等于具体玩具稳定；未做设备声学、续航、可靠性、儿童安全或整机认证；没有跨年度同口径成本下降数据。

---

## T204｜ESP-SR：2026 量化 WakeNet10/10s 扩大端侧语音能力，但不是本地完整 LLM

### 来源、标题、日期与访问

1. **标题**：espressif/esp-sr v2.6.0 — ESP-SR Speech Recognition Framework\
   **URL**：https://components.espressif.com/components/espressif/esp-sr/versions/2.6.0/readme\
   **发布/事件日期**：固定版本 README 的 News 明列下述日期；组件页访问时显示 uploaded 23 hours ago，但本文件不用相对时间伪造精确上传时刻。\
   **访问结果**：HTTP 200，读取固定版本全文、News、能力/目标矩阵与仓库提交 `1a1aee2ba87dc6071dd9b961334249f0cf4256ab`。
2. **标题**：Benchmark — ESP32-S3 — ESP-SR latest documentation\
   **URL**：https://docs.espressif.com/projects/esp-sr/en/latest/esp32s3/benchmark/README.html\
   **发布日期**：本轮未取得独立发布日期；属于访问日最新资源表，不把整张表都当作 2026 新增。\
   **访问结果**：HTTP 200，读取 WakeNet、AFE、MultiNet 资源与测试条件。
3. **标题**：WakeNet Wake Word Model — ESP32-S3\
   **URL**：https://docs.espressif.com/projects/esp-sr/en/latest/esp32s3/wake_word_engine/README.html\
   **访问结果**：HTTP 200；该说明页正文仍主要描述 WakeNet9 系列，不能覆盖或否定固定版本 README 的 WakeNet10 News。资源链接指向上面的 benchmark。
4. **标题**：ESPRESSIF MIT License — esp-sr LICENSE\
   **URL**：https://github.com/espressif/esp-sr/blob/1a1aee2ba87dc6071dd9b961334249f0cf4256ab/LICENSE\
   **读取地址**：https://raw.githubusercontent.com/espressif/esp-sr/1a1aee2ba87dc6071dd9b961334249f0cf4256ab/LICENSE\
   **访问结果**：HTTP 200，实际读取许可。

### 有日期的事件、定位与短引

固定版本 README **News**：

- **2026-08-17**：发布 WakeNet10；支持 `w16a16` 与默认 `w8a16` 量化，采用 ESP-DL。
- **2026-09-30**：WakeNet10 支持中文、英文、日文、法文、德文、西班牙文、葡萄牙文。
- **2026-10-09**：ESP-SR v2.6.0 开始支持 WakeNet10s，`“can run on chips without PIE (SIMD) instructions”`，列举 ESP32、C3、C5、C6。
- **旧基线 2025-04-21**：同一 README 已记录 WakeNet9s 可在无 PSRAM、无 SIMD 芯片运行。因此不能写成“低端 MCU 直到 2026 才能本地唤醒”。

### 版本、资源、许可与价格

- **版本**：ESP-SR v2.6.0；本次增量涉及 WakeNet10/10s。`w8a16` 是权重 8 bit/激活 16 bit，不应笼统写成所有计算均为 8 bit。
- **能力类型**：唤醒词和声学处理是端侧小模型；MultiNet 的有限离线命令识别也不等于开放式聊天 LLM 或任意语音转写。
- **访问日官方 S3 benchmark**：

| 模型/配置 | RAM | PSRAM | 平均每帧运行时间 | 帧长度 | 使用边界 |
|---|---:|---:|---:|---:|---|
| Quantised WakeNet9，3 channel | 20 KB | 347 KB | 4.3 ms | 32 ms | 旧模型资源参考，不冒充今年新增 |
| Quantised WakeNet10，3 channel | 17 KB | 523 KB | 7.1 ms | 32 ms | 文档注明默认检测模式 DET_MODE_3CH_90 |

- 两行不能简单转成全面优劣或识别质量结论，但足以反驳“新模型所有资源都下降”。WakeNet10 的 PSRAM、每帧计算时间在所列表格中高于对应 WakeNet9 行；**WakeNet10s 的同条件资源表本轮未取得**。
- Benchmark 中距离/噪声识别率表明确基于 **ESP32-S3-Korvo V4.0 和 WakeNet9 (Alexa)**，不能移植为 WakeNet10/10s 性能。表格中的 AFE/模型消耗也不是 Wi-Fi、GUI、音频缓存等全部应用消耗之和。
- **许可**：ESPRESSIF MIT License 对使用在 Espressif 产品上的软件授予免费权限；不可不加限定地外推至其他平台。README 另提醒唤醒词品牌、商标及名称权利须获得合法使用授权。没有取得全部模型训练管线、权重及第三方依赖的统一开放许可证明。
- **价格条件**：无硬件商用报价或定制唤醒词报价；不把已有组件免费使用推为全部服务免费。币种、地区、税运和采购数量不适用于组件资源表。

### 环节、推算与边界

- **分级**：D（模型与目标/语言扩展）+ A（访问日资源表）+ B（能力、资源、许可限制）。
- **主要映射**：实时交互；次要为原型语言适配。
- **能支持**：预制量化模型和更多目标芯片支持减少自行实现唤醒算法的工作。今年新增的是模型代际、语言与目标支持，不是首次端侧唤醒。
- **推算，不是实测**：10^9 参数 × 4 bit ÷ 8 = 500,000,000 byte，即约 500 MB（十进制）或 477 MiB，仅权重；还未计入运行时、激活、KV cache 等。因此几 MB PSRAM 的开发板不能因“支持量化”就被描述成可本地运行完整 1B 聊天模型。
- **仍需工程**：真实儿童发音、误唤醒/漏唤醒、口音、噪声和播放音量测试；麦克风布局、声学回采、模型选择、内存与调度预算。
- **缺口**：未测本机，未取得 WakeNet10s 同条件资源/识别率表，未对模型性能或开发成本作独立复现。

---

## T205｜TuyaOpen 2026 release：交互组件与外设适配更完整，成熟机电软件可继续复用

### 来源、标题、日期与访问

1. **标题**：TuyaOpen 1.6.0 Release Notes\
   **URL**：https://github.com/tuya/TuyaOpen/releases/tag/v1.6.0\
   **发布/事件日**：`2026-01-21T10:22:54Z`。
2. **标题**：TuyaOpen v1.9.0 Release Notes\
   **URL**：https://github.com/tuya/TuyaOpen/releases/tag/v1.9.0\
   **发布/事件日**：`2026-07-22T09:08:19Z`。
3. **实际读取的官方 release API**：https://api.github.com/repos/tuya/TuyaOpen/releases?per_page=12\
   **访问结果**：HTTP 200，读取 2026 各版 body 和日期；同时取得 2025 旧版本基线。
4. **标题**：TuyaOpen v1.9.0 README / Apache License Version 2.0\
   **URL**：https://github.com/tuya/TuyaOpen/blob/v1.9.0/README.md\
   **URL**：https://github.com/tuya/TuyaOpen/blob/v1.9.0/LICENSE\
   **读取地址**：https://raw.githubusercontent.com/tuya/TuyaOpen/v1.9.0/README.md\
   **读取地址**：https://raw.githubusercontent.com/tuya/TuyaOpen/v1.9.0/LICENSE\
   **访问结果**：均 HTTP 200；实际读取许可证及 Disclaimer and Liability Clause。
5. **旧基线**：https://github.com/tuya/TuyaOpen/releases/tag/v1.3.1 ，发布 `2025-06-09T08:38:39Z`；API body 明列新增 Otto Robot AI 应用。只作年份校正，不作为 2026 新增。

### 正文定位与短引

- v1.6.0 **New Features**：`“Agent-triggered music/story playback functionality”`；设备 MCP 内置查询设备信息、切换模式、调音量、拍照，并提供扩展注册 API。
- v1.6.0 **AI APIs Update / New audio_player Audio Playback Service Component**：Tuya AI API 升至 V2.1，新增 OPUS 上报、对话模式/自定义 UI、前后台流抢占或混音，以及多个媒体源和解码格式。
- v1.9.0 **New Features**：Wi-Fi DTIM 低功耗及 `ultra_lowpower_demo`；更多 T5AI/ESP32 等板卡、相机、IMU、SD 卡适配及 Otto ST7789 V1 屏幕配置。
- v1.9.0 **Bug Fixes / LCKFB_T5AI_TOUCH Hardware AEC**：没有 MIC2 回采回路时禁用硬件 AEC，以修复语音交互异常。

### 版本、许可与价格

- **版本**：框架 v1.6.0 / v1.9.0；v1.6.0 的 Tuya AI API V2.1 是接口版本，不等于整个开源框架版本号。
- **许可**：主框架 Apache-2.0；README 明确第三方子模块独立更新，并要求商用者自行完成全面功能、安全测试及承担相关责任。
- **商业依赖**：平台云授权、模型、ASR/TTS、音色和内容权利与框架许可证分离，详见 T208。不能写成全部软硬件及云服务完全开放免费。
- **价格/数量/地区/税运**：release 未给硬件价格或商用云费；软件框架本身不是采购 BOM。无同口径年度降价证据，也无本轮可验证的待机功耗下降百分比。

### 环节、增量与限制

- **分级**：D（交互/外设与电源管理适配）+ B（硬件 AEC 和商用责任）。
- **主要映射**：原型、实时交互、内容播放；次要为成熟机电控制复用。
- **能支持**：今年更多音乐/故事播放、混音、设备工具调用、显示与传感器代码可直接组合，减少从空白代码实现这些功能的步骤。新版 DTIM 示例提供电池设备优化入口，但并无通用续航承诺。
- **旧基线**：Otto AI 示例在 2025 年已存在；2026 新屏幕配置不应包装成今年才出现机器人/3D 打印路线。
- **仍需工程**：舵机限位与扭矩/供电保护、屏幕和音频驱动、AEC 回采、电池状态与功耗测量、异常动作约束和安全测试。
- **内容边界**：播放故事/音乐以及配置角色不授予对应 IP、音色或版权，也不能证明儿童适龄。
- **缺口**：没有实际设备测试、工期对照或功耗复现；没有审计全部第三方子模块和云服务合同。

---

## T206｜Tuya Cobuilder：2026 新工作台整合多个原型环节，官方明确不等于量产验收

### 来源、标题、日期与访问

1. **标题**：涂鸦智能发布2026年Q2及H1财报：推动AI能力在真实设备和实际场景中落地\
   **URL**：https://www.tuya.com/cn/news-details/Kfw78hyi7htuk\
   **文章发布日**：正文显示 **2026-08-25**；不能采用搜索摘要的 08-24 代替正文。\
   **事件日**：文中明确 **2026 年第二季度上线 Tuya Cobuilder**，即 04-01—06-30 范围；本轮没有进一步核准某一天为首发。\
   **访问结果**：CUA 最初经搜索结果跳转出现导航超时，随后在最终官方 URL 成功读取全文。财务数值及销量内容不是本条技术论据。
2. **标题**：Tuya Cobuilder（官方产品与常见问题页面）\
   **URL**：https://www.tuya.com/cn/cobuilder\
   **发布日期**：页面未给独立发布日期；功能与额度只按访问日现状使用。\
   **访问结果**：HTTP 200，实际读取产品能力与完整 FAQ；未注册、登录、生成、编译或烧录项目。

### 正文定位与短引

- 财报 **夯实开发者生态**：第二季度上线端到端系统，通过自然语言覆盖“**从产品构想到真机验证的核心开发流程**”。
- 产品 FAQ **Tuya Cobuilder 目前支持哪些硬件？**：固件生成、编译和烧录当前支持 T5 系列开发板，其他品牌后续扩展，具体型号以界面为准。
- 产品 FAQ **Cobuilder 生成的结果可以直接用于量产吗？**：“**AI 生成结果不等于已经通过量产验证**”。
- 产品 FAQ **Tuya Cobuilder 如何收费？**：每账号每自然月 2,000 免费资源点，最多同时运行 3 条会话。

### 版本、许可、价格与商业条件

- **版本**：商业云工作台，未公开语义化版本；不能把页面当前能力全部定年为第二季度首发时就有。
- **开发能力**：自然语言产品定义、App UI、智能体与受支持硬件固件；TuyaOpen 框架支持 ESP32 不代表 Cobuilder 访问日固件生成功能也支持 ESP32。
- **开放状态**：Cobuilder 不是已验证开源的全套平台；依赖涂鸦账号与平台。底层 TuyaOpen 的 Apache-2.0 不等于云工作台本身开源。
- **访问日价格条件**：Free 层按账号/自然月计 2,000 资源点，同时 3 会话；付费加油包价格以产品内购买页为准，本轮未取得。数字资源无运费，付费币种、税务及各区域适用价格未核。**开发工具资源点不是出货设备的语音云免费额度**。
- **其他边界**：FAQ 说明模型按功能场景与数据区域提供，当前不支持接入或替换为用户自有大模型；这是 Cobuilder 工作台的限制，不能混同于所有 Tuya 设备端方案的模型接入能力。

### 环节、增量与限制

- **分级**：D（2026 Q2 上线）+ A（访问日支持/额度）+ B（量产与硬件范围限制）。
- **主要映射**：原型、内容/角色配置、UI 与固件整合；量产只提供边界反证。
- **能支持**：今年增加一条将多个分散开发环节串进同一工作台的路径，可能减少入口切换和手动串接。未做真实项目计时，不接受“缩短 X%”或“几分钟就能量产”的外推。
- **仍需工程**：检查 AI 生成结果、硬件适配、功能和异常测试、安全与合规、目标地区服务能力、数据驻留及正式商业合同。
- **缺口**：精确首发日、最初上线版本功能清单、加油包实际价格、真实开发成功率与量产效果均未验证。

### T206-P｜JoyInside 联合方案补充：明确是计划证据，不是量产交付

- **标题**：涂鸦智能与京东JoyInside达成战略合作，加速AI硬件走向市场的快车道。
- **URL**：https://www.tuya.com/cn/news-details/Kg0o37a53kf34
- **发布日/事件日**：2026-08-26；正文说当天在深圳 IOTE 期间宣布并签约。
- **访问结果**：CUA 成功读全文；另一次 HTTP 200 读取同一正文。
- **定位/短引**：中部方案说明“**将……推出适配JoyInside的AI硬件方案**”；后文“计划从AI玩具、智慧家庭、机器人、健康养老等场景起步”。
- **版本/许可/价格**：未给联合模组型号、正式 SDK release、开源许可、MOQ、NRE、税运或可核验量产报价；商业合作方案。
- **映射**：潜在硬件—云集成，分级 P。
- **只支持**：2026 存在减少多方适配的联合方案规划。
- **不支持**：联合模组已批量供货、标准硬件已上市、费用已下降、具体玩具已经采用；不使用电商流量扶持、排名或销量宣传作技术验证。

---

## T207｜reSpeaker Flex：2026 新分体语音前端减少声学与结构集成重复工作

### 来源、标题、日期与访问

1. **标题**：Introducing reSpeaker Flex: The Smart Ear for Robotics and Embedded AI\
   **URL**：https://www.seeedstudio.com/blog/2026/04/09/introducing-respeaker-flex-the-smart-ear-for-robotics-and-embedded-ai/\
   **发布日**：公开元数据 `2026-04-09T10:20:55+00:00`。\
   **更新日**：公开元数据 `2026-04-17T02:13:20+00:00`，与正文 Last Updated on: April 17, 2026 一致。\
   **事件日**：这是新产品正式介绍记录；第一批实际交付日未单独核验。\
   **访问结果**：CUA 成功读取全文及上述公开元数据。
2. **标题**：Getting Started with reSpeaker Flex\
   **URL**：https://wiki.seeedstudio.com/respeaker_flex_introduction/\
   **发布日期**：未取得独立发布日期；按访问日规格说明使用。\
   **访问结果**：HTTP 200，实际读取芯片、接口、固件、供电、产品变体和资源链接。
3. **标题**：reSpeaker Flex XVF3800 Circular-4 with XIAO ESP32S3 | AI Mic Array for Robotics and Embodied AI\
   **URL**：https://www.seeedstudio.com/reSpeaker-Flex-XVF3800-Circular-4-with-XIAO-ESP32S3-p-6739.html\
   **发布日期/价格生效日**：未给可用于历史比价的独立日期。\
   **访问结果**：HTTP 200，取得 SKU、美元报价、10+ 阶梯、中国仓及变体信息；未结算。
4. **标题**：reSpeaker Flex XVF3800（官方仓库）\
   **URL**：https://github.com/respeaker/reSpeaker_Flex\
   **API**：https://api.github.com/repos/respeaker/reSpeaker_Flex\
   **仓库创建日**：`2026-03-30T06:47:24Z`，不是上市或固件发货日。\
   **访问结果**：仓库和目录 API HTTP 200；根目录列 README、python_control、xmos_firmwares、.github，没有 LICENSE，API `license` 为 null。
5. **标题**：reSpeaker Flex XVF3800 Firmware\
   **URL**：https://github.com/respeaker/reSpeaker_Flex/blob/main/xmos_firmwares/README.md\
   **读取地址**：https://raw.githubusercontent.com/respeaker/reSpeaker_Flex/main/xmos_firmwares/README.md\
   **访问结果**：HTTP 200，实际读取 `.bin` 格式、USB/I2S 变体和 v1.0.0—v1.0.4 changelog。另读 Python 控制脚本开头，未见许可头，不能据此断言整仓无任何隐含权利。
6. **失败记录**：https://api.github.com/repos/respeaker/reSpeaker_Flex/releases?per_page=10 返回 `fetch failed`；本轮未取得每个固件 tag 的准确发布日期，不以仓库创建日期补填。

### 正文定位与短引

- 发布文章 **Innovative Modular Split Design Microphone Array**：核心处理板与麦克风阵列分离，由 FPC 连接，可以把阵列放在设备外壳合适位置、处理板远离电机和舵机。
- **Developer-Friendly Integration / Preconfigured Variants**：USB 与 I2S 预配置固件，支持切换固件；有无 XIAO 版本预装模式不同。
- Wiki **Features / Main Components**：XMOS XVF3800，AEC、AGC、DoA、波束形成、VAD、降噪和去混响；USB UAC 2.0 或 I2S，圆形/线形四麦阵列。
- 固件 README **Introduction**：`“contains firmware images”`，命名格式以 `.bin` 结尾。可下载二进制不等于声学算法源代码开放。

### 版本、价格、许可与交付条件

- **硬件型号**：XMOS XVF3800；本次核价为带 XIAO ESP32S3 的圆形四麦版本，SKU `100070894`。
- **软件版本**：仓库固件 changelog 当前为 v1.0.4。Wiki 另将 XVF3800 处理器固件标为 v3.2.1；这两处版本处于不同说明上下文，未核清层级关系，不直接等同或合并，也不据此指定烧录版本。
- **访问日价格**：US$60.90；10 件以上 US$55.90。这个报价只绑定所读 SKU，不能套到无 XIAO、线形阵列或核心板单件。
- **地区/税运/数量**：商品显示中国仓；未指定收货国、未结算，税费和运费没有核成落地价。10+ 是采购数量条件，不能作为年度降价。未核是否包含目标整机所需扬声器、电池、充电、电源适配器、外壳等，不能作为整机 BOM。
- **许可**：商售音频模组；公开 Python 控制脚本和二进制固件。根目录无 LICENSE、API 许可字段空，未确认可任意再分发、商用修改或开放全部声学算法的许可；不可统称“全开源”。
- **定制/量产**：文章列麦阵形状、硬件修改、声学调参的定制选项，但未提供项目级 MOQ、NRE、交期、良率、认证和售后报价。

### 环节、增量与限制

- **分级**：D（2026 新分体模组）+ A（当前价格和固件）+ B（许可和整机边界）。
- **主要映射**：实时交互、原型；次要为从原型向产品结构迁移。
- **能支持**：现成音频前端、预配置接口及分体结构减少自行设计全部声学处理和固定一体麦阵位置的必要性。可复用的是前端/接口及结构集成路径，不是“今年首次有 AEC 或四麦”。
- **不能支持**：板上完整离线聊天大模型；所有下游 STT/LLM/TTS 都在本地；官方远场演示距离在所有玩具壳体和电机条件下成立。
- **仍需工程**：壳体声孔、腔体、麦距和 FPC、串扰与电机噪声、扬声器回采和音量、供电、电池续航、算法调参、与云或主机连接、安全限制。
- **缺口**：未做本机声学复现；未核固件 release 时间、完整商用再分发许可、首发价与年度降幅、实际定制量产条款。

---

## T208｜Tuya 当前计费：原型能低成本起步，但设备授权不覆盖无限 AI 用量

### 来源、标题、日期与访问

1. **标题**：TuyaOpen Licensing & Pricing\
   **URL**：https://tuyaopen.ai/pricing\
   **发布日期/事件日**：页面没有独立发布日期或价格变更日期；本条只代表 2026-10-10 可读取的现行价格和条件。\
   **访问结果**：HTTP 200，实际读取 Plans、How licensing works、Compare tiers 和 FAQ，未领取授权、登录或购买。
2. **标题**：Agent Metering and Billing\
   **URL**：https://developer.tuya.com/en/docs/iot/ai-agent-price?id=Kegb2s2shaj4d\
   **更新日**：页面显示 `2026-09-01 08:32:00`，未注明时区；不可当作所有价格在该日首次生效的证明。\
   **访问结果**：HTTP 200，实际读取计量周期、费用公式、ASR/TTS/模型价格、扩展能力和减免说明。没有仅凭搜索摘要报价。

### 正文定位与短引

- Pricing **FAQ / Is this a monthly subscription?**：设备授权一次性，但 AI 超出日免费额后 `“charged per use”`。
- Billing **Fee structure**：`“Total fee = Model fee + AI voice fee + Extended capability fee - Waived fee”`。
- Billing **AI voice fees**：ASR 按输入音频时长、TTS 按输出字符数计费；模型另按 token 消耗。
- Pricing **2 starter licenses**：每开发者可领 2 个开发调试设备授权；不是任意量产数量免费。

### 版本、价格及适用条件

- **版本/方案**：TuyaOpen Open Source、IoT Connection、AI + IoT；平台服务未提供统一语义版本。TuyaOS 授权码不能直接当作 TuyaOpen 专用授权使用。
- **开源本地层**：本地/离线项目无 Tuya Cloud 授权要求；第三方 API 项目不因此免除第三方收费。
- **设备授权**：

| 项目 | 访问日展示价格 | 计量/范围 | 不包含的推断 |
|---|---:|---|---|
| IoT Connection | US$0.69/设备 | 一次性云连接授权；页面约写 ¥5 | 不是完整 AI 用量包或整机价格 |
| AI + IoT | US$1.67/设备 | 一次性；页面约写 ¥12；附每日 AI 免费额度 | 不是无限量模型/ASR/TTS 永久免费 |
| 开发调试 | 2 个免费设备授权 | 需平台账号，原型调试用途 | 不能直接扩展到全部出货设备 |

- **汇率边界**：约人民币数字是页面近似换算，不把它们当作独立人民币合同报价；没有自行换汇或计算降幅。
- **ASR/TTS 平台价目表示例**（只选用以说明费用结构，不替代模型音视频分片）：

| 服务 | 指定供应商/模型 | 页面人民币价格 | 数量/单位与限制 |
|---|---|---:|---|
| ASR | ALIYUN paraformer-realtime-v2 | ¥0.13 | 每输入音频小时，指定模型报价 |
| TTS | ALIYUN cosyvoice-v3-flash | ¥1.00 | 每 10,000 输出字符，指定模型报价 |

- 模型 token、其他语音模型、音色克隆、搜索、历史总结、事件记忆等可产生额外费用；不能只取最低一项作为全链路对话成本。
- **地区/税费/运费/批量条件**：数字服务无运费；本轮没有确认指定账号服务区域、税务处理、各市场可用模型、企业批量折扣或合同保价。企业/初创/教育及规模部署可另询价，不拿公开小量价替代量产合同。
- **免费额缺口**：页面说明有每日额度和超额计费，但本轮未取得明确数值、所有减免条件或账号内实际权益。不能自行假定“轻度使用必然免费”，厂商概括不等于用户使用模型。

### 环节、增量与限制

- **分级**：A（访问日可获得价）+ B（持续服务成本）；不是 D 类年度降价。
- **主要映射**：长期服务；次要为原型和语音云接入。
- **能支持**：开发阶段可用小量免费授权起步；对云连接、模型、ASR/TTS 和扩展能力已有公开计费入口，便于预算。
- **不能支持**：今年同口径价格下降；一次设备授权覆盖终身 AI 费用；开源框架免费等于完整商业方案免费。
- **仍需工程/运营**：每设备身份及密钥、消费监控与封顶策略、超额/欠费处理、模型和音色可用性、断网降级、账号与云运维、隐私/儿童数据、内容安全、客服和售后。
- **不作估算**：没有统一每天音频时长、输出字符、输入输出 token、用户留存、免费额和活跃率，故不估每玩具每月费用或相对历史降幅。

---

## T209｜Seeed 2026 产测公开指南：更多可复用参考，不等于整套软件已完整开源

### 来源、标题、日期与访问

- **标题**：Open-Source Modular PCBA Testing: A Complete Guide from Hardware to Test Workflow。
- **URL**：https://www.seeedstudio.com/blog/2026/10/08/seeed-fusion-open-source-modular-pcba-testing-a-complete-guide-from-hardware-to-test-workflow/
- **发布日**：永久链接日期 2026-10-08，访问日正文显示 2 days ago，二者一致。本轮未读取该文绝对发布日期元数据，不补造具体时刻。
- **事件日**：可确认本指南在该日期公开；测试架构、内部软件何时首次研发或在工厂使用，正文没有给出。
- **访问结果**：CUA 成功读取完整正文、配置示例、参考项目与内部软件说明。没有下载或运行工具，也未核验到完整开源软件包与许可。

### 正文定位与短引

- 开头：`“Universal Test Box → Product-Specific Adapter Board → Configurable Test Software”`。
- **Why Use a Modular Test Architecture?**：对比传统产品专用测试板与通用测试盒加适配板，说明每个产品主要变更接口映射和测试流程。
- **Software Test Framework / Reference Project**：以 reSpeaker Flex XVF3800 Core Board with XIAO 为例，公开测试计划、接口资源映射和 INI 工作流，覆盖电源、GPIO、USB/I2C/I2S、固件、SN 等项目。
- **Reference Test Software**：`“Seeed uses an internal test application”`。这限制了标题中 Open-Source 的可外推范围。

### 版本、价格与开放状态

- **版本/对象**：通用测试盒、产品适配板与 `Seeed_Factory_Auto_Test_Tool` 工作流架构，参考对象是带 XIAO 的 reSpeaker Flex Core Board；正文没有给统一正式软件版本。
- **公开程度**：实际读到配置示例和架构说明，但未核验完整 UI/执行引擎/驱动源码、全部硬件设计包及其许可证。不称为“整套产测系统已完整开源”。
- **时间边界**：正文说 newer software 支持图形拖拽，没有明确该功能首次发布日，不能直接作为 2026 新功能计入。
- **价格条件**：没有测试盒、治具、适配板、NRE、软件部署、节拍和产线服务报价；币种、地区、税运、MOQ 均未核。文章比较的是架构可复用性，不是财务成本对照数据。

### 环节、增量与限制

- **分级**：D（2026 新公开指南）+ B（完整开源/量产成本边界）；证据强度低于固定 release，不作为核心技术突破。
- **主要映射**：量产准备与生产测试工程复用。
- **能支持**：今年公开了可直接参考的真实产品测试规划、资源映射和步骤配置；新项目可借鉴通用资源加产品适配板的方式，避免所有测试能力从零重新规划。
- **不能支持**：2026 才发明模块化产测；完整软件可免费商业使用；已减少某百分比制造成本；所有 PCBA 项目直接套用同一测试阈值。
- **仍需工程**：产品测试覆盖、接触治具和适配板、测量校准、误判/漏判、节拍与良率、追溯、日志及数据安全、实际维修与产线回归。
- **认证边界**：PCBA 功能测试不是整机 EMC/无线、电池/电气、机械/材料或儿童玩具安全验收。适用要求由产品定义和销售地区确定，本轮未做法规清单审计。
- **缺口**：完整源码和许可、厂内首用时间、外部可购买测试套件、服务报价、目标玩具生产效果均未取得。

---

## 2. 横向校正：不要混淆的成本与能力

### 2.1 成本分层

以下是预算结构提醒，不是已经取得报价的 BOM：

1. **开发板/模组**：T201、T207 的展示价只覆盖特定商品。
2. **完整硬件与制造**：还可能包含麦克风/扬声器、屏幕、执行器、PCB、保护/充电、电池、结构材料、线束、装配、烧录、测试、损耗、包装和运输。是否包含某项须由实际 SKU/BOM 判断。
3. **一次性工程**：结构与声学设计、PCB 与治具、固件集成、NRE、工具、验证及适用认证。
4. **持续服务**：设备授权、模型/语音调用、记忆/搜索等功能、后台和安全维护、内容与隐私运营、客服、退换/售后。

本轮没有形成上述四层的统一报价；不能将板价补成整机成本，也不能用开源许可费为零推导工程费为零。

### 2.2 端云分层

- 本地 VAD、唤醒词、降噪、AEC、有限命令识别：端侧小模型/声学功能。
- 小智、TuyaOpen 等：设备端交互、音频传输、云接入与控制组件。
- 云端 ASR/LLM/TTS：受模型、网络、区域、额度与商业条款约束。
- 完整产品：还需电源、结构、运动安全、儿童交互边界、内容/隐私、可靠性和服务保障。

**开发板 ≠ 完整语音产品；开源客户端 ≠ 本地大模型；演示跑通 ≠ 可量产认证玩具。**

### 2.3 3D 打印与成熟机电

- 本轮未取得同口径的 2026 年 3D 打印或舵机/执行器价格、性能、生产效率进一步改善的强证据。
- 可以把成熟结构、打印件、舵机及社区机器人方案作为既有基线，不将其自动计为今年新增的门槛下降原因。
- T205 的今年变化是软件适配、示例和接口复用；Otto AI 示例在 2025 年已经存在。
- T209 的机械治具说明不能外推为消费玩具外壳的 3D 打印突破。

## 3. 访问失败、未采纳资料与研究限制

### 3.1 访问过程中的具体问题

| 对象/URL | 实际结果 | 处理与可用性 |
|---|---|---|
| https://www.seeedstudio.com/blog/wp-json/wp/v2/posts?after=2026-01-01T00:00:00&before=2026-10-11T00:00:00&search=XIAO&per_page=100 | HTTP 请求等待导致执行超时，未取得可用正文 | 不据此得出发布结论；改用实际可读的官方文章，不重复扩搜该 API |
| https://www.seeedstudio.com/blog/2026/01/16/xiao-esp32-c5-5ghz-dual-band-wifi6/ | 一次直接 HTTP 为 403/Just a moment | CUA 正常加载后读到全文和公开元数据；未解验证码、未绕安全页面 |
| https://www.seeedstudio.com/blog/2026/02/12/monthly-wrap-up-for-january-2026-embedded-systems-iot-solutions-and-hardware-prototype/ | 初次导航处于挑战/空正文状态，后续正常页面出现 | 只作发现线索，不承担本文件任何核心发布/价格结论 |
| https://www.tuya.com/cn/news-details/Kfw78hyi7htuk | 搜索跳转时导航超时，最终页随后可读 | 已实际读取正文，发布日期采用 08-25 而不是搜索摘要 08-24 |
| https://api.github.com/repos/respeaker/reSpeaker_Flex/releases?per_page=10 | fetch failed | 固件各 tag 发布日保留未确认；README changelog 不能替代时间戳 |
| Google 的一次直接 HTTP 搜索请求 | 返回重定向/反馈提示，未得到正常检索正文 | 没有将该响应当证据；后续用正常 CUA 页面找到官方来源 |

未登录或绕过付费内容，未执行下载获得的代码，未产生硬件烧录、上电、购买或云账号变更。

### 3.2 旧材料没有冒充今年增量

- 查询 https://api.github.com/repos/espressif/esp-dl/releases?per_page=12 得到的最新 GitHub release 是 **v3.2.0，2025-10-23**，不能据此称 ESP-DL 在 2026 发布该版。本分片的今年端侧模型证据改用有明确 News 日期的 ESP-SR/WakeNet10/10s。
- WakeNet9s 无 PSRAM/无 SIMD 支持来自 **2025-04-21**；T204 已保留旧基线。
- TuyaOpen Otto AI 示例来自 **2025-06-09 v1.3.1**；T205 不将其整套算作 2026 新方案。
- 小智预编译固件、云客户端基础路线早于 2026；本分片只把有 release 支持的新构建入口、适配和修复定年为今年增量。
- 仅在搜索结果看到的其他旧语音板价格和文章，没有作为已核验正文纳入主证据。

### 3.3 未解决且不应继续无限扩展的问题

- 同型号、同配置、同数量、同地区、同税运口径的历史价格降幅：未取得，不估算。
- 新工具真实开发周期缩短量：未做对照实验，仅确认可用功能和减少重复步骤的机制。
- 目标玩具的整机 BOM、MOQ、NRE、认证、良率、返修和长期服务合同：未取得。
- reSpeaker 完整算法/软件许可、产测整套源码许可及固件 tag 日期：未核清。
- Tuya 账号内免费 AI 数量、指定区域最终计费、商业 SLA、小智官方商用云条款：未取得完整依据。
- 任何产品卡的实际采用：不由本分片推断，留给对应产品直接证据。

## 4. 集成建议与独立复核重点

### 4.1 优先采用顺序

- 核心有日期增量：**T201、T202、T203、T204、T205、T206、T207**。
- 持续服务成本边界：**T208**。
- 生产测试参考、保守使用：**T209**。
- 计划性补充：**T206-P JoyInside**，不得写成已交付模组。

### 4.2 推荐表述

> 2026 年，可复用客户端、稳定媒体框架、预训练端侧唤醒模型、模块化语音前端和集成开发平台继续增加，使“做出能联网、能听说的原型”更容易。向可售玩具迈进时，工程工作并未消失，而是更多集中到真实声学环境、结构与电源、生产测试、安全合规及持续云服务。现有报价能说明部分硬件和平台已可获得，不能直接证明同口径的年度整机降价。

### 4.3 禁止外推

1. “2026 年开发板/整机 BOM 下降 X%”。
2. “开源云客户端 = 本地完整 LLM = 免费商业服务”。
3. “厂商演示/开发工具生成 = 量产与认证通过”。
4. “平台合作公告 = 某具体产品已采用”。
5. “3D 打印、舵机、Otto 今年才让 AI 玩具成为可能”。
6. 把供应商声明的低延迟、远场距离或节省工期写成本机实测。

### 4.4 复核重点

- T201/T207 的发布日期、更新时间、当前价格与实际出货时间分别标注。
- T203 release 在 06-23，文章在 07-21，不互相替代；许可是平台限定 Modified MIT。
- T204 WakeNet9/10 表格条件和资源层级，特别避免把 WakeNet9 的识别率当 WakeNet10/10s 测试。
- T206 只核到第二季度上线，T5 支持和资源点属于访问日 FAQ；JoyInside 正文未来时不得升级为交付。
- T208 美元授权、人民币模型费率、日免费额度、开发工具资源点是不同计量层，不混算。
- T209 标题 Open-Source 与正文 internal test application 的差别必须保留。

## 5. 本文件交付状态

- 完整 T201—T209、精确来源 URL、原文标题、日期、正文定位与短引、访问失败、型号版本、价格和许可证边界已落盘。
- 无图片生成、无用户图片附件归档事项；未下载远程媒体。
- 本轮不再扩搜；未执行任何硬件测试、安装、运行外部代码、付费、登录或云资源创建。
- 仅允许修改本文件；不运行 Git、不修改根入口和 render。链接与资料的独立核验由后续审查处理，不能把本文件状态当成审查已通过。
