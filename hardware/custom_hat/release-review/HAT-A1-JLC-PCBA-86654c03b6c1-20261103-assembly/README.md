# HAT A.1双联PCBA本地审查包

源86654c03b6c1c8f51f7d5a4bef469aceed2ddfc73433b3e50426940c2a23164a，同源r18。**用于制造资料审查，不是生产放行、订单或付款。** 没有自主新板实物。

- 实际生产几何为85×82mm两联RS-274-X、PTH/NPTH及BMI08881%钢网；U301项目四窗69.63%，U701四窗、U702十六窗保持。钢网名义0.125mm，实际印刷/回流未验。
- 104个SMT坐标在panel-positions-smt.csv；12个THT位置/面在panel-positions-tht.csv；全116件在panel-positions-all-fitted.csv。panel-assembly-plan.csv另含两颗不装C307/B2_C307。
- unit-reference-map.csv覆盖SMT/THT/DNP全部位号。A2为A1沿KiCad Y正向偏移32mm，CAM Y相应减少32mm；第二单元前缀B2_仅坐标/BOM映射，板面丝印仍用原位号。
- unit-assembly-front/back.svg为源单元清晰装配图；第二单元方向完全相同。背面图已镜像便于翻板观察，**CSV/Gerber/钻孔不再次镜像**。
- J301/B2_J301在B面、其余五个THT每单元在F面；双面SMT完成后先支撑切断分板并检查毛刺，不手掰、不提前安装THT；随后全部THT逐点手工焊接，不使用整板波峰焊或通孔再流焊。tht-soldering-plan.csv列12件/118针的元件面与焊接面，tht-process-notes.md与depanel-process-notes.md列邻近件和实际过程条件。J301 B端子面在40P孔朝上时从左1→8，1:2S+、2:GND标记不可按旧F图左右理解。
- 12POFV位置/各层盘尺寸见via-process-requirements.csv。明确选择树脂塞孔+盖铜，U701.7孔0.15mm、B铜盘0.25mm，其它三层0.35mm。
- 制造选项见manufacturing-spec.md/JSON：FR-4四层、1.6mm标称、指定公开层叠基线、沉金/绿油/白字。这些为本地设计选择，不代表已接单。
- material-process-matrix.csv以单板35MPN/58件列原厂依据；面板数量以bom-fitted/bom-smt.csv为准。原厂PDF在项目研究目录归档，本便携包未附其原件，不宣称已收料或可代料。

仍需实际锡膏/温度曲线、第一面器件保持、SH应用回流及来料/MSL记录；线束/公差/头壳/完整机械和首板功能未验。详细工序见assembly-process-basis.md。MANIFEST列本包所有文件哈希，旧r13和单板原始BMI088100%Paste不混用。


本次关键勘误：r18将40个邮票孔中心放在单元名义边线上，连接带中心X=108/160mm，每组5孔，孔边到孔边0.4mm。仅在分板带缩进约0.6mm清除zone铜，全部原焊盘/走线不变，孔铜/连接/I2S参考铜核查通过。两单元Power类别完整复制；旧r17及以前拼板不能作为当前合格交付。制造拼板填铜仅在已记录分板区域与源单板不同。
