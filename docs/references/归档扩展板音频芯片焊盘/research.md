# U701.7焊接面铜盘收敛与正式回写

> **后续现状：** 主源96dcce92已补18项方向标记，同源双联r11/国内包见[当前报告](../归档扩展板极性与装配资料/research.md)。24热焊盘及C310避孔证据见[上一轮](../归档扩展板贴片与层叠复核/research.md)。本页3b1d/r7是当时检查点，U701分层尺寸结论保持。

日期2026-11-02。目标：解决窄QFN焊盘与0.35mm盘中孔铜盘叠加的具体制造问题，保留已验证的针网、I2S路径与填孔盖铜，不以布线实验失败更改功能范围。

## 现行结果

**[原厂规则/文件核对] 已回写仅对U701.7的分层via铜盘。** 主PCB SHA256 `3b1d903c776ec0975a15524962775c9ae288800421b583ea9c7e7ae0e592f145`。F.Cu/In1.Cu/In2.Cu仍0.35mm，B.Cu（codec焊接面）改为0.25mm；机械贯通孔0.15mm、位置、填孔/盖铜保持。原QFN land0.875×0.25mm及B.Mask/B.Paste均不变，B面via圆盘完整落在原land内部，不再形成较宽的0.35mm铜盘突出。

先前[22热焊盘采用](../归档扩展板热焊盘回写/research.md)保留，主板仍72封装、1130线段、100贯通via、58拟装件。回写改动只有PCB、限定B层规则及net-contract制造元数据。没有扩大板框或更改器件电路，A.1标记仍表示相同功能版本；制造源身份以完整SHA区分。

## 为什么采用此方案

用户提供的嘉立创国内[能力表](https://www.jlc.com/portal/vtechnology.html?active=pcb)明确多层via最小内径0.15/外径0.25mm，要求直径差≥0.10mm；对应单边环宽0.05mm。该组合为公开极限，不符合推荐直径差0.15mm以上，必须如实保留这一裕量限制。

[盘中孔设计细则](https://www.jlc.com/portal/q7i38630.html)提醒贴片焊盘小于过孔时应扇出；新[SMT细则62741](https://www.jlc-smt.com/technology/detail/62741.html)允许高密度使用树脂填孔+电镀填平。仅拿后者不能忽略前者。本次把焊接面via铜盘收进原贴片铜land，不修改器件厂家要求的焊接表面，再保留填孔盖铜防吸锡处理；其余三层保留较大铜盘。

**[几何依据]** 原land为圆角矩形0.875×0.25mm，圆角半径0.0625mm。via与land同心，0.25mm圆直径等于窄边、小于长向直段0.75mm，因而被原land包含；不是只用包围盒声称包含。原孔0.15mm仍被原0.25mm可焊开口覆盖，实际盖铜/平整度属于加工过程，不提前声称实物通过。

此前15个扇出尝试在SDI/SDO/BCLK拥挤区域未得到全部通过结果，搬移C305也仍需重新校核回流。本方案不是把这些失败候选改成通过，而是采用已公开支持、能保持原电路路径的另一局部几何解决方式。它解决的是“via铜盘比焊接land宽”的文件问题，不替代工厂成品公差或实物装配检验。

## 完整验证

1. [source-diff-contract.json](source-diff-contract.json)：原PCB对象ID全部保持，原via只新增front_inner_back padstack，唯一其它变化是B面地铜按间隙重铺；其它对象逐项相同。
2. [geometry-connectivity-check.json](geometry-connectivity-check.json)：焊盘几何/赋网、全部走线/孔位及原连接保持；原生DRC/未连接/parity/ERC/网表全0。
3. [reference-and-plot-check.json](reference-and-plot-check.json)：相同I2S采样点没有覆盖丢失；F/In1/In2铜、双面Mask/Paste和板框的完整Gerber绘图指令不变，只有B.Cu因via盘和邻接地铜变化不同。
4. [negative-controls.json](negative-controls.json)：将目标B铜盘缩0.24mm、目标F铜盘缩0.34mm、另一个普通地via缩小分别触发规则拒绝。限定规则只匹配U701庭院内唯一0.15mm +3V3贯通via且仅B.Cu生效；其它99孔≥0.125mm环宽规则不变，F/内层0.10mm规则仍有效。
5. padstack-detail.png已打开，原生B.Cu+Mask局部图显示via在原矩形land内；图上白色圆为钻孔显示，成品仍要求填孔盖铜。原图保留padstack-B.svg，统一顶视、B未镜像。
6. 回写前`promote_release_metadata.py`核源/候选/规则加载/几何契约，旧源保存在before-metadata；回写后完整工程再次重铺铜检查并绑定current-review。

这一B面几何调整是在公开规则边界内缩小局部铜盘，不是为报告通过降低全板要求。制造CSV现列F/In1/In2/B各层铜盘和最小名义环宽，避免旧Diameter_mm单列0.35掩盖B面0.25事实。

## 同版kicad-happy与交付

已重新运行固定版本2fd9aa0fe2d620f36627d9221e8b1393987ae38e的schematic、PCB full、cross、EMC、thermal、Gerber、SPICE及prior delta。原同MPN生命周期复用unknown，不声称库存。原生零违规不等于所有自动提示消失或实测通过；原始报告保存本目录，判定按证据处理。

codec/BMI088/音频路由只读审计也重新绑定当前源。net-contract只有qualified_codec_pth制造元数据变化，针网和GPIO/电源契约完全相同；保留旧overlay manifest及审计报告后，只更新该制造元数据的契约指纹，未重编驱动或设备树、未部署。脚本rebind_unchanged_audio_contract.py强制限定差异键并核DTBO二进制SHA，证据在software-contract-rebind.json；不凭手工写accepted字段冒充新硬件验收。

内部审查输出为[production-20261102-padstack-review](../../../hardware/custom_hat/rev_a/production-20261102-padstack-review/README.md)，国内RS-274-X及同源双联候选以[release-review入口](../../../hardware/custom_hat/release-review/README.md)和[panels入口](../../../hardware/custom_hat/panels/README.md)为准。旧90f27091/b369f9fc包保留历史，不混用当前源/钢网/规则。

同源r7拼板已生成并重铺铜DRC0/未连接0，复制验证增加逐层via铜盘尺寸检查，避免仅GetFrontWidth漏掉B面缩盘。制造副本最终目录为fabrication-candidate-bmi81-final-r2，32个BMI088开口81%、其它开口和非paste铜图保持。前后图panel-r7-front/back.svg/png均已打开，B图统一顶视未镜像。单板RS-274-X ZIP为`HAT-A1-JLC-RS274X-3b1d903c776e-20261102-padstack.zip`，SHA256 `20afe5aa83b2f639bd7a0adc8de6296d85a3276389ff2c674a36fdd3f1cf97d4`；不是完整SMT订单包，单板原始BMI088钢网仍不作为81%版本使用。

热焊盘首次重出时曾遗漏via-process CSV（旧流程由独立脚本后补），已在发包前发现：checkpoint导出入口现在必调逐孔工艺导出，新单板/拼板都含6/12项及逐层铜盘列，163孔原生/Excellon逐项匹配。缺CSV中间包未外发，退为历史，避免流程再靠手工后补。

## 未完成项

- C305/C310直接接铜与热平衡的具体取舍仍需核，不能把工艺建议当真实立碑故障，也不能忽略已发现参考铜损失。
- 逐器件极性可见性、回流/包装及实际层叠/铜厚、料源与机械堆叠未全部锁定。
- 双联候选必须按当前分层padstack复制并核每层铜盘，不能只比GetFrontWidth。
- 新板未制造，供电、音频/I2S、TTL、IMU/ToF与装配功能没有实物验收。未上传、建单、付款、上电或提交Git。

本轮工具失败：从普通Python子进程启动KiCad Python曾因继承环境未加载pcbnew而失败，改用已核PowerShell直接调用KiCad Python完成，无源修改。所有失败/负对照保持独立目录，未升级为成功证据。目标保持未完成。

收尾[completion-check.json](completion-check.json)核主源/current-review/单板制造包/国内ZIP/同源r7关系、163孔、6/12孔工艺表、104SMT坐标、BMI08832开口81%及三份软件审计绑定；r7再次独立规则哨兵产生199项，明确加载成功。脚本语法、当前链接及任务范围git diff --check通过，三个只读参考库无变更。原始自动报告仍有启发式告警，实际全目标未完成。
