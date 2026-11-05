# 外部策略与模型清单入口

- 外部候选与自训产物的来源、哈希、任务契约和 `deployment_verified` 见 [training/MODELS.md](../../training/MODELS.md)。
- 原始盘点：[model-inventory-20261031.json](../../docs/references/飞特策略模型上机核对/model-inventory-20261031.json)、[onboard-model-catalog-20261031.json](../../docs/references/飞特策略模型上机核对/onboard-model-catalog-20261031.json)。
- 板侧目录：`/home/radxa/duck-policies/hd1910-20261031/`。

## 边界

- 外部包不是自训产物；`deployment_verified=false` 表示未做动作/实物验收。
- 权重、缓存和大包默认不入库；清单记录来源、哈希和恢复位置。
