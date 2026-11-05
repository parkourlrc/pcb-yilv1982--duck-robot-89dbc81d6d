# Radxa Zero 3W 系统烧录记录（2026-10-13）

> **路线变更（2026-10-13 下午，用户决定）**：放弃 TF 卡启动路线，改为 **USB 直连 maskrom 直刷 eMMC**（RKDevTool v2.86）。「eMMC 封存不动」作废，eMMC 前任系统将被覆盖。本文上半部分（TF 卡尝试）为历史记录；现行路线见文末「USB 直刷 eMMC」节。

## 问题与范围（TF 卡阶段，历史）

二手 Radxa Zero 3W（RK3566）板载 eMMC 内含前任系统，当时采用 **TF 卡启动、eMMC 封存不动** 的路线（RK3566 启动顺序 TF 优先于 eMMC）。本记录覆盖：镜像准备与校验、TF 卡状态确认、自研烧录脚本两次失败的过程与弃用决定、改用标准工具 Rufus 的交接。

## 镜像（本机实测）

- 文件：`images/radxa-zero3_debian_bullseye_cli_b6.img`（2,549,646,336 字节 ≈ 2.55 GB，目录不入版本库，另有 `.img.xz` 原包）
- SHA512 实测（certutil，2026-10-13）与 `images/radxa-zero3.sha512` 完全一致：
  `5fbc0c478785b8928fbe986cd5d004d8bc59bfe373ccacd9112f707a5ff455660114b340ca60e67d4155cb18f18daf3d52beb630c9804c42753003e4ce1932e4`
- 结论：镜像完整，烧录失败与镜像文件无关。

## TF 卡与读卡器（本机实测，Get-Disk/Get-Volume，2026-10-13）

- Disk 1，Realtek PCIE Card Reader（笔记本内置），型号枚举 `SDXC Card`，**1 TB（1,024,005,767,168 字节）**。
- 原始状态：MBR + 单分区 exFAT 挂 D:，仅空的 `LOST+FOUND / MISC / DCIM` 目录（2026-10-06 格式化），无用户数据，确认可抹。
- 疑点：1TB 大容量 microSD 为假卡/扩容卡常见规格，本机未做读写回环验证（脚本被叫停前未跑成）。

## 自研烧录脚本两次失败（本机实测，已弃用）

用 Python 直写 `\\.\PhysicalDrive1` 的自研脚本烧录两次，均中止：

| 次 | 脚本版本 | 结果 |
|---|---|---|
| 1 | Python 文件对象直写 | ~66MB（2.6%）处 `OSError: [Errno 9] Bad file descriptor` |
| 2 | Win32 API 版（WriteFile，锁卷枚举修复 argtypes 后） | 同样 ~66MB（2.6%）处 `WriteFile` 返回失败，`Win32Error=5`（拒绝访问）；且报「已卸载 0 个卷」（未找到属于 Disk 1 的卷） |

**疑点更新（2026-10-13，用户反馈 Rufus 找不到设备后复查）**：先前怀疑「WriteFile 假成功、数据未落卡」**被推翻**——烧录尝试后复查磁盘，卡分区表已从原 MBR/exFAT 变为 **GPT 且无卷**，正是镜像开头的结构，证明第二次烧录的前 ~66MB 真实写入、只是中断。两次同位置确定性失败的原因仍未定位（卡/读卡器在 66MB 附近的写入问题，或 Windows 直写处理），留待标准工具验证。

**Rufus 不可用原因（本机实测）**：该卡经笔记本内置读卡器接入，`Get-Disk` 显示 BusType 为 **SCSI**；Rufus 默认仅列出 USB 总线设备，内置读卡器不在其设备列表中，与卡好坏无关。

**推断（未验证）**：两次同位置（~66MB）确定性失败 + 数据疑似未落卡，指向卡或读卡器写入路径异常（坏块/假卡/Realtek 读卡器对 1TB SDXC 直写兼容性），也可能是 Windows 对该盘直写的重枚举处理，自研脚本无法区分。

## 用户决定（2026-10-13，TF 卡阶段）

直写物理盘的自研工具风险过高，**弃用**，改用标准工具 **Rufus 4.15**（已备 `tools/rufus-4.15.exe`）。已删除：`tools/flash-sd.py`、`tools/verify-sd.py`、`tools/flash-card.bat`、`tools/verify-card.bat`、`tools/烧录SD卡.bat`、`tools/launch-flash.ps1` 及烧录/测试日志。保留只读诊断脚本 `tools/list-disks.ps1`、`tools/scan-usb.ps1`、`tools/scan-lan.ps1`。

## 判读标准（TF 卡阶段遗留，随路线变更暂停）

- **工具变更**：Rufus 因不识别 SCSI 总线的内置读卡器而弃用（2026-10-13 实测设备列表无此卡），曾计划改用 **balenaEtcher 2.1.7 便携版**，**实际未执行即转向 USB 直刷 eMMC**。
- Etcher 一次成功 → 之前失败归因于直写脚本的锁卷/句柄/重枚举处理，卡可用，继续后续 USB 串口配置。
- Etcher 也在中途报写入错误/校验失败 → 基本坐实卡或读卡器在 ~66MB 附近的物理问题，换卡或换读卡器再试。
- TF 卡 ~66MB 写入失败的根因**未定位、留作悬案**；若日后回退 TF 路线，仍需先过这一关。

## USB 直刷 eMMC（2026-10-13 下午起，现行路线 → 已移交专题目录）

- **用户决定**：放弃 TF 卡路线，改 USB 直连 maskrom 线刷 eMMC；「eMMC 封存不动」作废，eMMC 前任系统将被覆盖。
- 现行记录（工具链落位、官方流程、驱动安装坑、下载Boot失败排查、烧录结果回填）统一在 [eMMC 线刷记录](../瑞莎开发板存储线刷/research.md)，本专题不再维护刷机进展。
- **本专题遗留悬案**：TF 卡 ~66MB 确定性写入失败的根因未定位；若日后回退 TF 路线，需先过这一关。
- 烧成 eMMC 后**首次开机前拔掉该 TF 卡**（分区表残缺且 RK3566 启动顺序 TF 优先于 eMMC，插着会抢启动）。
