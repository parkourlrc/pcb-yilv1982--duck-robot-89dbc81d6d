#!/usr/bin/env python3
"""ID 200 闪断取证：独占串口，只发 PING/READ/SYNC_READ，逐块保存原始回包。

先暂停 servo-web；stdout 为 JSONL，保留 UTC 时间与发送后时差。
每个请求后持续监听 250 ms，包括成功应答之后，以发现晚答、重复和异 ID 帧。
不写寄存器、不复位、不改变扭矩或目标。运行结束由外部脚本恢复服务。
"""

import collections
import datetime
import json
import os
import struct
import sys
import time

import serial


def emit(obj):
    print(json.dumps(obj, ensure_ascii=False), flush=True)


def packet(sid, instruction, params=b""):
    body = bytes([sid, len(params) + 2, instruction]) + params
    return b"\xff\xff" + body + bytes([(~sum(body)) & 255])


def parse(data):
    frames = []
    cursor = 0
    while cursor + 4 <= len(data):
        start = data.find(b"\xff\xff", cursor)
        if start < 0 or start + 4 > len(data):
            break
        length = data[start + 3]
        end = start + 4 + length
        if length < 2:
            cursor = start + 1
            continue
        if end > len(data):
            break
        raw = data[start:end]
        good = (sum(raw[2:]) & 255) == 255
        frame = {"offset": start, "end": end, "id": raw[2],
                 "status": raw[4], "checksum_ok": good,
                 "params": raw[5:-1].hex(), "raw": raw.hex()}
        frames.append(frame)
        cursor = end if good else start + 1
    return frames


def capture(ser, label, tx=None, expect=(), nbytes=None, window=0.25):
    stamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    t0 = time.monotonic()
    if tx:
        ser.write(tx)
        ser.flush()
    chunks = []
    raw = bytearray()
    while time.monotonic() - t0 < window:
        chunk = ser.read(max(ser.in_waiting, 1))
        if chunk:
            raw.extend(chunk)
            chunks.append({"ms": round((time.monotonic() - t0) * 1000, 3),
                           "hex": chunk.hex(), "end": len(raw)})
    frames = parse(bytes(raw))
    for frame in frames:
        frame["complete_ms"] = next(c["ms"] for c in chunks if c["end"] >= frame["end"])
        params = bytes.fromhex(frame["params"])
        if frame["id"] == 200 and len(params) == 15 and frame["checksum_ok"]:
            frame["telemetry"] = {"counter": params[12], "flags": params[13],
                                  "gyro_raw": struct.unpack_from("<3h", params),
                                  "quat_xyz": struct.unpack_from("<3e", params, 6)}
    valid = [f for f in frames if f["checksum_ok"] and f["id"] in expect
             and (nbytes is None or len(bytes.fromhex(f["params"])) == nbytes)]
    record = {"kind": "capture", "utc": stamp, "label": label,
              "tx": tx.hex() if tx else None, "expected_ids": list(expect),
              "window_ms": window * 1000, "chunks": chunks, "frames": frames,
              "received_ids": [f["id"] for f in valid], "raw": raw.hex()}
    emit(record)
    return record


def main():
    fast_only = len(sys.argv) == 2 and sys.argv[1] == "--fast-only"
    interleave = len(sys.argv) == 2 and sys.argv[1] == "--interleave"
    if len(sys.argv) > 1 and not (fast_only or interleave):
        raise SystemExit("usage: imu200-raw-capture.py [--fast-only|--interleave]")
    if interleave:
        sys.path.insert(0, os.path.expanduser("~/servo-web"))
        import feetech
        ids = (20, 21, 22, 23, 24, 30, 31, 32, 33, 34, 10, 11, 12, 13, 14)
        emit({"kind": "metadata", "read_only": True,
              "note": "部署版解析器读取15颗舵机，等待指定间隔，然后原始捕获单ID200的SYNC_READ。"})
        bus = feetech.FeetechBus("/dev/ttyS2", 1000000)
        try:
            for index, gap in enumerate((0, 0.005, 0.02, 0)):
                replies = servo_complete = 0
                label = f"interleave_{index}_gap{int(gap * 1000)}ms"
                for _ in range(50):
                    bus.ser.timeout = 0.02
                    before = dict(bus.stats)
                    servo = bus.sync_read(ids, 56, 15)
                    present = [sid for sid, value in servo.items() if value is not None]
                    servo_complete += len(present) == len(ids)
                    emit({"kind": "servo_control", "label": label, "received_ids": present,
                          "stats_delta": {key: bus.stats[key] - before[key] for key in before}})
                    if gap:
                        time.sleep(gap)
                    bus.ser.timeout = 0.001
                    result = capture(bus.ser, label, packet(254, 130, bytes([56, 15, 200])),
                                     (200,), 15, window=0.1)
                    replies += bool(result["received_ids"])
                emit({"kind": "summary", "label": label, "requests": 50,
                      "imu_replies": replies, "servos_all15": servo_complete})
        finally:
            bus.close()
        return
    if fast_only:
        emit({"kind": "metadata", "port": "/dev/ttyS2", "baud": 1000000,
              "read_only": True, "window_ms": 100, "rate": "approximately 10 Hz",
              "note": "每种指令 100 次，原始监听 100 ms；无重试。"})
        with serial.Serial("/dev/ttyS2", 1000000, timeout=0.001, write_timeout=0.1) as ser:
            capture(ser, "passive_before", window=1.0)
            for label, tx, nbytes in (
                ("ping_200_10hz", packet(200, 1), 0),
                ("read15_200_10hz", packet(200, 2, bytes([56, 15])), 15),
                ("sync_200_10hz", packet(254, 130, bytes([56, 15, 200])), 15),
            ):
                rows = [capture(ser, label, tx, (200,), nbytes, window=0.1) for _ in range(100)]
                valid = [f for r in rows for f in r["frames"] if f["checksum_ok"] and f["id"] == 200]
                emit({"kind": "summary", "label": label, "requests": len(rows),
                      "any_reply": sum(bool(r["received_ids"]) for r in rows),
                      "empty_rx": sum(not r["raw"] for r in rows),
                      "after_20ms": sum(f["complete_ms"] > 20 for f in valid),
                      "after_60ms": sum(f["complete_ms"] > 60 for f in valid)})
            capture(ser, "passive_after", window=1.0)
        return
    emit({"kind": "metadata", "port": "/dev/ttyS2", "baud": 1000000,
          "read_only": True, "instructions": [1, 2, 130], "window_ms": 250,
          "note": "仅主机串口捕获，不能替代 DATA/V-G 示波器波形。"})
    results = []
    with serial.Serial("/dev/ttyS2", 1000000, timeout=0.001, write_timeout=0.1) as ser:
        capture(ser, "passive_before", window=1.0)
        for _ in range(10):
            results.append(capture(ser, "ping_200", packet(200, 1), (200,), 0))
        for _ in range(20):
            for sid in (200, 20, 10):
                results.append(capture(ser, f"read15_{sid}", packet(sid, 2, bytes([56, 15])), (sid,), 15))
        for _ in range(15):
            results.append(capture(ser, "sync_200", packet(254, 130, bytes([56, 15, 200])), (200,), 15))
        for _ in range(5):
            results.append(capture(ser, "identity_200", packet(200, 2, bytes([180, 16])), (200,), 16))
        ids = (20, 21, 22, 23, 24, 30, 31, 32, 33, 34, 10, 11, 12, 13, 14)
        for _ in range(5):
            results.append(capture(ser, "sync_servos", packet(254, 130, bytes([56, 15]) + bytes(ids)), ids, 15))
        capture(ser, "passive_after", window=1.0)
    grouped = collections.defaultdict(list)
    for record in results:
        grouped[record["label"]].append(record)
    for label, rows in grouped.items():
        valid = [f for r in rows for f in r["frames"] if f["checksum_ok"]
                 and f["id"] in r["received_ids"]]
        emit({"kind": "summary", "label": label, "requests": len(rows),
              "any_reply": sum(bool(r["received_ids"]) for r in rows),
              "all_ids_reply": sum(set(r["received_ids"]) == set(r["expected_ids"]) for r in rows),
              "valid_frames": len(valid),
              "after_20ms": sum(f["complete_ms"] > 20 for f in valid),
              "after_60ms": sum(f["complete_ms"] > 60 for f in valid),
              "bad_checksum_frames": sum(not f["checksum_ok"] for r in rows for f in r["frames"]),
              "empty_rx": sum(not r["raw"] for r in rows)})


if __name__ == "__main__":
    main()
