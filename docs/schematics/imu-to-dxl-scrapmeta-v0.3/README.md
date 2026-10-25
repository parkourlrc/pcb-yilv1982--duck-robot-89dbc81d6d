# imu_to_dxl v0.3（ScrapMeta）— 原理图存档

- **板上丝印**：`imu-to-dxl v0.3`，板框 32×22 mm，四角 φ2.2 孔距 29×19
- **器件**：STM32G031F8P6（TSSOP-20）+ LSM6DSV16X（SPI，SFLP）+ SN74LVC1G125 半双工缓冲 + AP2210K-3.3（**输入上限 5.5V，只能 5V 供电**）
- **连接器**：J1/J3 = B3B-EH-A（总线，1=GND 2=VBATT 3=DATA）；J2 = BM07B-SRSS-TB（调试 7P：3V3/CLK/DIO/GND/TX/RX/RST）

## 文件

| 文件 | 说明 |
|---|---|
| **`imu_to_dxl-v0.3-原理图.pdf`** | **实物板对应的图**（2026-10-09 从 eprj2 导出）。判别依据：J1 进 + **J3 出**双 EH 座 + J2 BM07 7P = 仓库 hardware.md 的 v0.3 特征；板名 `imu_to_dxl_1` |
| `实物板元件标注.jpg` | 实物照片 + 逐元件作用标注（2026-10-09：U1/U2/U3/U6、J1/J3/J2、阻容区、Y1、安装孔、版本丝印，底部附元件作用表）。⚠️ 实物丝印是 **IMU2DXL V1.0**，与仓库文档的 "imu-to-dxl v0.3" 字样不同——按用户确认的对应关系为准 |
| `imu_to_dxl-工程内另一页-单J1变体-仅参考.pdf` | 同一工程里的第二张图（板名 `imu_to_dxl_2`）：调试口同为 BM07，但总线**只有单 J1、无 J3**——介于 v0.2 与 v0.3 之间的变体页，**不是实物板**，仅留档 |
| `imu_to_dxl_ref_2026-08-30_18-59-47.eprj2` | **真源工程**，嘉立创EDA专业版可打开（免费）改图/导出；内含上述两页图页 |
| `hardware-netlist.md` | 仓库 `docs/hardware.md` 副本：v0.3 vs v0.2 差异、连接器脚位、MCU 脚位网络表、电源/保护拓扑 |
| `hardware-repo-README.md` | 仓库 `hardware/README.md` 副本 |
| **`production/imu_to_dxl_v03_gerber.zip`** | **生产文件**：2026-10-25 用户经嘉立创EDA从 `imu_to_dxl_1` 导出的 Gerber 全套（双层+钻孔+飞针 JSON），本机解析验证 33×22mm、4×φ2.2@30×19、J1/J3 双 EH（6×φ1.0）；嘉立创订单 85849959 用其打样，[下单调研](../../references/imu-v03-jlc-order-20261025/research.md) |
| **`production/imu_to_dxl_v03_bom_20261025.xlsx`** | **SMT 物料表**：EDA 导出原件，15 行全带立创 C 号（作者工程内已配好）；19 个贴片位号对应 |
| **`production/imu_to_dxl_v03_cpl_raw_20261025.xlsx`** | **坐标文件原件**：EDA 导出，24 行（含 3 个 DNP：C7/C8/Y1；2 个插件：J1/J3） |
| **`production/imu_to_dxl_v03_cpl_jlc_20261025.csv`** | **JLC 贴片用清理版 CPL**：19 贴片件（Designator/Mid X/Mid Y/Layer/Rotation），与 BOM 一致，供 PCB+SMT 一体单上传 |

两页图页共同确认的要点：标题栏写明 `DXL 2.0 · ID 200 · sync_read @124`（原设计是 Dynamixel 版，上飞特总线需刷 replica 0.2.0 固件，见 `flash/`）；VBATT → U3 AP2210K-3.3 直连（**5V 供电上限**）；LSE 32.768kHz 晶振为可选件（Y1）。

## 来源与版本

- 上游：https://github.com/ScrapMeta/microduck-diy/tree/main/imu_to_dxl（MIT）
- 下载日期：2026-10-09，取自 `main`，`imu_to_dxl/hardware` 最后改动提交 `aa4c32dc09c1e2876f3aead49af740a98b2abc67`（2026-09-10）
- 原厂协议契约（README/固件）：**Dynamixel 2.0 专用**（ID 200 @124）——本板要上飞特总线需刷 replica 0.2.0 飞特固件，刷机包见 `flash/`（引脚兼容性查证：`docs/references/imu-to-dxl-variants-20261009/research.md`）
