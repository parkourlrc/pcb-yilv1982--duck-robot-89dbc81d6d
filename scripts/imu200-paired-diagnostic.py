#!/usr/bin/env python3
"""现有接线下交错比较 IMU 单读/各舵机组前置读取；只发 PING/READ/SYNC_READ。

在 Radxa、servo-web 停止后运行，stdout 为 JSONL。复用部署版 feetech，
包装串口保存解析器真正读到的所有字节，并在事务结束后收集到本周期结束。
不会写设备寄存器、改扭矩、改串口驱动配置或重启设备。
"""

import array
import collections
import datetime
import fcntl
import json
import os
import random
import sys
import time

sys.path.insert(0, os.path.expanduser("~/servo-web"))
import feetech

ALL = [20, 21, 22, 23, 24, 30, 31, 32, 33, 34, 10, 11, 12, 13, 14]


def emit(obj):
    print(json.dumps(obj, ensure_ascii=False), flush=True)


class RecordedSerial:
    def __init__(self, serial):
        self.actual = serial
        self.events = []
        self.start = time.monotonic()

    def __getattr__(self, key):
        return getattr(self.actual, key)

    def event(self, kind, **fields):
        self.events.append({"kind": kind, "ms": round((time.monotonic() - self.start) * 1000, 3), **fields})

    def write(self, data):
        self.event("tx", hex=bytes(data).hex())
        return self.actual.write(data)

    def read(self, size=1):
        value = self.actual.read(size)
        self.event("rx" if value else "empty", wanted=size, hex=bytes(value).hex())
        return value

    def reset_input_buffer(self):
        self.event("reset_input", pending=self.actual.in_waiting)
        return self.actual.reset_input_buffer()

    def counters(self):
        try:
            values = array.array("i", [0] * 20)
            fcntl.ioctl(self.actual.fileno(), 0x545D, values, True)
            names = ["cts", "dsr", "rng", "dcd", "rx", "tx", "frame", "overrun", "parity", "brk", "buf_overrun"]
            return dict(zip(names, values))
        except OSError as exc:
            return {"unsupported": str(exc), "errno": exc.errno}


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    if not 1 <= n <= 150:
        raise SystemExit("cycles per condition must be 1..150")
    bus = feetech.FeetechBus("/dev/ttyS2", 1000000, timeout=0.02)
    serial = RecordedSerial(bus.ser)
    bus.ser = serial
    rng = random.Random(20261025)
    groups = {"solo": [], "all15": ALL, "left5": ALL[:5], "head5": ALL[5:10], "right5": ALL[10:], "silent15": list(range(100,115))}
    totals = collections.defaultdict(collections.Counter)
    emit({"kind": "metadata", "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
          "groups": groups, "cycles_per_condition": n, "period_ms": 100,
          "method": "每轮随机排列全部条件；使用部署版解帧，记录RX原始字节，失败后仍监听至本周期100ms。",
          "read_only": True, "uart_before": serial.counters()})
    try:
        for round_no in range(n):
            conditions = list(groups)
            rng.shuffle(conditions)
            for condition in conditions:
                ids = groups[condition]
                serial.events = []
                serial.start = time.monotonic()
                stamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
                before = dict(bus.stats)
                pre = {}
                if condition == "silent15":
                    # 地址100..114不是当前装机ID。合法只读帧，预期没有节点应答。
                    bus._send(254, feetech.SYNC_READ, bytes([56,15]) + bytes(ids))
                    time.sleep(0.005)
                    if serial.in_waiting:
                        serial.event("unexpected_silent_response", hex=serial.actual.read(serial.in_waiting).hex())
                elif ids:
                    pre = bus.sync_read(ids, 56, 15)
                pre_ms = (time.monotonic() - serial.start) * 1000
                imu_event_start = len(serial.events)
                result = bus.sync_read([200], 56, 15).get(200)
                returned_ms = (time.monotonic() - serial.start) * 1000
                # 保存解析器返回后才到达的数据；只读取已缓存字节，不占据下一个请求周期。
                deadline = serial.start + 0.1
                extras = bytearray()
                while time.monotonic() < deadline:
                    count = serial.in_waiting
                    if count:
                        value = serial.actual.read(count)
                        extras.extend(value)
                        serial.event("after_return", hex=value.hex())
                    time.sleep(0.0005)
                delta = {key: bus.stats[key] - before[key] for key in before}
                row = {"kind": "cycle", "utc": stamp, "round": round_no, "condition": condition,
                       "pre_ids": [sid for sid, value in pre.items() if value is not None],
                       "pre_ms": round(pre_ms, 3), "imu_event_start": imu_event_start,
                       "imu_ok": result is not None, "imu_return_ms": round(returned_ms, 3),
                       "imu_params": result[1].hex() if result is not None else None,
                       "extra_hex": extras.hex(), "stats_delta": delta, "events": serial.events}
                emit(row)
                totals[condition]["requests"] += 1
                totals[condition]["imu_ok"] += result is not None
                totals[condition]["pre_all"] += len(pre) > 0 and all(value is not None for value in pre.values())
                totals[condition]["extra_bytes"] += len(extras)
                for key in ("bad_id", "bad_checksum", "timeout"):
                    totals[condition][key] += delta[key]
        for condition, counts in totals.items():
            emit({"kind": "summary", "condition": condition, **dict(counts)})
        emit({"kind": "uart_after", "value": serial.counters()})
    finally:
        bus.close()


if __name__ == "__main__":
    main()
