# hardware 目录索引

本目录是可写工程与实物基线；上游图纸证据在 [docs/schematics](../docs/schematics/README.md)，只读参考在 [references](../references/README.md)。

| 目录 | 内容 |
|---|---|
| [replica/](replica/README.md) | 复刻整机基线入口（索引层，不复制原图/原理图） |
| [banana_pcb/](banana_pcb/README.md) | 电池取电板工作副本、KiCad 工程与生产文件 |
| [custom_hat/](custom_hat/README.md) | 自主 HAT 设计与制造；B.0 已付款、线路暂停、首板未验收；[版本与交付包清单](custom_hat/VERSIONS.md) |
| [templates/pcb-project/](templates/pcb-project/README.md) | 新 PCB 模块的需求卡、状态文件与首板测试模板 |

## 边界

- `replica/` 只做索引，不替代 BOM、PROGRESS、照片和原理图；首轮不移动 banana_pcb。
- `custom_hat/` 是自主设计，不等于已装机板；报价、制造放行、实物验收分开记录。
- 硬件照片放 docs/photos，图纸证据放 docs/schematics；不在本目录复制原件。
