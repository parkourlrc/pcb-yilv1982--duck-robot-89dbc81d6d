# Pollen HAT PCB 参考文件：C1 / D1

取得日期：2026-10-27。**这是卖家所提供 GitHub 地址的文档引用版本，尚未与用户白色鸭图案 HAT V1.2 对应。** 不把官方 R33 位号或贴装值直接套到 V1.2。

## 从卖家线索到原始工程

用户提供 [ScrapMeta IMU 固件目录](https://github.com/ScrapMeta/microduck-diy/tree/main/imu_to_dxl/firmware)。该仓库的 [HAT 信息卡](https://github.com/ScrapMeta/microduck-diy/blob/db04d323caa053ae0c96629268392cdbe7dc8b4f/wiki/concepts/board-hat.md) §1–4 写明官方 `ASE01187-C1 / PCB01186-C1`；[上游版本记录](https://github.com/ScrapMeta/microduck-diy/blob/db04d323caa053ae0c96629268392cdbe7dc8b4f/scripts/upstreams.lock) 的 HAT 行指向 `pollen-robotics/elec_RPI_Robot_HAT @ 88d51fa`。

本轮从官方 GitHub API 解析为完整提交 `88d51faf7f5fcc845d2e3b42d4f05ebb98b963b9`，下载下列文件。PCB 文件自身标题为 **C1 / 2026-07-08**，不是 V1.2。

## 优先查看：卖家文档引用的 C1

| 文件 | 用途与核验 |
|---|---|
| [C1 PCB 源文件](c1-88d51fa/elec_RPI_Robot_HAT.kicad_pcb) | KiCad 9 PCB，含焊盘、网络、走线、铺铜和器件位号；官方原件 |
| [C1 工程入口](c1-88d51fa/elec_RPI_Robot_HAT.kicad_pro) / [原理图入口](c1-88d51fa/elec_RPI_Robot_HAT.kicad_sch) | 同一固定提交；目录同时保留该提交根目录所有 `.kicad_sch`，未修改原件 |
| [C1 PCB PDF](PCB01186-C1_elec_RPI_Robot_HAT_PCB.pdf) | 官方单页生产图，标题 C1，已目视核对；只显示导出图层，不能代替多层源文件 |
| [C1 Gerber / 钻孔 ZIP](PCB01186-C1_elec_RPI_Robot_HAT_PCB.zip) | 已检查目录，含 F/In1/In2/B 四层铜、阻焊、丝印及钻孔文件；未改写生产包 |
| [C1 BOM](ASE01187-C1_elec_RPI_Robot_HAT_BOM.csv) / [贴片坐标](ASE01187-C1_elec_RPI_Robot_HAT_POS.csv) | BOM 第 32 行 R33=150R/0402，第 35 行 TH1=100R thermistor/0603；不是用户板实装值 |
| [C1 背面位号参考图](../../photos/hat-c1-r33-reference-20261027.png) | 基于 ScrapMeta 保存的官方 C1 CAD 截图标 R33/TH1，白色 V1.2 对应关系待核 |
| [源文件清单](c1-88d51fa/source-manifest.json) | 固定提交、下载 URL、Git blob、SHA256；3D 外部模型库未完整下载，不承诺离线 3D 完整显示 |

根目录 C1 PDF/BOM/POS/Gerber 先从官方后续提交的 `production/_old/` 取得；已核对与 `88d51fa` 当时 `production/` 中的 Git blob 完全相同，版本未混用。对应清单另见[追加下载记录](../../references/hat-imu-shared-bus-20261027/pcb-search/extra-sources-manifest.json)。

## 补充参考：D1

固定提交 `6de86283297e4c49a9da8312cd3395ab83c437e3`，PCB 标 D1 / 2026-10-06：

- [D1 PCB 源文件](elec_RPI_Robot_HAT.kicad_pcb)。
- [D1 装配位号图](ASE01187-D1_elec_RPI_Robot_HAT_ASS.pdf)：两页分别是正面/背面，均已打开核对。
- [D1 PCB PDF](PCB01186-D1_elec_RPI_Robot_HAT_PCB.pdf)。
- [D1 及首批下载清单](source-manifest.json)。

官方仓库 [LICENSE](LICENSE) 为 Apache-2.0，原件保留。这里只存原件和版本说明，没有进行板卡改版、生产下单或实物测试。

完整检索范围、其他作者的不同设计、未找到的 V1.2 工程与访问失败见[本轮研究](../../references/hat-imu-shared-bus-20261027/research.md#pcb-source-search-20261027)。
