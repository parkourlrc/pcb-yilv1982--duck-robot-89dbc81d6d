# HAT 原理图阶段说明

> 2026-10-28 历史草案；包含已取消屏幕/CSI及旧占位方案，不作现行指导。当前入口见 [rev_a/README.md](rev_a/README.md)与[真实性复核](../../docs/references/扩展板电路仿真工具/audit-20261030/review.md)。

日期：2026-10-28

## 已批准的模块边界

- Radxa ZERO 3W 40P 对插
- 动力输入、5V 降压、3V3 逻辑电源
- 飞特 TTL/外置 GD32 IMU 共享半双工总线，两个 3P 插座
- 头部 IMU 接口/候选器件
- ToF/I2C 扩展
- 3.5 寸无触摸 SPI 屏接口
- 22P CSI 摄像头中继口
- 音频接口占位
- 测试点

明确不设计：RS485、识别 EEPROM、充电、UPS。

## 当前建议信号表（待逐网核对）

| 资源 | 建议用途 | 状态 |
|---|---|---|
| 40P 8/10 UART2_M0 | 现有 TTL 总线兼容入口 | 官方默认 U-Boot/调试串口，必须先解决 console 冲突 |
| 40P 19/21/23/24 SPI3_M1 | 屏幕 SPI（MOSI/MISO/SCK/CS） | 仅候选，DC/RST/背光 GPIO 未定 |
| 40P 29/31 I2C5_M0 | 头部 IMU + ToF | 器件地址、上拉和电平待核 |
| 40P 12/13/35/38/40 I2S3 | 音频模块占位 | codec 主从和软件声卡未核 |
| CSI 22P 0.5 mm | Radxa CSI 到 HAT 的中继 | 差分布线、连接器接触面、弯折和机械禁布区待核 |

## 必须补齐后才能投板

1. 锁定 Radxa 40P 排母方向、孔位和 CSI FPC 两端连接器方向。
2. 锁定屏幕模块型号；当前候选为 LCDwiki MSP3525 无触摸 ST7796 模块，不能把它当裸屏。
3. 锁定头部 IMU 型号（BMI088 首选候选，LSM6DSV16XTR 次选）和 Linux 访问路径。
4. 核算 2S 输入、5V/3V3 负载峰值、动力支路载流、降压器件热和保护边界。
5. 解决 UART2_M0 启动日志/总线冲突，或改用其他可行 UART。
6. 用真实连接器符号/封装替换所有占位页，并运行 ERC；完成后才开始 PCB。

## 电源/TTL 页来源说明

`power.kicad_sch` 当前是官方 C1 参考工程 `power.kicad_sch` 的工作副本，包含 LM5050/AP63205 等参考器件；它**不是本项目已确认的新板网表**，输入范围、器件参数、保护边界和网络仍须按本项目 2S 供电实物重新核算。

`servo_ttl.kicad_sch` 当前来自 community-kit `dxl_hub.kicad_sch` 的工作副本，提供两个 3P 接口和共享 DATA 拓扑参考；接口系列、针序、串阻和半双工收发器尚未与本机 V1.2 HAT/HD-1910 线束逐针核对。页面中的 `DATA` 标签沿用上游名称，不能视为已批准的 `DXL_DATA` 生产网络；后续替换为本项目真实符号后再定名。

`radxa_40p.kicad_sch`、`head_imu_tof.kicad_sch` 分别复制自官方 C1 `main.kicad_sch`、`sensors.kicad_sch`，用于审查 Radxa/传感器功能块和候选网络；不代表本机 ZERO 3W 40P、BMI088、I2C 地址或连接器方向已逐针确认。

`camera_csi.kicad_sch`、`screen_spi.kicad_sch` 当前复制官方 C1 `main.kicad_sch` 作为接口审查底稿。它们**不等于**已完成 CSI 22P 中继或 MSP3525 14P SPI 屏网表；摄像头差分对、FPC 接触面、屏幕 DC/RST/背光 GPIO 和逻辑电平仍需用目标器件资料替换并逐网核对。没有将裸屏针序写入工程。

`custom_hat.kicad_sch` 已建立 8 个层级页入口，指向本目录的功能页；层级页目前主要固定模块边界，功能页内部仍有参考电路和未核网络，尚未组成可投板网表。层级接入后 ERC 报告为 234 条违规（含参考页重复电源标记、层级标签不匹配及占位库问题），因此不能视为 ERC 通过；完成真实网络和层级标签后必须重跑。

本轮未运行 KiCad GUI、ERC/DRC 或硬件测试；没有任何针序被视为已验证生产数据。

## 当前 ERC 结果

曾在层级接入前运行 ERC：0 errors、8 warnings。层级页接入后最新报告见 `custom_hat-erc.txt`，共 234 条违规；主要是参考页的重复电源标记、层级标签不匹配及未注册 `microduck` 库。它们表明当前工程仍处于参考/占位阶段，替换真实符号、封装、层级标签和网络后必须重新运行 ERC。
