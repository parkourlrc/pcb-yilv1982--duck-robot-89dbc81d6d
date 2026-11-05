# 主电流路径加宽生产审查包（不可下单）

此包已由[主控5V路径审查包](../production-20261031-five-volt-review/README.md)取代，只作历史证据，不再是当前输出入口。

PCB SHA256：af8da97fb052d1f55de10772e62a1a64559df7c82223fcad50c8c0b6d1114562。共用入口和舵机路径已由0.6mm加宽到1.2mm，所有原焊盘/网络/连接保留；原生DRC/ERC/未连接/parity/网表全0。

69封装、1101线段、98过孔；55拟装件、38分组、36唯一MPN。manifest.json绑定设计及输出；via-process-requirements.csv继续列6处filled/capped要求。

当前压降模型按相关载流铜层1oz/35µm计算；后续工艺核准应满足该铜厚设计意向，不能自动套用更薄内层铜。实际介质层厚、HDI微孔、填孔工艺与厂商接受均未锁定；不能从默认导出推定制造合格。

本包有意不含自动生成的.gbrjob：PCB没有明确stackup，该文件会填入未经确认的0.48mm×3介质层。原件及SHA已在审查专题归档，manifest列job_file_policy；实际Gerber/钻孔完整保留。不能用历史包的默认Job补回当前包。

加宽不构成整板额定电流或温升验收，+5V主输出压降、连接器/线束/保护及控制环仍待核。详见[同版审查](../../../../docs/references/扩展板电路仿真工具/power-paths-20261031/research.md)。仅供审查，未制造、未上电、未提交。
