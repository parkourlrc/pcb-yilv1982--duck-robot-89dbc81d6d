# 训练模型与产物清单

状态口径：哈希只标识文件身份；`deployment_verified=false` 表示未做动作/实物验收。外部候选与自训产物分开记录，不把外部包写成自研。

> **M2 用户验收（2026-11-05）**：官方模型已上机并完成基本动作，按用户口径闭环。表中 `deployment_verified=false` 是单模型自动标志，不等于用户验收，也不代表稳定/完整动作通过。

## 外部候选（kissqy HD1910 包，10 个）

2026-10-31 清单记录的包：`training/logs/b-feetech-walk-20261024/runtime-package-review/Microduck-Robotd-FT6-R17`，build `1fa8438-feetech-ft6-control.43`，console `1.0.167`，归档 SHA256 `bcfd5c183c697b9c4e0fdbd563d995eda6a48331a7c49b9e76d20bd156c65cce`。

| 名称 | 任务 | SHA256 前 16 | 板上导入 | deployment_verified |
|---|---|---|---|---|
| 起坐 | Mjlab-SitStand-Flat-MicroDuck | `1c94934c6421ec72` | 是 | false |
| 行走、零速度保持与倒地恢复联合策略 | Mjlab-VelStand-Rough-Backlash-MicroDuck | `1cbf8730eadd75a5` | 是 | false |
| 前滚翻 | Mjlab-Roulade-Flat-MicroDuck | `59e15d7b04d0c40e` | 是 | false |
| 右脚踢球 | Mjlab-BallKick-Flat-MicroDuck | `67ad09d82f4865d2` | 是 | false |
| 地面捡取 | Mjlab-GroundPick-Flat-Backlash-MicroDuck | `b14e3a8b56ddbb8d` | 是 | false |
| 左脚踢球 | Mjlab-BallKickLeft-Flat-Backlash-MicroDuck | `ee0376c927044cde` | 是 | false |
| 滑轮蹲下 | Mjlab-RollerCrouch-Flat-Backlash-MicroDuck | `82be20b115d925ab` | 否 | false |
| 滑轮原地转 | Mjlab-Spin-Flat-MicroDuck | `621fe9f3ae346308` | 否 | false |
| 滑轮倒地起身 | Mjlab-RollerStandUp-Flat-MicroDuck | `2575b5894bcd8e3f` | 否 | false |
| 滑轮对称滑行 | Mjlab-Velocity-Swizzle-Backlash-MicroDuck | `14195135fcaa60cc` | 否 | false |

- 6 个普通足部模型已导入板侧 `/home/radxa/duck-policies/hd1910-20261031/`，6/6 文件哈希一致；全部 `deployment_verified=false`，未做动作/承重验收。
- 4 个滑轮模型为本地候选，未导入板侧。
- **当前工作区未找到** `training/logs/b-feetech-walk-20261024/`（2026-11-05 检查）；不要声称本地仍保留该包。板上 6 个模型是当前可核对副本。
- 完整任务、契约、逐文件哈希见 [model-inventory-20261031.json](../docs/references/飞特策略模型上机核对/model-inventory-20261031.json) 与 [onboard-model-catalog-20261031.json](../docs/references/飞特策略模型上机核对/onboard-model-catalog-20261031.json)。

## 自训产物

- `training/checkpoints/` 现有 23 组运行目录（`duck_stand_*`、`duck_walk_*` 等），含 `ckpt_*.zip`；`training/logs/rsl_rl/duck_walk/` 保留 6 组运行，`2026-10-19_15-02-25/model_9999.pt` 仍在。
- 自训模型未上机部署；`training/models/` 目前是 MJCF/显示资产，不是策略权重。
- 训练与回放入口见 [training/README.md](README.md)；物理参数见 [params](params/)。

## 身份缺口

- 外部包的记录路径当前不在工作区；4 个滑轮模型未导入；23 个历史 SB3 `final.zip` 未在当前工作区找到（清单记为未验证，不推断已删除）。
- 自训 checkpoints 与外部包不能混用；部署前需重新核哈希、契约和标定。
