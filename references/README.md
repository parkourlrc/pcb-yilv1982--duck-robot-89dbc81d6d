# References：上游参考资料

三个独立上游快照统一放在本目录。**各子库内部只读**，不把本项目进度、采购状态、勘误或补丁混写进去；规则见 [AGENTS.md](../AGENTS.md)。2026-10-10 从根目录原位置整体迁入，文件内容不变。

| 目录 | 路线与用途 | 重要入口 |
|---|---|---|
| [microduck-community-kit/](microduck-community-kit/README.md) | **C 线主参考**：飞特路线社区电路板、固件、软件补丁 | [飞特补丁](microduck-community-kit/firmware/v1/patches/README.md)、[IMU 固件](microduck-community-kit/firmware/v1/README.md)、[舵机调试器](microduck-community-kit/software/hls_servo_debugger/README.md) |
| [microduck-replica/](microduck-replica/README.md) | **B 线复刻研究参考**：机械、电控、器件资料及训练 | [电控采购](microduck-replica/docs/电控采购清单.md)、[HD-1910 厂商资料](microduck-replica/tools/FeeTech_HD1910M_Servo/README.md)、[许可说明](microduck-replica/NOTICE.md) |
| [microduck-build-tutorial/](microduck-build-tutorial/README.md) | **A 线回退参考**：Pi Zero 2 W / OpenRB / XL330 教程 | [本项目 A 线存档](../docs/route-a-baseline-20260928.md) |

## 与其他目录的区别

- **`references/`**：上游参考库原件，保持各库许可和内部结构，不混合路线。
- **[`docs/references/`](../docs/references/)**：本项目自己的调研记录、证据、勘误与判断。
- **[`local-changes/`](../local-changes/README.md)**：历史本地修改提取件；未随本次迁移，不是完整可运行工程。
- **[`hardware/`](../hardware/)**：本项目明确管理的硬件工作副本。

修改上游参考库需要用户明确授权。内部文档、脚本可能包含上游或历史机器的绝对路径，目录移动不代表运行环境已经迁移或验证。迁移记录与校验结果见[目录整理记录](../docs/references/上游参考资料目录整理/research.md)。
