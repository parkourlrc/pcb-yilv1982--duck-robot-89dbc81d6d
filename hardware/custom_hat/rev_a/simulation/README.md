# Rev A 可运行仿真

运行：

```text
python hardware/custom_hat/rev_a/simulation/run_simulations.py
```

脚本生成：

- `simulation_report.json`：完整输入假设、扫描点和结果，便于后续把估算值替换为实测值。
- `simulation_report.md`：人工审查摘要。

当前包含两类行为级检查：

1. 5 V buck 反馈分压的参考电压/电阻容差角落，以及按规划负载估算输入电流。
2. 飞特 TTL 半双工数据线的串联电阻和负载电容扫描，使用一阶 `2.2RC` 10--90% 边沿时间。

这不是 SPICE。脚本不含具体芯片模型，也不验证开关电源环路稳定性、TTL 收发器争用、CSI/SPI 时序、音频失真或 Linux 驱动。选定真实器件后，应把数据手册/IBIS 模型和实测线缆参数加入独立的 ngspice/KiCad 仿真，并保留本报告作为前置筛选记录。
