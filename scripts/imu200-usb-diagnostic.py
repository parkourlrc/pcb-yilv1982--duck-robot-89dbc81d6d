#!/usr/bin/env python3
"""电脑侧 IMU 只读捕获：随机交错 PING/READ/SYNC，保留完整接收窗口。

仅发读指令；不写寄存器、不复位、不切换波特率、不控制舵机。
运行前由操作者确认适配器模式、外部供电、针序及串口独占。
"""

import argparse
import collections
import datetime
import importlib.util
import json
from pathlib import Path
import random
import time

import serial

spec = importlib.util.spec_from_file_location(
    "imu_raw", Path(__file__).with_name("imu200-raw-capture.py")
)
raw_helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(raw_helper)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--port", required=True)
    ap.add_argument("--rounds", type=int, default=60)
    ap.add_argument("--window-ms", type=float, default=100)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    if not 1 <= args.rounds <= 300 or not 10 <= args.window_ms <= 1000:
        ap.error("rounds=1..300; window-ms=10..1000")

    rng = random.Random(20261025)
    modes = [
        ("ping", raw_helper.packet(200, 1), 0),
        ("read15", raw_helper.packet(200, 2, bytes([56, 15])), 15),
        ("sync15", raw_helper.packet(254, 130, bytes([56, 15, 200])), 15),
    ]
    stats = collections.defaultdict(collections.Counter)
    with args.output.open("x", encoding="utf-8") as log:
        def emit(row):
            log.write(json.dumps(row, ensure_ascii=True) + "\n")
            log.flush()
            if row["kind"] in ("metadata", "summary", "finished"):
                print(json.dumps(row, ensure_ascii=True), flush=True)

        def capture(ser, label, tx, width, window):
            start = time.monotonic()
            utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
            written = ser.write(tx) if tx else 0
            if tx:
                ser.flush()
            data = bytearray()
            chunks = []
            while time.monotonic() - start < window:
                chunk = ser.read(max(1, ser.in_waiting))
                if chunk:
                    data.extend(chunk)
                    chunks.append({"ms": round((time.monotonic()-start)*1000, 3),
                                   "hex": chunk.hex(), "end": len(data)})
            frames = raw_helper.parse(bytes(data))
            for f in frames:
                f["complete_ms"] = next(c["ms"] for c in chunks if c["end"] >= f["end"])
                f["matches_tx"] = bool(tx and f["raw"] == tx.hex())
            valid = [f for f in frames if f["checksum_ok"] and f["id"] == 200
                     and f["status"] == 0 and len(bytes.fromhex(f["params"])) == width]
            emit({"kind": "capture", "utc": utc, "label": label,
                  "tx": tx.hex(), "written": written, "window_ms": window*1000,
                  "raw": data.hex(), "chunks": chunks, "frames": frames,
                  "ok": bool(valid)})
            return data, frames, valid

        emit({"kind": "metadata", "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "port": args.port, "baud": 1000000, "read_only": True,
              "rounds": args.rounds, "window_ms": args.window_ms,
              "random_seed": 20261025, "reset_input_buffer": False,
              "method": "Each round randomizes PING/READ15/SYNC15; full receive window, no retries."})
        with serial.Serial(args.port, 1000000, timeout=.001, write_timeout=.1) as ser:
            capture(ser, "passive_before", b"", -1, .3)
            for round_no in range(args.rounds):
                order = modes.copy()
                rng.shuffle(order)
                for label, tx, width in order:
                    data, frames, valid = capture(ser, label, tx, width, args.window_ms/1000)
                    stats[label]["requests"] += 1
                    stats[label]["ok"] += bool(valid)
                    stats[label]["empty"] += not data
                    stats[label]["bad_checksum_frames"] += sum(not f["checksum_ok"] for f in frames)
                    stats[label]["echo_frames"] += sum(f["matches_tx"] for f in frames)
                    stats[label]["after20ms"] += sum(f["complete_ms"] > 20 for f in valid)
            capture(ser, "identity", raw_helper.packet(200, 2, bytes([180, 16])), 16, .25)
            capture(ser, "passive_after", b"", -1, .3)
        for label, counts in stats.items():
            emit({"kind": "summary", "label": label, **counts})
        emit({"kind": "finished", "serial_closed": True})


if __name__ == "__main__":
    main()
