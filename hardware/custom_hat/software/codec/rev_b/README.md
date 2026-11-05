# Rev B.0音频配置候选

此目录仅针对Rev B.0候选硬件，尚未部署、没有音频实测；A.1配置继续留在上级目录追溯。

- `duck-hat-revb-audio.dts`采用独立12MHz固定时钟给codec，由codec统一输出BCLK/LRCK、CPU接收时钟，避免独立振荡器与CPU时钟异步；不再请求40P pin13的MCLK复用。I2C5仍pin29/31、100kHz，RESET仍pin33。没有BMI088节点。
- 扬声器接PAM8406右BTL通道，由codec RLOUT驱动，音量计划将左右DAC混入右线输出；不能沿用A.1的左线输出和J504路由。
- 板载麦接U701.16/MIC2R，默认右声道采集；外接两麦接LINE1L/LINE1R，采用single-ended模式。外接麦由MICBIAS经2.2kΩ供电；板载MEMS由3.3V供电。不能沿用A.1差分LINE1L麦克风设置。
- `audio-plan.py --speaker --microphone onboard`只输出ALSA控制计划，不连接设备或写寄存器；`external-stereo`切换到外接双麦。先静音再配置，起始PCM为−40dB，混音通路各约−6.5dB。
- 依据归档的实际内核`e6d12a77c8bc0ea6decbd3e4604ec131d4032c30`的AIC3X驱动控制名和PLL计算；12MHz支持须结合离线编译及首板时钟/播放/采集验收，不能仅凭设备树源断言运行通过。
- 已通过两种ZERO 3W基DTB（AP6212、AIC8800DS2）的`dtc`编译、`fdtoverlay`合并及关键属性回读，见`docs/references/扩展板乙版降本/audio-offline-audit.json`。首板音频约定48kHz/S32_LE/双通道；codec以12MHz生成转换和总线时钟。归档Rockchip驱动支持`BC_FC`从模式、AIC3X驱动支持`CBP_CFP`主模式；其它采样率和实物时序仍待验收。
- 不与A.1 overlay同时加载。已有A.1模块是否匹配新系统内核须现场核对，本轮不刷写或改变运行中的Radxa。
