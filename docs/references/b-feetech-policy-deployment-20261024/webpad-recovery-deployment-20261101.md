# 网页躺姿恢复部署验收

- 日期：2026-11-01；北京时间 23:49 部署完成，23:50 网页只读验收。
- 授权：用户明确要求“部署”。此前“先不部署”限制已被本次安装授权更新；起身、行走等动作仍未授权或执行。
- 范围：安装已验收的 robotd 与 Studio 恢复补丁；不修改模型、标定、通信、参数或服务自启设置。

## 实际结果

**[实测]** robotd 已运行 `0791fcd-feetech-qinmo-control.47+duck-recovery.1`，PID **843**；
Studio PID **851**。两服务均 `active/enabled`，六个模型加载成功，主程序 `motion/control`。
新单 3P IMU 继续原版混合 SYNC_READ；运行文件所在 `duck-v03-20261031` 只是历史目录名，不能据名称判断通信代码。

**[实测]** robotd 二进制 SHA256 为
`fe200aabe2700a492cfb4ea8523c505d4047c26e081c4b18266af1cb8511e82a`。
二进制及5个Studio文件全部匹配候选；41个受保护模型、sidecar、标定、配置和服务文件哈希前后一致。
页面HTTP和WebSocket均正常，实际提供的 `pad.js` 匹配候选哈希，后端恢复状态为
`available=true / ok=true / active=false / phase=idle / request_id=null`。

**[实测]** 部署前、停止Studio后、重启后及网页验收后均确认扭矩关闭、策略关闭。
关节反馈完整、IMU就绪。没有调用 `robot.recover`、`robot.init`、`robot.enable` 或模型技能，
没有启动恢复或行走。用户刷新Studio手柄页面后可看到新按钮；真机起身效果尚未验证。

## 安装与现场备份

锁内核对后备份，先停Studio，再次只读确认卸力，再停robotd；按原owner/mode原子替换，
先启动robotd并等模型、IMU及卸力状态验收，再启动Studio。没有修改系统服务定义或自启状态。

现场备份目录：
`/etc/robot/feetech-ft5/backup-before-duck-recovery-20261101T154921811536Z/`。
包含原robotd、4个原Studio文件、配置／标定／服务文件及部署前快照；新增`pad_recovery.py`原来不存在。
回退时先核对当时状态及并发修改；恢复该备份中的运行文件，只在新增文件仍匹配候选哈希时移除它。
不覆盖后续模型、标定或参数修改。

## 本轮失败与处理

1. 第一次执行停在打开`/run/microduck-helper/helper.lock`，因断电重启后运行时父目录不存在；尚未停服务、备份或替换。
   两服务PID仍为374/494。安装脚本补齐与helper相同的root运行目录初始化后继续；未更改锁名称或绕开互斥。
2. 安装记录内`journal`为空：当时使用ISO时间串读取journal未取得内容，已单独按UTC标准格式补取59行日志。
   保留原始记录，不把空日志宣称为“无错误”；修订后的安装脚本会记录journal错误。
3. 日志有实体手柄`padd`按键旁路不可用提示；本次为网页手柄，页面恢复入口已可用，未因此安装或启用额外手柄服务。

## 原始证据

- [部署前快照](webpad-recovery-deploy-before-20261101.json)
- [安装及前后哈希记录](webpad-recovery-deployment-20261101.json)
- [网页与最终原生回读](webpad-recovery-page-20261101.json)
- [补取启动日志](webpad-recovery-deploy-journal-20261101.log)
- [实际执行的安装脚本](webpad-recovery-installer-executed-20261101.py)，SHA256 `0b70b8b281955e38188d88669793e57a442938bd666e4feae0d0340ac31917f2`
- [当前部署清单](../../../tools/robotd-recovery/deployment-status.json)、[构建与离线验收](../../../tools/robotd-recovery/verification/README.md)

限制：仅完成安装和只读验证；未用真实浏览器点击起身，未验证承重或起身成功率。工作区修改未提交、未推送。
