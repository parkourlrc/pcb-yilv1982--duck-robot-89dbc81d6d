# 网页联合模型躺姿恢复：实现与离线验收

本文记录实现阶段的授权和离线条件；随后用户另行要求“部署”，现已完成安装及只读验收，详见[部署记录](webpad-recovery-deployment-20261101.md)。物理起身尚未测试。

- 日期：2026-11-01。
- 授权：用户明确“按方案实现，先不部署和动作”。对应 [Spec](../../specs/20261101-webpad-walk-recovery/spec.md)。
- 范围：C 线、飞特 HD-1910-C001、新单 3P IMU、原版混合 SYNC_READ；不沿用 v0.3 单播实验。
- 交付：[工作副本、补丁及候选入口](../../../software/robotd-recovery/README.md)。

## 已完成

**[源码核验／离线实测]** 实现独立 `robot.recover`、API 43 和网页按钮，直接选择已有 `Net::Walk` 联合模型。
开始、每 100 ms 心跳及取消均带会话约束；原生租约 500 ms，过期不接受旧心跳。
控制线程上力后重新读取完整反馈，滤波历史从当时关节位置开始；普通起步保护保留。
恢复最多 8 秒，连续 1 秒符合姿态判据后零速度保持；失效反馈、断连、超时及停止取消并请求卸力回读。
需要用户明确点“开始走”并通过普通起步检查才交接，不自动行走或自动重试。

源自固定 control.47 导出和 2026.10.3101 Studio，源码身份与原件 SHA 见 [SOURCE.md](../../../software/robotd-recovery/SOURCE.md)。
原生 10 个文件、Studio 5 个文件的补丁及哈希已保存，独立从原始包重放后逐文件一致。
总线、IMU 解码、依赖锁、六模型、标定与现有普通行走参数未改；没有写入设备。

**[实测／离线]** ARM64 release 构建成功；候选 robotd 为 7,222,040 字节，SHA256
`fe200aabe2700a492cfb4ea8523c505d4047c26e081c4b18266af1cb8511e82a`。
候选和基线回退材料只保存在本地，完整清单见 [candidate-manifest.json](../../../software/robotd-recovery/candidate-manifest.json)。

## 验收及限制

恢复状态机 4 项、真实 ONNX＋假 IO 完整流程 4 项、Studio 后端 7 项、浏览器心跳逻辑 7 项通过；
协议 55 项及普通起步相关 15 项通过。原始日志与失败修正见 [验收记录](../../../software/robotd-recovery/verification/README.md)。
一项旧 `r17_empty_snapshot_and_warming_imu_do_not_accept_home` 在候选及原始源码均失败，独立留档；未宣称全工作区测试通过。

**未验证：** 实际网页渲染、板侧加载及真机从躺姿恢复。假 IO 不模拟地面接触和机器人动力学，不能由这些测试推断成功率。
IMU 与关节判据只表示姿态满足条件，无法独立确认足底承重；已装模型的 `deployment_verified=false` 声明不变。
实现阶段未安装或动作；后续安装已获得明确授权并完成，起身与行走仍未执行。修改保留工作区，未提交、未推送。
