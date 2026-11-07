# 训练网页显示与依赖来源

2026-11-06。仅显示层适配，不改变训练物理、碰撞、质量、惯量、关节或策略接口。

## Studio 模型

- 原件：`software/studio/model-source-2026103101/`，固定上游提交 `3952471a8394c8b720817d2160ffd95ce5a54456`，部署来源版本 `microduck-software-v2026.10.3101`。
- 网页通过同源 `/studio-model/model/model.json`、`meshes.bin` 及 `model-worker.js` 读取原件，不复制简化几何、不回退简模。
- `studio-model.js` 复用原 Studio 网格解码结果、材质配色规则、body 层级、关节轴与原始挂接变换；修改的是网页相机、地面以及完整世界位姿驱动。
- [文件核验] Studio 有 16 个 body、28 个 mesh；根 `trunk_base` 的静态高度为 0.12 m，训练 `duck_v0.xml` 的初始根高为 0.1182 m。显示根直接采用仿真 world position 与 wxyz quaternion，不再叠加 Studio 静态根高度，不从重力推算偏航。
- [文件核验] 14 个训练关节按名称映射弧度；层级的相对位置、四元数和轴对应现有训练模型。额外 `mouth` 固定 0，不增加动作维度；不使用实物舵机 ID 或标定方向。
- 上述核验与外观复用不代表本机真实动力学对齐；Studio 原件及许可保留在源目录。每窗口独立材质、renderer、环境纹理，关闭释放 WebGL context；最后窗口释放共享几何。

## 固定本地分发依赖

全部文件保存在 `vendor/`，运行时无 CDN 请求；从 npm 固定版本分发取得，不升级训练 Python 栈。源包许可原样保存于各目录 `LICENSE`。

| 依赖 | 固定版本 | 分发来源 | 官方来源 |
|---|---|---|---|
| Preact | 10.26.4 | `https://cdn.jsdelivr.net/npm/preact@10.26.4/` | `https://github.com/preactjs/preact` |
| htm | 3.1.1 | `https://cdn.jsdelivr.net/npm/htm@3.1.1/` | `https://github.com/developit/htm` |
| ECharts | 5.6.0 | `https://cdn.jsdelivr.net/npm/echarts@5.6.0/` | `https://github.com/apache/echarts` |
| three.js | 0.160.0 | `https://cdn.jsdelivr.net/npm/three@0.160.0/` | `https://github.com/mrdoob/three.js/tree/r160` |

three.js 固定为现有 servo-web importmap 使用的 r160；OrbitControls、RoomEnvironment、BufferGeometryUtils 与主库同版。字体使用系统本地字体，无外部字体服务。文件 SHA-256 见 `vendor/manifest.json`。

技术依据官方文档：`https://preactjs.com/guide/v10/getting-started/`、`https://threejs.org/docs/#manual/en/introduction/Installation`、`https://echarts.apache.org/handbook/en/how-to/data/dynamic-data/`。本轮 web 检索未返回正文；原始固定包下载成功，版本与许可通过分发路径固定。

## 数据契约

前端遵循 `docs/specs/20261106-训练可视化工具/api-contract.md`。显示指标保留系列作用域与原始单位，缺测不补零，开发评估只画实际稀疏点。回放按 replay_id/generation/seq 隔离；根轨迹与仿真时间来自 worker 真实帧，暂停/重置/倍率通过服务控制独立进程。

刷新或独立窗口重连同一 replay_id 不新建 GPU 进程；回放卡片“关闭”显式 DELETE 释放会话。浏览器刷新无法可靠区别关窗，不使用 unload 杀进程，避免刷新损坏会话。独立窗口保留显式释放按钮。

## 2026-11-06 前端契约修正

- 任务以 `task_id + task_version` 选择与匹配；历史版本不借用当前任务版本身份。
- 运行事件按 `seq` 游标分页补齐，保留最近 1000 条、面板显示最近 80 条；并发刷新共享在途读取，不停留在最早 200 条。
- 新建、停止、续训、回放创建和控制按请求正文保留失败操作的 `request_id`，相同失败操作重试沿用；成功后的新操作获得新 ID。关闭为幂等 DELETE。
- 双 Spark 奇数环境预算预览明确不可均分，不显示小数环境分配；实际启动仍依赖后端配置校验。历史预算耗尽与行为评估结果分别说明。
- WSL CPU、内存、PID/RSS 与宿主机分别展示；使用独立 `wsl.samples` 时序和接收时间，进程 GPU 内存不支持时如实标注。断连与过期当前值标旧数据，不与 Windows 内存累加。
- 指标 tooltip 展示实际 `sample_count`；日志缺少所选时间轴时明确说明字段缺测。

[本机软件检查] `app.js`、`api.js`、`charts.js` 经 Node 静态语法检查通过。模拟 2205 条事件跨 3 页读取后保留最近 1000 条，再新增 2 条从 seq 2205 增量获取；模拟响应丢失后同一操作重试保留 request_id，成功后重复操作及正文变化获得新 ID，检查通过。以上为 CPU 合成接口检查，不是 GPU 训练验收；页面视觉与真实 worker 由主会话另行验收。

回放刷新恢复：通过 `GET /api/replays/{id}/frames?after_seq=0&limit=2500` 在首次挂载、WebSocket 重连和 generation 变化时读取当前代历史；HTTP 与实时帧按 replay_id/generation/seq 合并、去重、排序。只保留最近 2500 帧，旧代迟到的 HTTP 响应不能覆盖重置后的曲线。已关闭会话可在原独立窗口 URL 只读查看最后姿态与历史曲线，不新建 worker，控制按钮禁用；主页面已关闭会话仍移除。

[本机软件检查] `replay-frames.js` 的 CPU 合成检查覆盖 HTTP 历史与实时帧去重排序、reset 后仅保留新 generation、旧 HTTP 晚到、其他 replay_id 串入、2500 帧上限与 worker 原始字段转换，全部通过；`app.js` 与新增模块静态语法检查通过。此项未新建回放、未消费 GPU 预算。

[本机接口检查] 服务重启后只读请求已关闭会话，checkpoint 100 返回 generation 0 的 929 帧（seq 1–929），checkpoint 1000 返回 generation 1 的 4 帧（seq 867–870）；身份、当前代、排序唯一、2500 上限及 after_seq 末帧后空返回均通过。独立窗口不加载 checkpoint 评估详情，因此文案明确“独立窗口未加载评估记录；可回主页面查看”，不把未加载误写成没有评估。
