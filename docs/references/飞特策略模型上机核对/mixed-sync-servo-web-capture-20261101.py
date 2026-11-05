"""真实 servo-web WebSocket 只读采集；唯一设置命令为原有总线日志开关。"""
import asyncio
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import time
import urllib.request

import websockets

STAGE = Path('/home/radxa/restore-mixed-sync-20261101')
OUT = STAGE / 'servo-web-capture.json'
RAW = STAGE / 'servo-web-bus.log'
LOGDIR = Path('/home/radxa/servo-web/logs')


def info():
    with urllib.request.urlopen('http://127.0.0.1:8080/api/info', timeout=5) as r:
        return json.load(r)


async def main():
    assert not OUT.exists() and not RAW.exists(), 'Preserve prior capture'
    offsets = {p: p.stat().st_size for p in LOGDIR.glob('bus-*.log')}
    record = {'started_utc_board_clock': datetime.now(timezone.utc).isoformat(),
              'scope': 'real WebSocket; no motor commands; existing buslog toggle only',
              'before': info(), 'messages': []}
    assert record['before']['version'] == '0.15.3' and not record['before']['fake']
    original_buslog = False
    try:
        async with websockets.connect('ws://127.0.0.1:8080/ws', max_size=4*1024*1024) as ws:
            hello = json.loads(await asyncio.wait_for(ws.recv(), 5))
            record['hello'] = hello
            assert hello['type'] == 'hello'
            assert len(hello['present']) == 15
            assert len(hello['torque']) == 15 and all(v == 0 for v in hello['torque'].values()), 'Expected all servo torque already off'
            original_buslog = hello.get('buslog', False)
            await ws.send(json.dumps({'op': 'buslog', 'on': True}))
            start = time.monotonic()
            try:
                while time.monotonic() - start < 30:
                    message = json.loads(await asyncio.wait_for(ws.recv(), 4))
                    if message.get('type') != 'logs':
                        record['messages'].append({'elapsed_s': time.monotonic()-start, 'data': message})
            finally:
                await ws.send(json.dumps({'op': 'buslog', 'on': original_buslog}))
                await asyncio.sleep(1)
            record['duration_s'] = time.monotonic() - start
    except Exception as exc:
        record['error'] = f'{type(exc).__name__}: {exc}'
        raise
    finally:
        record['after'] = info()
        record['finished_utc_board_clock'] = datetime.now(timezone.utc).isoformat()
        raw = []
        for p in sorted(LOGDIR.glob('bus-*.log')):
            with p.open('rb') as f:
                f.seek(offsets.get(p, 0))
                chunk = f.read()
            if chunk:
                raw.append(chunk)
        RAW.write_bytes(b''.join(raw))
        states = [x['data'] for x in record['messages'] if x['data'].get('type') == 'state']
        imus = [x['data'] for x in record['messages'] if x['data'].get('type') == 'imu']
        summary = {
            'state_frames': len(states),
            'all_15_present_frames': sum(len(x['states']) == 15 and all(v is not None for v in x['states'].values()) for x in states),
            'imu_messages': len(imus),
            'imu_status_counts': dict(Counter(x.get('status') for x in imus)),
            'imu_status_bits_counts': dict(Counter(x.get('status_bits') for x in imus)),
            'last_imu': imus[-1] if imus else None,
            'stats_delta': {k: record['after']['stats'][k]-v for k, v in record['before']['stats'].items()},
            'raw_trace_bytes': RAW.stat().st_size,
        }
        record['summary'] = summary
        OUT.write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--suffix', choices=['', '-legacy'], default='')
    args = parser.parse_args()
    OUT = STAGE / f'servo-web-capture{args.suffix}.json'
    RAW = STAGE / f'servo-web-bus{args.suffix}.log'
    asyncio.run(main())
