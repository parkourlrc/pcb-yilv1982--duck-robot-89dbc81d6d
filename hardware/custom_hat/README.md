# HAT 自主设计工作目录

当前主工程在[rev_a](rev_a/README.md)。现行文件的原生连通/一致性检查通过，多项电源和布线修复已回写。**[用户确认，2026-10-31] 尚未送厂、没有新板实物。** 工艺/装配接受和供电使用条件尚待落实，当前未放行制造或上电；首板功能在制造后验证，见[最短首板草案](../../docs/specs/20261028-custom-hat/first-article-a1.md)。最新源哈希、数量、审查包以Rev A入口为准，真正待处理项集中在[问题矩阵](../../docs/references/hat-simulation-tools-20261029/issue-matrix-20261030.md)。历史报告只对其记录的源版本有效。

- [现状与证据](../../docs/references/hat-simulation-tools-20261029/qwiic-pinout-20261031/research.md)：A.1已修J502标准针序及C307钢网；旧Rev A不可混用。
- [离线codec驱动与设备树](software/codec/README.md)：对应历史主控内核，已做ABI/DTB文件核查，未部署或实测。
- [BMI088 Linux I2C适配器](software/imu/README.md)：双端点身份/配置/采集代码已构建，现场执行和实物数据未验收。
- [修复方案](../../docs/specs/20261028-custom-hat/recovery-plan.md)
- [需求与阶段](../../docs/specs/20261028-custom-hat/spec.md)

本目录根层的 `custom_hat.kicad_sch` 及功能页是历史骨架，含已取消的屏幕/摄像头，不再作为现行设计入口；保留供追溯。`rev_a/best.kicad_pcb` 等为布线实验，不能凭文件名判为可交付版本。本轮修订的是 `rev_a` 主工程及项目库。
