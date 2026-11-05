# kissqy完整仓库：头部IMU与HAT版本核查

日期：2026-11-04，Asia/Shanghai。用户先指出kissqy HAT新增了头部陀螺仪，随后明确要求先完整下载GitHub再详细分析。本轮以`kissqy/Microduck-kissqy`完整仓库和Git历史为核查范围，不运行其安装脚本，不改本机硬件/订单，不使用子代理。

## 下载与范围

- 上游：`https://github.com/kissqy/Microduck-kissqy`。
- 完整Git克隆路径：`E:/Projects/kissqy-Microduck-analysis-20261104`，位于本项目之外，防止把完整第三方Git库混入本项目提交。
- 普通`git clone`已完成，未使用浅克隆或稀疏检出：**2037个受版本管理文件、175个可达提交、3个远端分支**。`git fsck --full --no-reflogs`退出0，工作树干净，未发现Git LFS占位文件或submodule。
- 前置API实读main为`411878f89d38783ea87a5b21b54270632dbba7d7`，提交时间2026-11-03 16:40:28 UTC，即2026-11-04 00:40:28 +08:00。公开树2037个blob，列示大小合计374362526字节，Git历史大小另计。
- 前置快照与manifest：`../自主扩展板与社区版成本比较/head-imu-update/`。仓库下载不等于单独发布的系统镜像也已下载，是否涉及Release资产将分别记录。
- 本地检出文件总计376001925字节，Git pack为372010306字节；Git树原始文件总计374362526字节，文本检出的换行转换使工作区字节数与Git树统计不同。硬件二进制SHA与先前固定源一致。
- 仓库内13个ZIP/TAR.GZ包已检查成员清单，无额外电气CAD源文件。机械RAR作为原仓库文件保留，未解包或把机械文件当电气证据。
- GitHub另有767412924字节的`microduck-zero3w-0.15.1-R1.img.xz`系统镜像Release附件，不在Git树中，本轮未下载/挂载/执行；不影响已下载完整Git仓库的事实，也不能声称镜像内部内容已经审查。

## 已完成的交叉核对

1. 全部公开HAT/IMU EPRO2：实际有效PCB/SCH器件和DEVICE继承属性，避免把未放置库器件当实装。
2. 全仓库头部IMU源码、默认配置、启用路径及驱动地址。
3. 分支和文件提交历史：判断新增驱动、公开硬件更新与上游继承代码的时间关系。
4. 文档、BOM、装配资产和发布内容：区分头部IMU与独立躯干IMU。
5. 与本轮Y8固定86件工程核对，明确报价是否覆盖用户提到的新版本，更新此前过宽表述。

## 结论

**[源码核验，高置信度] 公开软件中“头部IMU”的驱动目标是BMI088，与本项目自主HAT U501的型号相同。** 驱动由`tofd`运行，地址为加速度0x19、陀螺0x68，提供`head_imu.stream`。默认配置关闭；软件支持不等于当前板已经焊接或用户本机已经启用。

**[工程文件核验，高置信度] 当前公开HAT两版本没有放置BMI088或另一颗IMU。** EH2.5 PCB为84件，AMP2.0 PCB为86件；原理图与PCB有效元件、DEVICE继承型号均已核对。它们均只有8个IC：U1 PAM8406DR、U2 TLV320AIC3104IRHBR、U3 XC6206P182MR、U5/6/7逻辑门、U9 AP63205WU-7、U10 LM5050MKX-1/NOPB。本轮不是只按README/BOM缺词推断。

**[工程文件核验，高置信度] 独立躯干IMU两版本均为U2 LSM6DSV16XTR（C5267406）＋U1 STM32G031F8P6（C529334），每板25件。** 这与头部BMI088是两个设备；不能拿躯干型号回答头部新增芯片问题。

**[历史/来源核验，高置信度] 头部BMI088代码是继承的既有实现。** `tof/src/imu.rs`在本仓库2026-10-07 13:06:49 +08:00的首个提交37adc97已存在，三个远端分支的blob均为`66e4462b5d7f1db74aad542efef6520891a9efb3`。按`PUBLICATION-MANIFEST.json`声明的Pollen官方固件`daemon-v0.15.1`、提交`1fa84386f07884e27866411bc1ba166977bced95`下载同路径文件，11972字节，SHA256均为`97b8ed013debf9bc8ec6c4b4255b72407c6f6dea30106ab91e254f24a00540ad`，逐字节相同。不能把它当kissqy最近新增硬件的提交记录。

**[待确认] 用户提到的“新增头部陀螺仪的kissqy HAT”实板/未公开新版，尚无与其对应的原理图、BOM、实装照片或版本资料。** 本仓库无法独立确定该新板实际采用的器件；BMI088是已证实的软件目标，不升级为新板实装结论。可能是尚未公开的改版、外接模块，或软件/模型中的头部IMU描述，但没有证据在三者之间裁决。

## 硬件与分支覆盖

| 对象 | PCB有效器件数 | 头部IMU | 原件SHA256前缀 |
| --- | ---: | --- | --- |
| HAT EH2.5，10-07文件 | 84 | 无有效放置器件 | 5aa0db7d |
| HAT AMP2.0，当前10-15同名文件 | 86 | 无有效放置器件 | 33586ff3 |
| HAT AMP2.0，历史10-15文件 | 86 | 无有效放置器件 | 9c2870a2 |
| 独立IMU EH2.5 | 25 | U2为躯干LSM6DSV16XTR | 4eb30bf9 |
| 独立IMU AMP2.0 | 25 | U2为躯干LSM6DSV16XTR | 824bad07 |

EPRO2按DOCHEAD划分PCB/SCH_PAGE/DEVICE，按记录ID应用更新/删除，再解析有效COMPONENT和器件继承属性；没有把库定义、历史删除记录或注释作为有效放置。每个SCH_PAGE比PCB多1个无位号记录，不把该记录算作多焊了一颗芯片。

`git log --all`中电气CAD路径只有4份公开EPRO2；所有可达历史共5个不同EPRO2 blob，其中HAT AMP2.0有新旧两个版本，均已解析。三个分支的区别是语音分支仍用旧HAT AMP2.0 blob，主分支与HUB分支用当前blob；没有发现另外的头部IMU工程。

AMP2.0工程最后修改为2026-10-30 19:55:49 +08:00的46874e0（Update HAT project）；其当前文件SHA与本轮Y8报价来源一致。仓库main的2026-11-04 00:40:28提交主要是装配显示等，不代表同日换了HAT芯片。BOM JSON未同步TH1/U6的问题仍按原勘误保留。

## 软件路径及容易混淆的证据

`microduck-hd1910/firmware/tof/src/imu.rs`文件注释将头部IMU写为BMI088，实际代码使用`bmi088::{Bmi088,Bmi088Ahrs,Config}`及`Bmi088::new`，I2C地址说明为加速度0x19/陀螺0x68。该文件同时处理未装BMI088的HAT情况。因此它能证实软件驱动目标，不能单独证实某块新HAT已焊接此芯片。

公开硬件README中的LSM6DSV16XTR目前列在独立IMU板，不应用其型号回答头部新芯片。用户新版本信息保留为待核，不因公开文件尚未匹配而否认其存在。

| 证据定位（均相对完整克隆根目录） | 核到什么 | 不能推出什么 |
| --- | --- | --- |
| `microduck-hd1910/firmware/tof/src/imu.rs:1`、`:223`、`:245` | BMI088目标、地址说明、实际初始化 | 新HAT已放置/实装 |
| `microduck-hd1910/firmware/tof/Cargo.toml:45` | 依赖Pollen `bmi088-rs` v0.1.2 | kissqy新研硬件型号已经公布 |
| `microduck-hd1910/firmware/tof/src/main.rs:143`、`:247` | 默认100Hz采样参数、配置启用分支 | 本机已开启或已有100Hz实测 |
| `microduck-hd1910/firmware/robotd-params/src/lib.rs:723`、`deploy/robotd.toml:392` | HeadImuParams默认bool=false、配置说明 | 缺样本必然等于没焊芯片 |
| `microduck-hd1910/firmware/deploy/audio/i2c3-pihat.dts:11`、`:31` | overlay注释描述共享I2C与BMI088 | 注释替代kissqy实际PCB网表 |
| `microduck-hd1910/firmware/kinematics/src/head.rs:34`、`:97`及`docs/raw-kinematics.js:45` | 存在可选head_imu坐标架/显示挂点 | 显示模型或坐标架是实装器件证据 |
| `microduck-hd1910/firmware/duck-control/src/imu.rs:1`、独立IMU EPRO2 U2 | 躯干IMU单独经总线接入 | 头部IMU与躯干IMU可不改软件互换 |

`docs/project/tof-on-demand.md:55`关于当时没有订阅者及CPU的描述是上游软件记录，本轮未在用户机器运行/测量，不把它当本机当前CPU、传感器或运动验收。

## 对之前报价与表述的修正

- **Y8的86件BOM没有包含头部IMU**，该订单/草稿仍对应公开33586ff3工程，未被本轮更换；不能拿其1160.39元草稿合计代表用户提到的未知新板。
- 之前“kissqy HAT没有BMI088”范围过宽，应限定为“本次Y8所用公开HAT工程未包含IMU”。公开软件支持BMI088的事实也应同步披露。
- 若用户的新板确实增加BMI088，两套按同料号/数量比较时，不能继续把自主BMI088的202.50元/5片全算独有功能差价。新板元件、PCB与装配报价须根据新资料重新生成，现不能简单在旧价上加芯片费充当实单。
- 本轮未修改Y7/Y8、未付款、未更换元件、未上电；本机实装状态仍以用户确认和后续硬件证据为准。

## 原始证据与检查

- `repository-audit.json`：克隆目录、HEAD、分支、历史、LFS/submodule、档案包清单与状态。
- `checkout-file-manifest.json`：2037个工作区文件的大小及SHA256。
- `epro-projects-audit.json`、`historical-hat-projects-audit.json`：有效元件、全部IC与传感器检索结果。
- `source-evidence.json`：关键源代码/文档的行号与原文定位；不是实机日志。
- `pollen-driver-comparison.json`、`pollen-pinned-head-imu.rs`：声明的官方版本与kissqy驱动逐字节比较。
- 可复现脚本：`inspect-epro-projects.py`、`audit-repository.py`、`compare-upstream-driver.py`。
- 上游来源：`https://github.com/kissqy/Microduck-kissqy/tree/411878f89d38783ea87a5b21b54270632dbba7d7`；官方对照：`https://raw.githubusercontent.com/pollen-robotics/microduck/1fa84386f07884e27866411bc1ba166977bced95/tof/src/imu.rs`。
- Git公开检索工具未返回可读页面，因此正文证据来自GitHub官方API、raw文件与完整Git克隆；没有从搜索摘要补造型号。
- 完整第三方仓库保持只读，许可文件完整保留；本项目新增分析文档/脚本未commit/push。
