# 足部奖励试验：完成与失败均计入预算

回放指标要求真实接触离开、连续净空>3mm至少40ms、再接触；短暂接触跳变不算合格步数。

| 运行 | 完成更新 | 消耗转换 | dev9 | 状态 |
|---|---:|---:|---|---|
| baseline-reference | — | — | 0/9 | 既有100轮参照，不计本轮消耗 |
| amplitude-20261107-gait010-s42 | 1 | 262144 | —/— | 实现失败 |
| amplitude-20261107-gait010-s42-r1 | 100 | 26214400 | 0/9 | budget_exhausted |
| amplitude-20261107-gait010_rawramp-s42 | 1 | 262144 | —/— | 实现失败 |
| amplitude-20261107-gait010_rawramp-s42-r1 | 100 | 26214400 | 0/9 | budget_exhausted |
| amplitude-20261107-gait020-s42 | 1 | 262144 | —/— | 实现失败 |
| amplitude-20261107-gait020-s42-r1 | 100 | 26214400 | 0/9 | budget_exhausted |
| amplitude-20261107-rawramp-s42 | 1 | 262144 | —/— | 实现失败 |
| amplitude-20261107-rawramp-s42-r1 | 100 | 26214400 | 0/9 | budget_exhausted |

| 运行 / 0.06m/s场景 | 实际前速 m/s | 左/右有效起落 | 交替率 | 最大航向偏差° | 足部门槛 |
|---|---:|---|---:|---:|---|
| baseline-reference / straight_0.06_101 | 0.00620 | 0/0 | 0.0% | 33.00 | 未通过 |
| baseline-reference / straight_0.06_102 | 0.00534 | 0/0 | 0.0% | 27.57 | 未通过 |
| baseline-reference / straight_0.06_103 | 0.00188 | 0/0 | 0.0% | 30.06 | 未通过 |
| amplitude-20261107-gait010-s42-r1 / straight_0.06_101 | 0.00005 | 0/0 | 0.0% | 73.78 | 未通过 |
| amplitude-20261107-gait010-s42-r1 / straight_0.06_102 | -0.00084 | 0/0 | 0.0% | 51.82 | 未通过 |
| amplitude-20261107-gait010-s42-r1 / straight_0.06_103 | -0.00083 | 0/0 | 0.0% | 50.85 | 未通过 |
| amplitude-20261107-gait010_rawramp-s42-r1 / straight_0.06_101 | 0.01485 | 0/0 | 0.0% | 175.58 | 未通过 |
| amplitude-20261107-gait010_rawramp-s42-r1 / straight_0.06_102 | 0.01488 | 0/0 | 0.0% | 171.98 | 未通过 |
| amplitude-20261107-gait010_rawramp-s42-r1 / straight_0.06_103 | 0.01503 | 0/0 | 0.0% | 163.59 | 未通过 |
| amplitude-20261107-gait020-s42-r1 / straight_0.06_101 | 0.02065 | 32/42 | 86.3% | 133.76 | 通过 |
| amplitude-20261107-gait020-s42-r1 / straight_0.06_102 | 0.02091 | 34/42 | 89.3% | 64.26 | 通过 |
| amplitude-20261107-gait020-s42-r1 / straight_0.06_103 | -0.00075 | 0/0 | 0.0% | 59.54 | 未通过 |
| amplitude-20261107-rawramp-s42-r1 / straight_0.06_101 | 0.00048 | 0/0 | 0.0% | 62.60 | 未通过 |
| amplitude-20261107-rawramp-s42-r1 / straight_0.06_102 | 0.00052 | 0/0 | 0.0% | 61.90 | 未通过 |
| amplitude-20261107-rawramp-s42-r1 / straight_0.06_103 | 0.00035 | 0/0 | 0.0% | 10.86 | 未通过 |

只有一个训练seed，不满足跨训练种子复核要求；即使单项改善，也不能据此宣布问题解决。
