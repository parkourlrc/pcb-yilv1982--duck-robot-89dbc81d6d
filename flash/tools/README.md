# flash/tools 说明

烧录工作流依赖的随仓库工具/发行包。

| 目录 | 用途 | 边界 |
|---|---|---|
| [xpack-openocd-0.12.0-7/](xpack-openocd-0.12.0-7/) | xPack OpenOCD 离线发行包（0.12.0-7） | 上游原样保留，不改二进制；再分发前核对上游版本、校验与许可 |
| [imu200/](imu200/) | imu200 验收辅助工具 | 与 `flash/README.md` 的板型边界一起使用 |
| [servo-web/](servo-web/) | 烧录/台架辅助脚本 | 不作为 servo-web 主工作副本；主副本在 `software/servo-web/` |

不因文件多而删除离线发行包；需要释放空间时先记录来源、版本、SHA 与恢复方式。
