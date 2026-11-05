# Studio 调试模式显示补丁

修复 commissioning 的舵机反馈位于 `last_sample.servos`、旧显示层却只读取 `native.joints` 的兼容问题。只处理显示数据，不改原始 RPC、串口、模型、标定、扭矩或动作入口。

- 来源：`fanhao375/microduck-replica`，固定提交 `3952471a8394c8b720817d2160ffd95ce5a54456` 的 Studio，软件包修订 `microduck-software-v2026.10.3101`。完整来源见[上级 SOURCE](../SOURCE.md)。上游根许可原件保存在 `LICENSE.upstream`；不代替模型许可。
- `upstream/studio/` 保存四个未改动原件，SHA 与安装前 Radxa 文件核对。
- `overlay/studio/` 是本次替换文件与新增显示模块，是部署增量，不是独立完整 Studio。
- `source-manifest.json` 保存原件及安装文件 SHA；`display.patch` 可对同一基线重放。
- `install.py` 先核对全部原件和增量 SHA、备份，再原子替换；不重启服务。仅支持 `/home/radxa/studio-dev` 此固定安装。
- `test_display.py` 使用已归档真机反馈检查总览/表格、重复旧帧、原生过期、读取失败、断连/新会话与其他模式。需要本机已下载的完整 Studio 缓存及其 `deps/`，不访问设备。

新鲜度取本机已观察到的样本推进时刻，并合并原生样本年龄与 IPC 接收年龄。超过 3 秒、读取失败或断连时，在线数为未知且不输出当前位置；同一旧帧的新 RPC 回包不能刷新寿命。重新连接 `hello` 后清掉旧上下文。

IMU 姿态仅用有效、新鲜反馈，安装方向未验证按实显示。没有从参考标定合成 3D 关节弧度，也没有将电流原始数值擅自转换为 mA。缺少的诊断字段仍为未知。

部署后只重启 `microduck-studio.service`；robotd 保持 commissioning。回退时先停 Studio，从安装报告的 `backup` 目录恢复四个原件，只删除本次新增的 `studio/commissioning_display.py`，然后启动 Studio；不改 robotd、其他备份或模型。

授权、验收与当前状态：[Spec](../../../docs/specs/20261031-studio-commissioning-display/spec.md)、[统一研究](../../../docs/references/飞特策略模型上机核对/research.md)。默认不提交、不推送。
