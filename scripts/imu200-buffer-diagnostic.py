#!/usr/bin/env python3
"""仅只读请求，交错比较 TCIFLUSH、等待和 tcdrain 对 ID200 响应的影响。

不修改部署程序、设备寄存器或串口驱动配置；停服独占后运行，由外部恢复服务。
所有条件使用相同原始接收器，保存请求及整个100ms窗口内的字节。
"""

import array
import collections
import datetime
import fcntl
import json
import importlib.util
from pathlib import Path
import random
import sys
import time

import serial

helper_path = Path(__file__).with_name("imu200-raw-capture.py")
if not helper_path.exists():
    helper_path = Path(__file__).with_name("imu200_raw_helper.py")
helper_spec = importlib.util.spec_from_file_location("imu200_raw_helper", helper_path)
helper = importlib.util.module_from_spec(helper_spec)
helper_spec.loader.exec_module(helper)
packet, parse = helper.packet, helper.parse


def emit(value):
    print(json.dumps(value, ensure_ascii=False), flush=True)


def counter(ser):
    try:
        values = array.array("i", [0]*20)
        fcntl.ioctl(ser.fileno(), 0x545D, values, True)
        return list(values)
    except OSError as exc:
        return {"error": str(exc)}


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    if not 1 <= n <= 150:
        raise SystemExit("rounds must be 1..150")
    modes = {
        "no_clear_no_drain": (False, 0, False),
        "clear_no_drain": (True, 0, False),
        "no_clear_drain": (False, 0, True),
        "clear_drain": (True, 0, True),
        "clear_wait1ms": (True, 0.001, False),
        "clear_wait5ms": (True, 0.005, False),
    }
    rng = random.Random(20261026)
    totals = collections.defaultdict(collections.Counter)
    request = packet(254, 130, bytes([56, 15, 200]))
    with serial.Serial("/dev/ttyS2", 1000000, timeout=0.001, write_timeout=0.1) as ser:
        emit({"kind":"metadata", "utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "conditions":modes,"rounds":n,"read_only":True,"uart_before":counter(ser)})
        for round_no in range(n):
            order = list(modes)
            rng.shuffle(order)
            for label in order:
                clear, wait, drain = modes[label]
                pending = ser.in_waiting
                orphan = ser.read(pending) if pending else b""
                if clear:
                    ser.reset_input_buffer()
                if wait:
                    time.sleep(wait)
                start = time.monotonic()
                stamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
                ser.write(request)
                if drain:
                    ser.flush()
                chunks = []
                raw = bytearray()
                while time.monotonic()-start < 0.1:
                    value = ser.read(max(ser.in_waiting, 1))
                    if value:
                        raw.extend(value)
                        chunks.append({"ms":round((time.monotonic()-start)*1000,3),"hex":value.hex(),"end":len(raw)})
                frames = parse(bytes(raw))
                for f in frames:
                    f["complete_ms"] = next(c["ms"] for c in chunks if c["end"] >= f["end"])
                valid = [f for f in frames if f["id"] == 200 and f["checksum_ok"] and len(bytes.fromhex(f["params"])) == 15]
                emit({"kind":"cycle","utc":stamp,"round":round_no,"condition":label,"tx":request.hex(),
                      "orphan":orphan.hex(),"raw":bytes(raw).hex(),"frames":frames,"chunks":chunks,"ok":bool(valid)})
                totals[label]["requests"] += 1
                totals[label]["ok"] += bool(valid)
                totals[label]["empty"] += not raw
                totals[label]["bad_checksum"] += sum(not f["checksum_ok"] for f in frames)
                totals[label]["orphan_bytes"] += len(orphan)
        for label, counts in totals.items():
            emit({"kind":"summary","condition":label,**dict(counts)})
        emit({"kind":"uart_after","value":counter(ser)})


if __name__ == "__main__":
    main()
