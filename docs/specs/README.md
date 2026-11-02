# Spec 目录索引

功能/修改任务的 spec 存档：每任务一个 `YYYYMMDD-主题/` 目录，内含 `spec.md`。流程与模板见[简单 Spec 开发流程](../spec-process.md)。

| 目录 | 任务 | 状态 |
|---|---|---|
| [20261101-webpad-walk-recovery](20261101-webpad-walk-recovery/spec.md) | 网页独立调用联合walk模型从躺姿恢复 | 已部署并通过只读验收；用户随后尝试恢复和行走并报告停机，11-02日志排查中，尚无成功起身验收；11-02 用户要求全量提交 |
| [20261101-webpad-policy-enable](20261101-webpad-policy-enable/spec.md) | 网页手柄接通六模型加载 | 用户批准后已接通；六模型加载、五绑定无错，保持卸力，动作未测试；11-02 用户要求全量提交 |
| [20261101-studio-calibration-handover](20261101-studio-calibration-handover/spec.md) | 将 robotd 启动配置接入 Studio 原生标定交接 | 已交付；迁移仅重载、预览通过；用户随后正式写入成功、进入 motion/control；11-02 用户要求全量提交 |
| [20261101-studio-home-zero-alignment](20261101-studio-home-zero-alignment/spec.md) | 对齐 Studio 舵机页与 IMU 页站姿零位 | 用户批准后已部署，15 个 zero_raw=2048 原生回读通过；两服务恢复、保护不变，未试站姿；11-02 用户要求全量提交 |
| [20261101-restore-mixed-sync-read](20261101-restore-mixed-sync-read/spec.md) | 新单口 IMU 恢复原版混合 SYNC_READ 和状态判据 | 已回滚部署；servo-web 30 秒只读通过，动作未测试 |
| [20261101-servo-first-imu-read](20261101-servo-first-imu-read/spec.md) | 三次站姿复现、等待判错比较与先舵机后 IMU 对照 | 实验完成，四次均在起身阶段失败并卸力；7/7 传输测试通过，改序未解决问题，该次回退原单播版，现通信补丁已撤回（历史实验） |
| [20261031-studio-commissioning-display](20261031-studio-commissioning-display/spec.md) | Studio 调试模式舵机数据显示适配 | 已部署，真实网页接口总览/舵机表均 15/15；IMU 更新，方向验证标志保留，模型未运行 |
| [20261031-reference-policy-data](20261031-reference-policy-data/spec.md) | 按参考项目导入六模型、运行参数和标定数值 | 10-31 已导入并通过6/6无电机预检；11-01 已改为本机标定、六模型加载成功，动作未测 |
| [20261031-robotd-v03-unicast](20261031-robotd-v03-unicast/spec.md) | 安装 Studio/Python 3.13/robotd，适配当前 v0.3 IMU 单播 READ | 环境安装保留；v0.3 单播补丁 11-01 已撤回，原验收作为历史记录 |
| [20261028-custom-hat](20261028-custom-hat/spec.md) | KiCad 自设计 HAT；[审查清单（原报告未入库）](../references/hat-simulation-tools-20261029/kicad-happy-review-20261030/manifest.json)、[供电/地检查点](../references/hat-simulation-tools-20261029/power-repair-20261030/research.md)、[制造条件](20261028-custom-hat/order-checklist.md) | **局部修复完成，最终审查不通过**；普通DRC为0，仍1项未连接，另有MPN/fiducial/工艺/热/回流缺口；不可投板 |
| [20261027-sync-read-cascade](20261027-sync-read-cascade/spec.md) | SYNC_READ 主机侧缺席连锁错位缺陷（缺席 ID 之后全部应答被错位吃掉；实测坐实，含单舵机 294.7ms 逐项对账与 386 拍 bad_id 5786 精确吻合） | **待确定（未立项）**：排障期保持上游对照，暂不修；候选修复方向已列 |
