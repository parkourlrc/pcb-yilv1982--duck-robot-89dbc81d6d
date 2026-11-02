# HAT音频路由与控件配置（2026-10-31）

> 本工具建立于6fe440f3…基线。后续[A.1](../qwiic-pinout-20261031/research.md)保留主控/codec/音频模拟链针网，当前只读审计已绑定A.1完整指纹；旧报告留存。下述未改PCB指本工具编写阶段，不表示主板仍停在6fe版本。

## 当前结果

**[文件/源码/模拟核对]** 已为现有TLV320AIC3104驱动补出音频路由工具：主扬声器可接收L+R混音，J504保持立体声，J505选LINE1L差分输入到左ADC。工具先匹配真实声卡/控件再允许写入，默认只生成计划；失败会尝试静音并如实记录结果。

**[未验证]** 没有访问真实ALSA声卡、启动PCM、播放、录音或操作Radxa。当前主控状态、硬件复位/时钟、负载、麦克风和声学表现仍未验收。PCB继续为`6fe440f3cfcd9a30550299258cba5bf9355d888b0c166f62919a21adfc5de82a`，没有改变电路或生产包。

产物：[hat_audio.py与使用说明](../../../../hardware/custom_hat/software/codec/AUDIO-ROUTING.md)、control-catalog.json。`both-mic-plan.json`是离线示例计划，不是设备状态。

## 厂商与源码依据

| 来源 | 定位/适用范围 |
|---|---|
| TI TLV320AIC3104 SLAS510G | 既有PDF页5表7-1：pin10/11为左差分输入、19/23为HP左右、27为LEFT_LOP；页65表10-51：模拟增益设置13为-6.5dB |
| Diodes PAM8302A DS41333 Rev6-2 | 既有PDF页2典型应用：3=IN+、4=IN-、5/8为两个扬声器输出、1=SD；不能把端子当GND或虚构软件使能 |
| 精确codec驱动 | radxa/kernel提交e6d12a77…，tlv320aic3x.c SHA与已构建模块源一致；aic3x_snd_controls、aic3104_extra_dapm_widgets、aic3104_left/right_pga_mixer_controls、intercon |
| 同提交soc-dapm.c | mux使用widget名，mixer使用widget名+control名，不把“Route”字样误拼进mux控件名 |
| 同提交soc-ops.c | 布尔/整数类型和stereo/enum计数；ADC HPF采用DOUBLE枚举，必须传两个值 |
| alsa-utils v1.2.8/amixer.c | info输出card ID，contents/cset输出类型、范围、枚举和读回格式；不是本机目标程序版本已读取 |
| ALSA Control Interface文档 | https://www.alsa-project.org/alsa-doc/alsa-lib/control.html；控制项身份/值的接口背景，不等于声音测试 |

新增网络来源及SHA见sources-manifest.json；两份原厂PDF沿用metadata-repair专题，当前SHA和页码另见final-audit.json。没有改写原厂驱动或使用AIC3101/3107才有的Mono/Class-D控件。

## 真实连接与路由

- 主扬声器：U701.27 AUDIO_LINE_L→C321=1µF→U803.3；U803.4经C322=1µF接地参考；U803.5/8到J506 SPK_P/SPK_N。
- J504：U701.19/23经各10µF的C317/C318到AUDIO_L/R，第三脚地；没有更改容量或负载定义。
- 录音：J505 AUDIO_MIC经C325=1µF到U701.10；U701.11经C326=1µF接地参考；U701.15 MICBIAS经R312=2.2kΩ供给麦克风。按手册选择LINE1L differential，右ADC保持静音。
- R311仍100kΩ上拉AUDIO_AMP_EN，未新增GPIO控制。本程序只能设置codec的路径/静音，不控制PAM8302A电源。

原生PCB读取在native-audio-pins.json；最终审计重新与明确的预期针网对照，不能只拿网名自证真实器件功能。TI/Diodes页码与原电路记录共同提供依据。

## 配置范围与计算

从精确源码提取78项AIC3104可用控件，每个计划使用其中70项、74次有序设置：4组静音、66项配置、4组启用。枚举顺序、单/双值数量、布尔/整数范围均来自该版本源；运行时再次匹配，格式/类型/缺项不符不写入。

主扬声器开启Left Line Mixer的DACL1/DACR1两条路由，各ALSA raw105；由于该控件max118且invert=1，芯片设置为118−105=13，手册表10-51是-6.5dB。**[计算]** 两个满幅同相理想输入求和为`2×10^(−6.5/20)=0.9463`，约-0.4794dB。它只说明名义混音选值，不能当PAM8302A实际余量、功率或失真保证。

J504走独立HP左右直通，主扬声器混音不会把它强制变成单声道。默认PCM raw47对应-63.5+47×0.5=-40dB；PGA默认0dB。关闭AGC、所有模拟PGA旁路和未使用的输出路径，避免直接把麦克风路由到输出。实际MICBIAS候选2.0V由既有overlay控制，是否适合具体麦克风仍待验证。

原软件资料缺少这些设置不能直接说明原电路必然无声：它说明驱动/overlay/声卡枚举之外还缺显式路由步骤。本轮补的是可执行配置能力，未宣称原硬件已有或已修复实测故障。

## 模拟检查与真实边界

routing-tool-audit.json记录10个host模拟场景及8个输出/麦克风组合。场景包括完整路由、错误card ID、缺控件、范围变化、枚举重排、中途写失败、读回不符、Ctrl-C中断、静音也失败、报告已存在；全部通过。

错误身份/元数据在写入前拒绝；中途失败不进入最后启用阶段，并尝试4组静音；静音失败时明确记录false，不假称恢复。额外无关write-only控件被忽略，不因为它缺读值误判所需控件。已有报告不覆盖。夹具报告均标simulated，未调用真实amixer、ALSA或声卡。

这是解析/控制事务的源码验证，不能证明当前系统列出的控件完全相同，也没有验证PCM路径、时钟、功放、J504负载或实际录音。最终native/源码/模拟报告绑定见final-audit.json。PCB不变，已有kicad-happy同版审查继续适用；没有重新制造一个“全通过”的虚假硬件结果。

## 剩余事项

实际声卡/控件、PCM与声学测试需要当前主控和已核准的新HAT条件。J504低阻负载、扬声器/麦克风型号与水平、制造工艺、输入保护/线束及首板验收仍未完成。已有代码不能替代这些条件。未提交、推送、下单、部署或操作实物，未使用子代理；完整目标仍未达成。
