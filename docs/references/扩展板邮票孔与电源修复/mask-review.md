# r18实际阻焊Gerber开窗核对

2026-11-03 Asia/Shanghai。主源86654c03b6c1c8f51f7d5a4bef469aceed2ddfc73433b3e50426940c2a23164a；拼板fd6cd170fc09848e37feb88e10dad3bbf1d21954a8139f7bb0f8a303e4ceb22c。检查对象为当前20261103-assembly ZIP对应的F.Mask/B.Mask，不是仅查工程设置或Paste。

## 结果与范围

**[文件几何核对] F.Mask 261、B.Mask 381，共642个实际开窗与原生pad逐一匹配。** 坐标、圆/矩形/椭圆/圆角矩形、尺寸及圆角半径一致；18个单板/拼板fiducial的0.5mm单边阻焊外扩纳入。所有200个拼板via设置为tenting，但不能据此假定焊盘开窗不会露出其孔，所以另逐孔检查真实开窗交叠。

- 不同开窗最小名义间隙0.228554mm，位于U701及B2_U701外角相邻引脚；没有小于0.1mm的开窗间隙。
- 未检出开窗内异网pad、track/via铜或实际filled zone铜外露。同网焊盘接线处露铜属于原开窗内容，不被错误当作异网问题。
- 10个F面U301孔和2个B面U701.7孔与开窗相交，12个UUID与双联POFV清单完全相同，且原生均filled+capped；未见未填孔被开窗露出。
- 人工构造0.05mm间隙的负对照检出0.050001mm，可被0.1mm筛查拒绝；这只验证距离检测，不是本板实际违规。

完整逐开窗/近距对/孔交叠见[mask-opening-audit.json](mask-opening-audit.json)。结论只到文件形状与已指定工艺，不是实际成品阻焊桥宽、LDI对位公差或工厂生产稿接受。

## 依据与工具覆盖

嘉立创国内[能力表](https://www.jlc.com/portal/vtechnology.html?active=pcb)的[归档正文](../归档扩展板嘉立创规则自查/sources/pcb-capabilities.txt)第271～307行：开窗可与铜1:1；1oz绿油“焊盘间距”≥0.10mm的最小桥设计条件。本文另外测的是实际开窗间隙，未把铜盘间距概念偷换为成品桥宽保证。板层/颜色选择仍为既有FR4四层、外铜35µm、绿色阻焊。

[阻焊指南](../归档扩展板嘉立创规则自查/sources/mask-guide.txt)说明工厂可能调整大开窗及通孔焊环，因此名义结果不能跳过真实生产稿，尤其FID的1mm铜/2mm窗口和U701.7分层铜盘/POFV。原材料/工厂实现仍未发生。网页续开未返回可用正文，采用已归档官方资料，未写成当天重新在线确认。

`audit_hat_mask_openings.py`读取实际Gerber flash；拒绝未知坐标格式、regions、未知宏、非正交原生pad以及无法逐项匹配的开窗。RoundRect宏的9个绘图primitive已核为矩形主体、4圆和4边，逐字比较；不只凭宏名推形状。二分碰撞计算采用KiCad几何，报告保留1nm级量化值，实际解释约0.229mm。

API核对发现直接`pad.GetEffectiveShape(F.Mask/B.Mask)`没有包含FID的0.5mm外扩，不能将它当实际开窗。当前脚本从导出Gerber重建开窗，再用GetSolderMaskExpansion与原pad几何对照；没有改动PAD、PCB或交付包。本轮新补的是既有native-dimensions明确排除的mask-bridge范围，不是修复已发生的阻焊缺陷。

现有kicad-happy最终Gerber报告仍适用，包、铜、钻孔、Paste、坐标未改，不重复全套仿真。制造/装配/完整机械和首板仍见[剩余事项](remaining-actions.md)。修改只留工作区，未外发、下单、付款、上电或提交。

[收尾核对](mask-documentation-check.json)确认包SHA与两份Mask文件绑定保持、脚本语法/专题链接/git diff --check通过、只读参考库无改动。前轮完成了分板工序与交付字段统一，本轮完成此前未覆盖的Mask文件专项；两轮均有实际证据增量，但仍不足以将全目标或制造标完成。
