# kissqy HAT REVA：另版 PCB 参考

> **2026-11-04头部IMU复核**：已完整克隆kissqy仓库并核3分支、175提交、四份当前EPRO2及历史HAT版本。公开EH2.5/AMP2.0 HAT仍未放置IMU；软件头部驱动是BMI088，与声明的Pollen v0.15.1版本逐字节相同，独立躯干板为LSM6DSV16XTR。用户指出另有新增头部陀螺仪的HAT，其实装型号/新版工程仍待来源确认，不能用旧公开工程否认其存在，也不能以软件支持证明实装。见[完整仓库分析](../../references/社区作者仓库完整核查/research.md)。Y8仍使用不含IMU的公开86件源，未替换订单资料。

> **2026-11-04当前源文件核对**：上游`main`已为`411878f89d38783ea87a5b21b54270632dbba7d7`，同名10-15工程SHA变为`33586ff3…`；原d4d21c1的BOM JSON尚未随之更新。当前工程TH1为**0Ω/0603WAF0000T5E**、U6为**SN74LVC1G125DBVR/C23654**；C8/C9/C15空缺字段已从DEVICE读出。当前工程仍86件，34个唯一MPN，30个普通0.305mm孔。新原件另存[成本比较专题](../../references/自主扩展板与社区版成本比较/research.md)，本目录10-15原件仍保留旧SHA作为历史。上游更新不代表用户实物同步改过。

> **2026-11-02 用户确认（现行结论）**：当前整机使用的 **HAT 与 IMU 都是本仓库 [hardware](https://github.com/kissqy/Microduck-kissqy/tree/main/hardware) 的设计**。记录时 `main` 提交为 `d4d21c1073d2c12ad2b5dfe3deb031030f7792ef`（2026-11-02），本地存档副本固定在 `7c5fba9`（2026-10-27），两者可能已有差异。
>
> 此前 2026-10-27 依据 PCB 预览与照片推断“与本机白色 V1.2 不对应”，现按用户确认更正。**仍待核**：实物是 EH2.5（10-07 工程）还是 AMP2.0（10-15 工程）接口版；旧照片里“F303 类 MCU”的判读（作者时间线未列该器件）。

2026-10-27 查找白色 HAT V1.2 PCB 时取得。按 2026-11-02 用户确认，本机在用即此设计；但维修/改阻仍须按对应版本工程与实物位号核对，不能跨版本套用。

来源仓库：[kissqy/Microduck-kissqy](https://github.com/kissqy/Microduck-kissqy)，固定提交 `7c5fba929e668aab4fa86f608fb7586c0e9718b2`。原文快照：[HAT 时间线](../../references/扩展板双口惯性缺答复核/pcb-search/kissqy-HAT-TIMELINE.md)。作者描述为两层 HAT-V5/REVA 设计；**2026-11-02 用户确认本机在用**，接口版本与实物对应待核。

**历史BOM核对（2026-11-02，AMP2.0 版，取自 `d4d21c1`）**：作者发布的 [AMP2.0-BOM](AMP2.0-BOM-d4d21c1.json) 列HAT86件、IMU25件；HAT最高引脚数IC为**U2 TLV320AIC3104IRHBR（HVQFN-32）**，另有PAM8406DR/SOIC-16等IC，**没有48脚MCU**；IMU为**STM32G031F8P6（TSSOP-20）＋LSM6DSV16X**。此前“唯一多脚IC”措辞不准确，现更正。旧照片中LQFP48判读与此设计不一致，不能跨版用于接线；新工程的TH1/U6等差异见顶部现行核对。

## 电源模块（BOM＋作者说明核对，2026-11-02）

- **输入**：J13/J14 的 pin2 = `BATT_IN`，两路舵机口直挂；同一 `BATT_IN` 送 5V 级。
- **5V 级**：**U9 AP63205WU-7**（3.8～32V 输入、固定 5V、**2A**）＋ L4 6.8µH/3A ＋ C21/C22 22µF×2 ＋ C20 100nF bootstrap ＋ R3 0Ω（SHDN 拉高）；输出经 **U10 LM5050-1 ＋ Q2 SI2312** 理想二极管/ORing 接到 40P 的 5V（用于与 USB 5V 并供、防倒灌；具体接法待图核）。
- **保护与滤波**：D1 BAT54SW、D4 BZT52C5V1（5.1V钳位）；TH1在DATA线上，旧d4d21c1工程为100R PTC，当前411878f工程已改0Ω。**BATT主路没有保险丝/PTC**；当前实物TH1不能据上游新版本推定。
- **作者自己的缓冲设计**：作者另有 **HUB 板（¥69）**，明确写“自带 **1000µF 总电源缓冲电容**，缓冲舵机瞬时负载，防止瞬时压降导致 ZERO 重启”；HAT 本身没有这级大电容。
- **对本机电压问题的含义**：
  - 舵机电流**不经过** 5V buck，直接从 `BATT_IN` 走；AP63205 的 2A 只覆盖主控与板上逻辑/音频。
  - 舵机瞬态直接落在 `BATT_IN` 上，HAT 输入端只有小容量电容，这与作者用 1000µF HUB 的动机一致——没有 HUB 时压降更容易传到 buck 和 IMU。
  - 若 `BATT_IN` 跌破 buck 输入下限，5V 会跟随塌陷，Radxa 复位；因此测量必须同时看 `BATT_IN` 与 5V。
- **待核**：实物 U9 丝印是否 AP63205、C21/C22 是否 22µF、LM5050 的 ORing 具体接法、`BATT_IN` 铜箔/连接器的载流能力。

## HUB（DXL HUB V2）识别要点（2026-11-02）

> **2026-11-02 用户确认**：手上有一块 kissqy **DXL HUB V2**（对应上述 4×AMP2.0 3P + 2P 输入 + 1000µF 特征），**但尚未接入电源链路**（台供仍直接进 HAT），1000µF 当前不在电路中；接入方案与注意项见[电压复核](../../references/飞特策略模型上机核对/voltage-sag-review-20261102.md)第十节。

- 来源：作者装配数据 [assembly-hub-layout.js](https://github.com/kissqy/Microduck-kissqy/blob/main/docs/assembly-hub-layout.js) / [assembly-hub-layout.json](https://github.com/kissqy/Microduck-kissqy/blob/main/docs/assets/assembly-hub-layout.json)，引用工程 `ProPrj_DXL_HUB_V2_2026-10-30.epro2`（SHA256 `8913c6b9…`）；该工程未出现在 `hardware/` 公开目录。
- 尺寸/孔位：**23 × 34 mm**、1.6 mm 厚，4 个 Ø1.2 mm 安装孔（±9.5 / ±15.0 mm）。
- 接口：**J1–J4 共 4 个 A2007WR-3P（AMP2.0 3P）**，脚序 **1=SERVO_BUS、2=VIN、3=GND**；CN1 为 2P 电源输入（1=GND、2=VIN）。
- 电容：**C1 1000 µF / 16 V 电解，装在 PCB 背面**（作者确认）。
- 装配位置：**髋部中央**；躯干舵机 30 → HUB，HUB 再分到左腿 20、右腿 10 等分支（见装配数据）。
- 判定“我有没有”：找一块约 23×34 mm 的小板，4 个白色 3P 座 + 1 个 2P 电源座，背面一颗大电解电容；若电池/台供先进 HUB 的 VIN/GND、再由 HUB 分到 HAT 与腿部，则 1000 µF 已在链路中。
- **易混板卡**：
  - 黑色 XT60 **5/6/7V 可选降压模块**（BUS SERVO POWER SUPPLY V1.3，造物の乐趣）是**稳压模块**，不是 HUB；3P 口出稳压 VCC、PWR OUT 直通，6V 档实测输入下限约 6.3V（见 [降压模块测试单](../../../buck-module-test.md)）。它属于台架工具，不在作者 HAT/HUB 设计里。
  - 社区 **dxl_hub**（[只读参考](../../../../references/microduck-community-kit/hardware/dxl_hub/README.md)）也是“多 3P 口分线板”，KiCad 开源，可焊 EH 或 AMP2.0 座，兼总线数据合并；**没有 1000 µF**，与本仓库 HUB V2 不是同一块。区分看：是否有背面大电解、3P 座的数量/类型。


**2026-10-27 PCB连线核查**：用户指定本工程查找串阻旁路点；两版均核到R33两端为`DXL_DATA_INT/CLAMPED`，可对应到 **R32第2焊盘 / TH1第1焊盘**。本工程R33已为0Ω，R31实际是RX上拉，不能混用位号。见[定位图、原始网名/脚号及限制](../../references/扩展板焊盘脱落修复/research.md#kissqy-bypass-points-20261027)；仍不等同白色V1.2实物维修点。

| 原件 | 作者记录 | Git blob / SHA256 |
|---|---|---|
| [10-07 工程](ProPrj_HAT_REVA_SCH_2026-10-07.epro2) | EH2.5 接口版 | `224264002c69ca71b8b16f88a2ad482f2b0b063e` / `5aa0db7d24a14887e9e7340c1c3708c9d2a60ef5638243d39e743cc7430447f7` |
| [10-15 工程](ProPrj_HAT_REVA_SCH_2026-10-15.epro2) | AMP2.0 接口版 | `c993a56e275a84d0c7377489ec4d81a556620835` / `9c2870a28b29845ef6e559369cf3ea3c27e3fccd12b63745ed661af77fff32b0` |

已检查文件容器：两份 `.epro2` 均为 ZIP，包含 `HAT_REVA_SCH.epru`、`project2.json` 和内嵌预览；工程记录确有 PCB、SCH/SCH_PAGE，PCB UUID 为 `9d00f144890fd6bb`。不是只含原理图的 PDF。未启动嘉立创 EDA 修改/重新导出。

文件最初下载到调研 `pcb-search/`，本轮归档移至此目录，内容哈希未变。原下载 URL/状态/哈希见[清单](../../references/扩展板双口惯性缺答复核/pcb-search/fetch2-manifest.json)，容器检查见[10-07](../../references/扩展板双口惯性缺答复核/pcb-search/kissqy-ProPrj_HAT_REVA_SCH_2026-10-07-inspection.json)和[10-15](../../references/扩展板双口惯性缺答复核/pcb-search/kissqy-ProPrj_HAT_REVA_SCH_2026-10-15-inspection.json)。

本轮未专门核定该硬件工程许可，不据公开可下载推定可任意商用或转授权。作者关于 R33/TH1 的改动与运行情况只作上游记录，不是本机实测。完整检索结论见[研究](../../references/扩展板双口惯性缺答复核/research.md#pcb-source-search-20261027)。

## PCB预览提取件

- [10-07预览](pcb-preview-2026-10-07.webp)：原EPRO2内`IMAGE/9d00f144890fd6bb.webp`，SHA-256 `92bf9aea8d2d5cd67524da5c8cb54483f85a4daf887e90a5ee39a65d0aa071fa`。
- [10-15预览](pcb-preview-2026-10-15.webp)：同一成员路径，SHA-256 `454934f40a7fd3c2c5a02af3c5363ae26e61b30c6f35144e2d08c9bb18b1614d`。
- 两张为2026-10-27提取的来源原图，不是本机照片；生成标注图另存photos，脚本和精简网络证据见上文维修专题。均已打开核查。
