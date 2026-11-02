# 已装模型能否从躺姿自动起身

当前补充：下面保留原版control.47的来源核对。用户随后批准独立恢复入口实现并要求部署；新入口已安装、只读验收通过，见[部署记录](webpad-recovery-deployment-20261101.md)。物理起身效果仍未验证。

日期：2026-11-01。用户问“现在有模型，让它躺着的时候能自己站起来吗？”本次为只读问答核对，未改配置、重启、发送扭矩／站姿／速度／技能命令。

## 结论及边界

- **[上游模型说明／训练配置核验] 有倒地恢复训练配置，但本机尚未验收效果。** 已加载的 walk 模型是 `velstand`，SHA256 `1cbf8730eadd75a5704332c9f3c10f60bfa9412135b907831c9dbd731ce1795f`。随包 manifest.description 写明行走、零速度保持、倒地恢复；导出 env.yaml 同时包含倒地初始化课程和恢复奖励。同时 `entry_pose=standing`、`deployment_verified=false`。不能把配置、作者说明或成功加载等同于本机任意躺姿都能起身，详见下方继续核对。
- **[源码核验] 已运行过程中倒地与躺着启动是两个入口条件。** 原生 safety 的倒地判定本身不停止正在驱动的策略，HOME 起步保护只检查从关闭到开启的边沿。walk 联合模型可在已开启的运行中继续依据姿态反馈输出；未实测恢复成功率，也不能覆盖通信丢失、用户卸力等其他停止条件。
- **[源码核验] 当前从躺姿、策略关闭状态，普通网页入口不能直接启动恢复策略。** 网页“站起来”调用 `robot.init`，走关节回 HOME，不是调用倒地恢复模型；“开始走”调用 `robot.enable on=true`，飞特起步需实测 HOME、关节上力、新鲜反馈和倾角不超过10°。躺着不能满足直立检查。
- **[源码核验／实测] 底层保留旧手动恢复代码，但参考版本已明确退役该技能，并非本机漏装。** `robot.do(skill=stand_test)` 的旧分支要求同名技能；`config/r17-management.json` 和 `packaging/configure.py` 则明确删除这个旧 teacher 技能，并把 LB 迁移为 kick_left。当前只存在 roulade、kick_left、kick_right 和内置 ground_pick、sit_toggle，符合该迁移。不能照旧“LB起身”注释操作，也不应仅补回旧配置。
- **[实测] 此次回读已变化为上力保持。** `motion/control`，扭矩开启且已确认，`homed=true`，动态 `policy_enabled=false`、`active_model=null`、`home_recovery=false`。IMU推算倾角约90.77°，最大HOME误差5.27°；HOME起步保护ready=false，当前回报先命中关节误差，姿态也不满足≤10°要求。未做实物量角，不判断是仰躺、俯卧或侧躺。

上述普通起步限制有原版源码与回包支持；“这台机器能从某躺姿成功恢复”仍未验证。用户随后批准[联合模型恢复入口方案](../../specs/20261101-webpad-walk-recovery/spec.md)并要求部署，已完成实现、离线验证及板侧安装，新独立入口可用；普通起步限制保留。见[实现记录](webpad-recovery-implementation-20261101.md)和[部署验收](webpad-recovery-deployment-20261101.md)，未触发起身动作。

## 用户要求继续后的来源核对（2026-11-01）

### 旧入口为什么不能直接补配置

**[源码核验]** 固定来源为 `fanhao375-Microduck-kissqy-27d7921`、原版 control.47；本机已恢复此版混合 SYNC_READ。以下相对路径均从下方来源第 3 项的 firmware 根计算：

- `config/r17-management.json:152–169` 的 `retire_standalone_recovery` 指定删除 `stand_test`、旧模型 `a481d9f211f31d9476ab1a319fe362a2`，将 LB 从起身迁到左踢，RB 补为右踢。
- `packaging/configure.py:240–245` 实际执行退役迁移；`verification/kick154-input-audit.json:299` 明确写明 joint walk policy handles recovery，teacher 源文件仅保留作回归素材。
- `robotd/src/selftrained_checks.rs:102–165` 中 6 秒的 stand_test 测试属于旧 teacher。旧流程结束时 `main.rs:2735–2749` 关闭策略并把 hold 置为 HOME；不能将固定时长结束当作已检测到站稳。
- `robotd/src/control.rs:612–638,708–741` 只对 `Net::Walk` 应用当前模型的 uniform 执行参数。把同一 ONNX 放入 `Net::Skill` 会绕开这条分支，因此“同一权重”不等于“相同输出处理”。

**更正**：上一轮“专用恢复入口尚未配置”的描述不足，容易误解成漏装一个技能。现已替换为“旧 teacher 已退役，当前缺少供用户从策略关闭的躺姿启动联合模型的网页入口”。旧代码可用于参考预载、上力后重读、请求取消流程，不能当作当前推荐接线或运行方案。

### 联合模型包含什么训练证据

模型源目录为 `training/logs/b-feetech-walk-20261024/runtime-package-review/Microduck-Robotd-FT6-R17/models/1cbf8730eadd75a5704332c9f3c10f60/`：

| 文件和定位 | 核验内容 | 证据边界 |
|---|---|---|
| `使用说明.md:23` | 行走老师和联合模型均使用 walk 槽；联合模型包含相应倒地恢复训练 | 作者说明，非本机实测 |
| `deployment-execution.json` | uniform：action_scale=1.0、head_lowpass=0.5、legs_lowpass=0.7 | 当前导出的运行参数；新入口应原样复用 |
| `deployment-runtime.json` | source_iteration=9599、24 steps/env、training_step=230376 | 导出元数据，非独立训练运行日志 |
| `upstream-params/env.yaml:2805` 起的课程区 | fell_over 终止角从 70° 放宽至 π；prone 初始化分阶段增加，到 step 53760 配置 prone_prob=0.45、face_down_prob=0.5、side_prob=0.5、crouch_prob=0.2 | 配置包含倒地课程；未核验 reset 函数对条件概率的精确定义，不计算实际仰卧／俯卧／侧卧比例 |
| 同文件 `recovery_success_weight` | step 23040 后恢复奖励 10.0，fallen_tax=-0.5 | 奖励设计不能证明策略学会恢复或给出成功率 |
| 同文件 `fallen_too_long` | gate_z_below=0.08、gate_tilt_above_deg=40、max_duration_s=8 | 带姿态／高度条件的训练倒地终止配置，不是硬件安全时长认证 |

**[实测：文件哈希]** env.yaml 的 SHA256 为 `7dd666e4515ad91c1512ce2188152a34764830126dc0ede8145d768f851a6027`，与 deployment-runtime 声明及 export-data.zip 中同名文件一致。未执行带 Python 对象标签的 YAML；只读文本和字节哈希。

**[推断]** 导出的 training_step 高于最后倒地课程阈值，与作者“行走＋倒地联合9600轮”说明一致。仍未排除：训练实际完成度不足、某类倒地姿态覆盖不足、实物与训练参数差异、推理周期不足等；没有仿真回放或本机起身成功数据来逐项排除，不报告成功率。

### 网页与真机边界

- **[部署源码快照核验]** `webpad-models-snapshot-20261101.json` 中 `studio/pad_drive.py:1591–1608,1749–1822` 同时在展示和后端要求普通技能处于 DRIVING；只补技能名或只改按钮会继续被拦截。应加独立恢复操作，普通站姿／行走入口保持原有条件。
- **[部署源码快照核验]** `web/pad.js:35` 为100 ms发送节拍，pad_drive.py开头引用的原生速度deadman为500 ms；pad_drive.py:89方向盘租约为6秒，pad.py:53的watch为2秒续期／6秒失效。普通速度归零不会关闭联合模型，所以新增恢复还需单独的有限期运行租约，不能把现有watch误写成已具备恢复断连卸力。
- **[源码核验]** 入场可参考原版 main.rs:3113–3274：当拍完整传感器、已确认 IMU、预载当前位置后上力、上力后重新读取，以及请求 generation 取消屏障。恢复要走 `Net::Walk`，不能调用旧 teacher。
- **[限制]** 现有反馈没有足底接触或机身离地高度的直接测量。IMU 直立、关节接近 HOME 只能作为“姿态恢复”判据，不能独立证明稳定承重。新方案明确区分软件判据和实物站稳。
- **[实测历史]** 前序卸力状态下曾测到主控 85°C、408 MHz 降频；约 50 Hz 的卸力循环不等于模型推理满足实时要求。后续动作验收需记录实际周期，不能据加载成功保证运行表现。

本轮尝试通过浏览工具打开来源仓库 `https://github.com/fanhao375/Microduck-kissqy`，工具未返回可读正文；未将其当作在线核验依据。上述结论来自已归档固定源码及模型导出文件，不代表查询到了上游最新版本。摘录和文件哈希见 [本轮源码证据](getup-source-review-20261101.json)。

## 来源

1. [当前真机回包](getup-availability-20261101.json)：由现有 [只读脚本](check-webpad-policy-gate-20261101.py) 经 SSH 执行，调用 robot.policies、robot.skills、pad.bindings、robot.health、robot.busStatus 和 HTTP模型库。板钟UTC独立记载。Windows SSH结束有既有pending socket提示，JSON完整解析通过，不是动作错误。
2. [已部署模型附属文件快照](webpad-models-snapshot-20261101.json)：models 中walk的manifest.json、model-info.json；后者名称“行走＋倒地联合9600轮”。这里的“官方”是随包作者文字，不升级为硬件厂商认证。
3. 固定原版源码根 `training/logs/b-feetech-walk-20261024/controller-preparation-20261031/controller-source/fanhao375-Microduck-kissqy-27d7921/microduck-hd1910/firmware/`：
   - `robotd/src/main.rs:5533–5570`：专用stand_test分支及未加载拒绝；5877–5960：普通enable起步检查；3669–3688：仅已接通的手动恢复获得独立入口。
   - `robotd/src/home_start.rs:105–144`：实测HOME、上力、5°关节误差及10°倾角门槛；文件开头说明不检查已经运行的策略。
   - `robotd/src/control.rs:495–610`：当前技能/起坐/站立/行走优先级；没有把“模型含倒地恢复”变成无条件自动启动。
   - `duck-control/src/safety.rs:22–24, 382`：倒地判定本身不是运行中策略停止条件。
   - `duck-control/src/policy.rs:395–415`：未配置独立stand网络时回退到walk；本机stand=none不表示联合模型内部恢复能力被拆掉，也不证明该能力有效。
4. [网页加载与映射验收](webpad-models-check-20261101.md)：六模型已加载、网页站起来→robot.init，LB为kick_left；此前部署结束时卸力是历史验收状态，本轮新回读为上力保持。

记录已保存，未提交。参考库、运行代码与配置均未修改。
