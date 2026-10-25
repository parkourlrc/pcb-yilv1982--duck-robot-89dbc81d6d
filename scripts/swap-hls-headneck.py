#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 hls_servo_debugger 部署副本的 30/31 头颈名称换成本机映射。

背景：实物确认 30=head_pitch、31=neck_pitch（2026-10-22 用户确认），
而上游/旧部署表和本项目早期记录是 30=neck_pitch、31=head_pitch。
只换 _JOINT_SOURCE 里这两行的关节名，ID 和 home 角都不动（两者 home 都是 0.3491）。

用法（板上）：
    python3 swap-hls-headneck.py [provision.py 路径]
默认路径：/home/radxa/hls_servo_debugger/hls_debugger/provision.py
已换过会提示并退出 0；文件不存在退出 1。
"""

import os
import shutil
import sys
import time

DEFAULT = "/home/radxa/hls_servo_debugger/hls_debugger/provision.py"

OLD = ('("neck_pitch", 30, "头颈", 0.3491),', '("head_pitch", 31, "头颈", 0.3491),')
NEW = ('("head_pitch", 30, "头颈", 0.3491),', '("neck_pitch", 31, "头颈", 0.3491),')


def main(path):
    if not os.path.isfile(path):
        print(f"找不到 {path}")
        return 1
    with open(path, "rb") as f:
        raw = f.read()
    nl = b"\r\n" if b"\r\n" in raw else b"\n"
    text = raw.decode("utf-8").replace("\r\n", "\n")
    if NEW[0] in text and NEW[1] in text:
        print("已经是 30=head_pitch、31=neck_pitch，未改。")
        return 0
    if OLD[0] not in text or OLD[1] not in text:
        print("没找到预期的 30/31 两行，可能版本不同，未改。")
        return 2
    backup = path + time.strftime(".bak-%Y%m%d-%H%M%S")
    shutil.copy2(path, backup)
    text = text.replace(OLD[0], NEW[0]).replace(OLD[1], NEW[1])
    with open(path, "wb") as f:
        f.write(text.replace("\n", nl.decode()).encode("utf-8"))
    print(f"已改为 30=head_pitch、31=neck_pitch；备份 {backup}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else DEFAULT))
