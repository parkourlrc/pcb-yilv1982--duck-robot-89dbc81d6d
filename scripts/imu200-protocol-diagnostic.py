#!/usr/bin/env python3
"""板②双协议只读对照；从项目只读上游模块复用编码/CRC。

仅 PING/READ。主机先安静300ms等待协议粘滞期结束，不写协议锁寄存器。
--stop-service 只暂停并在finally恢复duck-servo-web。输出原始JSONL。
"""

import argparse
import datetime
import importlib.util
import json
from pathlib import Path
import signal
import subprocess
import sys
import time

import serial

codec_path = Path(__file__).resolve().parents[1] / "references/microduck-community-kit/firmware/v1/host/bus.py"
if not codec_path.exists():
    codec_path = Path(__file__).with_name("imu200_upstream_codec.py")
spec = importlib.util.spec_from_file_location("imu200_codec", codec_path)
codec = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = codec
spec.loader.exec_module(codec)


def emit(value):
    print(json.dumps(value, ensure_ascii=False), flush=True)


def parse(raw, protocol):
    frames = []
    header = b"\xff\xff\xfd\x00" if protocol == "dxl" else b"\xff\xff"
    pos = 0
    while True:
        pos = raw.find(header, pos)
        prefix = 7 if protocol == "dxl" else 4
        if pos < 0 or len(raw) < pos + prefix:
            break
        length = int.from_bytes(raw[pos+5:pos+7], "little") if protocol == "dxl" else raw[pos+3]
        end = pos + prefix + length
        if len(raw) < end:
            break
        frame = raw[pos:end]
        try:
            sid, status, params = (codec.dxl_parse_status if protocol == "dxl" else codec.fee_parse_ack)(frame)
            frames.append({"id":sid,"status":status,"params":params.hex(),"raw":frame.hex()})
        except codec.ProtocolError as exc:
            frames.append({"error":str(exc),"raw":frame.hex()})
        pos = end
    return frames


def run(n, crc_challenge=False):
    emit({"kind":"metadata","utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
          "read_only":True,"baud":1000000,"id":200,"quiet_before_phase_ms":300,"n":n,
          "intentional_bad_crc_control":crc_challenge})
    modes = [
        ("fee_ping", "fee", codec.fee_ping(200), 0, 0),
        ("dxl_ping", "dxl", codec.dxl_ping(200), 3, 0),
        ("fee_read20", "fee", codec.fee_read(200,128,20), 20, 0),
        ("dxl_read20", "dxl", codec.dxl_read(200,124,20), 20, 0),
        ("fee_ping_return", "fee", codec.fee_ping(200), 0, 0),
    ]
    if crc_challenge:
        valid = codec.dxl_ping(200)
        corrupted = valid[:-1] + bytes([valid[-1] ^ 1])
        modes = [("dxl_valid_before", "dxl", valid, 3, 0),
                 ("dxl_intentional_bad_crc", "dxl", corrupted, 0, 32),
                 ("dxl_valid_after", "dxl", valid, 3, 0),
                 ("fee_return", "fee", codec.fee_ping(200), 0, 0)]
    with serial.Serial("/dev/ttyS2",1000000,timeout=0.001,write_timeout=0.1) as ser:
        for label, protocol, tx, width, expected_status in modes:
            time.sleep(0.3)
            old = ser.read(ser.in_waiting)
            emit({"kind":"phase","label":label,"old_rx":old.hex()})
            ok = empty = invalid = 0
            for i in range(n):
                start = time.monotonic()
                utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
                ser.write(tx)
                ser.flush()
                raw = bytearray()
                chunks = []
                while time.monotonic()-start < 0.1:
                    value = ser.read(max(1,ser.in_waiting))
                    if value:
                        raw.extend(value)
                        chunks.append({"ms":round((time.monotonic()-start)*1000,3),"hex":value.hex()})
                frames = parse(bytes(raw),protocol)
                good = any(f.get("id")==200 and f.get("status")==expected_status and len(bytes.fromhex(f["params"]))==width for f in frames)
                ok += good
                empty += not raw
                invalid += sum("error" in f for f in frames)
                emit({"kind":"capture","label":label,"i":i,"utc":utc,"tx":tx.hex(),"raw":raw.hex(),
                      "chunks":chunks,"frames":frames,"expected_status":expected_status,"ok":good})
            emit({"kind":"summary","label":label,"requests":n,"ok":ok,"empty":empty,"invalid_frames":invalid})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stop-service",action="store_true")
    ap.add_argument("--count",type=int,default=50)
    ap.add_argument("--crc-challenge",action="store_true",help="用已知错误CRC的PING验证0x20含义，明确标为人为对照")
    args = ap.parse_args()
    if not 1 <= args.count <= 150:
        raise SystemExit("count must be 1..150")
    def interrupted(signum, frame):
        raise KeyboardInterrupt()
    signal.signal(signal.SIGTERM, interrupted)
    try:
        if args.stop_service:
            subprocess.run(["systemctl","--user","stop","duck-servo-web.service"],check=True)
        if subprocess.run(["fuser","/dev/ttyS2"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode == 0:
            raise RuntimeError("serial port still occupied")
        run(args.count, args.crc_challenge)
    finally:
        if args.stop_service:
            subprocess.run(["systemctl","--user","start","duck-servo-web.service"],check=True)
            state=subprocess.check_output(["systemctl","--user","is-active","duck-servo-web.service"],text=True).strip()
            emit({"kind":"service_restored","state":state})


if __name__ == "__main__":
    main()
