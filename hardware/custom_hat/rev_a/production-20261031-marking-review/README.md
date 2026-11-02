# 当前 HAT 生产审查包（未放行，不可下单）

历史检查点：现行使用[pth-clearance-review](../production-20261031-pth-clearance-review/README.md)。后续已修制造规则及加载问题，本包不再作为发布入口，原数据保留。

源PCB SHA256：`b06b1051d84509c7434347d5889afb7908dffe1af99b67eea67eb4c3e33a9849`。包含TTL本地旁路及`DUCK HAT Rev A`丝印，详细结论见[最终文件复审](../../../../docs/references/hat-simulation-tools-20261029/board-marking-20261031/research.md)。

- 同版Gerber/钻孔、58件完整坐标、52件SMT坐标、拟装/SMT/追踪BOM、逐件装配意向和双面定位SVG。
- 6个THT器件为J101/J301/J401/J402/J403/J802，装配方式待选；C307 DNP。
- 底面装配图已镜像，CSV不再镜像；值和MPN查BOM。
- 5个热通孔及1个B.Cu–In2.Cu微孔的填孔盖铜要求见via-process-requirements.csv。
- 未确认的默认介质层叠Job已隔离在证据目录；真实层叠/铜厚/HDI、保护及热/控制环未放行。

manifest.json绑定源文件与输出。原生DRC/ERC/连通/一致性通过不等于制造接受；所有此前审查包均为历史检查点，不混用文件。
