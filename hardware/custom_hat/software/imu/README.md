# 自设计HAT BMI088 Linux I2C适配器

针对本板头部IMU U501的两个I2C端点：加速度计`0x19`、陀螺仪`0x68`；不替代现有TTL身体IMU200。使用固定版本Bosch BMI08x SensorAPI，已构建ARM64静态程序，并检查错误身份/读失败时不会进入配置。**尚未在Radxa或实物BMI088上运行，不能据此标记IMU验收通过。**

产物：`arm64/bmi088-i2c`、`arm64/manifest.json`。源码为`bmi088_i2c.c`，Bosch原始源码在[驱动证据目录](../../../../docs/references/扩展板电路仿真工具/driver-compatibility-20261031/sources/)，原许可保留于`LICENSE.Bosch`。提交固定为`c1ed227e7bb7da1fa600bbd4e5c82d0da1eb416a`；使用普通BMI088，未套用MM/anymotion变体或COINES板的供电/GPIO操作。

## 工作方式

- `--describe`只输出编译时配置，不打开设备。
- `--probe`只对明确指定的i2c-dev节点读取两个CHIP_ID，要求分别为`0x1E`和`0x0F`；不扫描其它地址、不写传感器配置。读取采用寄存器地址写入+重复起始读取，不等于总线上完全没有写方向报文。
- `--stream`先确认两个身份，再软件复位、初始化、上传Bosch易失配置、设置电源和量程/ODR，并回读配置。任一步失败或回读不一致即停止，不输出假样本。
- 初始诊断配置是100Hz名义ODR、加速度±6g、陀螺仪±500°/s；不是实际频率测量、完整性能上限或整机控制策略的采样合同。
- JSONL输出身份、配置及数据记录：原始三轴整数、m/s²、rad/s、两端点各自的主机读取起止时间、状态位和主机调度超期次数。
- 采集是轮询两端点，**没有硬件同步、标定、姿态融合或机器人坐标变换**。时间戳是CLOCK_MONOTONIC主机读取区间，不是传感器采样时刻。

加速度`accel_ready`来自0x03状态位，读取数据后清除。陀螺仪`gyro_drdy_pulse`是短暂的中断状态，手册规定约280–400µs后自动清除；轮询看到false不表示数据为零或没有历史样本，也不能由它保证每帧为全新同步样本。

## 后续在已核准的新HAT上调用

先核对实际I2C5的设备节点、供电和针序；不要把下例的Linux总线编号直接当本机已确认值。当前新板未制造，以下命令本轮没有执行：

```sh
chmod +x bmi088-i2c
./bmi088-i2c --describe
./bmi088-i2c --device /dev/i2c-5 --probe
./bmi088-i2c --device /dev/i2c-5 --stream --samples 100 > bmi088-samples.jsonl
```

地址由本板焊接配置决定，不提供任意改址参数。没有I2C_SLAVE_FORCE；若地址已被内核驱动占用则拒绝运行。程序使用同一字符设备的协作锁，不能阻止不遵守该锁的其它用户态工具；采集时应由一个程序管理BMI088，不能与其它初始化/采集程序并发。非I2C字符设备、缺少组合传输能力、不完整ioctl结果和NACK均作为失败。

退出只停止读取、关闭文件描述符，不恢复此前传感器寄存器；`--stream`设定的100Hz模式可能继续工作。后续应用应显式初始化自己的配置，不能假设退出会断电。此程序不操作舵机、GPIO、电源开关、内核模块或设备树。

## 离线重现及验证边界

在仓库根目录，使用普通Python和已准备好的Ubuntu WSL工具链：

```powershell
python -X utf8 hardware/custom_hat/scripts/build_bmi088_adapter.py
python -X utf8 hardware/custom_hat/scripts/verify_bmi088_transport_faults.py
```

构建器默认拒绝覆盖已有ARM64产物，先检查manifest；已审阅的源码修复可显式传`--replace-reviewed`，它先核现有产物并归档旧二进制/源/manifest再重建。实际构建工作副本在LOCALAPPDATA缓存，路径会解析成真实位置后再转换为WSL路径。目标静态链接，不依赖Ubuntu构建机的动态glibc，但仍未在目标CPU/系统执行。

已完成native与ARM64警告视为错误的编译、无硬件说明/参数拒绝检查、ARM64静态ELF检查及7个host源代码故障注入场景。故障夹具只模拟身份读和失败路径，拦截所有设备系统调用；没有仿真成功初始化/采样，也没有访问真实I2C。测试源码`bmi088_fault_shim.c`未链接进交付程序。

详细依据、失败与验证数据见[适配记录](../../../../docs/references/扩展板电路仿真工具/bmi088-adapter-20261031/research.md)。实际芯片配置、双端点数据、时间关系、安装方向与整机使用仍待实物核验。
