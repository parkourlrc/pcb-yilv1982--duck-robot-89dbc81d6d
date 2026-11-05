# HAT A.1同源双联r11

> **2026-11-03撤出现行，仅历史。** 此拼板缺第二单元Power类别映射；旧DRC0不代表规则完整。使用[r18](../a1-smt-2up-20261102-r18/README.md)并见[勘误](../../../../docs/references/扩展板邮票孔与电源修复/research.md)，本目录及派生文件不再用于制造。

2026-11-02，源96dcce92ca42bbfcee423ef8590e3e1318c5e10c660d5d688f634b0924fa7036。85×82mm、8mm工艺边、R2外角、2mm槽、40邮票孔/4定位孔，双面各3全局Mark。单板仍65×30mm。

18个方向器件新标记随板复制；位号转换使用实际绘制角，修复r10的J301二单元文字反向/间距问题。原生DRC0、未连接0、原连接/单元隔离/逐层via及文字样式检查通过。r10失败版不用于制造。

制造副本以[fabrication-candidate-bmi81-materials-r3/manifest.json](fabrication-candidate-bmi81-materials-r3/manifest.json)为准：116拟装、104SMT、12THT、12POFV；BMI08832个开口81%，C307/B2_C307不装无Paste。r2修随包链接，r3修JST顶插卷盘数量1500/reel；均未改铜/锡膏。

材料矩阵、送料/回流/清洗依据附在制造目录；工艺仍未实测，不能据文件零违规安排生产。来源和限制见[本轮报告](../../../../docs/references/归档扩展板极性与装配资料/research.md)。
