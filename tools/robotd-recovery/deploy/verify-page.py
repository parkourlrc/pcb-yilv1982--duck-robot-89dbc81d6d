"""Read the deployed Studio static file and WebSocket snapshots; never request motion."""
import asyncio
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import urllib.request

import websockets

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUT = ROOT / 'docs/references/b-feetech-policy-deployment-20261024/webpad-recovery-page-20261101.json'
record = {'time_utc': datetime.now(timezone.utc).isoformat(), 'scope': 'HTTP plus WebSocket page heartbeat and read-only watch; no drive lease or motion', 'sent': []}


async def main():
    origin = 'http://192.168.1.35:8000'
    for path in ('/', '/pad.js'):
        with urllib.request.urlopen(origin + path, timeout=8) as response:
            content = response.read()
            record[path] = {'status': response.status, 'sha256': hashlib.sha256(content).hexdigest()}
    manifest = json.loads((HERE.parent / 'candidate-manifest.json').read_text(encoding='utf-8'))
    assert record['/pad.js']['sha256'] == manifest['candidate_files']['studio/web/pad.js']
    async with asyncio.timeout(20):
        async with websockets.connect('ws://192.168.1.35:8000/ws', origin=origin, open_timeout=5, max_size=4 * 1024 * 1024) as ws:
            for message in ({'t': 'hb', 'seq': 1, 'visible': True, 'route': '/pad', 'pad_visible': True},
                            {'t': 'cmd', 'id': 'recovery-readonly-watch', 'name': 'pad.op', 'args': {'op': 'watch'}}):
                await ws.send(json.dumps(message))
                record['sent'].append(message)
            while True:
                message = json.loads(await ws.recv())
                if message.get('t') == 'state':
                    record['state'] = {key: message.get(key) for key in ('robotd_ok', 'mode', 'phase', 'build', 'posture', 'present', 'start_error')}
                if message.get('t') == 'result' and message.get('id') == 'recovery-readonly-watch':
                    record['watch_result'] = message
                    assert message.get('ok') is True, message
                if message.get('t') == 'pad':
                    record['pad'] = message
                recovery = record.get('pad', {}).get('motion', {}).get('recovery', {})
                if recovery.get('available') and record.get('state', {}).get('robotd_ok') and record.get('watch_result', {}).get('ok'):
                    assert recovery.get('phase') == 'idle' and recovery.get('active') is False
                    break
    code = (HERE / 'probe.py').read_bytes()
    result = subprocess.run(['ssh', '-o', 'BatchMode=yes', 'radxa', 'python3 -'], input=code, capture_output=True, timeout=35, check=True)
    record['after'] = json.loads(result.stdout)
    bus = record['after']['robot.busStatus']
    assert bus['policy_enabled'] is False and bus['native']['torque_state_confirmed'] is False
    assert bus['walk_recovery']['phase'] == 'idle' and bus['walk_recovery']['request_id'] is None
    before = json.loads((OUT.parent / 'webpad-recovery-deploy-before-20261101.json').read_text(encoding='utf-8'))
    assert before['protected'] == record['after']['protected']
    record['status'] = 'deployed page and native state verified; no recovery request, torque OFF, protected files unchanged'


try:
    asyncio.run(main())
finally:
    OUT.write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'status': record.get('status'), 'state': record.get('state'), 'recovery': record.get('pad', {}).get('motion', {}).get('recovery')}, ensure_ascii=False, indent=2))
