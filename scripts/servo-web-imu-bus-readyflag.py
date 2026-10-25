#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修复 bus 模式 IMU 面板永远「数据无效」的上游 bug（2026-10-25）。

页面的 validPacket()（imu_attitude.js）要求 imu 帧 `ready===1 && configured===1`——
这两个字段是 SWD/JLink 桥的概念；`--imu-bus` 的帧从未填过（empty_frame 恒 0），
导致总线模式下面板永远显示「数据无效」，即使四元数完全正常。
本补丁给部署副本 imu_bus.py 的 _frame() 补上两字段（总线桥永远就绪）。
用法：python3 servo-web-imu-bus-readyflag.py ~/servo-web --dry-run|--apply
"""

import argparse
import os
import shutil
import sys
import time


class PatchError(Exception):
    pass


OLD = '''    def _frame(self, status, message, **extra):
        frame = empty_frame("live", status, message)
        frame.update(backend="bus", probe_name="舵机总线 ID 200", **extra)
        return frame'''

NEW = '''    def _frame(self, status, message, **extra):
        frame = empty_frame("live", status, message)
        frame.update(backend="bus", probe_name="舵机总线 ID 200", **extra)
        # 2026-10-25 本机补丁：页面 validPacket 要求 ready==1 且 configured==1（SWD/JLink
        # 桥的字段），总线模式从未填过 → 面板永远「数据无效」。总线桥本身永远就绪，补上。
        frame["ready"] = 1
        frame["configured"] = 1
        return frame'''


def read(path):
    with open(path, "rb") as f:
        return f.read().decode("utf-8").replace("\r\n", "\n")


def write(path, text):
    with open(path, "rb") as f:
        raw = f.read()
    nl = "\r\n" if b"\r\n" in raw else "\n"
    with open(path, "wb") as f:
        f.write(text.replace("\n", nl).encode("utf-8"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    path = os.path.join(os.path.abspath(os.path.expanduser(args.dir)), "imu_bus.py")
    text = read(path)
    if NEW in text:
        print("  = 已打过")
        return 0
    n = text.count(OLD)
    if n != 1:
        raise PatchError(f"匹配 {n} 处（预期 1）")
    if args.dry_run:
        print("  * dry-run：匹配唯一（未写入）")
        return 0
    backup = path + time.strftime(".bak-%Y%m%d-%H%M%S")
    shutil.copy2(path, backup)
    write(path, text.replace(OLD, NEW))
    print(f"已写入；备份 {backup}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except PatchError as e:
        print(f"错误：{e}", file=sys.stderr)
        sys.exit(2)
