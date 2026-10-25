#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""只读比较 ID 200 对 PING、READ 和单 ID SYNC_READ 的响应率。

在 Radxa 上运行；应先停止 servo-web 释放 /dev/ttyS2。该脚本只发只读指令，
每种模式按 10 Hz 最长运行指定秒数（默认 30 秒），用部署版 feetech.py 解帧。
"""

import statistics
import os
import sys
import time

sys.path.insert(0, os.path.expanduser("~/servo-web"))
import feetech

PORT = "/dev/ttyS2"
BAUD = 1_000_000
IMU_ID = 200
ADDR = 56
LENGTH = 15
PERIOD = 0.1


def run(bus, name, operation, seconds):
    samples = []
    n = replies = status_errors = 0
    before = dict(bus.stats)
    start = time.monotonic()
    deadline = start + seconds
    next_tick = start
    while next_tick < deadline:
        delay = next_tick - time.monotonic()
        if delay > 0:
            time.sleep(delay)
        t0 = time.monotonic()
        n += 1
        try:
            result = operation()
        except feetech.BusError:
            result = None
        dt_ms = (time.monotonic() - t0) * 1000
        if result is not None:
            replies += 1
            status = result[0] if isinstance(result, tuple) else result
            if status != 0:
                status_errors += 1
            samples.append(dt_ms)
        next_tick += PERIOD
        if next_tick < time.monotonic():
            next_tick = time.monotonic() + PERIOD

    elapsed = time.monotonic() - start
    after = bus.stats
    if samples:
        ordered = sorted(samples)
        p95 = ordered[int(0.95 * (len(ordered) - 1))]
        latency = (f"p50={statistics.median(samples):.2f}ms "
                   f"p95={p95:.2f}ms max={max(samples):.2f}ms")
    else:
        latency = "no successful replies"
    print(f"{name}: replies={replies}/{n} ({100 * replies / max(n, 1):.1f}%), "
          f"rate={n / elapsed:.1f} req/s, {latency}, "
          f"nonzero_status={status_errors}, "
          f"timeout=+{after['timeout'] - before['timeout']}, "
          f"bad_checksum=+{after['bad_checksum'] - before['bad_checksum']}, "
          f"bad_id=+{after['bad_id'] - before['bad_id']}", flush=True)


def main():
    seconds = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    if not 1 <= seconds <= 300:
        raise SystemExit("seconds must be 1..300")
    bus = feetech.FeetechBus(PORT, BAUD, timeout=0.02)
    try:
        run(bus, "PING", lambda: bus.ping(IMU_ID), seconds)
        run(bus, "READ(56,15)", lambda: bus.read(IMU_ID, ADDR, LENGTH), seconds)
        run(bus, "SYNC_READ([200],56,15)",
            lambda: bus.sync_read([IMU_ID], ADDR, LENGTH).get(IMU_ID), seconds)
    finally:
        bus.close()


if __name__ == "__main__":
    main()
