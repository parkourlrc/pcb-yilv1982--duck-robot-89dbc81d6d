# Y701 有源晶振匹配提示核对

日期：2026-11-04，Asia/Shanghai。用户询问嘉立创提示“匹配无法识别BOM中晶振是否有源，请确认匹配到的晶振是否符合需求”是否有问题。

**结论：[原厂资料＋文件核验] 当前保存的Y9匹配记录中，Y701为C7425459 / YXC OT3EL89CJI-111YLC-12M，即12MHz、1.8–3.3V、CMOS输出的有源振荡器；本板也按有源振荡器供电、使能并接入codec MCLK。没有发现此项有源/无源选型不一致，无需因这条提示更换成无源晶体。** 这一结论只处理该匹配提示，不构成整板制造、贴装角度或实物时钟验收。

## 证据

| 来源 | 定位与核对内容 |
|---|---|
| [用户截图原件](user-y701-active-oscillator-warning-20261104.png) | 2026-11-04收到；Y701行及有源/无源人工确认提示。原截图型号与C编号有截断，完整身份以下方保存的Y9记录为依据 |
| [Y9逐组比对](y9-bom-reconciliation-20261104.json) | Y701，C7425459，MPN `OT3EL89CJI-111YLC-12M`，5板用5，精确型号比对通过 |
| [报价BOM](../../../hardware/custom_hat/rev_b/quote-99ecc45d/BOM.csv) | Y701对应同一MPN及C编号；封装`YXC_2520_YSO110TR_B` |
| [商品记录](stock-details.json) / [商品页面](https://www.jlc-smt.com/lcsc/detail/C7425459.html) | 保存的C7425459条目商品目录明确“有源晶振”；12MHz、1.8–3.3V、CMOS、SMD2520-4P。不是仅根据四脚外形判断 |
| [YXC原厂资料](sources/yxc-12mhz.pdf)第1页 | `YSO110TR Wide Voltage`；供电1.8–3.3V、CMOS输出；Tri-State高电平或悬空使能、低电平或GND禁用。此PDF为系列资料，12MHz具体频点由完整MPN与商品记录确定 |
| 同PDF第2页 | 1=Tri-state、2=GND、3=OUTPUT、4=VDD；2520封装图、顶视图与底视图分开标示 |
| 当前PCB `custom_hat_rev_b.kicad_pcb` | pcbnew只读提取：Y701.1=+3V3、.2=POWER_GND、.3=AUDIO_MCLK、.4=+3V3；AUDIO_MCLK端点为Y701.3与U701.1 |
| [音频原理图](../../../hardware/custom_hat/rev_b/audio_codec.kicad_sch) | Y701完整MPN/C编号及有源振荡器符号；当前PCB沿用99ecc45d源，没有修改电路/BOM/贴装坐标 |

原厂PDF取得于2026-11-04，URL及哈希见[sources/manifest.json](sources/manifest.json)，原始下载地址为`https://atta.szlcsc.com/upload/public/pdf/source/20260116/277ADDA9FE6BD42D3AF503786E6466E2.pdf`。本轮查看既有第1/2页渲染图；PDF文字层为空，未把空文本当作缺资料。

## 提示含义与边界

- [截图事实] 页面要求人工判断“是否有源”，没有明确说匹配型号错误；勾选框也不能单独证明电气适用。
- [推断] 这是匹配器无法仅由BOM字段自动判断器件类别的提醒。替代可能是用户此后换了匹配料号；若完整C编号/MPN发生变化，本次结论须重新核对，不能套用到另一颗“12MHz、2520”器件。
- 有源振荡器通电后输出时钟，无源晶体需要外部振荡电路，两者不能仅凭频率或封装互换。本板需要前者。
- 没有在网页替用户确认/改料、没有付款或操作实物。时钟波形、实际频率/音频工作仍未实测；工厂贴装方向按既有极性复核流程处理。

截图从用户提供的临时路径复制为稳定仓库文件，SHA256与原件一致；来源为用户提供、收到日期2026-11-04，未推断拍摄日期。原图未覆盖或标注。记录与图片未提交Git。
