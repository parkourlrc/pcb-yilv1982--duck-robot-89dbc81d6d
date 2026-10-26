#!/usr/bin/env python3
"""微雪台架只发飞特单播 PING；发现一颗舵机后短测连续应答，保存原始帧。"""
import argparse
import datetime
import importlib.util
import json
from pathlib import Path
import time

import serial
from serial.tools import list_ports


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--port', required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    spec = importlib.util.spec_from_file_location(
        'raw_capture', Path(__file__).with_name('imu200-raw-capture.py'))
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    preferred = [1, *range(10, 15), *range(20, 25), *range(30, 35)]
    scan_ids = preferred + [i for i in range(254) if i not in preferred and i != 200]
    with args.output.open('x', encoding='utf-8') as log:
        def emit(row):
            log.write(json.dumps(row, ensure_ascii=True) + '\n')
            log.flush()
            if row['kind'] in ('metadata', 'found', 'summary', 'finished'):
                print(json.dumps(row, ensure_ascii=True), flush=True)

        emit({'kind': 'metadata', 'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'port': args.port, 'baud': 1000000, 'read_only': True,
              'instruction': 'unicast PING only; no broadcast, writes or movement',
              'scan_ids': scan_ids, 'verify_count': 20, 'receive_window_ms': 100,
              'supply': 'external 7.4V previously user-confirmed; unchanged assumed',
              'topology': 'user connected servo; whether IMU removed awaiting clarification',
              'ports': [{'device': p.device, 'description': p.description, 'hwid': p.hwid}
                        for p in list_ports.comports()]})
        found = None
        requests = 0
        with serial.Serial(args.port, 1000000, timeout=.001, write_timeout=.1) as ser:
            def receive(tx=b''):
                t0 = time.monotonic()
                utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
                written = ser.write(tx) if tx else 0
                if tx:
                    ser.flush()
                data = bytearray()
                chunks = []
                while time.monotonic() - t0 < .1:
                    value = ser.read(max(1, ser.in_waiting))
                    if value:
                        data.extend(value)
                        chunks.append({'ms': round((time.monotonic()-t0)*1000, 3),
                                       'hex': value.hex(), 'end': len(data)})
                return {'utc': utc, 'tx': tx.hex(), 'written': written,
                        'raw': data.hex(), 'chunks': chunks,
                        'frames': helper.parse(bytes(data))}

            emit({'kind': 'passive_before', **receive()})
            for sid in scan_ids:
                row = receive(helper.packet(sid, 1))
                frames = [f for f in row['frames'] if f['checksum_ok']
                          and f['id'] == sid and f['params'] == ''
                          and f['raw'] != row['tx']]
                row.update(kind='capture', phase='scan', id=sid,
                           response=bool(frames), ok=any(f['status'] == 0 for f in frames))
                emit(row)
                requests += 1
                if frames:
                    found = sid
                    emit({'kind': 'found', 'id': sid, 'frames': frames})
                    break
            ok = responses = empty = 0
            if found is not None:
                for _ in range(20):
                    row = receive(helper.packet(found, 1))
                    frames = [f for f in row['frames'] if f['checksum_ok']
                              and f['id'] == found and f['params'] == ''
                              and f['raw'] != row['tx']]
                    good = any(f['status'] == 0 for f in frames)
                    ok += good
                    responses += bool(frames)
                    empty += not row['raw']
                    emit({'kind': 'capture', 'phase': 'verify', 'id': found,
                          'response': bool(frames), 'ok': good, **row})
            emit({'kind': 'passive_after', **receive()})
        emit({'kind': 'summary', 'scan_requests': requests, 'found_id': found,
              'verify_requests': 20 if found is not None else 0,
              'verify_responses': responses, 'verify_ok': ok, 'verify_empty': empty})
        emit({'kind': 'finished', 'serial_closed': True})


if __name__ == '__main__':
    main()
