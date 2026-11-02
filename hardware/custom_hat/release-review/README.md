# HAT A.1 本地CAM评审包

**[用户确认，2026-10-31] 尚未送厂、没有自主HAT新板实物。** 用户已授权仅向嘉立创询评、不下单/付款，并于2026-11-02决定自行微信询问。可直接复制[微信正文](../../../docs/references/hat-jlc-inquiry-20261031/wechat-message.txt)，配合下列固定ZIP发送；[资料/回复指南](../../../docs/references/hat-jlc-inquiry-20261031/wechat-handoff.md)列出重点问题与包内索引。助手此前只发过网页渠道询问，未上传ZIP；用户自行发送结果尚未取得。实际进展见[询评记录](../../../docs/references/hat-jlc-inquiry-20261031/research.md)。本包仍不是订单或上电放行。

现行资料为[状态更新版ZIP](HAT-A1-CAM-review-90f270910175-status-confirmed.zip)，PCB仍为A.1 / `90f27091017525a22f45c8818c973c317ed6262387a98fdf06bdc26337dac2a6`。此次只更新包内制造状态说明，22个制造输出按原清单复制，不重出Gerber、不改铜/孔/钢网/BOM。包内MANIFEST逐成员绑定，ZIP SHA256为`f4a286d38c9645a15bb49e8a6bf0aec0796e2c5933ecc5dd7bc8968fe0d16676`，详见[包身份记录](../../../docs/references/hat-simulation-tools-20261029/qwiic-pinout-20261031/review-bundle.json)。

原 `HAT-A1-CAM-review-90f270910175.zip` 保持不变，SHA256 `4749c422facd4122f56ab57663215d7d21bc6ebd46a6f2889fca1f46597a68ca`；它是收到制造状态答复前的历史快照，包内“状态待确认”不再代表现状。旧包及身份记录保留用于追溯，后续评审使用状态更新版。

工厂需反馈的10项问题仍在包内CAM-QUESTIONS.csv，包括0.15mm机械孔/0.1mm环宽、6处POFV和联合land、实际层叠/铜厚、双面装配/供料/高度等。不得从本地完整性检查推定厂商已经接受。

下一阶段条件见[原目标审计](../../../docs/references/hat-simulation-tools-20261029/qwiic-pinout-20261031/completion-audit.md)与[最短首板草案](../../../docs/specs/20261028-custom-hat/first-article-a1.md)。
