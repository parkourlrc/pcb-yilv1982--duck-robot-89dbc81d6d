# 照片归档区（历史硬件）

本目录存放**已被现行结论取代**的历史照片与标注图。原件移入此处保留追溯，不再作为当前接线、针序或上电依据。

| 归档集 | 内容 | 归档原因 | 现行替代 |
|---|---|---|---|
| [hat-v1.2-white-20261010/](hat-v1.2-white-20261010/README.md) | 白色 V1.2 HAT 正反面、标注、针序、R31 定位等 20 个文件 | 2026-11-02 用户确认当前 HAT 为 kissqy/Microduck-kissqy hardware；作者 AMP2.0 BOM 无 48 脚 MCU（唯一多脚 IC 为 TLV320AIC3104 QFN-32），与本组照片的 F303 LQFP48 冲突，确认不是当前硬件 | [kissqy 参考工程](../../schematics/kissqy-hat-reva-reference/README.md)；当前实物照片待补 |
| [imu-gd32-single-port-20261014/](imu-gd32-single-port-20261014/README.md) | jyg9 GD32 单 3P IMU 正反面与定位标注 5 个文件 | 2026-11-02 用户确认当前 IMU 为 kissqy `imu_to_dxl RevA V1`（STM32G031 + LSM6DSV16X） | [IMU 版本调研](../../references/惯性单元三版来源对比/research.md) |
| [hat-v1.0-sch-pages/](hat-v1.0-sch-pages/) | 旧 V1.0 原理图 PDF 的 5 页导出图（page1–5.png） | 图纸版本 V1.0，与旧白色 V1.2 已不对应，更非当前 kissqy HAT | [原理图索引](../../schematics/README.md) |

## 使用规则

- 本区文件**只用于追溯历史判断**，不得据其针序、供电或位号操作当前硬件。
- 新增归档时同步更新 [照片索引](../README.md) 与对应专题，写清归档原因和替代入口。
- 不删除原始文件；如需更正，另存新图并在此登记。
