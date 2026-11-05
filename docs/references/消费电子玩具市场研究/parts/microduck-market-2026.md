# Microduck市场补录：X11开源社区平台与研究框架修正

> 观察日：2026-10-10。Solvelite Analyst-Coder补片；范围仅Microduck，不重做全市场。D101—D105为5条新增证据编号，**不是报告原附录D**。旧229编号与原40卡保留，现行234编号／41覆盖＝37消费核心基线＋3邻接＋1开源平台，不是41款已售产品。独立审查与版本同步由主会话办理。

## 结论与遗漏原因

用户称“Microduck这么大的爆款”为用户判断；公开资料能进一步确认：官方主仓9,276 stars／1,199 forks、独立训练栈及教程／复刻／板件补充构成显著社区信号（D105），但全球销量爆款仍无证。遗漏来自原取样偏零售成品、财报与电商，未给开源DIY、创作者内容和二次开发平台独立入口；不是Microduck不重要，也不应以没有GMV把社区价值降为零。

**为什么值得看：**小型双足、头喙与全身动作形成可辨识的角色表达；运动本身就是玩乐价值，不必先有LLM对话。官方“内置动作→仿真重训→部署→分享”以及社区教程／适配板把从零自研拆成可复用步骤，为动作内容、套件／备件、装配支持与AI二次开发提供候选路径。这里的低门槛是相对从零研发，不是零装配／零算力成本；变现与持续参与待验证。

## 分开比较，不拼成一台不存在的机器人

| 口径 | 已核身份／参数 | 用途与边界 |
|---|---|---|
| 官方2026 Microduck成品预售 | 25cm、约0.8kg、15电机、RK3566、相机／ToF／双IMU；美国展示USD399未含税运 | D101当前产品；预售新订单估计4—6个月，不是现货验收；不由旧资料指定其舵机SKU |
| A社区XL330教程路线 | Pi Zero 2 W／OpenRB／Dynamixel XL330，教程及镜像入口 | D104复刻资料；供电／训练／价格不回填官方现款或C线 |
| B复刻研究 | 同时有XL330与HD-1910版本；机械、协议、CAD许可分开 | 只读资料与上游作者记录；不是本项目已经完成，过时IMU全称断言不采纳 |
| C社区HD-1910路线 | 本项目选型HD-1910-C001×15；社区PCB、GD32固件、主机工具与飞特适配补丁 | 板件／软件生态，不是官方USD399套装；完整源码与补丁版本缺口保留，不重定硬件路线 |

## 框架补丁与验证方向

- **双轨纳样：**保留消费零售基线；新增开源社区平台轨，按运动／角色玩法、源码／训练资产、教程／衍生设计、部件供应、社区参与和商业履约六项分别记录。少销售披露不取消社区轨资格，也不与消费整机共用销量分母。
- **证据梯度：**stars／forks是兴趣与代码分支行为；贡献、复刻完成、策略部署是更深参与；支付、交付、复用、留存另取证。先按各仓库记录，不造跨仓总人数。没有真实社媒播放数据，不猜“全网破圈”数量。
- **机会而非既定结论：**运动／角色动作包、教程与装配支持、合规可供的套件／备件是可验证方向；须测动作复用、复刻完成率、支持工时、返修和实际愿付。AI语音／视觉接入仅为二次开发假设，要另测延迟、安全、内容权利和持续价值，不写成现款已接LLM。

## 完整证据记录

<a id="d101"></a>
### D101｜官方 Microduck 产品页与商店：成品预售、价格与新订单延期

- **等级／日期／版本：** A，Pollen Robotics 第一方产品与商店声明；2026-10-10 HTTP 200访问，非实机或订单验收。产品页定位“Pick your pack / Tech specs / Open source”，商店定位价格、Key Specifications、Shipping & Availability及顶部公告。当前 Microduck 成品，不是旧XL330复刻套件、Microban或Reachy Mini。
- **来源：** [官方产品页](https://pollen-robotics.com/microduck/)（由官方运行时README的“Get yours here”发现）；[官方商店美国／USD参数页](https://store.pollen-robotics.com/products/microduck?currency=USD&country=US)；[商店无地区参数页](https://store.pollen-robotics.com/products/microduck)。
- **原文与证据：** 产品页“Pre-orders open August 27, 2026”“$399 before taxes and shipping”；盒内“Robot, battery, USB-C cable, game controller”。美国参数页显示“$399.00 USD”，Shopify active currency及priceCurrency均为USD。无参数访问显示EUR340.00，不作汇率换算或美国报价。商店顶部：“We can’t promise Christmas delivery for new microduck orders anymore…Current estimate for new orders: 4–6 months.”正文仍有“First deliveries targeted before Christmas 2026”：是早期首批目标，不能用来覆盖新订单警示。
- **产品架构与玩法：** 第一方列15电机、25cm、前向广角相机、8×8 ToF LiDAR、2 IMU、可动夹取喙、麦克风／扬声器、头与喙两处NFC、RK3566＋AI accelerator、1GB RAM／32GB存储、Wi-Fi／Bluetooth、可换NP-F550。产品页约800g、商店780g，保留页面差异，不强行视作同一称重条件；本卡用约0.8kg。官方列走路、坐站、踢球、低头拾取、轮滑、倒地起身，称随附7个动作策略及50Hz本地策略环，不从图中验证成功率。续航“approx. 1 hour”仅店方宣称，未测工况，不据此估算DIY续航。
- **购买口径与限制：** 2026-10-10美国展示价USD399，未含税运；默认EUR340税费状态未单独锁定。是含机器人／电池／USB-C线／手柄的预售套装；充电器包、开发包、附件包另购，不能把配轮玩法当标配轮子。官方列首发US／Canada／EU／UK／Norway／Switzerland／Japan／South Korea，中国未列，不推定可直邮。新订单4—6个月是估计，不是发货／签收证据；网页Add to cart／InStock结构化标签不改变预售身份。“The community ordered a lot of ducks”与正在爬产、新单交期拉长，是企业自述的需求／排产压力直接线索；不是只有GitHub围观，但未给订单量、取消率或实际出货。
- **独立抽核：** 主会话另于2026-10-10真实HTTP 200核对产品页25cm／RL／开箱可玩／8月27日预售／$399未含税运，以及美国参数商店399USD／15电机／顶部订单与4—6个月公告；未结账、购买或实测，不扩为全部来源复核。
- **结论／下一步：** 已有明确成品商业入口，不应因DIY属性漏收；价格、配件和供货须分地区／订单批次继续核验。没有购买、结账或联系商家；全球销量、退款、留存和实际交付仍未知。

<a id="d102"></a>
### D102｜官方运行时、架构与软件许可：动作脑不等于生成式对话

- **等级／日期：** A，2026-10-10读取官方`main`的README、LICENSE及架构文件，均HTTP 200；源文件为当前分支，不冒称固定提交快照。
- **来源／定位：** [microduck README](https://github.com/pollen-robotics/microduck/blob/main/README.md)“This repo is the duck’s brain / It does things / Under the hood”；[架构](https://github.com/pollen-robotics/microduck/blob/main/docs/design/architecture.md)顶部状态与§1／§2；[LICENSE](https://github.com/pollen-robotics/microduck/blob/main/LICENSE)。
- **证据：** README称RK3566上运行Rust工作区，`robotd`拥有50Hz控制环／15舵机总线并加载ONNX神经策略；`updaterd`更新／回滚、`configd`网络身份、`btd`蓝牙、`padd`手柄、`mediad`相机WebRTC、`tofd`深度传感器，通过Unix socket JSON-RPC通信。训练链路指向`microduck_rl`，README为动作提供官方演示链接。架构文件顶部仍标draft／2026-07-22及“first shipped version”目标；因此不将整张设计图当每台机器已完成配置，尤其传感器可选／未装配情形。
- **许可／媒体：** 软件LICENSE为Apache-2.0；不自动扩张为所有硬件CAD、品牌或宣传照片的开放许可。README首张[官方主视觉](https://github.com/user-attachments/assets/c2f7c245-8217-46a1-8d1e-e0ba967cd969)有4种配色，表示同一产品，不计4款。本轮唯一新增媒体为900×312 JPEG小预览，已用`view_image`核对画面、比例和无裁切；主会话另独立打开900×312派生图，确认四配色全身、比例清晰无裁断，仅属图片视觉复核。图片权利与哈希见媒体清单。
- **结论／限制：** 可编程、可读源码和本地动作执行成立于公开资料层面；没有在这些已读来源中核到现成LLM聊天或长期生成式陪伴功能。RL动作控制≠生成式会话，相机／NFC／AI accelerator和可扩展API亦不能证明已接大模型。未编译、刷写、运行或实测延迟／动作／安全／离线全功能；动作视频未播放验证。

<a id="d103"></a>
### D103｜microduck_rl：可训练、导出与分享的动作生态

- **等级／日期／来源：** A，2026-10-10 HTTP 200读取[默认develop README](https://github.com/pollen-robotics/microduck_rl/blob/develop/README.md)与[LICENSE](https://github.com/pollen-robotics/microduck_rl/blob/develop/LICENSE)；定位Quickstart、Tasks、Publishing a policy。早先读取main可达，但本条以主会话确认的默认develop为准，不混称不同分支固定版本。
- **证据：** `mjlab`（MuJoCo Warp）＋PPO；训练50Hz策略、导出ONNX交运行时部署。列速度行走／头姿控制、倒地恢复、坐站、喙触地拾取、踢球、翻滚及轮滑等任务；踢球条目标注actor is ball-blind，不能擅写成视觉自主追球。Quickstart要求CUDA GPU，亦可使用Hugging Face Jobs；公开BAM执行器建模、域随机化、backlash仿真及策略发布步骤。LICENSE为Apache-2.0。
- **结论：** 社区不只是围观硬件，还能训练、发布和复用动作；从“买来玩”到“改玩法”的路径是市场观察对象。标准化环境、模型与发布工具**可能降低从零研发的部分成本**，但学习、GPU、装配、动力学匹配和调试门槛仍在；README的训练时长不是本项目复现结果。
- **限制／下一步：** 未跑训练／sim2real，不将任务清单视为所有成品或C线HD-1910均能直接执行；未获得社区策略下载／实际部署人数及持续贡献队列。需按执行器、固件、模型版本核兼容并统计复用与完成率。

<a id="d104"></a>
### D104｜本地只读社区资料：教程、双舵机复刻与PCB／固件供应链

- **等级／日期：** A（各作者对自己项目的一手说明），2026-10-10读取本地参考库；不是实时远端全量审计，也不是本机测试。
- **来源／定位：** [A教程README](../../../../references/microduck-build-tutorial/README.md)硬件／镜像／运行段（[上游](https://github.com/AI-FanGe/Microduck-build-tutorial)）；[B复刻README](../../../../references/microduck-replica/README.md)“两种舵机”、CAD入口及构建记录，并读[NOTICE](../../../../references/microduck-replica/NOTICE.md)（[上游](https://github.com/fanhao375/microduck-replica)）；[C社区套件README](../../../../references/microduck-community-kit/README.md)“主要包括／其他说明”及[飞特补丁快照](../../../../references/microduck-community-kit/firmware/v1/patches/README.md)（[上游](https://github.com/jyg9/microduck-community-kit)）。
- **已核内容：** A提供Pi Zero 2 W／OpenRB／XL330路线教程、镜像、接线与运行步骤；B把XL330与HD-1910-C001的机械、协议、训练模型区分，CAD另有版本入口，并有作者构建／调试记录；C明确“不是官方Microduck仓库”，提供imu_to_dxl PCB／固件／主机工具、banana_pcb、dxl_hub、飞特舵机调试器与运行时补丁，并有作者板件供应入口。它们分别体现教程内容、衍生结构与可采购部件方向，不是三个独立终端用户群。
- **纠错与兼容边界：** 不采用B首页“IMU未开源／唯一公开重建”的过时全称断言，C已公开自己的IMU工程和固件；这也不反向证明官方当前成品每块硬件均开放。C首页“完整源码可编译”不能盖过本项目已记录的本地`software/microduck_feetech/`完整源码缺口；补丁基线`f0d934e`有明确快照限制，不承诺适配当前main。上游真机／编译记录不写成本项目完成。A的XL330参数、C的HD-1910参数及官方2026成品分栏，不复用供电、扭矩、成本表或训练结论。
- **许可／结论：** B为文件级混合许可，GitHub NOASSERTION不等于全Apache；不得把软件许可推广到全部CAD或商用成品。教程与模块化补充确实构成降低从零复刻门槛的路径，但“更低门槛”是相对从零自研的机制推断，不是普通消费者零门槛、不保证套件交付与售后。未核板件订单、销量或良率；下一步需完成复刻数、支持工时、备件兼容和版权链证据。

<a id="d105"></a>
### D105｜GitHub公开社区快照：五仓库分开记录，不合计独立用户

- **等级／日期／归属：** A，GitHub官方REST公开字段。2026-10-10主会话逐仓库真实HTTP 200核验后以消息回传；本Analyst-Coder直接登记，未重复请求。观察时分未记录，仅保留日期；[小型JSON与全部回传字段](microduck-community-snapshot-20261010.json)。

| 仓库／官方API | stars | forks | created_at（UTC） | pushed_at（回传精度） | 默认分支／API许可 |
|---|---:|---:|---|---|---|
| [pollen-robotics/microduck](https://api.github.com/repos/pollen-robotics/microduck) | 9,276 | 1,199 | 2026-07-29T07:52:16Z | 2026-10-09T15:19:16Z | main／Apache-2.0 |
| [pollen-robotics/microduck_rl](https://api.github.com/repos/pollen-robotics/microduck_rl) | 2,396 | 543 | 2025-12-06T13:00:59Z | 2026-10-09T10:08:49Z | develop／Apache-2.0 |
| [AI-FanGe/Microduck-build-tutorial](https://api.github.com/repos/AI-FanGe/Microduck-build-tutorial) | 1,211 | 300 | 2026-09-04T17:18:43Z | 2026-09-11（仅日） | main／MIT |
| [fanhao375/microduck-replica](https://api.github.com/repos/fanhao375/microduck-replica) | 1,131 | 204 | 2026-08-28T13:42:48Z | 2026-10-08（仅日） | master／NOASSERTION |
| [jyg9/microduck-community-kit](https://api.github.com/repos/jyg9/microduck-community-kit) | 14 | 5 | 2026-09-27T08:30:35Z | 2026-10-10T01:20:56Z | main／Apache-2.0 |

- **额外回传字段：** 五项`full_name`一致、`fork=false`、`archived=false`；microduck描述为“Tiny biped duck robot”，homepage为`https://pollen-robotics.com/microduck`，subscribers_count=54。`fork=false`只指GitHub仓库关系，不否认存在衍生设计或共享代码。
- **结论／限制：** 主仓9,276 stars／1,199 forks、训练仓与两套千星级教程／复刻资料，足以支持“值得独立纳入的开源社区现象”，纠正只看零售成品的选样偏差。**star≠销量／留存，fork≠完成复刻，跨仓库用户重叠；仓库创建日≠产品首发，单日累计≠今年增长曲线。**不据此宣称全球消费级销量爆款、总用户数或市场排名。还缺独立贡献者／完成复刻与部署／教程播放／订单履约／D30或D90再用等数据。

## 本轮过程、验证状态与未完成项

- 已真实HTTP 200读取官方产品页／商店、运行时README／架构／LICENSE及RL默认develop README／LICENSE；本地三参考库只读。首次抓取因终端GBK无法输出Unicode中止显示；设PYTHONIOENCODING=UTF-8后完成读取。HTML解析尝试因未安装bs4中止，改用现有requests与标准库提取，不安装依赖；非网页访问失败。
- 已保存官方README主视觉900×312预览并用view_image打开，4种配色、比例与画面核对通过，不裁切／不生成假图；仅保留轻量研究引用，不宣称原始大图永久归档。原媒体38图／4视频不改；新数39图／4视频、43记录、41个product_id。
- GitHub计数来自主会话本轮API核查回传，不冒称独立二次采集；JSON保留日期精度差异及所有回传字段。
- 未做购买、结账、联系、实机、训练、视频动态播放、全网播放统计、销量或留存核验；本机装配／供电路线不变。程序与生成检查结果追加正式evidence质量日志，交独立审查；不暂存／commit／push。
