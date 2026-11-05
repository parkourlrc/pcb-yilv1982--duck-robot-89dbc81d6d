# 自主 HAT 版本与交付包清单

状态口径：**开发 / 报价候选 / 制造获准 / 历史或撤回**。订单、付款、制造放行和实物验收分开记录：报价或付款不等于制造放行，制造放行也不等于首板验收。

| 版本 | 源身份 | 版本状态 | 订单/实物 | 交付或报价包 | 证据入口 | 替代关系 |
|---|---|---|---|---|---|---|
| **B.0（rev_b）** | `84362651a5dc57338a24f6b0d7a642267d32f4bc81888ccc2809bb129fc1bcf0` | 开发检查点：`native_clean_development_checkpoint_not_for_order`，`production_ready=false` | Y10／SMT2611051346，5 片，2026-11-05 已付款、待收货；线路暂停；首板未验收 | [quote-84362651](rev_b/quote-84362651/README.md)、[review-output](rev_b/review-output/) | [rev_b](rev_b/README.md)、[checkpoint](rev_b/checkpoint.json)、[Y10 状态](../../docs/references/扩展板乙版降本/layout-spacing/y10-quotation-status.md) | 当前版本 |
| **A.1（rev_a / r18）** | `86654c03b6c1c8f51f7d5a4bef469aceed2ddfc73433b3e50426940c2a23164a` | 历史开发源（2026-11-03）；未制造/首板未验收；被 B.0 取代 | Y7 未付款（历史）；不用于新单 | [release-review 20261103-assembly](release-review/README.md)（ZIP SHA256 `46413368d6837e2b7f131f91f67a7f359d85bd663f88ff39f4a52a3b3de24194`） | [rev_a](rev_a/README.md)、[r18 报告](../../docs/references/扩展板邮票孔与电源修复/research.md) | 由 B.0 取代 |
| **旧检查点 r1～r17** | 多个源哈希，见归档专题 | 历史/退出制造入口 | 无 | [release-review](release-review/README.md) 内历史 ZIP，不覆写 | [归档专题索引](../../docs/references/README.md)「归档」组 | 由 r18→B.0 取代 |
| **A.2 全现货改版** | 未定/未实施 | 方案，未批准 | 无 | 无 | [A.2 spec](../../docs/specs/20261104-hat-jlc-stock-redesign/spec.md) | 若批准，作为 A.1/B.0 之外的新候选 |
| **外部装机板（kissqy HAT REVA / 白色 V1.2）** | 上游/实物，不由本项目版本控制 | 非自主设计；当前装机板按实物与来源核对；白色 V1.2 为历史 | 整机在用板，不等同自主 HAT | 无 | [kissqy 图纸来源](../../docs/schematics/kissqy-hat-reva-reference/README.md)、[白色板查证](../../docs/references/白色扩展板原理图查证/research.md) | 不适用 |

## 说明

- **B.0 的两种状态并存**：工程检查点为 `not_for_order`、`production_ready=false`；商务侧已有 5 片付款订单。两者不能互相替代：付款不补写工程放行，源检查也不证明实物验收。
- **A.1 的 release-review 是本地 CAM 评审包**，不等于工厂接受或制造放行；包内 SHA 与替代关系以 [release-review/README.md](release-review/README.md) 为准。
- **报价、制造、收货、首板验收**分别记录；本清单只维护版本与包的身份，不改变订单或接线许可。
