# 项目知识（2026-09-30）

> **历史记录 / 2026-10-15 复查**：三个上游参考库位于 `references/`，本项目调研仍在 `docs/references/`。以下旧主机/训练日志保留历史含义，不是本轮运行结果；当前工作区为 `E:\Projects\duck-robot`，WSL2 Ubuntu 已列为 Running，旧训练环境及 Linux CUDA/依赖功能尚未核验。见[本轮软件研究](../docs/references/动作训练软件研究/research.md)。

## 2026-10-09 增补
- **硬件到位**（用户确认，实物复测未做）：微雪 Bus Servo Adapter (A)、黑色 XT60 降压模块（丝印 7.2-16V 待核；2026-10-10 实测更新见 PROGRESS 与 docs/photos：实为 7.2-18V，空载下限 ≈6.3V）、绿色 IMU2DXL 板（2026-10-09 用户确认 = ScrapMeta microduck-diy **v0.3**，STM32G031；本行早先记"v1.0 待核"已过时）、白色鸭图案 HAT（**实物丝印 V1.2**，2026-10-10 照片确认，PROGRESS 已同步；存档原理图为 V1.0，图物差异大：背面多 F303 类 MCU + 超级电容，V1.2 图纸待向板卡来源索取）；全部舵机与打印件到位，数量待清点。明细与待办见根 `PROGRESS.md`。
- **方案方向**：主参考改为 `microduck-community-kit`（飞特 HD-1910-C001 + 官方 robotd 飞特补丁 + imu_to_dxl 总线从站）。缺口：`software/microduck_feetech/` 未推送、主控↔总线物理适配未开源、真机整定值需复测。
- **参考库清理**：replica 锚定 `0f2cff6bd7`、tutorial 还原为上游 main（2026-10-09 哈希校验 0 差异）；A 训练库内修改（4 改 + 51 增）提取至 `local-changes/`，其中 `export_onnx.py` 含失效 `/mnt/e/` 路径。
- 工程自 E 盘迁 C 盘后，文件时间戳全部为 2026-10-09，**不能再按时间戳找改动**，版本核对一律走上游哈希对比。

## 范围与规则
- **2026-10-09 历史工作区快照**：当时从 E 盘迁至 `C:\Projects\duck-robot`；当前（2026-10-15）为 `E:\Projects\duck-robot`，旧 `/mnt/e/`、`E:/` 路径须逐项核对，并非全部必然失效。交流用简体中文；含中文的 `.ps1` 必须 UTF-8 BOM，文件操作不跨 shell 拼接。
- A、B 是独立上游源码快照，不能混合模型、策略、硬件配置或采购资料。不要为了跑通而直接修改上游配置或锁文件。
- **参考库只读（2026-10-09 用户定规）**：`references/microduck-replica/`、`references/microduck-community-kit/`、`references/microduck-build-tutorial/` 是别人的方案，只读参考，禁止在里面做任何修改。用户进度记在根 `PROGRESS.md`；历史混入的本地修改已提取到 `local-changes/` 并还原上游原样（快照锚点与校验记录见 PROGRESS.md「参考库使用规则」）。
- **2026-09-29/30 历史验收**跑通的是 B 的 XL330 平地短训练链路，不是 HD1910/C 线，也不是本轮验收；当时没有进行实机控制。

## 已安装环境与入口

> ⚠️ **本节为旧机训练环境历史记录**：2026-10-09/10 的“无 WSL”是当时状态；2026-10-15 已查询到 WSL2 Ubuntu Running。旧 venv、日志、Linux CUDA/训练依赖是否可用仍待查，不把下面版本/PID/路径当现行事实。复用应在可写工作副本逐项核对，见[本轮复查](../docs/references/动作训练软件研究/research.md)。
- WSL 发行版 `Ubuntu`，用户 `yilv`，Ubuntu 24.04；RTX 4080 16GB 可用。
- Linux uv：`/home/yilv/.local/bin/uv`，版本 0.12.20。
- 训练目录：`/mnt/e/Projects/duck-robot/references/microduck-replica/software/training`。
- 虚拟环境：`/home/yilv/.venvs/duck-robot-training`。设 `UV_PROJECT_ENVIRONMENT` 为此路径；`UV_HTTP_TIMEOUT=600`、`UV_LINK_MODE=copy`。使用 `uv run --frozen`。
- 已按锁文件安装 142 包：Python 3.12.3、PyTorch 2.9.1/CUDA 12.8、Warp 1.12.0、MuJoCo 3.10.0、MuJoCo Warp 3.8.1、BAM 1.0.1、rsl-rl-lib 5.0.1、ONNX Runtime 1.24.4。
- 新增 `scripts/b-training.sh` 和 `docs/b-training.md`，已经独立审查。入口支持 check/list/smoke/play/export/tensorboard，**没有正式 train 模式**；smoke 固定 64 环境×5轮，play 固定1环境，export拒绝覆盖，TensorBoard仅127.0.0.1默认6007。
- PowerShell 可运行：`wsl -d Ubuntu -- bash /mnt/e/Projects/duck-robot/scripts/b-training.sh check`。
- 重要陷阱：mjlab 1.3.0 的 `list-envs` console入口把任务数量作为退出码；改用 `uv run --frozen python -m mjlab.scripts.list_envs`，不能 `|| true` 吞错误。
- PowerShell向 `wsl ... bash -lc '含shell变量的复杂脚本'` 传参可能提前展开变量。本次可靠方式是 PowerShell单引号here-string，经管道传给 `wsl -d Ubuntu -- bash -c "tr -d '\r' | bash -s"`。

## 已验证成果
- 短训练：64环境×5轮，7680环境步，5轮nan_state均0；20项测试通过（test_nan_guard、test_obs_nan_guard、test_head_pose_bias）。
- 证据目录：`references/microduck-replica/software/training/logs/setup/20260929-165723/`，含check/list/smoke/tests/export日志、validation.json、xl330-smoke.onnx、model-preview.png。
- ONNX checker及CPU ORT 5组有限值检查通过，输入[1,61]、输出[1,14]，包含观测归一化。
- model-preview.png是MuJoCo GLFW渲染的**静态STAND姿态，不是策略行走表现**。交互play/native/viser尚未实际验收。
- TensorBoard曾在 http://localhost:6007/#scalars 后台启动，Windows端主页和scalar API均HTTP200；状态会变化，先检查再启动/停止。旧PID保存在上述目录的tensorboard.pid，不能不核验身份就kill。
- 上游pyproject.toml SHA256：45f3476af2b5bba1c3199aadb8372ec1bb08496ca91b08dec78543addd5c8440；uv.lock：2eeeb680025baa737e7ccf3a87da3695a9d49b228de0bb60d8af0c022ab5f1aa。安装前后均未变。

## 用户完成的正式训练及性能
- Run：`references/microduck-replica/software/training/logs/rsl_rl/velocity/2026-09-29_17-16-06_xl330_walk_v1/`。
- 实际参数见该run的 `params/agent.yaml`、`params/env.yaml`，优先于当前源码默认值。YAML含Python标签；只读提取用 `yaml.BaseLoader`，不要UnsafeLoader。
- 对应命令：`uv run --frozen train Mjlab-Velocity-Flat-MicroDuck --env.scene.num-envs 1024 --agent.max-iterations 5000 --agent.logger tensorboard --agent.run-name xl330_walk_v1`；resume=false，重复命令会重新训练。
- 最终checkpoint为 `model_4999.pt`。1024×24×5000 = 122,880,000环境步；5000是PPO采样/更新轮数，不是5000个动作或episode。
- TensorBoard实际5000轮时间跨度109.8分钟；均值采样1.17275秒/轮、学习0.10352秒/轮，约19409环境步/秒。采样/仿真占采样+学习时间约92%。
- 最后一轮平均episode长度约914步（18.3秒，上限20秒），不等于速度跟踪或实机已达标。不要用综合奖励直接宣称会走。
- 对5090 32GB同1024环境/5000轮/无实时渲染，仅给过**70–100分钟粗估**，未做5090实测，不应当成benchmark。建议热身后测100–200轮再外推。4096环境×5000轮有4倍样本，不是同工作量。

## B训练结构与任务含义
- `software/training/src/mjlab_microduck/tasks/__init__.py`注册任务；`microduck_velocity_env_cfg.py`定义观测/动作/奖励/课程/PPO；`robot/microduck_constants.py`定义HOME、BAM和模型选择；`robot/microduck/robot_walk.xml`为14主动关节模型。
- Actor：归一化→61→512→256→128→14，隐藏层ELU、训练Gaussian探索；Critic：76→512→256→128→1。无RNN；部署仅Actor及归一化。
- Actor输入48维本体状态（角速度3、重力3、关节位置14、速度14、上次动作14）+13维指令（速度3、头颈4、身体姿态6）。输出为默认姿态上的关节位置偏移，scale=1。
- 物理dt=0.005，decimation=4，控制dt=0.02；每轮每环境采样24步；PPO5 epochs×4 minibatches，gamma=.99、lam=.95、初始lr=.001自适应。
- 该任务练习平地速度跟踪、站立、转向和头部指令，不练导航、视觉理解或摔倒起身；跌倒触发reset。身体姿态输入保留但对应reward权重为0。
- 速度指令每3–8秒重采样：vx±.4m/s、vy±.3m/s、yaw±1rad/s。头部指令每2–5秒重采样。episode上限20秒，跌倒倾角阈值70°。
- 保存的课程：step=迭代×24；站立比例2%→25%，动作变化惩罚-.1→-1；躯干重心扰动3mm→15mm，头部3mm→10mm。有源码注释与实际stage不一致，读取实际配置/日志。
- reward manager本次按dt缩放：r=0.02×sum(weight×term)。部分惩罚函数本身为负，不能仅看weight正负。

## 可视化边界
- 当前mjlab 1.3.0标准train没有实时三维viewer入口，可用 `--video True --video-interval 2000 --video-length 200` 录制训练视频，输出run/videos/train；默认只渲染选中环境和少量邻居。
- `play --num-envs 1024 --viewer viser`可显示多环境（Environment/Hide others不勾选），但这是**固定checkpoint评估，不是同批训练实例的实时直播**。脚本play固定1环境，多环境须直接调用uv。
- 真正边训练边看需增加低频状态监视；建议显示16–64个环境，可选1024全景，不为可视化直接迁移整套Isaac Lab。

## A的缺失与镜像取证
- A部署控制14舵机，但现存 `microduck/src/model/urdf/robot.urdf`和`model/mjcf/robot.xml`为19可动关节结构（双臂6、双腿12、头1）；XML actuator第597–615行。**不能据此断言缺失的A训练模型也是19关节。**
- A训练缺 `mjlab_microduck/src/mjlab_microduck/robot/`及microduck_constants定义；当前源码还缺子项目README、uv.lock、部署cad/docs。
- A自带walk.onnx实际[1,51]→[1,14]；其部署代码仅兼容51或加2相位的53维，不可直接换B的61维ONNX。A行走KP125，B训练kp_fw200，IMU坐标亦须核对。
- 已**实际只读分段检查**官方image.v1镜像，不只是README推断。镜像内 `/home/user/microduck/`含uv.lock、README、cad/step及stl、docs（含dev/clone_sd.md）、.venv、walk.onnx和手柄服务。未在已检查用户目录、部署目录、/opt与部署venv找到完整训练工程/缺失robot定义。
- 镜像walk.onnx与本地A SHA256完全一致；抽查main.py、constants.py、pyproject.toml及19执行器robot.xml忽略CRLF后与本地一致。镜像没有自动解决仿真模型错配，CAD存在不保证适合当前14舵机实物。
- 镜像只读检查工具/块缓存：`C:\Users\yilv\AppData\Local\Temp\duck-image-audit-20260929\inspect_image.py`，用 `uv run --no-project --with dissect.extfs python ...`；支持目录、--cat、--hash、--xml-summary、--grep、--filter。未刷卡或执行镜像内程序，未整包下载校验SHA。
- 镜像URL：https://github.com/AI-FanGe/Microduck-build-tutorial/releases/download/image.v1/microduck.img.xz ，768792340bytes，官方SHA256 096885dc32fb5b1db2ad69ba6bea868d8ab988f2b47c0d884eb63ba0dfdcb5c4。

## 硬件与结论边界
- XL330官方供电3.7–6.0V；A/B仿真存在超过6V的参数，绝不是安全供电建议。
- A启动main.py就会使能扭矩并回中位，不能假设按v才动。任何实机动作前须验证供电、映射、零位、IMU并可靠支撑。
- 训练优化的是策略，不会自动辨识实物质量、摩擦或电机参数。Real2Sim先修正固定约定与主要响应，随机化覆盖剩余可测变化；完整步态和实机效果仍需独立验收。

## 嘉立创自动下单工具（tools/jlc-order，2026-10-08）
- 官方API已取证：嘉立创开放平台 open.jlc.com，网关 https://open-api.jlc.com，全POST+JSON（上传multipart、签名用meta JSON）。鉴权 Authorization: JOP appid/accesskey/nonce/timestamp/signature；签名串5行（方法/去域名URL/unix秒/32位随机串/报文体）各以\n结尾，HmacSHA256(SecretKey)+Base64。JOP签名实现已用官方文档示例值逐字节golden验证（tests/test_auth.py）。
- PCB业务5大接口（计价/创建订单/返单/查单/进度）+文件上传；官方SDK仅Java，工具为纯标准库Python≥3.11，uv管理dev依赖。33个测试通过；dry-run零网络发送、下单类命令默认交互确认且失败不自动重试。
- **未完成**：api_spec.py 中除 /order/v1/createOrder（官方文档示例路径）外均为占位，需登录 open.jlc.com 控制台（仅支持微信扫码登录）→ 接口文档对齐路径与字段；真实联调（doctor→quote）与真实下单验收未执行。用户已有密钥但未在本会话提供/登录。
- banana_pcb 实测：板框矩形 126.41,86.5→165.6,93.29mm 即 39.19×6.79mm 双层板；production/banana_pcb.zip 为完整KiCad gerber包（13文件，校验通过）。下单参数模板 examples/banana_pcb.toml。
- 真实配置 tools/jlc-order/jlc-order.toml 与台账 orders.jsonl 已加入根 .gitignore；密钥仅存该文件或 JLC_APP_ID/JLC_ACCESS_KEY/JLC_SECRET_KEY 环境变量。