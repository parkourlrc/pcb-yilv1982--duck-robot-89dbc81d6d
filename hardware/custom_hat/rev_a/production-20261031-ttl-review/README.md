# TTL 去耦阶段审查包（历史检查点，不可下单）

源PCB：`143a483d578822d332f4576c3eb01c66c11131f45257d675dd95d15c6c0e8985`。后续增加板名/版本丝印，现行包见[marking-review](../production-20261031-marking-review/README.md)。

包含同版Gerber、钻孔、58件完整坐标、52件SMT坐标、拟装/SMT/追踪BOM、装配分类与正反定位SVG。C307不装，6个通孔件的装配方式未选；底面定位图已镜像，坐标CSV不再镜像。

6处填孔盖铜要求见via-process-requirements.csv。未经确认的默认介质层叠Job已移出本包，归档于对应证据目录。真实层叠/HDI、保护、热/控制环和硬件功能未放行。

详情见[修复与复审](../../../../docs/references/hat-simulation-tools-20261029/ttl-bypass-20261031/research.md)。manifest.json绑定源和输出，文件检查通过不等于制造批准。
