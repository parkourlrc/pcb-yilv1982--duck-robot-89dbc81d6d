# 整机供电架构（飞特路线，2026-10-10 定稿）

> 依据：imu_to_dxl v0.3 网表（[docs/schematics/imu-to-dxl-scrapmeta-v0.3/hardware-netlist.md](./schematics/imu-to-dxl-scrapmeta-v0.3/hardware-netlist.md)）、HAT V1.1 查证记录（[docs/references/白色扩展板原理图查证/research.md](./references/白色扩展板原理图查证/research.md)）、community-kit 各板 README、电源板空载实测（[buck-module-test.md](./buck-module-test.md)）。

## 一句话结论

**降压模块（BUS SERVO POWER SUPPLY V1.3）= IMU 的 5V 专属电源 + 电池配电中转；HAT = 自己吃电池直通电压、板内降压给主控、自带总线半双工驱动。**

## 拓扑

```
2S 电池（8.4V 满 → 带载最低 6.6V）
  │
banana_pcb（电池触点转接板：U6068 插针插电池触点，焊接出线，线径按 3-5A）
  │ XT60
  ▼
BUS SERVO POWER SUPPLY V1.3
  │
  ├─ PWR OUT（直通 2P 端子，实测跟随输入）──→ HAT 的 +BATT 电源口
  │        ├─ HAT 板上 AP63205 降出 5V/2A ──→ 主控（Radxa Zero 3W）
  │        └─ HAT 舵机口 CN11/CN12（JST EH 3P）直出 +BATT（经自恢复保险 F1 + 5.1V TVS）
  │              └─→ 舵机总线链：HD-1910 ×15 链式串联（吃电池电压，真机用法 7.8-8.1V）
  │
  └─ VCC（3P 排针 GND/VCC/NC，改焊 5V 档后）──→ IMU 板供电支路（专用）
```

## 各板取电方式

| 板 | 电从哪来 | 接口与备注 |
|---|---|---|
| banana_pcb | 电池触点 | U6068 插针 ×2 + 拆电池焊接出线；线径 3-5A |
| 电源板 | banana_pcb 出线 | XT60 输入，丝印 7.2-18V（实测 5V 起可工作，下限 ≈6.3V） |
| HAT | 电源板 PWR OUT（电池直通） | +BATT/GND 两线；板内 AP63205 降 5V，**2A 只够主控，不能当舵机动力** |
| 主控 Radxa | HAT 板载 5V | 经 HAT 板载供电，无需自行接线 |
| 舵机 ×15 | 总线电源线（电池电压） | HAT 舵机口起步，逐颗串联；EH 3P（HAT 座）vs 飞特原线 5264 端子，装前试插 |
| IMU 板 | **电源板 VCC 稳压 5V**（改焊后） | 见下方铁律 |

## IMU 板接线三铁律（引脚经原理图网表核实）

J1 = JST EH 3P，引脚 **1=GND、2=VBATT（供电）、3=DXL_BUS（数据）**，与舵机座同序。

1. **J1 绝不直接插进舵机总线链**——总线上是电池电压 7.4-8.4V，IMU 的 LDO 上限 5.5V，插上即烧。IMU 是**叶节点**：J3 永远空置（J1/J3 板内穿板直连，插链还会把 5V 支路与总线电压短路）。
2. **做一根"混血"3P 线**：GND、DATA 从总线侧取（HAT 第二舵机口或链上任一空座并联），VBATT 脚接电源板 VCC 的 5V。三根线两个来源，只在 IMU 端汇合。
3. **改焊 5V 档并空载复验 5.00V 之前，VCC 不接 IMU**（当前 6V 档即超压）。

另：IMU 板 J2 调试口 7P 的 1 脚（+3V3）是板内 3.3V 轨引出，**不是供电入口**，烧录时仅作 DAPLink 电平参考；IMU 供电永远走 J1。

## 未定项与风险

- **总线路径二选一**：PWR OUT → HAT 舵机口 → 总线（电流过 F1 保险）vs PWR OUT → 总线直连（绕开 F1，HAT 单独喂）。取决于 F1 保持电流（研究记录标"未查手册"），**台架带载复测时拿数据定**。
- 电源板丝印 **MAX 6A** 是总电源天花板；15 颗 HD-1910 同时堵转远超此数，靠 robotd 飞特补丁的力矩限幅兜底（真机整定值待复测，见 PROGRESS 方案方向节）。
- HAT 供电链还有 LM5050 理想二极管 + PWR_DET 关机检测等细节，对本架构无影响，详见 HAT 查证记录。

## 勘误记录

- 2026-10-10：电源板"DC 母座"系照片误判，用户实物核对**板上无此件**（金色圆孔疑为镀铜安装孔/过孔）。接口分工最终版：XT60 输入 / PWR OUT 直通 / 3P VCC 稳压，全部经空载实测闭环，无未知接口。
