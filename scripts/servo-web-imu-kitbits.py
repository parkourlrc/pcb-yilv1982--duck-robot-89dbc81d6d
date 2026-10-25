#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 servo-web 部署副本 imu_bus.py 的 IMU 状态位判据改为社区 kit v1 语义。

背景（2026-10-24 实测定案）：本机 IMU 板②（jyg9，飞特协议）每帧 flags=0x81 且四元数
有效、陀螺/加速度真实（scripts/imu200-diag.py 干净探测），固件状态位是社区 kit
imu_to_dxl v1 语义（host/bus.py TELEM_FLAG_BITS：bit0=sflp_valid 四元数有效、
bit1=cnt_wrap 计数回绕、bit2=gyro_sat、bit3=sensor_err、bit4=simulated、bit7=fusion_ok）。
而 servo-web 的 imu_bus.py 沿用 duck-control 旧语义（bit0=融合未就绪、bit1=通信失败、
bit2=自检失败、bit3=读太慢），两套 bit0/bit1 含义相反：本板的有效帧全部被判
「融合还没出数」（面板永远不出数），计数回绕（100 Hz 采样每 2.56 s 一次）被当
「通信失败」刷错误日志。

本脚本只改传入部署目录的 imu_bus.py（先备份），参考库不动。判据改为：
- bit3（sensor_err）→ error 传感器探测失败；
- bit0 未置位或四元数全 0 → stale 融合未出数；
- bit1/bit2 不再当错误（回绕/饱和为正常事件）；
- 假小板（--fake 演示）同步改为 kit 语义的 flags。

用法：
    python3 servo-web-imu-kitbits.py ~/servo-web --dry-run
    python3 servo-web-imu-kitbits.py ~/servo-web --apply
"""

import argparse
import os
import shutil
import sys
import time


class PatchError(Exception):
    pass


REPLACES = [
    # 1) 常量表
    ("""BIT_FUSION_NOT_READY = 0x01
BIT_IMU_COMM_FAIL = 0x02
BIT_SELF_TEST_FAIL = 0x04
BIT_READER_TOO_SLOW = 0x08
SLOW_READER_HZ = 30      # 固件 BIT3 = 两次读之间刷新 > 4 次（120 Hz 采样）≈ 读得比 30 Hz 慢""",
     """# 2026-10-24 本机补丁：板②固件状态位为社区 kit v1 语义（host/bus.py TELEM_FLAG_BITS）
# ——bit0=四元数有效、bit1=计数回绕、bit2=陀螺饱和、bit3=传感器探测失败、bit4=模拟器、
# bit7=融合运行中。上游 duck-control 旧判据（bit0=未就绪、bit1=通信失败）与本板相反，
# 曾把有效帧全判“融合没出数”、把计数回绕当“通信失败”。
BIT_SFLP_VALID = 0x01
BIT_CNT_WRAP = 0x02
BIT_SENSOR_ERR = 0x08
BIT_FUSION_OK = 0x80"""),

    # 2) errors 汇总
    ('''"errors": {"imu": d["bits"] & (BIT_IMU_COMM_FAIL | BIT_SELF_TEST_FAIL), "spi": None,''',
     '''"errors": {"imu": d["bits"] & BIT_SENSOR_ERR, "spi": None,'''),

    # 3) 判位分支
    ('''        elif d["bits"] & BIT_SELF_TEST_FAIL:
            frame = self._frame("error", "小板报告 IMU 自检失败（BIT2，WHO_AM_I 不对）：检查 IMU 芯片焊接。", **extra)
        elif d["bits"] & BIT_IMU_COMM_FAIL:
            frame = self._frame("error", "小板报告跟 IMU 芯片通信失败（BIT1：SPI/复位/配置/FIFO/数据过期）。", **extra)
        elif not any(d["quat_fp16"]) or d["bits"] & BIT_FUSION_NOT_READY:
            frame = self._frame("stale", "IMU 融合还没出数（四元数全 0 / BIT0），刚上电约 0.5 秒内正常。", **extra)''',
     '''        elif d["bits"] & BIT_SENSOR_ERR:
            frame = self._frame("error", "小板报告传感器探测失败（BIT3，kit 语义 sensor_err）：检查小板与 IMU 芯片。", **extra)
        elif not (d["bits"] & BIT_SFLP_VALID) or not any(d["quat_fp16"]):
            frame = self._frame("stale", "IMU 融合还没出数（SFLP_VALID 未置位 / 四元数全 0），刚上电约 0.5 秒内正常。", **extra)'''),

    # 4) live 分支的“读太慢”提示：kit 语义 bit3=传感器错误已按 error 处理，这里不再适用
    ('''                slow = ("；BIT3：两次读之间块刷新了 4 次以上，读得太慢"
                        if d["bits"] & BIT_READER_TOO_SLOW
                        and (self.poll_hz is None or self.poll_hz >= SLOW_READER_HZ) else "")''',
     '''                slow = ""   # kit 语义 bit3=传感器错误已在上面按 error 返回；旧“读太慢”提示不适用本板'''),

    # 5) 假小板（--fake 演示）flags 同步为 kit 语义
    ('''            return bytes(12) + bytes([n & 0xFF, BIT_FUSION_NOT_READY, 0])''',
     '''            return bytes(12) + bytes([n & 0xFF, 0, 0])   # kit 语义：未就绪=bit0 不置位'''),
    ('''        return (struct.pack("<3h", *gyro) + struct.pack("<3e", *quat)
                + bytes([n & 0xFF, 0, 0]))''',
     '''        return (struct.pack("<3h", *gyro) + struct.pack("<3e", *quat)
                + bytes([n & 0xFF, BIT_SFLP_VALID | BIT_FUSION_OK, 0]))'''),
]

OLD_IDENTS = ("BIT_FUSION_NOT_READY", "BIT_IMU_COMM_FAIL", "BIT_SELF_TEST_FAIL",
              "BIT_READER_TOO_SLOW", "SLOW_READER_HZ")


def read(path):
    with open(path, "rb") as f:
        raw = f.read()
    return raw.decode("utf-8").replace("\r\n", "\n")


def write(path, text):
    with open(path, "rb") as f:
        raw = f.read()
    nl = "\r\n" if b"\r\n" in raw else "\n"
    with open(path, "wb") as f:
        f.write(text.replace("\n", nl).encode("utf-8"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir", help="servo-web 部署目录，例如 ~/servo-web")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    path = os.path.join(os.path.abspath(os.path.expanduser(args.dir)), "imu_bus.py")
    if not os.path.isfile(path):
        raise SystemExit(f"缺少 {path}")
    text = read(path)
    changed = 0
    for old, new in REPLACES:
        if new in text and old not in text:
            print(f"  = 该段已是 kit 语义：{old.splitlines()[0][:40]}…")
            continue
        n = text.count(old)
        if n != 1:
            raise PatchError(f"匹配 {n} 处（预期 1）：{old.splitlines()[0][:60]}…")
        text = text.replace(old, new)
        changed += 1
        print(f"  * 已替换第 {changed} 段")
    leftover = [i for i in OLD_IDENTS if i in text]
    if leftover:
        raise PatchError(f"仍残留旧标识 {leftover}，中止未写入")
    if args.dry_run:
        print("完成（dry-run，未写入）")
        return 0
    backup = path + time.strftime(".bak-%Y%m%d-%H%M%S")
    shutil.copy2(path, backup)
    write(path, text)
    print(f"已写入；备份 {backup}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except PatchError as e:
        print(f"错误：{e}", file=sys.stderr)
        sys.exit(2)
