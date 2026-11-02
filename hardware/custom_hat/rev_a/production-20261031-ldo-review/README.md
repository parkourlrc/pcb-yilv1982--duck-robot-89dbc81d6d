# LDO局部回路生产审查包（不可下单）

已由[参考地铜修复审查包](../production-20261031-reference-review/README.md)取代，保留作历史源哈希证据，不再作为当前输出入口。

PCB SHA256：fda50c8019c3ab68c7c54228fc09fb36dd028e35b43afe26a7dc0f6c090b0771。C308/C309为2.2µF，R703为47mΩ电容支路阻尼；Buck C303～C306的1210升级保留，C307仍DNP。

55拟装件、38分组、36唯一MPN；69封装、1096线段、97过孔。manifest.json绑定设计、Gerber、钻孔、坐标、BOM和via-process-requirements.csv的哈希。6处filled/capped要求仍需厂商接受。

原生DRC/ERC/未连接/parity/网表全0，[同版审查报告](../../../../docs/references/hat-simulation-tools-20261029/ldo-capacitors-20261031/research.md)说明模型、误报和限制。完整环路、整板载流、热/回流、HDI与实装未完成，不能据此投板。未下单或上电。
