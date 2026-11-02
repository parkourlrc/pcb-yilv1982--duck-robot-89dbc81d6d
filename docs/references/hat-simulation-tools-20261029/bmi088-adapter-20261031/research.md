# BMI088双端点Linux I2C适配（2026-10-31）

> 本程序构建时的PCB基线为6fe440f3…。后续[A.1](../qwiic-pinout-20261031/research.md)未改变U501/主控针网；最终只读审计已按A.1指纹和原生检查更新，旧审计保留。下方“PCB未改”描述属于适配程序构建阶段，现行源以Rev A.1入口为准。

## 当前结论

**[代码/离线构建]** 已实现本板BMI088的Linux i2c-dev适配，生成ARM64静态程序；覆盖加速度0x19及陀螺仪0x68，不能再把“还没有适配程序”列为当前缺口。**[未验证]** 程序尚未在Radxa/实物BMI088运行，实际配置、采样、同步、安装方向和整机功能仍未验收。

本轮无PCB修改，主板源保持`6fe440f3cfcd9a30550299258cba5bf9355d888b0c166f62919a21adfc5de82a`，此前同版原生检查、BOM/钻孔与kicad-happy审查仍适用。具体代码、产物和调用边界见[适配器说明](../../../../hardware/custom_hat/software/imu/README.md)。没有上电、部署或读取真实I2C。

## 需求与选择依据

原目标包括板载头部IMU可用。已核到历史内核同版本官方发布包没有编入BMI088/BMG160驱动，且所核IIO加速度计实现是SPI路线；详见[官方包复核](../driver-compatibility-20261031/research.md)。本轮保留已有I2C硬件，使用Bosch官方SensorAPI作为用户态适配基础，不为缺内核模块而重排PCB，也不拿只读陀螺仪冒充六轴。

用户既有指示由设计方落实专业参数，本轮选择100Hz、±6g/±500°/s作为初始诊断配置；这不是对用户原需求增加性能上限，也不是已经验证的整机策略采样率。未来若实际用途需要同步、不同ODR/量程或更高带宽，须结合总线和目标应用再核查，不能仅改软件数字就声明达到性能。

## 原始证据

| 来源 | 定位与本轮用途 |
|---|---|
| Bosch BMI088手册 | 已归档`../metadata-repair-20261030/sources/bst-bmi088-ds001.pdf`，BST-BMI088-DS000-19，Revision 1.9/2024-01；PDF页44接口引脚表、页48地址、页26加速度状态、页38陀螺仪状态；SHA见sources.json |
| Bosch SensorAPI | 提交`c1ed227e7bb7da1fa600bbd4e5c82d0da1eb416a`，bmi08a.c/bmi08g.c/bmi08xa.c及三个头文件；逐文件SHA与下载manifest一致，原始许可证保留 |
| Bosch read_sensor_data示例 | bmi08xa_init→bmi08g_init→load_config_file→power/meas配置顺序；只借鉴流程，没有复制COINES供电、SPI/引脚操控；示例main默认BMI085，不能照抄为本板BMI088 |
| Linux i2c-dev文档 | https://www.kernel.org/doc/html/latest/i2c/dev-interface.html，本轮归档HTML及SHA；组合I2C_RDWR、适配器能力和地址选择 |
| 主板/原理图契约 | U501.7 PS=3.3V、.14 CSB1=3.3V、.15 SDO1=3.3V、.10 SDO2=GND、.8/.9为I2C5 SCL/SDA；按真实针号映射到地址0x19/0x68 |

本板U501符号的显示针名仍是Pin_N；不能按名字搜索不到SDO就推断无地址选择。本轮先检查analyzer schema/输出，再按手册针号核对原图板，未把“Pin_15”当厂商功能名。CSB2在本板保持DNC，两个中断网出至测试接口，当前程序不靠中断GPIO或声称硬件同步。

## 已实现的行为

1. 明确区分无硬件`--describe`、只读身份`--probe`和会配置芯片的`--stream`。必须显式给出实际i2c-dev节点，不自动扫描地址。
2. 两个独立端点固定为0x19/0x68；Linux I2C_SLAVE不会被FORCE绕过。必须是major89字符设备并支持I2C_FUNC_I2C，使用协作flock，但不宣称能阻止其它未加锁的用户态工具。
3. ID均匹配0x1E/0x0F后才允许进入配置；软件复位、Bosch初始化/易失配置、100Hz/量程/电源设置后，再读回关键字段。不一致即失败，不输出错误缩放样本。
4. 按Linux接口检查组合读的返回消息数必须为2、寄存器写必须为1；部分完成或负返回均失败。不能把返回非负就当全成功。
5. 输出JSONL：身份、配置、原始六轴、m/s²/rad/s、每个端点的主机读取时间区间和状态。没有输出伪造实测记录，故障夹具不产生sample记录。
6. 100Hz是名义设置/主机轮询目标，未测实际ODR或调度性能；陀螺仪DRDY只是280–400µs短脉冲，false不当成数据失效判据。两传感器分开读取，不宣称同步或完整姿态输出。

静态换算采用16bit有符号输出：加速度raw×6×9.80665/32768，陀螺仪raw×500×π/(180×32768)。这是按已设量程的单位换算，不是零偏、比例因子或安装误差校准；实际范围先由寄存器回读确认。

## 构建与错误路径核查

`build-audit.json`记录源码SHA、709,152-byte ARM64静态ELF和构建输出，现行二进制SHA256为`cb801d516f36c880dd31aa9fc990f046ed171de72e07d61171f66c2769545c1f`。native与ARM64均以-Wall/-Wextra/-Werror编译；目标没有INTERP或动态段，未在AArch64执行。补装了本机WSL的libc6-dev-arm64-cross/linux-libc-dev-arm64-cross，未改变Radxa。

第一次构建失败来自Windows应用的LOCALAPPDATA虚拟路径直接传给WSL；统一先resolve真实路径后再wslpath，原日志保留。第二次失败来自错误使用了不存在的bmi08a_get_regs入口；按实际头文件改用bmi08a_get_status，返回值是规范化的0/1，状态判断也同步修正。没有修改原厂源码来掩盖接口差异。

随后代码复核发现调度超期比较只使用传感器读取完成时间，未计入stdout输出可能阻塞的时间；已改为每轮输出完成后的实际monotonic时间，避免延迟输出后连续追赶。初版源码、二进制、manifest及故障审计保存在build-history/，新版本重新编译并复核错误路径，不把旧source hash的报告套到新程序。

`transport-fault-audit.json`的7个场景是**本机host源代码+虚拟系统调用的故障注入**，不是传感器实测：

| 场景 | 期望与结果 |
|---|---|
| 正确身份probe | 两次身份读成功，配置写0，无sample输出 |
| 错误accel ID / 错误gyro ID | 两端读取后拒绝stream，配置写0 |
| accel组合读只返回1条 / gyro组合读只返回1条 | 拒绝继续，无有效身份/配置/样本输出 |
| 读NACK | 失败退出，配置写0 |
| gyro地址被内核占用 | 在身份读/配置前退出，FORCE未使用 |

所有场景通过。夹具拒绝真实设备打开，检查I2C_RDWR的地址、方向、寄存器与消息长度；未仿真成功初始化、寄存器读取时序、正常采样或ARM64执行。交付程序未链接该夹具。编译、参数拒绝和故障模拟不能替代目标设备功能验收。

`final-audit.json`另从原生PCB读取U501的PS/CSB/SDO/SCL/SDA焊盘，核0x19/0x68配置及CSB2 DNC；同时绑定当前程序/原厂源/故障报告SHA和许可证，并证明PCB仍与上轮kicad-happy检查点同版。它不把接口几何正确提升为总线实测。

## 尚未完成与下一步

- 当前主控内核/实际DTB/I2C5占用未在线取得；历史SSH超时不作当前设备永久离线的结论，本轮也未盲目重试扫描。
- 新HAT仍未制造、未通过工艺/输入配对及首板供电验收；本轮没有执行probe/stream，不将fixture的ID输出当用户板数据。
- 实际BMI088初始化/读回、两部分有效数据、采样关系、安装方向/标定仍需首板。ToF具体外设、音频mixer/负载及其它功能仍各自未完成。
- 目标保持未完成；不提交、推送、下单、上电或使用子代理。下一步只能在现行证据基础上继续，不能退回SPI改板或旧默认地址来制造表面通过。
