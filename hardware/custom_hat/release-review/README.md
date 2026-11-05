# HAT A.1 本地CAM评审包

**当前86654c03/r18。** [完整双联PCBA包](HAT-A1-JLC-PCBA-86654c03b6c1-20261103-assembly.zip)，SHA256 `46413368d6837e2b7f131f91f67a7f359d85bd663f88ff39f4a52a3b3de24194`；104SMT/12THT/116全坐标、118含DNP映射、370孔、402Paste及12POFV。BMI08881%、U301/TI窗口保持；未外发或制造放行。

[单板RS-274-X格式参考](HAT-A1-JLC-RS274X-86654c03b6c1-20261103-panel-edge.zip)，SHA256 `4cf5cacca00c27636e9f4652bb47c1c9e0dc39febcde500f904299e6b813d0bd`；11层/163孔/6POFV，其BMI088100%Paste不作实际钢网。见[单板记录](../../../docs/references/扩展板邮票孔与电源修复/rs274x-delivery.json)和[双联记录](../../../docs/references/扩展板邮票孔与电源修复/pcba-review-bundle.json)。

制造规格保留沉金/绿油/白字、树脂盖铜和既定层叠/0.125mm钢网基线。真实工艺/来料/工厂、完整机械/首板仍未验，见[报告](../../../docs/references/扩展板邮票孔与电源修复/research.md)。

**勘误：旧r1～r17拼板遗漏第二单元Power类别。** `HAT-A1-JLC-PCBA-b610f1dcd136-20261102.zip`（r14）退出现行，其ZIP不覆写，内部README只按生成日期留历史。旧单板包仅按源版本失效，无B2问题。

## 历史包（不作为现行嘉立创国内提交件）

`20261103-tht.zip`（SHA5099eb8bc2eaca79f4a65d460b0427d70b13c128263b2deab57961002afbee21）已被`20261103-assembly.zip`替代：增加先分板后装THT顺序，统一总装说明和两份CSV的THT工序文字；几何/位置未改。旧总装说明原本已禁止整板波峰焊，不能声称此前完全未写禁用；本次完善的是工序与字段一致性。

同源`HAT-A1-JLC-PCBA-86654c03b6c1-20261103.zip`（SHA256 `440c6de46b24d766a4d891d40ec5b75bc9d64ba965e3dc950c442412ae6f1f57`）已由当前`20261103-assembly.zip`补全THT焊接方式替代。13份Gerber/钻孔完全相同，原包不覆写；当前工序明确双面SMT及支撑切断分板后逐点手工焊接，不使用整板波峰焊或通孔再流焊。新包包含12件/118针的元件面/焊接面与邻近件记录，仍非工厂接受。

[状态更新版ZIP](HAT-A1-CAM-review-90f270910175-status-confirmed.zip)保留A.1源及历史X2输出，不能直接按国内说明投用；SHA256为`f4a286d38c9645a15bb49e8a6bf0aec0796e2c5933ecc5dd7bc8968fe0d16676`，原[包身份记录](../../../docs/references/扩展板电路仿真工具/qwiic-pinout-20261031/review-bundle.json)保持历史用途。此次发现格式要求后原包未覆盖。

原 `HAT-A1-CAM-review-90f270910175.zip` 保持不变，SHA256 `4749c422facd4122f56ab57663215d7d21bc6ebd46a6f2889fca1f46597a68ca`；只留历史，不作当前文件。热焊盘初版因未纳入via工艺CSV被thermal-r2替代，之后又经历padstack、钢网及分板修订；这些中间包均非现行，未外发。

原包CAM-QUESTIONS.csv十问改由自查矩阵裁决，不再作全量问卷；`20261102.zip`和`20261102-r2.zip`都属旧90f27091源，不作为现行入口。不得从本地完整性检查推定厂商已经接单。

下一阶段条件见[原目标审计](../../../docs/references/扩展板电路仿真工具/qwiic-pinout-20261031/completion-audit.md)与[最短首板草案](../../../docs/specs/20261028-custom-hat/first-article-a1.md)。
