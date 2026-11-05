# DuckHAT音频路由配置

`hat_audio.py`与`control-catalog.json`为本板TLV320AIC3104提供可预览的ALSA配置。**已做源码、PCB和模拟后端核查，尚未连接真实DuckHAT声卡，也没有播放/录音实测。** 不能把控件读回成功当作声音正常或制造放行。

## 路径与初始值

| 选择 | 行为 |
|---|---|
| `--output none` | Line/HP/HPCOM输出开关保持关闭 |
| `--output speaker` | 左右DAC分别以名义-6.5dB混入LLOUT，经C321/PAM8302A到J506；避免只播放左声道 |
| `--output aux` | 左右DAC分别走HPLOUT/HPROUT，经C317/C318到J504，保持立体声 |
| `--output both` | 同时使用上述主扬声器混音和J504立体声 |
| `--mic` | J505→C325/C326→LINE1L差分输入→左ADC；右ADC静音，不能当成双麦克风录音 |

默认PCM数字衰减为-40dB，捕获PGA为0dB；可用`--pcm-db`在-63.5..0dB内以0.5dB步进调整，`--capture-db`在0..59.5dB调整。它们是寄存器配置，不是已测声压、扬声器额定或麦克风灵敏度。实际麦克风与负载仍未核准。

主扬声器两路的ALSA raw=105，经反向控制变为寄存器13；TI表10-51对应-6.5dB。理想相干双声道求和约0.9463倍（-0.4794dB），这是选值计算，不是输出功率/失真实测。J504使用独立的直通立体声路由，不改成单声道。

工具关闭模拟PGA旁路、未使用的HPCOM/右Line输出及AGC，避免沿用未知旁路设置；录音不被内部直通到扬声器。PAM8302A的使能仍由R311上拉，本工具没有功放断电GPIO，静音不能等同功放或扬声器端子无电压。J506两脚均不是地。

## 先预览与检查

普通Python即可预览，不要求安装amixer，也不打开声卡：

```sh
python3 hat_audio.py plan --output speaker --mic
python3 hat_audio.py plan --output both --pcm-db -40 --capture-db 0
```

后续在新HAT供电/接线条件已经核准、codec模块及overlay匹配当前主控并成功注册后，才检查实际控件：

```sh
python3 hat_audio.py inspect --output both --mic
```

只选ALSA ID为`DuckHAT`的硬件卡，不用默认声卡或随启动变化的数字序号。写入前，工具检查所需70个控件的名称、类型、值数量、整数范围、枚举顺序及读写权限。额外的无关控件不会造成误拒绝；缺少或改变任何必需控件则不写入。

## 显式应用

以下是将来对已核准新板使用的命令，本轮没有执行真实应用：

```sh
python3 hat_audio.py apply --output speaker --mic --report speaker-mic-first.json
python3 hat_audio.py apply --output aux --report aux-first.json
python3 hat_audio.py apply --output none --report muted.json
```

报告文件必须是新文件，已有记录不会覆盖。应用顺序为4组输出/捕获先静音→增益/路由→最后启用目标路径；每次设置核读回，末尾再核完整状态。报告保留之前的值、每次请求及读回、最终快照。默认使用当前系统的amixer，按已归档1.2.8源码的输出格式解析；实际格式/元数据不匹配时失败，而不猜测。

中途失败或Ctrl-C会尝试关闭4组开关，并分别报告是否读回零；关闭失败时明确保留未知状态，不宣称已恢复原设置。强制终止/掉电不能保证清理执行。该过程不是跨进程原子事务，不能与其它程序同时修改同一声卡。工具本身不启动PCM、不播放测试声、不录音、不加载模块、不改变设备树或电源状态。

## 仍需现场完成

- 实际card ID、控件列表/格式、模块/设备树及引脚占用匹配。
- codec硬件RESET、MCLK/I2S与实际PCM参数；初次使用可先按既有48kHz/双声道候选核对，不能从mclk-fs推定已正确出时钟。
- 扬声器/J504负载、音量、麦克风类型/2.0V偏置适配与实际播放/录音。J504低阻耳机条件仍未解决，不能因已有aux配置就放行低阻负载。
- J505是单路模拟麦克风，当前配置选择左ADC。若PCM录音使用两个时隙，右侧静音属于此配置，不能作为第二路麦克风或丢帧故障的证据。

源码/原厂资料、模拟场景和PCB对应关系见[审查记录](../../../../docs/references/扩展板电路仿真工具/audio-routing-20261031/research.md)。模块及overlay说明见[codec入口](README.md)。
