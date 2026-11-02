# HAT Buck反馈与补偿局部重排（2026-10-31，历史检查点）

**当前工程已继续升级C303～C306，见[现行电容审查](../capacitor-upgrade-20261031/research.md)。以下计数、电容选择和待办仅对应09f1d958检查点；其FB/COMP布局修复保留，不作为当前BOM或生产包入口。**

## Overview

主会话按持续授权执行，未用子代理。R301/R302、R304/C301移到U301旁，器件数值、型号、封装和原理图均未改变。**[文件/工具核对] 敏感网络缩短并全部改走F.Cu，原有焊盘连接保留；原生DRC普通违规、未连接、parity、ERC、网表mismatch全0。**

现行PCB SHA256：09f1d958da205e4707848f6fb08b4cddaf02255d2f333e774bc5bb97b277f4fe。54/54设计MPN状态不变；本轮是布局检查点，**不是环路稳定性或制造放行**。

## Previous Review Delta

| 网络 | 修改前总线长 | 当前总线长 | 层/过孔 |
|---|---:|---:|---|
| +5V_FB | 19.964mm | 6.332mm | 新线均F.Cu，原2个过孔移除 |
| BUCK_COMP | 26.159mm | 4.509mm | 新线均F.Cu，原2个过孔移除 |
| COMP_RC | 3.138mm | 1.638mm | F.Cu |

FB总长包含U301到R302约4.607mm与两反馈电阻之间1.725mm，不把总长和端到端距离混用。新的5V分压取样支路约18.15mm；它不是FB高阻节点，取样支路和主负载铜没有混同。

## Critical Findings

1. **电容有效值仍需改进。** 新取得逐料号原厂模型，现用22µF在约5V时典型约剩11µF；标称44µF不能用于直接验算，详见[模型核查](../capacitor-models-20261031/research.md)。本轮未改变容量/MPN或C307 DNP。
2. **完整环路、热和载流仍未验收。** 缩短走线不能替代有效C/ESR、内部参数、瞬态、温升与实际负载核查。
3. **6处填孔盖铜与HDI工艺仍未获接受。** 5个U301热通孔与U701.7微孔的要求保留，同版CSV已重出。
4. **首板尚未制造，实际功能/装配未测。** H1/H2排母侧≤4.5mm M2.5圆柱头且无垫圈约束继续有效。

## Component Summary

R301=52.3k、R302=10k、R304=14k、C301=3.3nF，原MPN/0805封装保留。54个拟装器件、38个有效BOM分组、36个唯一MPN不变；C307仍DNP，未新增采购件。

## Power Tree

2S→U301→5V；Radxa3.3V→U702→1.8V，R309舵机动力桥接不变。R301高端从C305输出电容附近取样，低端R302接POWER_GND；本轮没有改变输出目标值或供电架构。

## Analyzer Verification

geometry-connectivity-check.json只允许4个无源件的8个焊盘作指定刚体移动/旋转，其余焊盘、原赋网和原焊盘连接保留。移除31个FB/COMP/RC铜对象及2段R301原5V末梢线；其余原线路几何不变。新线与计划UUID集合逐一相等，不凭总数放行。

坐标仅容许KiCad整数换算的2nm差异，角度按360°同余核对（−90°与270°相同）。初次验证因角度表达未归一而拒绝，已修正比较方法，未忽略实际几何差异。完整副本填铜保存后再读原生连接图；回写主工程后再次完整检查，见post-promotion-summary.json。

## PCB Layout Analysis

新位置：R301=(130.2,110.2)、R302=(130.2,113.75)、R304=(130.2,117.7)、C301=(130.2,121.2)，均F.Cu、−90°。元件位于U301与电感之间的空隙，courtyard/铜间距全通过；没有缩小封装或放宽规则。

新FB/COMP/RC线宽0.25mm。5V取样线从输出电容附近到R301，共3段0.25mm；仅触及C305.1与R301.1，和原5V铜的接触都限定在C305焊盘附近0.25mm扩展区，逐0.01mm路径采样无区域外接触。**这是文件检查，不是电流实测或全频Kelvin性能认证。**

## Signal Analysis Review

取样支路的直流电流约4.984V/(52.3k+10k)=80µA；没有给其他负载供电，因此不把它和主5V载流线混淆。原主电源线路宽度不变。其他音频、I2S、TTL、IMU/ToF端点未改。

## Power Analysis

反馈分压和外补偿参数未改，名义输出仍4.984V。布局更集中是文件事实；其对噪声/稳定性的改善幅度没有实测，寄生、供电阻抗和器件参数仍可能限制结果。

## PDN / Effective Capacitance

原厂逐料号PDF与DC偏压图已归档。当前两颗输出22µF在约5V的典型模型合计约21–22µF；加入容差、TCC、老化的假设敏感性场景会更低。一阶补偿计算和局限见模型专题。没有把典型模拟曲线当保证下限，也没有据它宣称实物已失败。

## Thermal Analysis

5个U301同网热孔、C303靠近VIN、C308直接接LDO输入的前一阶段修复全部保留。自动热评分仍用0.043W假设，不作为温升验收；本轮未重新定义整板输出电流额定。

## Power Budget

入口/接插件/铜箔/线束额定协调仍未完成。分压支路电流小不代表主5V或舵机路径可以按芯片/跳线额定满载；现有安全边界未放宽。

## EMC / Cross-Domain Analysis

本阶段重新运行cross/EMC。敏感节点取消内层长走线和4个过孔，但没有进行EMI测量或证明I2S参考层回流已完成。旧“无地孔”及基于近似几何的孤岛判断继续与原生证据区分。

## Simulation Verification

ngspice自动子电路为理想/行为模型，AP64350自动0.6V参数错误未用于放行。p17 Eq12疑点后来已由[独立图示网络推导与仿真](../power-acceptance-20261031/research.md)核对，不再停留于等待解释；仍不据此生成本板相位裕量或实际瞬态通过结论。

## Component Lifecycle

本轮对未变的36个唯一MPN重新查询，unknown不转成在产/库存通过。型号和装配状态没有因为布局重排发生变化。

## Manufacturing / DFM

[同版审查包](../../../../hardware/custom_hat/rev_a/production-20261031-control-review/README.md)重出Gerber/钻孔/坐标/BOM及via-process-requirements.csv。6个filled/capped要求及其坐标/几何保持不变，仍需供应商接受；普通无填孔四层服务不可直接代用。

## False Positives / Reviewer Overrides

若自动载流分析把新的0.25mm取样线当主5V负载通道，应以本轮末梢/接触核对区分；不能全局忽略5V载流检查。DS-002的同级目录发现限制、FID/J101 courtyard边距及Paste闪光比例解释沿用已有原始证据；原生DRC没有豁免。

## Failures / Decisions

首次摆放使C301地焊盘离现有3V3铜不足，C301上移0.1mm后消除2项违规。新5V取样路径最初网格点过多，使用原生铜形状检碰后从210段简化为3段，重新DRC通过。一个想绕更远的两段取样线候选与其他网冲突，仅作只读检查，未采用；未将有限尝试失败写成“板面不够”。

## Sources / Images

主要布局依据为归档Diodes AP64350 DS41976 Rev5-2 p22及图32，原厂URL为https://www.diodes.com/assets/Datasheets/AP64350.pdf。基线布线长度和支路边界在before-control-routing.json；新路径在control-route-plan.json。

原生F/B图和control-layout-review.png已打开检查。图中是F.Cu文件布局，标签/总长与当前铜对象对应，不作实物照片或稳定性测试证据。脚本render_buck_control_annotations.py可复现。

## Analyzers Actually Run

aklofas/kicad-happy提交2fd9aa0fe2d620f36627d9221e8b1393987ae38e；实际跑schematic、pcb --full、gerbers、cross、EMC、thermal、SPICE、lifecycle、prior schematic delta，命令/日志/JSON同目录。

## Not Performed / Review Limits

电容参数改进尚未实施；完整环路、真实负载、温升、回流、HDI工艺接受、首板功能与装配仍未完成。未下单、付款、上电、commit或push。

## Final Verdict

关闭长FB/COMP跨层布线的布局缺口，原连接保留、原生检查全0。新的原厂电容模型使下一步从“泛泛待查”收敛为具体裕量方案比较；仍不可投板，继续完成有效电容、载流、热/回流及制造条件，再做首板必要验收。

收尾final-audit.json核对54个MPN及原理图/PCB五字段、BOM数量/位号、源/制造输出指纹、新导航和git diff --check，均通过。标注图已打开检查；所有修改未提交，目标未标完成。
