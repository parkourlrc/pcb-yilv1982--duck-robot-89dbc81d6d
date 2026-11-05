#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""三组对照实验脚本（2026-10-27 深夜系列，固化存档）。

板上实际执行时为 ssh heredoc 内联（各轮输出摘要见
docs/references/舵机网页工具惯性显示/research.md 续 11 的表格；本文件为同逻辑固化版，
含 IMU 在线探测行）。口径：50Hz（20ms tick）、地址 56 长 15、1 Mbps；须停 servo-web 独占。

用法（板上）：systemctl --user stop duck-servo-web && python3 imu-triple-exp-20261027.py [秒数，默认 30]
"""
import sys
import time
from collections import Counter

import feetech

SECONDS = int(sys.argv[1]) if len(sys.argv) > 1 else 30
bus = feetech.FeetechBus("/dev/ttyS2", 1_000_000, timeout=0.02)
JOINT = [10, 11, 12, 13, 14, 20, 21, 22, 23, 24, 30, 31, 32, 33, 34]
online = [sid for sid in JOINT if bus.ping(sid) is not None]
imu = bus.ping(200) is not None
print(f"在线: {online} 共{len(online)}颗；IMU(200) 探测: {'应答' if imu else '无应答'}", flush=True)


def burst(ids, seconds, label):
    ok = {i: 0 for i in ids}
    n = 0
    errs = Counter()
    dts = []
    cnts = []
    t_end = time.monotonic() + seconds
    next_t = time.monotonic()
    while time.monotonic() < t_end:
        s0 = dict(bus.stats)
        t0 = time.monotonic()
        r = bus.sync_read(ids, 56, 15)
        dts.append((time.monotonic() - t0) * 1000)
        n += 1
        for k in ("timeout", "bad_checksum", "bad_id"):
            errs[k] += bus.stats[k] - s0[k]
        for i in ids:
            if r.get(i):
                ok[i] += 1
                if i == 200:
                    cnts.append(r[200][1][12])
        next_t += 0.02
        gap = next_t - time.monotonic()
        if gap > 0:
            time.sleep(gap)
        else:
            next_t = time.monotonic()
    print(f"--- {label}: ticks={n} 频率={n/seconds:.1f}Hz", flush=True)
    print(f"  批耗时 min={min(dts):.1f} avg={sum(dts)/n:.1f} max={max(dts):.1f}；错误 {dict(errs)}", flush=True)
    if 200 in ids:
        diffs = Counter((cnts[j+1] - cnts[j]) % 256 for j in range(len(cnts) - 1))
        print(f"  IMU 成功率={ok[200]/n:.4f}（{ok[200]}/{n}）；计数差分 "
              f"{dict(sorted(diffs.items(), key=lambda x: -x[1])[:6])}", flush=True)
    sv = {i: ok[i] / n for i in ids if i != 200}
    if sv:
        print(f"  舵机成功率 min={min(sv.values()):.4f} max={max(sv.values()):.4f}"
              f"（各颗一致: {len(set(sv.values())) == 1}）", flush=True)


burst(online, SECONDS, f"测试1 纯舵机{len(online)}颗")
burst([200], SECONDS, "测试2 IMU 单发")
burst([200] + online, SECONDS, f"测试3 IMU+{len(online)}颗混读")
bus.close()
