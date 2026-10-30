# HAT 工程处理流程

2026-10-30：只在完整工程副本中工作；本轮不修改主电路、PCB 或制造规则。使用 KiCad Python（能 import pcbnew），必要时设置 KICAD_CLI 为本机 kicad-cli.exe。

从仓库根目录执行：

```powershell
$kiPython = Join-Path $env:LOCALAPPDATA 'Programs\KiCad\10.0\bin\python.exe'
& $kiPython hardware/custom_hat/scripts/pipeline.py prepare
```

输出工作目录 `hardware/custom_hat/runs/<时间-编号>/work` 与报告目录。完整副本含主 PCB、工程规则、原理图/子页、库表/本地库和契约；历史路由/生产文件不作为输入。manifest 保存每个源文件 SHA256。不会运行 build、stitch、autoroute，不改变源文件。

修改工作副本后重新检查：

```powershell
& $kiPython hardware/custom_hat/scripts/pipeline.py check --project 'hardware/custom_hat/runs/<时间-编号>/work'
```

每次报告独立保存：CLI 版本/命令/日志、实际导出网表、ERC、重铺铜且含 schematic parity 的 DRC、网表与板焊盘/契约差异、源摘要。violations、unconnected_items、schematic_parity 分列。显式 NC 在板上空网单独列出，不冒充真实短路，原始 parity 仍保留。

退出码：0=离线检查无未解释项（仍不是制造放行）；2=已执行检查但设计有阻塞；1=工具/输入失败。不得把非零码忽略后继续读旧报告。源或工作副本在检查期间变化，检查报失败。

只有电气/几何与一致性前置检查通过后才允许自动路由；允许尚有未连接，必须显式传入工作副本：

```powershell
& $kiPython hardware/custom_hat/scripts/autoroute.py --project 'hardware/custom_hat/runs/<时间-编号>/work' --passes 20
```

路由另建完整候选，不改输入工作副本或主工程。使用唯一 DSN/SES 路径，检查导出、路由退出码、导入成功、源与 DSN 摘要。原制造规则保持不变；输出还需检查，不能因为 SES 存在就认为完成。当前主板有真实错误及一致性问题，前置检查会阻止自动路由；本轮未验证 Java 布线成功路径或批准其 DSN 规则可制造性。

`build_pcb_rev_a.py` 与 `dsn_power_class.py` 已停止命令行执行，保留历史实现供追溯。其余旧补孔/扇出脚本不是新流程入口，部分写死主路径，禁止直接用于现行工程。先完成几何/网络依据再修复相应脚本，不盲跑实验。

本流程只生成候选和检查点，不自动回写主工程。设计者审查实际修复、制造条件与变化后再决定回写；默认不提交、不下单、不操作硬件。工作副本在 runs 下本地留存；审计证据长期保存在 docs/references 对应专题。
