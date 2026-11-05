# Radxa Zero 3 系统镜像核查（2026-10-14）

## 问题与范围

当前 Radxa 板使用 KDE 桌面版系统镜像，评估是否有必要换成更小的版本（server/minimal）。

## 设备与系统

- 设备：Radxa Zero 3（hostname `radxa-zero3`），4 核，内存 3.8 GiB（含 1.9 GiB zram），eMMC 58.2 GiB
- 系统：Debian 12 (bookworm)，内核 6.1.84-10-rk2410-nocsf
- 连接方式：`ssh radxa@172.16.108.54` 或别名 `ssh radxa`（已配置本机 `~/.ssh/config` Host radxa）；2026-10-14 已将本机 `id_ed25519` 公钥追加到板子 `~/.ssh/authorized_keys`，免密登录已验证（KEY_AUTH_OK）

## 实测数据（via SSH，非本机直连）

- 磁盘：`/dev/mmcblk0p3` 57G 总量，已用 5.9G（11%），可用 49G
- 内存：空闲时 used 215 MiB，available 3.6 GiB；负载 0.07（空闲）
- 桌面环境：KDE Plasma 5.27.5（kde-standard）、sddm 0.19 已安装；**sddm 处于 disabled，默认目标为 multi-user.target**
- 即：桌面环境完整安装但当前未运行，开机进的是纯字符界面

## 结论

**没有必要重刷小镜像。**

1. 磁盘：64G eMMC 只用了 11%，桌面包约占 2–3 GB，重刷省出的空间没有意义。
2. 内存/性能：sddm 未启用、默认 multi-user.target，桌面完全不驻留，空闲内存占用 215 MiB，运行时零开销。
3. 重刷成本：需要重新配置网络、蓝牙、dnsmasq、机器人软件环境，风险大于收益。

## 可选操作（均非必要）

- 需要桌面时：`sudo systemctl enable --now sddm`
- 确实想精简：可卸载 `kde-standard plasma-desktop sddm` 释放约 2–3 GB，但当前无此需求。

## 验证状态

- 本机实测（SSH 远程命令输出）：磁盘、内存、服务状态
- 未验证：桌面实际启动后的内存占用（当前未运行，无数据）

## 限制与下一步

- 若后续在此板部署训练/推理程序且内存吃紧，再评估卸载桌面或换镜像；目前保持现状。
