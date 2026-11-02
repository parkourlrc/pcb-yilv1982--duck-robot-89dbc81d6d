# Meta 2026 Q3 自由现金流为负的含义

- 日期：2026-11-01（Asia/Shanghai）。
- 问题：继 Alphabet 财务概念问答后，用户询问“说 Meta 的自由现金流为负，这个是什么意思”。
- 范围：核对本期公司披露并解释期间流量与现金存量；不是投资建议，不涉及机器人项目路线或采购。
- 证据等级：财务数字为 **[公司披露]**；指标解释为 **[定义/算术解释]**，不是本机实测或经营机理假说。

## 核查结论

**[公司披露]** Meta 于 2026-10-21 发布截至 2026-09-30 的第三季度结果，以下现金流数字对应 2026 年 7—9 月三个月，不是成立以来的累计现金。

| 指标 | 金额（亿美元） | 期间/时点与来源定位 |
|---|---:|---|
| 经营活动现金流量净额 | 约 327.9 | Q3；S1 官方检索摘录的 Cash flow 段 |
| 资本开支，含融资租赁本金支付 | 约 349.1 | Q3；S5 电话会转录摘要写约 349；349.1 与 S1 经营现金流减 FCF 约数相符 |
| 自由现金流 | 约 -21.2 | Q3；S1 官方检索摘录的 Cash flow 段 |
| 现金、现金等价物及有价证券 | 约 824.5 | 2026-09-30；S1 官方检索摘录的 Cash, cash equivalents, and marketable securities 段 |
| 净利润 | 98.6 | Q3；S1a 官方检索摘录的 Third Quarter 2026 Financial Highlights，Net income 行 |

**[定义/算术解释]** 按本次披露的约数：327.9 - 349.1 = -21.2 亿美元。经营产生的净现金仍为正，但没有覆盖当期资本开支（该公司这里含融资租赁本金支付），所以自由现金流为负。

**[定义/算术解释]** 负数描述这三个月的差额，不能解释成“过去积累的现金全部用完”或“账户余额为负”。截至季末仍有上述现金、现金等价物及有价证券；该合计包括证券投资，不能称为纯现金或扣债后的净现金。

**[定义/算术解释]** 负自由现金流也不自动表示会计净亏损；本期公司同时披露正净利润。现金余额还受融资、其他投资、股东分配等影响，不能断言余额恰好减少 21.2 亿美元。

## 来源及核验范围

- S1：Meta 投资者关系官网，Meta Reports Third Quarter 2026 Results，发布于 2026-10-21。
  https://investor.atmeta.com/investor-news/press-release-details/2026/Meta-Reports-Third-Quarter-2026-Results/default.aspx
  官方检索摘录明确显示现金与证券、经营现金流及自由现金流。直接打开失败，不声称取得完整正文、行号或报表附注。
- S1a：同一官网公告的不带 default.aspx 地址；检索取得发布日期、截至日期及净利润表。直接打开返回 DNS 连接失败。
  https://investor.atmeta.com/investor-news/press-release-details/2026/Meta-Reports-Third-Quarter-2026-Results/
- S2：尝试访问的 SEC EX-99.1 地址，未取得可用正文，不作本次已核验来源。
  https://www.sec.gov/Archives/edgar/data/1326801/000162828026066700/meta-09302026xexhibit991.htm
  直接打开返回不可访问。本记录撤回早期草稿对该地址已读取具体行号的表述。
- S3：CNBC，Meta stock sinks nearly 7% as AI spend pushes free cash flow negative，2026-10-22。
  https://www.cnbc.com/2026/10/22/meta-stock-q3-earnings-free-cash-flow.html
  检索确认报道发布日期及自由现金流转负的新闻标题；数字以 S1 官方摘录为准。
- S4：SEC，Beginners' Guide to Financial Statements。
  https://www.sec.gov/about/reports-publications/beginners-guide-financial-statements
  检索摘要定位：Balance sheets show...at a fixed point in time；Cash flow statements show...over a period of time。用于区分时点存量、期间流量，不用于核对 Meta 金额。
- S5：Investing.com，2026 Q3 电话会转录，2026-10-21；摘要明确 CapEx 约 34.9 billion，含 finance lease principal payments，FCF 约 -2.1 billion。
  https://www.investing.com/news/transcripts/earnings-call-transcript-meta-beats-q3-2026-estimates-as-ai-push-lifts-shares-93CH-4964260
- S6：SEC，Non-GAAP Financial Measures，Question 102.07；通常的 FCF 定义为经营现金流减资本开支，具体应说明公司口径。
  https://www.sec.gov/rules-regulations/staff-guidance/corporation-finance-interpretations/non-gaap-financial-measures

## 限制与下一步

- 用户未提供所见报道或截图；本回答针对官方 2026 Q3 的 -21.2 亿美元，不假定另一篇报道也采用相同期间及定义。
- 原始披露采用十亿美元约数，本记录统一换算为亿美元；未将新闻中精确到百万美元的附表数字冒充已在官方完整调节表核验。
- 浏览器直接访问官网和 SEC 附件失败；关键财务数字由官网检索摘录核对，融资租赁口径另有电话会转录摘要支持；未保存不存在的全文、行号或页码。
- 本轮未分析资本开支的回报、未来持续性、借款或股票发行的具体补资路径；不由单季度负自由现金流判断公司无偿债能力或投资价值。
- 不影响项目硬件现行入口；仅新增本记录，保留工作区，未 commit/push。
