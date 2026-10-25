#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 hls_servo_debugger 部署副本的 30/31 头颈名称换回上游 microduck_feetech。

背景：2026-10-22 用 swap-hls-headneck.py 按本机实物把部署副本改为
30=head_pitch、31=neck_pitch（该脚本带单向幂等保护，检测到即拒绝再改）。
2026-10-24 用户指示 ID 对齐方案 B 飞特版，舵机 EEPROM 已改回
30=neck_pitch、31=head_pitch，本脚本把部署副本表同步换回（两行精确替换，
含 ID 字段互不相同，顺序替换安全）。参考库不动。

用法（板上）：python3 hls-headneck-revert-upstream.py [provision.py 路径]
默认路径：/home/radxa/hls_servo_debugger/hls_debugger/provision.py
"""

import shutil
import sys
import time

DEFAULT = "/home/radxa/hls_servo_debugger/hls_debugger/provision.py"

PAIRS = [
    ('("head_pitch", 30, "头颈", 0.3491),', '("neck_pitch", 30, "头颈", 0.3491),'),
    ('("neck_pitch", 31, "头颈", 0.3491),', '("head_pitch", 31, "头颈", 0.3491),'),
]


def main(path):
    text = open(path, encoding="utf-8").read()
    if PAIRS[0][1] in text and PAIRS[1][1] in text:
        print("已是上游 30=neck_pitch、31=head_pitch，未改。")
        return 0
    backup = path + time.strftime(".bak-%Y%m%d-%H%M%S")
    for old, new in PAIRS:
        n = text.count(old)
        if n != 1:
            print(f"匹配 {n} 处（预期 1）：{old}")
            return 2
    shutil.copy2(path, backup)
    for old, new in PAIRS:
        text = text.replace(old, new)
    open(path, "w", encoding="utf-8").write(text)
    print(f"已换回上游 30=neck_pitch、31=head_pitch；备份 {backup}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else DEFAULT))
