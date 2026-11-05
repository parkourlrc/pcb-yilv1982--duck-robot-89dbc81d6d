# HAT A.1 双联 r18：规则继承与分板边缘修复

主源86654c03b6c1c8f51f7d5a4bef469aceed2ddfc73433b3e50426940c2a23164a；拼板fd6cd170fc09848e37feb88e10dad3bbf1d21954a8139f7bb0f8a303e4ceb22c。

85×82mm，8mm工艺边/R2，双面各3个PFID，4定位孔，40个0.6mm邮票孔居中于单元边线；X108/160连接带局部退铜。两单元Power类别与原规则完整继承，原生DRC0/未连接0；原焊盘/走线/连接、隔离、逐层via与参考铜检查通过。

[制造副本](fabrication-candidate-bmi81-edge/manifest.json)含104SMT/12THT/12POFV、402Paste；BMI08881%、U301四窗69.63%、U701四窗/U702十六窗、C307 DNP无Paste保持。[完整PCBA包](../../release-review/HAT-A1-JLC-PCBA-86654c03b6c1-20261103-assembly.zip)补全THT坐标/面及118位号映射。

[勘误与证据](../../../../docs/references/扩展板邮票孔与电源修复/research.md)：旧r1～r17缺第二单元Power映射；不能再以旧DRC0当完整复制等价。r18的局部分板填铜与源单板有明确差异。所有文件仅本地制造审查，未制造放行、外发或下单。
