# M1 市场数据与需求证据：全球消费电子化玩具桌面研究

> **分析已确认：** 用户已确认 A1 分析及核心口径边界，本文件由 Coder M1 按已确认分析落盘，供主报告集成。
>
> **信息截止与访问日期：2026-10-10。本文是公开来源桌面研究，不是本机实测，也不是用户硬件验证。** “已核验”仅指实际访问所列公开网页或 PDF 正文，不代表独立审计发布方数据或复现其统计模型。
>
> 授权写入范围仅本文件；未操作 Git。付费研究仅读取公开摘要，未购买或绕过付费墙；未保存、上传版权全文 PDF。本文仅保留必要短引、数据与定位，不复制网页全文。

## 1. 方法与核心结论

- 范围为全球消费电子化潮玩、机器人玩具、AI 玩具的市场背景及需求，儿童与成人分开，行业中立。
- 优先采用完整年度 2025；日本及 VTech 使用最新已完成财年并标明日期。2026 已披露期间与未来预测分开。
- M01—M17 均已实际打开网页或读取 PDF 正文，不以未打开的搜索摘要充当核验证据。
- 主要通过 CUA in-app browser 阅读；POP MART 港交所 PDF 通过 Python requests 和 pypdf 在内存中解析，没有写入 PDF。
- 保留原币种、原金额单位、原统计层级；不做汇率折算，不相加交叉口径。

### 核心结论

1. **2025 全球全玩具市场为 USD 123.0 billion，同比约 +8%。** 是行业背景，不是电子/机器人/AI 玩具市场（M01）。
2. **成人需求真实增长，但年龄口径必须拆开。** 美国 2026 上半年 18+ 受赠者/使用者对应玩具销售额 +25%，12—17 岁 +33%；无儿童家庭贡献 55% 销售不能解释成成人自用占 55%（M03）。
3. **增长集中于 IP、卡牌、积木、收藏等方向，不可整体归因于 AI。** 美国 2025 三个大类贡献 92% 行业增量，多数产品并不电子化（M02）。
4. **电子化需求存在，但不是所有电子玩具普涨。** 日本高科技趋势玩具 +15.5%，英国 Toniebox 等表现突出；VTech FY2026 北美电子学习产品收入 -12.7%、欧洲 +1.5%（M05、M08、M14）。
5. **不建议给单一“全球 AI 玩具市场规模”。** GMI、GVR、TBRC 的 smart toys 定义不同，包含非生成式交互、连接游戏、教育产品，TBRC 还含 app-connected drones；公开摘要存在内部数字冲突（M15—M17）。
6. 大盘增长不能代替企业盈利验证；公司收入与零售动销还受渠道库存、返利、出货时点、汇率和关税影响（M09—M14）。

## 2. 全球、区域与需求证据

### M01｜The Toy Association：Global Sales Data

- **URL：** [Global Sales Data](https://www.toyassociation.org/ta/toys/research-and-data/data/global-sales-data.aspx)
- **发布日期：** 页面未标具体日；标注来源为 Circana, The 2026 Global Toy Report (2025 Year-end data)，版权年度 2026，不能以访问日冒充发布日期。
- **数据期／地域／口径：** 2025 自然年，全球，全玩具市场，USD billion。
- **原文短引／定位：** 开头：`Global toy sales reached $123.0 billion in 2025, up 8% over 2024`。下方 `Global Toy Market Size in $USD Billions` 年度表：2020 为 98.9，2021 为 109.5，2022 为 111.0，2023 为 110.8，2024 为 114.3，2025 为 123.0；正文列五年累计约 +24%、2020—2025 CAGR 约 4%。
- **实际访问结果：** 2026-10-10，CUA 成功打开协会正文及年度表。旧路径 `https://www.toyassociation.org/ta/research/data/overall-toy-sales-data.aspx` 返回 404，后经真实搜索找到现行路径。
- **支持的结论：** 2025 行业大盘较快增长，可作为消费支出背景。
- **验证状态／限制：** 协会授权转载 Circana 数据，公开页已核验，未取得会员版完整报告及估算方法。**不是电子/AI 玩具 TAM。** 应使用同版年度序列，避免把旧版 2024 数字拼接到新版 2025 序列，不把修订差异自动解释成实际新增市场。

### M02｜Circana：U.S. Toy Industry Returns to Growth in 2025, Circana Reports

- **URL：** [美国 2025 年行业结果](https://www.circana.com/post/u-s-toy-industry-returns-to-growth-in-2025-circana-reports)
- **发布日期：** 2026-02-03。
- **数据期／地域／口径：** 2025 自然年，美国，玩具零售追踪，11 个 supercategories；销售额、销量、ASP 分列。
- **原文短引／定位：** 首段：`Total annual dollar sales grew by +6%`；销量 +3%、ASP +4%。品类段：Games & Puzzles +37%、Building Sets +15%、Explorative & Other Toys +20%，三类贡献 **92% 行业增量**。价格段：USD 30—69.99 价格段销售 +18%，USD 20 及以上合计获得近 4 个百分点销售额份额。
- **实际访问结果：** 2026-10-10，Circana 原站全文成功读取。此前也实际打开 Yahoo 转发稿，浏览地址为 `https://finance-yahoo-com.translate.goog/news/u-toy-industry-returns-growth-170500214.html?_x_tr_sl=en&_x_tr_tl=zh-CN&_x_tr_hl=zh-CN&_x_tr_pto=sc`；正式引用原站，不把转发当独立第二套数据。
- **支持的结论：** 需求回暖并向较高价格、授权、收藏倾斜，恢复包含销量增长，不只是涨价。
- **验证状态／限制：** 数据发布方公开稿。**不是各品类普涨，也不是 AI 驱动得到证明。** 增速为发布方舍入值，不用其乘积反推精确增速。本条未给美国市场绝对总额，不补未经核验数字。

### M03｜Circana：US Toy Industry Posts Strongest First Half in Six Years, Circana Reports

- **URL：** [美国 2026 上半年及年龄需求](https://www.circana.com/post/us-toy-industry-posts-strongest-first-half-in-six-years-circana-reports)
- **发布日期：** 2026-08-12，署名 Kristen McLean。
- **数据期／地域／口径：** 2026 年 1—6 月，美国；零售销售与家庭、受赠者/使用者分组，对比上年同期。
- **原文短引／定位：** 首段销售额 **+17%**、销量 +12%、ASP +4%；人口分组段：`Toy sales for adults ages 18+ grew +25%`。12—17 岁 +33%，两组贡献近 60% 行业销售额增量。`Adult-only households accounted for 55% of toy sales`，该家庭组销售额 +16%。授权产品销售额 +24%、占比 39%。
- **实际访问结果：** 2026-10-10，原站全文成功读取，包括年龄段、家庭类型及假日展望。
- **支持的结论：** 成人、青少年是重要需求来源，玩具兴趣爱好、收藏与社交用途扩大。
- **验证状态／限制：** **半年不是 2026 全年实绩。** 必须区分家庭类型、购买者、最终使用者；无儿童家庭仍可能买儿童礼物，55% 不等于成人自用份额。12—17 岁不属于成人；假日展望是预测。

### M04｜Circana：Regional Toy Market Dynamics Across Europe, The Americas, and Asia-Pacific

- **URL：** [2026 区域市场差异](https://www.circana.com/post/circana-reveals-regional-toy-market-dynamics-across-europe-the-americas-and-asia-pacific)
- **发布日期：** 2026-08-10，署名 Frédérique Tutt。
- **数据期／地域／口径：** 截至 2026-06 的滚动 12 个月及 2026 上半年；主要增速为 **G14 零售追踪市场**。另含 Global Toy Report 区域年度指标与中国观察。
- **原文短引／定位：** 首段：`toy sales grew +9.5% in the 12 months ending June 2026`；最近六个月销售额 **+14%**。欧洲段：2025 每名 10 岁以下儿童对应年度玩具支出约 **USD 240**。中国段指出婴幼儿/学前大类销量下降、ASP 上升；Arts & Crafts、Explorative & Other Toys、Action Figures & Accessories 为中国增长较快大类。
- **实际访问结果：** 2026-10-10，原站全文、来源说明、地域脚注成功读取。
- **支持的结论：** 地区类别、IP、季节性不同，不能全球套同一产品组合；中国儿童数量因素与单件价值提升可同时存在。
- **验证状态／限制：** **G14 不等于全球全部国家。** 脚注列美国、加拿大、墨西哥、巴西、智利、秘鲁、比利时、法国、德国、意大利、荷兰、西班牙、英国、澳大利亚，不含中国、日本、韩国。中国观察不能自动纳入 G14 增速。区域每儿童支出不等于受访家庭实际人均支出；使用“global”时必须带追踪范围。

### M05｜BTHA／Circana：UK Toy Market Returns to Growth for First Time in Five Years

- **URL：** [英国 Toy Fair 官方新闻稿](https://www.toyfair.co.uk/press_release/uk-toy-market-returns-to-growth-for-first-time-in-five-years/)
- **发布日期：** 网页未独立标日；正文称 Toy Fair 当日公布，附注新闻日为 **2026-01-20**。建议写“2026 年 1 月发布”，不冒充精确网页元数据。
- **数据期／地域／口径：** 2025 年 1—12 月；脚注为 Circana (UK) Ltd, **GB Consumer 360° Service** 与 **UK Retail Tracking Service**，两服务地域与采集口径不能假定一致。
- **原文短引／定位：** 正文市场 **GBP 3.9 billion，+6%**；12 岁以下玩具销售 +4%、占整体支出 67%；文中 `over the age of twelve` 的 kidult 组 +10%。积木 +25%、授权占销售额 38%。年度畅销产品段列 LEGO Botanicals、无屏 Toniebox 音频播放器、Squishmallows。平均玩具价格 GBP 12.37，+5%。
- **实际访问结果：** 2026-10-10，BTHA 主办展会原站全文成功读取。Guardian 同题页 `https://www.theguardian.com/lifeandstyle/2026/jan/20/uk-toy-sales-rise-lego-toniebox` 出现 ERR_CONNECTION_CLOSED，未取得正文，不作为证据。
- **支持的结论：** 儿童基本盘仍大，成人化不等于儿童市场消失；无屏音频电子产品有实际畅销证据。
- **验证状态／限制：** **kidult 不等于 18+ 成人。** 原文“over twelve”边界措辞照录，不擅改成精确 12+ 定义。GB 家庭与 UK 零售统计不能直接交叉计算。Toniebox 上榜不等于披露其独立销售额，更不是 AI 销售额。

### M06｜Global Toy News：French Toy Market 2025 In Review

- **URL：** [法国市场年度回顾](https://globaltoynews.com/2026/01/19/french-toy-market-2025-in-review/)
- **发布日期：** 2026-01-19。
- **数据期／地域／口径：** 2025 自然年，法国，全玩具市场；Yann Fresnel 综合 Circana、La Revue du Jouet、法国玩具联合会及个人观察。
- **原文短引／定位：** `Market Performance`：**EUR 4.7 billion**，销售额 +7.1%、销量 +7%；`Performing Categories`：`Audio storytellers: +63 percent`，积木 +35%、卡牌 +78%。
- **实际访问结果：** 2026-10-10，全文成功读取，文末明确综合来源及作者身份。
- **支持的结论：** 欧洲大陆存在玩具回暖及音频故事设备增长证据，可与英国并列。
- **验证状态／限制：** **二级行业综述，不是原始统计公报**，未逐项给底层表格。kidult、授权段用 `global toy sales`，地域措辞歧义，建议**不引用 33%／30% 份额**，更不能当世界成人/授权份额。音频故事设备不必使用生成式 AI。

### M07｜央视新闻转述中国玩协《2026 年中国玩具和婴童用品行业发展白皮书》

- **标题：** 《2025年我国儿童玩具市场基本盘稳固 潮玩市场增势迅猛》。
- **URL：** [央视正文](https://jingji.cctv.com/2026/03/27/ARTIo4EUZ4C9hSbTupTCJUKP260327.shtml)
- **发布日期：** 2026-03-27 11:24。
- **数据期／地域／口径：** 2025 自然年，中国国内零售；分别列不含潮玩的玩具、潮流与收藏玩具；另含消费者调查。
- **原文短引／定位：** 第二个正文段：`玩具（不含潮玩）国内市场零售总额为1035.3亿元`，同比 **+5.8%**；下一段潮流与收藏玩具 **人民币 676.9 亿元，+45.4%**。调查段：56.8% 受访消费者将 IP 列为选择潮流玩具时最关注因素。
- **实际访问结果：** 2026-10-10，央视正文成功打开，来源、日期与数据可见。
- **支持的结论：** 儿童基本盘与潮流收藏增速显著不同；IP 是明确需求因素。
- **验证状态／限制：** 官方媒体转述协会白皮书，**未取得完整方法、样本、问卷**。676.9 亿元不能解释为成人专属，更不是电子/AI 收入。建议两项规模并列、不合成统一总额，不与授权商品收入交叉相加。1035.3 的单位是“亿元”，不能误译为 1035.3 billion yuan。

### M08｜日本玩具协会：2025年度玩具市場規模調査結果

- **URL：** [日本协会统计正文](https://www.toys.or.jp/toukei_siryou_data.html)
- **发布日期：** 2026-06-22。
- **数据期／地域／口径：** **2025-04-01—2026-03-31**，日本国内，**希望零售价／上代价格**口径估计，不是 2025 自然年成交价零售额。
- **原文短引／定位：** 标题与概况：`1兆1,664億円`、`前年度比106.3％`，即同比 +6.3%；卡牌 JPY 3,384 亿、hobby JPY 1,960 亿。`2025年度の商品動向`：高科技趋势玩具 `ハイテク系トレンドトイ` 为前年度比 115.5%，即 **+15.5%**；列 Tamagotchi Paradise、マイクロペット为推动产品。
- **实际访问结果：** 2026-10-10，协会原站正文、发布日期、财年定义及分类说明成功读取，无需下载统计 PDF。
- **支持的结论：** 少子化不必然导致玩具金额收缩；电子宠物有较具体需求增长证据。
- **验证状态／限制：** 总市场含 hobby、杂货、部分乘用相关产品，主要 10 分野会剔除这些内容，范围不同。不能直接与美英或世界市场相加比较份额。高科技趋势玩具不等于联网玩具，更不等于生成式 AI。
## 3. 企业财报：需求与盈利交叉验证

### M09｜LEGO：2025 全年业绩

- **原文标题：** The LEGO Group delivers record results in 2025 driven by strong brand and innovative portfolio。
- **URL：** [LEGO 2025 财务结果](https://www.lego.com/en-us/aboutus/news/2026/march/the-lego-group-delivers-record-results-in-2025-driven-by-strong-brand-and-innovative-portfolio)
- **发布日期：** 2026-03-10。
- **数据期／地域／口径：** 2025 自然年，集团全球经营，DKK；公司收入和消费者销售分列。
- **原文短引／定位：** `Highlights vs. FY 2024`：`Revenue increased 12% to DKK 83.5 billion`；consumer sales +16%；营业利润 **DKK 22.0 billion，+18%**；净利润 DKK 16.7 billion，+21%。产品段：全年超过 860 款产品、约半数新品。
- **实际访问结果：** 2026-10-10，企业官网业绩全文成功读取，包括经营解释和年报链接；未下载版权全文 PDF。
- **支持的结论：** 品牌、持续创新、全年龄覆盖及执行可带来高于大盘的增长。
- **验证状态／限制：** **集团总收入不是电子积木或 AI 收入**；revenue 与 consumer sales 不同。公司对玩具市场增速的对照也不能替代 M01 全球估计或与之混合年度序列。

### M10｜LEGO：H1 2026 Results

- **原文标题：** Strong demand and brand relevance drive LEGO Group revenue up 21%, operating profit up 22% in H1 2026。
- **URL：** [LEGO 2026 中期业绩](https://www.lego.com/en-us/aboutus/news/2026/august/strong-demand-and-brand-relevance-drive-lego-group-revenue-up-21-operating-profit-up-22-in-h1-2026)
- **发布日期：** 2026-08-25。
- **数据期／地域／口径：** 2026 上半年，集团全球经营，DKK；报告汇率与固定汇率增速分列。
- **原文短引／定位：** `Highlights vs. H1 2025`：收入 **DKK 41.9 billion，+21%**，固定汇率 +26%；consumer sales +22%；营业利润 **DKK 10.9 billion，+22%**。`Innovating the LEGO brand and play experiences` 确认已推出 **LEGO SMART Play** 平台，应用于 Star Wars、Pokémon。
- **实际访问结果：** 2026-10-10，官网全文成功读取；最终浏览 URL 自动附加 `?locale=en-us&age-gate=grown_up`，未提交年龄验证；上方保留同一页面内容路径。
- **支持的结论：** 主流玩具企业正在把电子交互嵌入既有玩法与 IP 体系，有实际平台布局。
- **验证状态／限制：** **未披露 SMART Play 独立收入或销量**，不能把集团增长归因于该平台。半年不是全年实绩；电子交互不自动等于 GenAI。

### M11｜Mattel：Fourth Quarter and Full Year 2025 Financial Results

- **URL：** [Mattel 2025 财务结果](https://investors.mattel.com/news/news-details/2026/Mattel-Reports-Fourth-Quarter-and-Full-Year-2025-Financial-Results/default.aspx)
- **发布日期：** 2026-02-10。
- **数据期／地域／口径：** 2025 自然年，全球集团净销售及品类 gross billings，USD million；Q4 与全年分开。
- **原文短引／定位：** `Full Year 2025 Highlights Versus Prior Year`：`Net Sales of $5,348 million, down 1%`；营业利润 USD 546 million。`Gross Billings by Category / Full Year 2025`：Dolls -7%；Infant, Toddler, and Preschool -17%；Vehicles +11%；Action Figures, Building Sets, Games, and Other +14%。
- **实际访问结果：** 2026-10-10，IR 原站正文、全年表和展望成功读取。
- **支持的结论：** 大盘回暖不代表所有公司或儿童品类增长；组合、渠道、成本影响明显。
- **验证状态／限制：** **gross billings 与 net sales 不能混加**；合并品类不能当纯 AI 分部。页面的 2026 指引及 2027 后投资回报预期不是实绩，可能被后续季报更新，不当截止日最新指引。

### M12｜Spin Master：Q4 2025 Financial Results，含全年财务报表

- **URL：** [Spin Master 官方结果](https://www.spinmaster.com/en-US/corporate/media/press-releases/123011/)
- **发布日期：** 2026-03-05，页面时间 Thu, 05 Mar 2026 06:30:00 -0500。
- **数据期／地域／口径：** 2025 自然年，全球集团，USD million；含 Toys、Entertainment、Digital Games。虽以 Q4 为题，后附全年报表。
- **原文短引／定位：** `Consolidated statements of (loss) earnings and comprehensive (loss) earnings / Year Ended Dec 31`：2025 Revenue **2,112.9**、2024 **2,263.0**；2025 Net Loss **148.5**、Impairment of non-current assets **250.4**。Q4 Toys 表列 Toy Revenue **522.3**，同比 **-7.0%**。
- **实际访问结果：** 2026-10-10，原站初始加载正文为空，加载完成后成功读取正文与全年合并表；未以空页面或摘要代替核验。
- **支持的结论：** 零售需求、渠道订货、减值与公司财务可能分化；集团不是单一智能玩具业务。
- **验证状态／限制：** **Digital Games 不是实体电子玩具收入**；`Activities, Games & Puzzles and Dolls & Interactive` 为合并品类，不能当纯机器人/AI 分部。Q4 玩具收入不能错标全年。亏损含减值，不能全部解释为当前产品现金亏损。

### M13｜POP MART：2025 年全年业绩公告

- **URL：** [港交所公告 PDF](https://www1.hkexnews.hk/listedco/listconews/sehk/2026/0325/2026032500285.pdf)
- **发布日期：** 2026-03-25，港交所公告。
- **数据期／地域／口径：** 截至 2025-12-31 的全年，集团确认收入；表格单位 **RMB'000**。
- **原文短引／定位：** **PDF 第 10 页，Note 4 REVENUE**：总收入 **37,120,052 千元**，上年 **13,037,749 千元**；PRC operations **20,851,717 千元**，Overseas operations **16,268,335 千元**。表格另分 retail store、online、roboshop、wholesales and others。
- **实际访问结果：** 2026-10-10，CUA 打开公告；Python requests 与 pypdf 在内存中成功解析 **48 页 PDF**、读取第 10 页收入表。后续第二次请求出现 TLS EOF，不影响首次成功读取，但不声称再次成功。未保存或上传版权全文 PDF。
- **支持的结论：** 全年收入约人民币 **371.20 亿元**；按同表计算同比约 **+184.7%**，计算式 `(37,120,052 / 13,037,749 - 1) × 100%`，属本研究计算。支持角色/IP 潮玩及海外业务需求强。
- **验证状态／限制：** **POP MART 收入不是电子/AI 玩具收入**；`roboshop sales` 是自动售货渠道，**不是机器人玩具销售**。本轮未进一步完成毛绒与各 IP 收入表核验，不从摘要补入细项。

### M14｜VTech：FY2026 Annual Results

- **URL：** [VTech FY2026 业绩](https://www.vtech.com/en/press_release/2026/vtech-announces-fy2026-annual-results/)
- **发布日期：** 2026-05-21。
- **数据期／地域／口径：** 截至 **2026-03-31** 的财年；集团及 Electronic Learning Products（ELPs）地区收入，USD million；不是 2026 自然年全年。
- **原文短引／定位：** 顶部集团收入 **USD 2,027.5 million，-6.9%**。`Segment Results / North America`：ELPs **388.5，-12.7%**；`Europe`：ELPs **311.7，+1.5%**；`Asia Pacific`：ELPs **72.2，+4.9%**；`Other Regions`：ELPs **10.1，+8.6%**。
- **实际访问结果：** 2026-10-10，官网全文及地区分部说明成功读取。
- **支持的结论：** 比综合玩具集团更贴近**儿童电子玩具**的收入证据，显示区域分化。公司解释北美受关税、暂停出货、提价、零售商延迟布货影响，即使行业回暖公司 sell-in 仍可能下降。
- **验证状态／限制：** ELPs 不等于生成式 AI。集团还含电话与代工，不能整体计作玩具。FY2027 ELP 增长是管理层展望，不是已实现结果。

## 4. 细分报告：仅公开摘要，保留定义与内部矛盾

### M15｜Global Market Insights：Smart Toys Market Size & Share 2025–2034

- **URL：** [GMI 公开摘要](https://www.gminsights.com/industry-analysis/smart-toys-market)
- **发布日期：** **2024 年 12 月**，Report ID **GMI12756**，未给具体日。
- **数据期／地域／口径：** 全球 smart toys；2024 基年估计，2025—2034 预测；公开说明覆盖金额 USD billion、数量 million units。
- **原文短引／定位：** `Smart Toys Market Size`：`valued at USD 19.3 billion in 2024`；Key Takeaways、Report Attributes 预测 **2034 年 USD 72 billion**，CAGR **14.4%（2025—2034）**。
- **定义／分类：** 产品列 Interactive robots、Robots、Educational toys、Others（STEM 等）；技术 Wi-Fi、Bluetooth、NFC、RFID；年龄 0—3 岁、3—5 岁、6—12 岁、13 岁以上 teens；价格 under USD 50、USD 50—150、over USD 150。不是只研究生成式 AI。
- **实际访问结果：** 2026-10-10，CUA 初入加载/验证跳转，随后公开摘要完整显示并成功读取；未解验证码、未购买、未提交样本申请。Python 直连曾 TLS EOF，正式依据为成功显示的浏览器正文。
- **支持的结论：** 作为机构看好智能连接玩具的预测证据，不作为确定 GenAI 规模。
- **验证状态／内部矛盾／限制：** 2024 年 12 月发布，2024 金额亦应标机构估计，不升级成完整年度实绩。Interactive robots 与 Robots 边界未解释，成人是否完整覆盖不清楚。趋势图 **2025 `$0`** 为异常显示，不能当市场数据。欧洲段有“29% ... for the US market”措辞问题，不引用该份额。未取得付费全文、原始样本或厂商明细。

### M16｜Grand View Research：Smart Toys Market 2026–2033

- **URL：** [GVR 公开摘要](https://www.grandviewresearch.com/industry-analysis/smart-toys-market-report)
- **发布日期：** **2026 年 6 月**；页尾 `Published: June 2026`、`Last Updated: June 2026`，未给具体日。ID **GVR-4-68039-906-6**。
- **数据期／地域／口径：** 全球 smart toys；2025 历史估计，2026—2033 预测；主表 USD billion。
- **原文短引／定位：** `Smart Toys Market Summary`、`Report Scope`：2025 **USD 14.4 billion**；2026 估计 **USD 15.7 billion**；2033 预测 **USD 44.0 billion**；2026—2033 CAGR **15.8%**。
- **定义／分类：** Interactive Games、Robots、Educational Toys；连接应用、语音、传感器、适应性学习等，**不要求生成式 AI**。摘要称 interactive games 占 2025 收入 75.9%、offline 占 77.4%，为该模型份额，不能跨来源套用。
- **实际访问结果：** 2026-10-10，公开摘要、分类、Report Scope、FAQ、页尾日期均成功读取；未购买全文、未申请样本。
- **支持的结论：** 智能玩具研究覆盖广义互动/学习产品，不仅 AI 对话毛绒或机器人，可展示预测及不确定性。
- **验证状态／内部矛盾／限制：**
  1. 2026 金额：正文及主表 **15.7 billion**，FAQ **15.8 billion**。
  2. 北美 2025 份额：摘要连续出现 **38.9% 与 40.4%**，不能选便利数字而隐去冲突。
  3. 主预测期 2026—2033，分类说明残留 `2018 to 2030`；分类列表又列 2021—2033。
  4. 可注明“主表估计”，但**不引用冲突份额，不把模型 `Actual data` 标签等同官方审计实绩**；未取得抽样、定价层级及软件/订阅处理细节。

### M17｜The Business Research Company：Smart Toys Market Report 2026

- **URL：** [TBRC 公开摘要与定义](https://www.thebusinessresearchcompany.com/report/smart-toys-global-market-report)
- **发布日期：** **2026 年 9 月**，未标具体日。
- **数据期／地域／口径：** 全球 smart toys；2025 历史估计、2026—2030 预测；USD billion。
- **原文短引／定位：** `Market Overview`、`What Is The Smart Toys Market Size and Share 2026?`、`Growth Forecast`：2025 **USD 25.02 billion**；2026 **USD 30.51 billion**；2030 **USD 66.9 billion**。预测正文及 FAQ 给 CAGR **21.7%**。
- **定义／分类：** `What Is Covered Under Smart Toys Market?`：按预设模式运行、响应外界刺激、设计为通过 Wi-Fi/Bluetooth 等连接的玩具。含 Robots、Interactive Games、Educational Robots，以及 Smartphone-Connected Toys、Tablet-Connected Toys、Console-Connected Toys、**App-Connected Drones**。用户组包含幼儿、学前、学龄、stripling；不是仅 GenAI，也未充分披露成人收藏边界。
- **实际访问结果：** 2026-10-10，摘要、定义、分类、预测表、FAQ 成功打开；仅公开摘要，无付费全文访问。
- **支持的结论：** 提供已核验的 2030 预测终点，显示连接设备/无人机的纳入会影响估值，不宜直接代表儿童 AI 陪伴玩具。
- **计价口径补充（V1独立正文抽查）**：原文明示 `factory-gate values`，计制造者销售货物及相关服务的价值，不包含供应链后续转售价值。不是终端零售口径，不能与M01全玩具零售背景相除得到智能玩具零售渗透率；即使均用USD也不能消除计价层级差异。
- **验证状态／内部矛盾／限制：** 主体及 FAQ 的 2026—2030 CAGR 为 **21.7%**，`Forecast Analysis` 表却写 **21.9% from 2026 to 2030**；21.9% 也用于 2025—2026 增长。宜引用“正文预测 2030 年 USD 66.9 billion”，披露 CAGR 冲突。2026 仍为全年估计/预测，不因写 `increased to` 就当实绩。公开信息不足以校准与 GVR/GMI 的厂商、定价、确认收入口径，不能平均为统一 TAM。

## 5. 细分数字如何进入报告

| 来源 | 2025 或最近基年 | 预测终点 | 应如何标注 |
|---|---|---|---|
| GMI（M15） | 2024：USD 19.3 billion | 2034：USD 72 billion | 2024 年底发布的 smart toys 模型估计/预测 |
| GVR（M16） | 2025：USD 14.4 billion | 2033：USD 44.0 billion | smart toys 估计；公开页有内部冲突 |
| TBRC（M17） | 2025：USD 25.02 billion | 2030：USD 66.9 billion | 更广的连接式玩具定义；预测非实绩 |

**建议正文表述：**

> 公开商业研究对 smart toys 的定义和估值尚未统一。仅就 2025 年，已核查的 GVR 与 TBRC 分别估计为 USD 14.4 billion 与 USD 25.02 billion，相差约 1.74 倍；两者产品覆盖、连接设备范围和研究方法不完全一致，公开页亦有内部不一致。因此本文不将这些数字平均、相加或视作“全球生成式 AI 玩具市场”的确定规模。

**2027—2030：** 已核验 TBRC 的 2030 终点预测；未取得公开的逐年 2027、2028、2029 数据。若需要年度情景，应由主报告自行建模，明确标注假设，不能伪装成原报告数据。

## 6. 建议的市场框架

### 6.1 市场口径分四层，不能相加

- **全玩具市场：** 行业支出背景。
- **电子化实体玩具：** 声光、电机、遥控、电子宠物、音频故事设备等，可不联网。
- **智能/连接式玩具：** 传感器、应用连接、编程、适应性反馈等；与电子玩具大量交叉。
- **生成式 AI 玩具：** 以模型生成对话/故事/行为为核心的子集；本轮**未取得可信统一全球规模**。

IP、毛绒、机器人是另一些分类维度：毛绒可以完全无电子，也可以内置 AI；机器人不必使用大模型。

### 6.2 人群至少分三组

- **儿童：** 父母/监护人付费，重视安全、教育价值、耐用性与长期兴趣。
- **青少年 12—17 岁：** 单列，不能为了突出成人市场而吞入成年人。
- **成人 18+：** 收藏、兴趣、陪伴、桌面互动、DIY 等不同需求还应细分。

证据里的 **kidult 常含 12+**；不能与 18+ 实际成人口径互换。

### 6.3 财务比较保留“卖给谁”的差异

- Circana 多为零售 sell-through。
- 企业收入通常为公司确认收入，受到批发、直营、出货时点、返利、库存影响。
- IP 集团收入、数字游戏收入、自动售货渠道收入不能当实体 AI 玩具收入。

## 7. 明确缺口与优先补查项

1. **韩国：** 本轮未取得可核验的最新完整年度官方玩具市场金额；不得拿 GVR/TBRC“覆盖韩国”替代韩国实绩。
2. **欧洲整体：** 已取得英国、法国及 Circana 区域证据；没有取得统一 EU27/全欧洲 2025 总额。英国/法国不能相加冒充欧洲。
3. **美国绝对规模：** 已核验 2025 增速和结构，未核验同版绝对总额。
4. **生成式 AI 独立市场：** 缺零售规模、装机活跃率、订阅收入及退订/退货数据。
5. **成人电子陪伴需求：** 全玩具成人增长不能证明成人机器人购买、持续使用或订阅意愿；需产品级销量、留存、退货等证据。
6. **付费方法：** 三家细分报告只读公开摘要，未取得完整样本、厂商纳入清单、渠道加价及软件收入处理办法。
7. **2026 财报更新：** 已核验 LEGO H1、VTech FY2026；Mattel/Spin Master/POP MART 的 2026 中期搜索结果已发现，但**未在本轮完成正文核验，不应纳入已验证数字**。
8. **Persistence electronic toys：** 本轮未打开其正文，不能引用先前候选数字。已有 GMI/GVR/TBRC 三家实际访问的细分证据，足以先写主体。
