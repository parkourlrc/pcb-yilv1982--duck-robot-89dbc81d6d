# 自设计HAT codec离线驱动包

本目录补齐历史主控内核`6.1.84-10-rk2410-nocsf`官方发布包未编入的TLV320AIC3104驱动，并提供对应HAT的设备树候选。**已做离线文件检查，尚未在Radxa安装、加载或验证音频。** 构建基线为6fe440f3…；后续Rev A.1保留此接口，已重新做只读适用性绑定，现行见[主板入口](../../rev_a/README.md)。没有修改现有白色HAT或其v2接线。

## 产物与依据

- `6.1.84-10-rk2410-nocsf/snd-soc-tlv320aic3x.ko`：codec核心模块。
- `6.1.84-10-rk2410-nocsf/snd-soc-tlv320aic3x-i2c.ko`：I2C传输模块，依赖核心模块。
- `manifest.json`：精确内核版本、源码/headers/模块SHA、ARM64 ELF与导入符号CRC检查结果。
- `duck-hat-audio.dts`及同版本目录的`.dtbo`/`overlay-manifest.json`：I2C5、I2S3 M0、MCLK、Pin33复位、供电模型及声卡端点的候选配置。
- [音频路由工具](AUDIO-ROUTING.md)：`hat_audio.py`与精确源码控件目录，提供主扬声器L+R混音、J504立体声、J505左ADC录音的预览/检查/应用；仅离线验证，未操作真实声卡。
- [完整证据](../../../../docs/references/扩展板电路仿真工具/driver-compatibility-20261031/research.md)：官方资产SHA、配置/模块索引、两种Zero3W官方DTB、失败记录和未验证条件。

模块源来自radxa/kernel提交`e6d12a77c8bc0ea6decbd3e4604ec131d4032c30`的三个原文件，原文保存在证据目录`sources/exact-sound__soc__codecs__tlv320aic3x*`，遵循其原GPL许可；没有把厂商驱动改写为本项目原创。离线构建使用官方同版本headers及Module.symvers，未重建整套内核。Ubuntu gcc13与官方构建所用Debian gcc12.2存在版本差异，ABI文件核对不能替代实际加载验证。

## 设备树与PCB对应

| 配置 | 本板连接 |
|---|---|
| I2C5 M0，100kHz | J101.29/.31，codec 0x18；板载BMI088 0x19/0x68，后者暂不在overlay中伪绑定缺失驱动 |
| I2S3 M0 | BCLK=Pin12、MCLK=Pin13、LRCK=Pin35、SDI=Pin38、SDO=Pin40 |
| 时钟主机 | Radxa提供BCLK/LRCK，TX时钟供收放共用；mclk-fs=256，实际时钟/采样率待验证 |
| 硬复位 | J101.33=GPIO3_C3，bank3 offset19，低有效；保留板上R308/C310 |
| 3.3V供电 | 使用官方DT的`vcc3v3_sys`，对应官方V1.11页20/22的GPIO `VCC3V3_SYS`；没有误接睡眠时可能关闭的`vcc_3v3`模型 |
| 1.8V供电 | 固定regulator模型描述HAT的LP38691输出，无软件开关GPIO，不意味着软件能关闭这路实际电源 |
| 播放 | LLOUT→板载PAM8302A→J506；HPLOUT/HPROUT→J504 |
| 录音 | LINE1L→J505模拟麦克风路径，MICBIAS候选2.0V；实际麦克风类型/偏置和差分输入mixer配置待确认 |

`HAT J504`的Line widget只是DAPM端点类别，不核准低阻耳机、不删除或改变外部负载需求。R311使功放默认使能，overlay没有虚构功放GPIO开关。J506两个端子均不是地。

## 本地重现

在仓库根目录，使用已具备Python和Ubuntu WSL交叉编译工具的环境：

```powershell
python -X utf8 hardware/custom_hat/scripts/prepare_codec_module_build.py
python -X utf8 hardware/custom_hat/scripts/build_codec_module.py
python -X utf8 hardware/custom_hat/scripts/verify_codec_overlay.py
```

已有模块产物时构建器会拒绝覆盖；先检查现有manifest，不盲目重跑。headers/source工作副本在LOCALAPPDATA缓存，路径由`module-build-preparation.json`记录；不把目标ARM64 host工具直接当x86_64工具执行。构建脚本只在该私人缓存中重建host工具。

## 使用前仍需核对

当前Radxa版本、实际DTB、I2C5/I2S3/Pin33占用、已加载的其它overlay和模块状态尚未读取；不得仅凭历史uname就安装。若版本不同须使用该版本的源码/headers重新构建。此处没有自动安装/重启/上电脚本。

codec节点和ALSA声卡成功注册后，可用[路由工具](AUDIO-ROUTING.md)核对70个必需控件，再显式配置LLOUT/J504及LINE1L；实际控件和声音尚未验收。没有将overlay编译、声卡枚举或模拟读回当作播放/录音验收。100nF RESET的实际低脉冲、MCLK/I2S、音频负载、麦克风及供电仍需在已批准首板条件下验证。[BMI088 I2C适配器](../imu/README.md)已另行产出，但实际采样及ToF外设仍未验收。
