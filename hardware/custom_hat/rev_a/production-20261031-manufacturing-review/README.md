# 当前 HAT 生产审查包（未放行，不可下单）

历史检查点：现行使用[pth-clearance-review](../production-20261031-pth-clearance-review/README.md)。本包之后已修复DRU加载/范围问题并取消盲孔，不再作为发布入口；原产物和哈希保留。

源PCB SHA256：`c6c09b3306832200c0c723443a350882a816cb00a92d79b10551363b588d35df`。对应[制造文字规则与孔距复审](../../../../docs/references/扩展板电路仿真工具/manufacturer-rules-20261031/research.md)，此前包均为历史检查点。

- 58拟装件、38 BOM分组、35唯一MPN；52 SMT、6 THT，C307不装。C309仅使用本地丝印变体封装，器件/焊盘不变。
- 同版Gerber、钻孔、完整/SMT坐标、分类BOM、装配意向和双面定位图；底面图已镜像，CSV不再镜像。
- 6处填孔盖铜要求在via-process-requirements.csv；现行微孔仍在，真实HDI层叠未锁定，默认介质Job已隔离。
- [制造参数提案](../../../../docs/references/扩展板电路仿真工具/manufacturer-rules-20261031/manufacturing-brief.md)只供本地审阅，未发送或获厂商接受。

manifest.json绑定源与产物。原生规则/连通检查通过，不等于电气、工艺或首板实测放行。
