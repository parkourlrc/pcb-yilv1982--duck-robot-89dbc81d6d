# Microduck NP-F550 取电结构：GitHub 查证记录

查证日期：2026-10-08（Asia/Shanghai）。本次只读调查远端资料，没有发 issue、修改远端或进行硬件通电测试。

## 结论

**目前最有力的结构线索不是大块市售摄影扣板，而是：两枚取电插针 + 一块狭长 banana PCB + 打印固定件。**

- **原版直接证据**：Pollen 的模型文件含 `banana_pcb_locker.stl`，配套 `.part` 元数据原名为 `Banana_PCB_locker <1>`。这证明原版模型包含 banana PCB 固定件；不能单凭名字证明其触点规格或量产实装。
- **社区可获取的实施方案**：`jyg9/microduck-community-kit` 公布取电小板原理图、PCB、Gerber 和装配渲染图，并推荐 2.5 mm 香蕉头 PCB 插针。
- **交叉印证**：`fanhao375/microduck-replica-cad` 最新 README 的采购表明确列出“2.5mm 香蕉插头 PCB 铜镀金 ×2”和“banana PCB ×1”。
- **尚未证实**：Pollen 原厂取电板原理图、触点厂家料号，以及用户手上电池/打印件与该社区板的机械、电气适配。不能把社区板说成官方发布或已由本次验证。

因此，前文“只有两片 power_support，没有更具体线索”需要修正：**本地旧 BOM 遗漏了 banana PCB 固定件的指向，而且远端已有新的取电板与采购资料。**

## 1. 原版模型里的证据

- [官方 banana_pcb_locker.part](https://github.com/pollen-robotics/microduck_rl/blob/develop/src/mjlab_microduck/robot/microduck/assets/banana_pcb_locker.part)
- [官方 banana_pcb_locker.stl](https://github.com/pollen-robotics/microduck_rl/blob/develop/src/mjlab_microduck/robot/microduck/assets/banana_pcb_locker.stl)
- [官方 power_support.stl](https://github.com/pollen-robotics/microduck_rl/blob/develop/src/mjlab_microduck/robot/microduck/assets/power_support.stl)

`.part` 中 `name` 为 `Banana_PCB_locker <1>`，同时保留上游 CAD 的 documentId / elementId / partId。此次官方树中查到的是固定件，并没有由此找到完整取电板工程。

官方在 [issue #166](https://github.com/pollen-robotics/microduck/issues/166#issuecomment-5440229849) 和 [issue #168](https://github.com/pollen-robotics/microduck/issues/168#issuecomment-5529698359) 曾说明软件开源而硬件并非整体开源。这与某些单独电子板仓库公开不矛盾，不能推导为所有电路都已公开。

## 2. 最直接可用的社区方案：jyg9

- [取电板目录与说明](https://github.com/jyg9/microduck-community-kit/tree/main/hardware/banana_pcb)
- [原理图](https://github.com/jyg9/microduck-community-kit/blob/main/hardware/banana_pcb/banana_pcb.kicad_sch)
- [PCB](https://github.com/jyg9/microduck-community-kit/blob/main/hardware/banana_pcb/banana_pcb.kicad_pcb)
- [Gerber 制造包](https://github.com/jyg9/microduck-community-kit/blob/main/hardware/banana_pcb/production/banana_pcb.zip)
- [装配渲染原图](https://github.com/jyg9/microduck-community-kit/blob/main/hardware/banana_pcb/docs/img/1.jpg)
- [公开引入记录，2026-09-27](https://github.com/jyg9/microduck-community-kit/commit/2221d1dbd1e9852f9a0ee247d6f53175b66699df)

作者说明：小板固定在电池上方，把电池电力引到其他板子；推荐“2.5mm 香蕉头 PCB 连接器 13mm，尾部 1.5mm（参考型号 U6068）”。这些是作者给出的选型描述，不是本次对插针或电池的实物测量。

本次读取 KiCad PCB 与制造包，核得：

| 项目 | 文件中的事实 |
|---|---|
| 板框 | 39.19 × 6.79 mm，来自 Edge.Cuts 起终点差值 |
| 两插针中心距 | 33.80 mm，X = 129.17 / 162.97 mm，Y 相同 |
| 插针焊接孔 | 1.70 mm；这是焊接尾部的 PCB 孔径，不是接触电池端的直径 |
| 连接关系 | J1 → J3 的 pad 1；J2 → J3 的 pad 2，两路独立直通 |
| 板上器件 | 两个单针连接器与一个双焊盘出线位；没有降压、充电或保险器件 |
| Gerber 核对 | 板框、插针孔距和 1.70 mm 孔径与 PCB 对应；未做完整制造审查 |
| 图示 | CAD 装配渲染，不是实物安装或带载测试照片 |

**极性不能凭 J1/J2 名字猜。** 两个网络只是 `Net-(J1-Pad1)` / `Net-(J2-Pad1)`，本次没有据此确认哪侧为电池正极。需依据实物标识及电压测量确定，且焊接时拆下电池。

作者还写“正常运行电流 3–5A”，但未见该目录提供完整工况、连接器额定或温升报告，不能把它当作整机电源定额或安全验收。

社区 README 的配电示意走 `电池 → banana_pcb → 腹部 dxl_hub → 头部/左右腿/IMU`。这属于该社区实现，并非原厂线束已得到确认。

## 3. 复刻 CAD 的最新采购表支持同一结构

[fanhao375/microduck-replica-cad README，采购表](https://github.com/fanhao375/microduck-replica-cad/blob/master/README.md#L187-L198)：

- #32：`banana_pcb_locker` 打印件。
- #42：2.5mm 香蕉插头 PCB 铜镀金，2 个。
- #43：banana PCB，1 块。
- 同表另有“电池座”，但用途和与 banana 板的装配关系未由此表明确；不能认定所有项目必须叠加使用。

[采购表中给出的插针商品参考](https://item.taobao.com/item.htm?id=1066300439603&skuId=6116801109787)。本次没有核验商品现售规格、价格、库存或载流能力，只确认该链接被列入 BOM。

本次也浏览了该仓库的 21 页装配 PDF，未从中取得更明确的取电触点安装步骤。不能用一般装配手册替代插针机械配合验证。

**文档存在新旧不一致**：远端主复刻仓的 BOM 仍保留“触点方案未知”的旧文字；而 CAD 仓 2026-09-29 采购表已列出插针和 banana PCB。采购与取电判断应结合实际新文件，不能继续只引用旧结论。

## 4. 其他复刻线索及反证

### 7757/fanduck

[仓库](https://github.com/7757/fanduck) 的 [板件包](https://github.com/7757/fanduck/blob/main/downloads/maker-20260916/fanduck-boards-20260916.zip) 含 `电池触点板_v0.3/banana_power_contact.*`。

包内说明给出：46 × 7.5 × 1.6 mm、触点距 33.8 mm、Harwin H2183-05、保险器件候选 1206SFS800F/24，以及 AWG16 出线。

**关键边界**：包内 README 明写实物极性、夹持、插入深度、压降、保险选择、温升仍待验证，状态 `DO NOT POWER`；制造说明只放行小批工程配合样板。这不是可直接照抄通电的成熟方案。其 1.75 mm 触点方案也不能与 jyg9 推荐的 2.5 mm 插针混为一谈。

### ScrapMeta/microduck-diy

[mechanical-power-pocket.md](https://github.com/ScrapMeta/microduck-diy/blob/main/wiki/concepts/mechanical-power-pocket.md) 专门分析 `power_support / banana_pcb_locker` 口袋，但文末仍写触点/插头的机械落点未定。证明此前社区确实探索这条路线，也提醒“看图能装”不等于自己的模型版本和实物必然配合。

### 其他资源筛查

筛查了 `AI-FanGe/Microduck-build-tutorial`、`LuwuDynamics/xgoduck_hardware`、`SaberOnGo/open-microduck`、`lingzolabs/microduck-hardware-replica`、`qianen6/microduck-replica-kit`、`prodou/microduck-replica`、`Shiyao-Huang/ChinaMicroDuck`、`tachytelicdetonation/microduck-replica-lab` 等元数据、README 或目录树。未取得比上述小板工程更直接、且能确认为原厂取电结构的证据。各项目主控、舵机和供电路线不同，不宜拼接套用。

## 5. 从这块小板到主控

[官方 RPI Robot HAT README](https://github.com/pollen-robotics/elec_RPI_Robot_HAT/blob/main/README.md) 明确写它通过 motor connector 接入电源，而不是保证有独立的“电池专用插座”。

功能链应理解为：

```text
NP-F550 的正负电极
  → 两枚适配取电插针
  → banana PCB：只引出电池原电压
  → 合适的保护/开关/配电与 HAT 电源网络
  → HAT 的 5V 降压支路
  → Radxa 主控
```

HAT 当前公开主线已经是 D1，用户手上可能是 C1 或复刻版；端子与针序必须按实物版本核对。**HAT 标称输入范围不代表挂在同一电源网络的舵机允许该电压。** 例如 NP-F550 满电 8.4V 不能直接作为 XL330 合规供电。

官方另有 [elec_battery_mngt](https://github.com/pollen-robotics/elec_battery_mngt) 的 2S BMS/充电板，以及 [issue #174 的未来量产机板载充电回复](https://github.com/pollen-robotics/microduck/issues/174#issuecomment-5559420730)。这并不能证明老版 NP-F550 取电小板带充电管理。

### 给本机的下一步

1. 拍电池触点面、已打印支架与 HAT 的型号/端子丝印，确认版本和尺寸。
2. 如保持原外形，优先评估 banana 小板 + 两个适配插针，不必先买一整块大摄影扣板。
3. 先做断电机械试装，确认无短接风险、无强行挤压及可靠保持；不能只看“2.5mm”就认定兼容。
4. 焊接时取下电池。首次取电用直流电压档确认正负极；不得电流档跨接电池。
5. 先只验证主控支路，确认 5V 稳定；整机带载前另核保护、压降、线径/接头额定和温升。不要同时把外部 USB 5V 与 HAT 5V 盲目并联。

## 检索范围与限制

- GitHub `microduck` 仓库搜索共返回 376 项元数据，逐项尝试根 README.md/readme.md，成功读取 331 项。清单见同目录 `github-repository-index.json`。
- 这是搜索默认范围，不是所有 fork 的全文穷尽检索；45 项未成功读取，可能是空仓库、非标准 README 名称或网络错误。不能说“已查尽 GitHub 上所有资料”。
- 针对官方/复刻的 battery、NP-F、电池、banana、contacts、holder、hardware 相关 issue/PR 做搜索，再检查相关回复；许多命中是仿真接触或测试用语，与取电无关。
- 重点检查官方模型树、独立 HAT/电池电子仓、社区板工程、CAD 最新 BOM 和装配 PDF、Fanduck 板件 ZIP。
- 没有认证式 GitHub 全站代码检索；没有对所有视频逐帧复核；没有替用户下单、制造或接电。
- 所有实物极性、插针保持力和整机负载结论仍须现场验证。
