#!/usr/bin/env python3
"""电脑侧双协议只读排障；复用已有诊断，显式指定 COM 口，不运行停启服务逻辑。"""
import argparse
import datetime
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import serial


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--port', required=True)
    ap.add_argument('--count', type=int, default=8)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    if not 1 <= args.count <= 50:
        ap.error('count must be 1..50')
    spec = importlib.util.spec_from_file_location(
        'protocol_diagnostic', Path(__file__).with_name('imu200-protocol-diagnostic.py'))
    diag = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(diag)

    def open_port(original_port, *pos, **kw):
        if original_port != '/dev/ttyS2':
            raise ValueError('Unexpected source port')
        return serial.Serial(args.port, *pos, **kw)

    diag.serial = SimpleNamespace(Serial=open_port)
    with args.output.open('x', encoding='utf-8') as log:
        def emit(row):
            log.write(json.dumps(row, ensure_ascii=True) + '\n')
            log.flush()
            if row['kind'] in ('metadata', 'summary', 'finished'):
                print(json.dumps(row, ensure_ascii=True), flush=True)
        diag.emit = emit
        emit({'kind': 'metadata', 'port': args.port, 'baud': 1000000,
              'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'supply': 'external 7.4V confirmed by user',
              'source': 'imu200-protocol-diagnostic.py run(); no service control'})
        diag.run(args.count, crc_challenge=False)
        emit({'kind': 'finished', 'serial_closed': True})


if __name__ == '__main__':
    main()
