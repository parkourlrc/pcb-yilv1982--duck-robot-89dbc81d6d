# 已确认硬件原理图档案

存放**本项目实物在手、且已确认对应关系**的硬件原理图/设计源文件。每块板一个子目录，来源与版本钉死在上游提交。查证分析记录另见 `docs/references/`（那里保留研究过程，这里只放权威文件副本）。

| 子目录 | 硬件 | 确认依据 | 权威文件 | 上游来源与版本 |
|---|---|---|---|---|
| `imu-to-dxl-scrapmeta-v0.3/` | 绿色 IMU 板（imu_to_dxl v0.3，32×22mm，STM32G031F8P6 + LSM6DSV16X） | 2026-10-09 用户确认对应 [ScrapMeta/microduck-diy](https://github.com/ScrapMeta/microduck-diy/tree/main/imu_to_dxl) | `*.eprj2`（嘉立创EDA专业版工程，真源） | `main @ aa4c32d`（hardware/ 最后改动，2026-09-10）；MIT |
| `microduck-hat-v1.0-sch/` | 白色鸭图案 HAT（实物丝印 **V1.2**，2026-10-10 照片更正；Radxa Zero / Pi Zero 形态） | 2026-10-09 用户供图并确认 | `SCH_..._2026-10-06.pdf`（5 页原理图，图版本 **V1.0**） | 社区改绘版（嘉立创EDA，原理图 V1.0，2026-09-03~09-20）；派生自官方 pollen-robotics/elec_RPI_Robot_HAT（Apache-2.0）。⚠️ 图物差异大（实物多 F303 MCU + 超级电容）。查证：`docs/references/microduck-hat-20261006/` |

**上游设计资料已取得、实物修订对应仍待核的硬件**：

| 硬件 | 来源与边界 |
|---|---|
| jyg9 / community-kit 单 3P GD32 IMU（当前排查对象） | 本地只读参考目录已有[KiCad 工程](../../references/microduck-community-kit/hardware/imu_to_dxl/imu_to_dxl.kicad_pro)、[PCB 布局](../../references/microduck-community-kit/hardware/imu_to_dxl/imu_to_dxl.kicad_pcb)、[原理图](../../references/microduck-community-kit/hardware/imu_to_dxl/imu_to_dxl.kicad_sch)。KiCad 9，布局标 `imu2dxl 0.2 / 2026/9/27`；2026-10-26 上游 API 亦确认文件存在，但当前上游 blob 与本地快照不同，未同步覆盖。实物修订尚未逐网核对，来源、指纹及生产文件入口见[记录](../references/imu-to-dxl-variants-20261009/research.md#single-port-pcb-20261026)。 |
| 微雪 Waveshare Bus Servo Adapter (A)，实物丝印 v1.1 | 2026-10-25 从官方 Wiki 取得[含 CH343P/USB 的单页原理图](../references/servo-web-imu-3d-20261024/waveshare-bus-servo-adapter-a-schematic-20261025.pdf)；图中未标版本号，不能宣称已与实物逐件对应。供电网络核对、SHA256 及旧无 USB 图的区别见[供电研究](../references/servo-web-imu-3d-20261024/research.md#waveshare-usb-20261025)。更正此前“无公开原理图”的记录。 |

**尚未取得原理图的到位硬件**（只留定位信息）：

| 硬件 | 说明 |
|---|---|
| 黑色降压模块（XT60，丝印 7.2-16V） | 通用商品模块，无公开原理图；用前实测输入下限/输出（见 PROGRESS 待办） |

> 同源参考：fanhao375 replica 的 imu_to_dxl 原理图 PDF（STM32G031 同引脚布局的另一块板）在参考库 `references/microduck-replica/hardware/imu_to_dxl/imu_to_dxl-原理图.pdf`，可作对照，但**不是本档案板的图**。
