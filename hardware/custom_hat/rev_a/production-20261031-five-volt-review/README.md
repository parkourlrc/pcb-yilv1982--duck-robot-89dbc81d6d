# 主控5V路径生产审查包（不可下单）

已由[功放去耦审查包](../production-20261031-amp-review/README.md)取代，保留为历史证据；当前BOM和装配文件以后续包为准。

PCB SHA256：0fd6c68918039867ef0d55a028844bbba7efaec68fe107d4a4b0a021ce7169c0。主要内层5V主干、排母入口和pin2→pin4连接已改1.2mm；反馈、器件、过孔及全部原焊盘连接保持。

69封装、1099线段、98过孔；55拟装件、38分组、36唯一MPN。manifest.json绑定源和输出；默认层叠.gbrjob已自动移到专题证据，6处filled/capped清单保留。原生DRC/ERC/未连接/parity/网表全0。

仍需修复U803就近去耦，核实际层叠/铜厚、HDI、保护、控制环和热条件。本设计不支持带电USB源与HAT并供；资料依据和模型限制见[同版复审](../../../../docs/references/hat-simulation-tools-20261029/five-volt-paths-20261031/research.md)。未制造、未上电、未提交。
