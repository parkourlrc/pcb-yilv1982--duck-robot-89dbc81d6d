# kissqy HAT REVA：另版 PCB 参考

2026-10-27 查找白色 HAT V1.2 PCB 时取得。**这是另一作者的设计，未与用户白色鸭图案 V1.2 对应，不用于定位本机 R31 或直接决定改阻。**

来源仓库：[kissqy/Microduck-kissqy](https://github.com/kissqy/Microduck-kissqy)，固定提交 `7c5fba929e668aab4fa86f608fb7586c0e9718b2`。原文快照：[HAT 时间线](../../references/hat-imu-shared-bus-20261027/pcb-search/kissqy-HAT-TIMELINE.md)。作者描述为两层 HAT-V5/REVA 设计；本机未使用或验证。

**2026-10-27 PCB连线核查**：用户指定本工程查找串阻旁路点；两版均核到R33两端为`DXL_DATA_INT/CLAMPED`，可对应到 **R32第2焊盘 / TH1第1焊盘**。本工程R33已为0Ω，R31实际是RX上拉，不能混用位号。见[定位图、原始网名/脚号及限制](../../references/pcb-pad-repair-20261027/research.md#kissqy-bypass-points-20261027)；仍不等同白色V1.2实物维修点。

| 原件 | 作者记录 | Git blob / SHA256 |
|---|---|---|
| [10-07 工程](ProPrj_HAT_REVA_SCH_2026-10-07.epro2) | EH2.5 接口版 | `224264002c69ca71b8b16f88a2ad482f2b0b063e` / `5aa0db7d24a14887e9e7340c1c3708c9d2a60ef5638243d39e743cc7430447f7` |
| [10-15 工程](ProPrj_HAT_REVA_SCH_2026-10-15.epro2) | AMP2.0 接口版 | `c993a56e275a84d0c7377489ec4d81a556620835` / `9c2870a28b29845ef6e559369cf3ea3c27e3fccd12b63745ed661af77fff32b0` |

已检查文件容器：两份 `.epro2` 均为 ZIP，包含 `HAT_REVA_SCH.epru`、`project2.json` 和内嵌预览；工程记录确有 PCB、SCH/SCH_PAGE，PCB UUID 为 `9d00f144890fd6bb`。不是只含原理图的 PDF。未启动嘉立创 EDA 修改/重新导出。

文件最初下载到调研 `pcb-search/`，本轮归档移至此目录，内容哈希未变。原下载 URL/状态/哈希见[清单](../../references/hat-imu-shared-bus-20261027/pcb-search/fetch2-manifest.json)，容器检查见[10-07](../../references/hat-imu-shared-bus-20261027/pcb-search/kissqy-ProPrj_HAT_REVA_SCH_2026-10-07-inspection.json)和[10-15](../../references/hat-imu-shared-bus-20261027/pcb-search/kissqy-ProPrj_HAT_REVA_SCH_2026-10-15-inspection.json)。

本轮未专门核定该硬件工程许可，不据公开可下载推定可任意商用或转授权。作者关于 R33/TH1 的改动与运行情况只作上游记录，不是本机实测。完整检索结论见[研究](../../references/hat-imu-shared-bus-20261027/research.md#pcb-source-search-20261027)。

## PCB预览提取件

- [10-07预览](pcb-preview-2026-10-07.webp)：原EPRO2内`IMAGE/9d00f144890fd6bb.webp`，SHA-256 `92bf9aea8d2d5cd67524da5c8cb54483f85a4daf887e90a5ee39a65d0aa071fa`。
- [10-15预览](pcb-preview-2026-10-15.webp)：同一成员路径，SHA-256 `454934f40a7fd3c2c5a02af3c5363ae26e61b30c6f35144e2d08c9bb18b1614d`。
- 两张为2026-10-27提取的来源原图，不是本机照片；生成标注图另存photos，脚本和精简网络证据见上文维修专题。均已打开核查。
