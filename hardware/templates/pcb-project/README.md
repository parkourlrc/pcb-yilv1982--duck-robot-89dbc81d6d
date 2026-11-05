# PCB 项目模板

复制本目录到 `hardware/<模块>/`，填写 `requirements.md`，然后按 [PCB 运行手册](../../../docs/pcb-production-runbook.md) 的 Stage 0–10 执行。

| 文件 | 用途 |
|---|---|
| `requirements.md` | 唯一需要用户填的需求卡 |
| `checkpoint.json` | 源哈希、检查、生产包、订单与制造放行状态 |
| `order-status.json` | 阶段、报价、订单、付款、物流、来料与首板状态 |
| `first-article-test.md` | 首板上机测试记录 |

建议目录：`design/`（KiCad）、`checks/`（ERC/DRC）、`release/<hash>/`（同源包）、`orders/`（报价/订单）、`first-article/`（测试证据）。
