# HAT 主控驱动与官方内核包核对（2026-10-31）

> 本页驱动构建基线为6fe440f3…。后续[A.1](../qwiic-pinout-20261031/research.md)只更正J502接口/局部线及钢网，主控/codec/BMI088针网保持。overlay和只读适用性审计已按A.1完整指纹重新绑定；旧报告保留在该专题software-before-a1/。下面“未改PCB”等描述指本构建阶段，不覆盖后续板修订。

## 当前事实与范围

**[本机历史记录]** 2026-10-14与2026-10-24的本机Radxa记录为Debian 12、`6.1.84-10-rk2410-nocsf`。这不是2026-10-31在线读取结果；上一轮SSH连接超时，当前运行内核/DT仍未取得。依据分别为[系统记录](../../瑞莎开发板系统镜像/research.md)和[现场复核](../../飞特策略模型上机核对/research.md)。引用后者只取本机系统版本，不引入B线策略、接线或训练结论。

**[官方发布文件核对]** 已取得`radxa-pkg/linux-rk2410-nocsf`的`6.1.84-10`官方发布包，包内配置明确未编入TLV320AIC3X的I2C/SPI驱动、BMI088加速度计及BMG160陀螺仪驱动。包内1204个模块文件及modules.alias/builtin/dep另行检索，未找到这些驱动。**如果实际主控仍使用该未改动发布包，单加设备树不会产生可用codec/完整BMI088驱动。** 不把这个条件推成当前主控已经现场检查。

本轮已构建匹配该版本的两个离线codec模块，并完成声卡overlay对两种官方Zero3W DTB的编译/合并检查；后续也已产出[BMI088双端点Linux适配程序](../bmi088-adapter-20261031/research.md)，但均未在目标板运行。没有改变PCB；主板仍是`6fe440f3cfcd9a30550299258cba5bf9355d888b0c166f62919a21adfc5de82a`，此前同版原生检查及kicad-happy复审适用。

## 官方包和源身份

| 项目 | 已取得的身份 |
|---|---|
| 发布页 | https://github.com/radxa-pkg/linux-rk2410-nocsf/releases/tag/6.1.84-10 |
| 包装仓库提交 | `317ea1500020f5c3e7ecdebc77a672146a968ace` |
| 内核src提交 | `e6d12a77c8bc0ea6decbd3e4604ec131d4032c30`，radxa/kernel |
| image包 | `linux-image-6.1.84-10-rk2410-nocsf_6.1.84-10_arm64.deb`，26,889,672 bytes |
| image SHA256 | `9c685954f65735a2ee4f778984ff59014313a4b5a04b1e8a7dd7e1687cc9707b`，与GitHub发布资产digest一致 |
| headers包 | `linux-headers-6.1.84-10-rk2410-nocsf_6.1.84-10_arm64.deb`，8,546,704 bytes |
| headers SHA256 | `7c6db6d5191dd9e4167afa54918eab5684394b4df324e213d368cc673b134700`，与发布资产digest一致 |
| Bosch SensorAPI | boschsensortec/BMI08x_SensorAPI，提交`c1ed227e7bb7da1fa600bbd4e5c82d0da1eb416a` |

大包保存在本机LOCALAPPDATA下的duck-robot-tools/radxa-kernel/6.1.84-10缓存，准确路径及SHA见`runtime-package-audit.json`、`module-build-preparation.json`。关键配置、模块索引、三份官方Zero3 DTB和所用源码已在本专题`sources/`归档，不能只靠临时聊天证据。下载程序只解析ar/tar中的选定常规文件，未安装或执行deb的维护脚本。

最初查到的是**不带nocsf**的`radxa-pkg/linux-rk2410`，其本地Makefile指定RK3588配置，标签最高为本次查询到的6.1.84-9，内核src为04e2d04…；它与本机历史版本不相同，作为被排除的比较分支保留。`source-selection.json`描述该初始比较及Bosch来源，**不能作为当前待构建内核的身份**；以`runtime-package-audit.json`为准。

## 包内编译配置

定位：`sources/runtime-config-6.1.84-10-rk2410-nocsf`，逐项结论同时存于`runtime-package-audit.json`。

| 能力 | 官方同版本包配置 | 含义 |
|---|---|---|
| I2C字符设备 | CONFIG_I2C_CHARDEV=y | 有用户态I2C接口基础，实际i2c5启用/权限另核 |
| Rockchip I2C | CONFIG_I2C_RK3X=y | 控制器驱动存在，不表示HAT总线已经启用 |
| Rockchip I2S/TDM | CONFIG_SND_SOC_ROCKCHIP_I2S=y、I2S_TDM=y | I2S3仍需引脚、时钟及声卡配置 |
| simple-audio-card | CONFIG_SND_SIMPLE_CARD=m | 相关两个模块文件存在 |
| TLV320AIC3X I2C/SPI | 两者not set | AIC3104所需codec模块缺失，新增overlay不足以补齐 |
| BMI088_ACCEL | not set | 包内无该IIO加速度计驱动；所核源码Kconfig且依赖SPI，不是本板I2C接口的完整方案 |
| BMG160 | not set | 包内无兼容BMI088陀螺仪的该IIO驱动 |

官方DTB中I2C5和I2S3均为disabled；存在`i2c5`、`i2s3_2ch`、`gpio3`、`pinctrl`及所需M0 pinctrl符号。已将ap6212版DTB反编译为`runtime-zero3w-ap6212.dts`用于核对；aic8800ds2和3e原始DTB一并归档。反编译保留上游重复地址/图节点等警告，不当成此次HAT改动产生。用户当前实际DTB型号/overlay仍待读取。

## codec模块准备与限制

精确内核提交的`tlv320aic3x.c/.h`和`tlv320aic3x-i2c.c`已归档；I2C设备表包含`tlv320aic3104`，OF表包含`ti,tlv320aic3104`。核心驱动与之前参考Linux v6.1文件SHA相同，但“源码支持”不代表发布内核已编译，这次正是两者有差别。

本地Windows/WSL原先没有所需gcc/make/ARM64交叉编译器或dtc，Docker守护进程未运行，未启动Docker。已在本机Ubuntu WSL安装必要的gcc、make、ARM64交叉编译器、头文件/库开发包与dtc等构建工具；这只改变本机开发环境，未改变Radxa。当前gcc为Ubuntu 13系列，官方内核由Debian gcc12.2构建，后续必须明确该差异并核查ABI，不将编译器警告忽略为实测通过。

headers包是ARM64目标环境的包，带有ARM64构建工具。本地x86_64构建须重新编译fixdep/modpost/genksyms，不能直接执行原ARM64文件。首次尝试普通`make scripts`触发了headers包不具备的完整Kconfig重建，失败后已从原始SHA一致的headers恢复；第二次外部模块模式没有重建这些host工具，缺fixdep而失败。失败日志保留，均未产生可交付的已验证模块，未修改PCB或运行设备。

`build_codec_module.py`现已完成构建，`software/codec/Kbuild`描述两个模块组合。核心模块109,672 bytes，I2C模块10,744 bytes；两者均为AArch64 ELF，vermagic均为`6.1.84-10-rk2410-nocsf SMP mod_unload modversions aarch64`。44+11项导入符号CRC与官方Module.symvers/本次核心模块导出一致，0不匹配；源/headers/模块SHA已写入`codec-module-audit.json`及[模块目录](../../../../hardware/custom_hat/software/codec/README.md)。只算离线构建及ABI文件核对，不能宣称已加载、播放、录音或复位波形通过。

第三次构建已成功，但Windows启动的WSL PATH未包括modinfo/modprobe位置，审计暂时失败；改用`/usr/sbin/modinfo`及只读`modprobe --dump-modversions`后检查通过。这两个调用没有加载模块。此前失败记录未计作通过。

## 声卡overlay的实际检查范围

`duck-hat-audio.dts`已编译，并分别与官方ap6212和aic8800ds2版Zero3W DTB离线合并。核对I2C5=100kHz、codec地址0x18、I2S3实际选中的5个M0引脚组、GPIO3_C3低有效复位、codec实际选中的GPIO pinctrl、3.3V/1.8V供电引用、CPU/codec DAI和主时钟角色；结果在`audio-overlay-audit.json`，没有将“符号存在”当作“节点已经选择该符号”。引脚映射另与当前PCB网表契约对照，MCLK明确为Pin13。

供电引用使用`vcc3v3_sys`。这是依据官方Zero3W V1.11原理图页20的GPIO `VCC3V3_SYS`及页22电源标识，并与发布DTB固定3.3V节点对应；没有把睡眠可能关闭的`VCC_3V3`混为同一路。原厂PDF沿用`../metadata-repair-20261030/sources/radxa_zero_3w_schematic_v1.11_20250116.pdf`，不表示用户实物版本已识别。

候选采用Radxa为BCLK/LRCK主机、TX时钟收放共用、mclk-fs=256，MICBIAS设置候选2.0V；主扬声器为LLOUT路径，J504为HPLOUT/HPROUT，录音为LINE1L及Mic Bias。J504的DAPM Line widget不核准任何负载，也不取消用户需求。实际采样率/时钟、静音和mixer路由、麦克风型号、RESET波形仍待现场核对；没有进行binding-schema校验、ALSA注册或功能测试，更没有部署/重启主控。

## BMI088：保留I2C接口的可行路线

在此次核对的IIO源码及vendor input/sensors的accel/gyro目录中，未找到可直接覆盖本板I2C加速度计的完整现成驱动。这个搜索范围不覆盖所有外部模块或当前主控自行安装的软件，不做“Linux绝不支持”的断言。

Bosch官方SensorAPI有I2C接口、独立加速度计/陀螺仪上下文及读写回调，能够作为Linux i2c-dev适配的基础，**无需仅因上述发布包缺驱动就改PCB为SPI**。本板SDO1高、SDO2地，对应accel 0x19、gyro 0x68，分别期望CHIP_ID 0x1E/0x0F；codec保持0x18。初始化、power mode、量程/ODR与读取需分别覆盖两个器件，不能只出现一个地址就标六轴IMU通过。

已下载的是普通BMI088接口相关`bmi08a.c`、`bmi08g.c`、`bmi08xa.c`及头文件/示例；库同时含MM/anymotion变体，不能无条件混用。第一次请求`bmi08x.c`为404，实际源文件是`bmi08xa.c`，已根据官方tree补取，失败条目保留。后续已生成ARM64静态Linux I2C适配器，完成严格编译、原板针序绑定和7项host故障注入检查；实际目标执行、采样、时间戳或安装方向仍未验，见[适配记录](../bmi088-adapter-20261031/research.md)。

## 文档真实性修复与下一步

发现仍在使用的`order-checklist.md`保留“U701.7未连、MPN/fiducial缺项”等旧结论和错误相对路径，现已改为当前制造条件：已关闭文件问题单列，制造/采购、输入配对/负载、实际驱动和首板条件仍保留。此前已停用的BOM/设计/上电草案保持历史状态，不重新启用固定100/300mA或通用4.75V阈值。

BMI088适配代码已补；下一步在取得当前主控状态后核查codec包/overlay及IMU程序适用性，按实际设备完成加载、配置与功能验证。当前实际内核/DT未取得前不部署或加载。制造接受、J504负载定义、输入保护/线束、首板功能与装配仍未完成。目标保持active，不提交、不推送、不下单、不操作实物、不使用子代理。

本轮最终`offline-package-final-audit.json`核两个模块的当前文件SHA/ABI、全部源码SHA、overlay源/二进制/网表绑定、两种官方DTB实际选择的针组与供电/DAI、headers `.config`与官方image配置逐字节一致，以及PCB源保持6fe440f3…，结果通过；相关文档链接和`git diff --check`通过。这些检查没有扩大为制造或硬件通过。

## 2026-11-04 补：实际板卡的无线模块型号

板侧内核与启动日志给出直接证据，**本机是 AIC8800D80 组合模块，不是 AP6212**：

- `walk-crash-current_kernel-20261102.log`：`aic8800_bsp: loading out-of-tree module`、`AICWFDBG(LOGINFO) aicwf_sdio_chipmatch USE AIC8800D80`，固件路径 `/lib/firmware/aic8800_fw/SDIO/aic8800D80/…`；
- `walk-crash-boot-tail-20261102.log`：`Starting rsetup-aic8800-reset AIC8800 Bluetooth on ttyS1…`；内核同时注册 `Bluetooth: Core ver 2.22`、`PF_BLUETOOTH`。

因此：

- **WiFi**：AIC8800D80，支持 5 GHz（作者建议 ZERO 用 5 GHz 避开 2.4 GHz 手柄干扰）；
- **蓝牙**：同模块提供，走 UART（ttyS1）+ `rsetup-aic8800-reset` 服务，系统用 BlueZ/`btd`，手柄配对走 `robotctl pad pair`；
- 本目录归档的 `ap6212` DTB 只是官方包里的另一变体，**不能当作本机无线型号**；此前按 ap6212 推断的 2.4G-only 不适用于本机。
