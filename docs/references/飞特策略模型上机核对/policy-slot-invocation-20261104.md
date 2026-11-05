# 策略槽的调用逻辑（robotd 源码核对，2026-11-04）

- 对象：kissqy/Microduck-kissqy 的 robotd（R17 V167 / control.43 同源），核对时 `main` 提交 `d4d21c1`。
- 目的：说明一个 ONNX 策略从配置到每 50 Hz 推理、再到关节目标的完整调用链，作为自建模型上机的前置说明。
- 证据等级：[源码核验]；未在实机复跑这些函数。

## 源码位置

| 层 | 文件 |
|---|---|
| 配置结构 | `microduck-hd1910/firmware/robotd-params/src/lib.rs`（`PolicyParams`、槽位与调参） |
| 策略加载/推理 | `firmware/duck-control/src/policy.rs`（`Policy::load`、`Policy::infer`、`Net`） |
| 观测/命令 | `firmware/duck-control/src/obs.rs`（`Observation::build`、`Command`、61 维布局） |
| 控制循环/调度 | `firmware/robotd/src/control.rs` |
| 启动与 RPC | `firmware/robotd/src/main.rs`（`Policy::load` 调用、`robot.policies`、`robot.loadPolicy`） |

## 1. 配置层

`[policy]` 解析成 `PolicyParams`：

- `enabled`：是否加载策略。`false` 时只保持姿势、循环仍然健康；
- `mode`：`walk` / `roller`，决定默认槽位；
- 槽位路径：`walk`、`stand`、`sitstand`、`ground_pick`、`kick_left`、`kick_right`、`roulade`；`"none"` 表示禁用该槽；
- 调参：`gain`、`standing_gain_ratio`、`action_scale`、`standing_action_scale`、`head_lowpass`、`legs_lowpass` 等。

## 2. 加载层：`Policy::load`

```rust
Policy::load(&PolicyPaths, standing_threshold)
```

1. `ensure_runtime()`：先探测 ONNX Runtime dylib，避免 `ort` 在控制线程里 panic；
2. 对每个槽位，如果同目录有 `deployment-contract.json`：
   - 读合同，检查 `contract.slot` 与槽名一致；
   - 检查所有模型声明的 `firmware_p` 一致（BAM 增益不能混）；
3. 每个槽建一个 `Network`（`ort::Session`）：
   - 校验输入 `[1, 61]`、输出 `[1, 14]`；
   - 读取元数据（关节名、默认姿态、action scale、归一化等）；
   - 预热一次；
4. 任一步失败 → **整次加载失败**，robotd 保持姿势并报 unhealthy（让 updater 回滚），而不是带着坏模型走。

## 3. 每 tick 调用链（control.rs）

```text
1. 推进 skill 窗口/计时（roulade、kick、ground_pick、sit↔stand）
2. command = 平滑后的意图（twist=[vx,vy,vyaw]、head[4]、body{z,roll,pitch}）
3. net = 选择网络：
     显式 skill 请求 > sit/rise > 按速度幅值的 stand/walk
   优先级：roulade > kick > ground_pick > sit/rise > stand(阈值内) > walk
4. obs = Observation::build(imu, q, dq, home, last_action, command)  // 61 维
5. action = policy.infer(&obs, net)                                  // 14 维
6. targets = home + action_scale × action
7. 可选一阶低通（head 5..9、legs）
8. safety.apply(targets) → 总线写舵机
9. last_action = action（进入下一 tick 的 obs）
```

- `Observation::build` 的 61 维布局：0..3 陀螺、3..6 投影重力、6..20 关节位置（减 home）、20..34 关节速度、34..48 上一动作、48..61 命令块（48..51 vx/vy/vyaw、51..55 头、55..60 body padding）；
- `Policy::infer`：按 `Net` 选网络；切换网络时 `reset()` 清 LSTM 状态；推理失败不把状态带进下一 tick；请求了未加载的槽会回退到 walk（调度器本应先检查 `has_*`）。
- `stand` 选择：`twist_magnitude() < standing_threshold`（默认 0.05）且已加载 stand 时用站立网络。

### 3.1 九个阶段的实现要点

1. **窗口推进**：`SkillDef` 的 `duration` 决定窗口（roulade 1.0 s、kick 0.5 s），`chain` 决定能否连发（roulade true、kick false），`unwind_s` 决定收招时长。`start_skill` 设 `ActiveSkill { phase: Holding, remaining: duration, chain: 0 }`；`step()` 开头判断 `remaining <= 0` 做转移，**电机写入之后**才 `remaining -= dt`（dt=0.02 s），所以窗口长度=ceil(duration/0.02) 帧，最后一帧仍执行技能命令。`chain` 由 `start_skill` 在收到同技能请求时置为 `CHAIN_WINDOW=0.15 s`，窗口结束时 `chain>0` 就重开一轮并 `policy.reset()`。`Sit::Rising` 同样倒计时转 `Up`；ground_pick 相位在写入后推进（`phase += dt/period`，到 `end_phase` 结束）。
2. **命令再编码**：技能运行中 twist 用定义里的 `command/unwind`，head/body 清零；ground_pick 用 `[cos φ, sin φ, 0]` 编相位；sit 用 `[1,0,0]`、rise 用 `[0,0,0]`；walk/stand 用平滑后的原命令。每个模型还有 `contract.clamp_command` 把命令夹到训练范围。
3. **网络选择**：`skill > ground_pick > sit/rise > stand(幅值) > walk`；`twist_magnitude() < 0.05` 且有 stand 网络时走 stand；`body_active` 时清零 twist 并强制 stand。
4. **观测**：`Observation::build` 按 61 维布局填充；关节位置减 home；`policy_joints` 跳过嘴部；`last_action` 是上一帧**未缩放**的 14 维输出。
5. **推理**：`Policy::infer` 选网络、切换时 `reset()` 清 LSTM、`ort` 单线程跑、失败不把状态带入下一帧。
6. **目标**：`scatter_action` 把 14 维散到 15 关节（嘴部保持 home）；`targets[j] = home[j] + scale × offset[j]`；scale/gain 按 walk/stand/skill 和 contract 的 runtime profile 选；contract 的 EMA 在低通之前。
7. **低通**：头 5..9 与腿（除头/嘴）各用一阶 `t = α·t + (1−α)·prev`；contract 可要求 passthrough。
8. **安全层**：`Safety::apply` 先按需写 gain；非有限值**拒绝**并写入 hold；再逐关节夹到执行器行程；最后 `io.write(JointTargets)`（总线 sync_write）。命令死区在更早的 `Safety::gate`：intents 超时只清零 twist，不清 head。**注意：Feetech/HD1910 后端的 `set_gain` 是 no-op**（`feetech.rs` 明确写“retains native servo gains; XL330 gain requests are not written”），所以 `[policy] gain` 在这台机器上不会真正改舵机 P 增益，只是被计算/上报；要改增益需用舵机调试工具直接写寄存器。
9. **反馈**：`last_action = action`（原始 14 维）供下一帧观测；过滤后的 `targets` 存 `self.previous` 供下一帧低通。

### 3.2 动作衔接与“行走时做头部动作”

- **没有网络间的混合/过渡**：一次只有一个 `Net`。切换时 `Policy::infer` 对目标网络 `reset()`（清 LSTM/内部状态），但控制器级的 `last_action`、`previous` 目标**不会**因 `start_skill` 重置（只有 `reset()` / `reset_for_home()` 会清）。所以新技能第一帧的观测仍带着上一个网络的 `last_action`，目标低通也可能从旧目标开始；衔接质量主要取决于训练时的 entry pose/命令编码和滤波配置，不是 runtime 保证的。
- **行走 + 头部动作不需要两个网络**：61 维命令块里的 `head[4]`（neck_pitch/head_pitch/head_yaw/head_roll）就是给 walk 网络的命令。官方训练 recipe 把 `head_pose_tracking` 作为主目标之一，命令每 2–5 秒重采样，观测里也有 `head_command`——所以边走边转头/点头是同一网络的正常输入，不是叠加。
- **不要后加头部偏移**：命令已经在 obs 里，再往 walk 输出上叠加会“双重添加”（obs.rs 注释专门警告过）。
- **超出训练范围的头部动作**：只能把该动作作为 head 命令加入 walk 的训练课程（仍是一个网络）；runtime 不支持 walk 与 head-only 两个网络并行，也不支持输出叠加，除非改 Rust 代码。

### 3.3 命令块（48..61，共 13 维）

| 索引 | 内容 | 单位/含义 | 训练范围（官方 recipe） |
|---|---|---|---|
| 48..51 | vx, vy, vyaw | 躯干系速度 m/s、m/s、rad/s | vx ±0.4、vy ±0.3、vyaw ±1.0；2% 零命令、15% 原地转圈桶 |
| 51..55 | neck_pitch, head_pitch, head_yaw, head_roll | **相对 HOME 的角度增量**，rad | 课程上限：±1.10、±1.10、±1.40、±0.31；初始只有 ±0.05/0.07/0.015 |
| 55..57 | body x, y | 相对标称站姿的位移，m | 训练里采样 ±0.005，但 **runtime 硬编码为 0**（未绑定） |
| 57 | body z | 高度增量，m | ±0.005 |
| 58 | body roll | rad | ±0.05 |
| 59 | body pitch | rad | ±0.05 |
| 60 | body yaw | rad | **runtime 硬编码为 0**（未绑定） |

要点：

- 命令是**目标/增量**，不是叠加偏移；策略在训练中学会跟踪它，runtime 不再二次相加；
- head 是相对 HOME 的增量，不是绝对关节角；body 是相对标称站姿的增量；
- body 的 x/y/yaw 在 runtime 固定为 0，喂非零值也不会进入观测；
- 行走/站立用同一套 61 维布局，技能会重编码命令（roulade/kick 全零、ground_pick 用相位、sit 用 [1,0,0]），见 3.1。

### 3.4 每个模型的命令语义不同

| 槽/技能 | 61 维输入 | 13 维命令的语义 |
|---|---|---|
| walk | 是 | twist 速度 + head 增量 + body（walk 里 body 奖励为 0，基本不响应） |
| stand | 是 | 期望接近零命令（站立保持） |
| sitstand | 是 | twist 的 vx 是**姿势标志**（1=坐，0=起/站），不是速度 |
| ground_pick | 是 | twist = 相位编码 `[cos 2πφ, sin 2πφ, 0]`；head/body 全零；周期 4 s、窗口 2.8 s（end_phase 0.7） |
| kick/roulade | 是 | 全零命令；固定 1 s/0.5 s 窗口 |

所以“形状都是 61 维”不代表“每个模型都能执行任意命令”——同一组数字在不同模型里含义不同，喂错就是分布外输入。

**GroundPick 期间 vx>0**：**这是代码重编码，不是模型权重行为**——`step()` 在 `ground_pick.is_some()` 时直接把 twist 换成相位 `[cosφ, sinφ, 0]`，操作者的 vx 在进入 `Observation::build` 之前就被覆盖，模型根本看不到它；但 `start_ground_pick()` 不检查速度/是否站立，所以可以在行走中触发，机器人会带着动量从行走直接进入抓起动作（entry_pose 是 standing，属于分布外）。若绕过调度器直接把 vx>0 喂给 ground_pick 网络，则是它没训练过的输入，输出不可预期。

## 4. RPC 与热切换

- `robot.enable` / `robot.stop`：开/关策略；
- `robot.policies`：列出槽位、来源、加载状态；
- `robot.loadPolicy`：运行期换模型；新网络在**独立线程**加载（约 1 秒），若替换的是正在驱动的网络，机器人先回 home 再切换；失败时保留旧控制器；
- 技能按钮走 `robot.do` 一类请求，映射到 `skills` 列表的索引。

## 5. 对自建模型的要求

- ONNX 输入 `[1,61]`、输出 `[1,14]`，元数据包含 14 关节顺序、默认姿态、`action_scale`、归一化已烘入；
- 训练时执行器用 **BAM M6**、控制 50 Hz，否则 sim2real 差；
- 需要同目录 `deployment-contract.json`（`slot` 与配置槽名一致，`firmware_p` 与其它模型一致）；
- 作为**新槽位**加入 `[policy]`（如 `skills` 列表），不要覆盖官方 walk；
- 机器人支撑、策略关闭/扭矩受控时切换，先低速验证。
