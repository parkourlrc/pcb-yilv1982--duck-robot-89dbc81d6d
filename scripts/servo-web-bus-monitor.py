#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""servo-web 总线丢帧监测（2026-10-24）：伪装页面客户端触发轮询，采样统计。

用法（板上）：python3 servo-web-bus-monitor.py [秒数，默认 240]
输出：每 6s 一行 (时间 tx rx_ok timeout bad_checksum bad_id) 与结束增量；日志新增告警。
"""
import asyncio
import json
import sys
import time
import urllib.request

import websockets

DUR = int(sys.argv[1]) if len(sys.argv) > 1 else 240


def stats():
    with urllib.request.urlopen("http://127.0.0.1:8080/api/info", timeout=5) as r:
        d = json.load(r)
    s = d["stats"]
    return time.strftime("%H:%M:%S"), s["tx"], s["rx_ok"], s["timeout"], s["bad_checksum"], s["bad_id"]


async def main():
    t0, *s0 = stats()
    print("start", t0, s0)
    async with websockets.connect("ws://127.0.0.1:8080/ws", max_queue=1) as ws:
        deadline = time.monotonic() + DUR
        while time.monotonic() < deadline:
            sample_at = time.monotonic() + 5   # 每 5 秒采样一次；窗口内只排空消息
            while True:
                remain = sample_at - time.monotonic()
                if remain <= 0:
                    break
                try:
                    await asyncio.wait_for(ws.recv(), timeout=remain)
                except asyncio.TimeoutError:
                    break
            print(*stats(), flush=True)
    t1, *s1 = stats()
    print("end", t1, s1)
    print("delta tx=%d rx=%d timeout=%d bad_ck=%d bad_id=%d over %ds"
          % (s1[0] - s0[0], s1[1] - s0[1], s1[2] - s0[2], s1[3] - s0[3], s1[4] - s0[4], DUR))


asyncio.run(main())
