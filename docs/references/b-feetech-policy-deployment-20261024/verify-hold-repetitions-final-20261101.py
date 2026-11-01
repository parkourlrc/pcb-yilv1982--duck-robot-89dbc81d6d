#!/usr/bin/env python3
"""Read status/files only via SSH; never open UART, send motion, or restart services."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent
REMOTE = r'''
import datetime, hashlib, json, socket, subprocess, urllib.request
from pathlib import Path
root = Path('/home/radxa/duck-runtime-stage-20261031')
r = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
     'scope': 'Read-only RPC status, service state, HTTP health and file hashes; no UART open or motion'}
def command(args):
    p = subprocess.run(args, capture_output=True, text=True, timeout=8)
    return {'returncode': p.returncode, 'stdout': p.stdout, 'stderr': p.stderr}
r['services'] = {u: {op: command(['systemctl', op, u]) for op in ['is-active', 'is-enabled']}
                 for u in ['robotd', 'microduck-studio']}
r['old_servo_web'] = {op: command(['systemctl', '--user', op, 'duck-servo-web'])
                      for op in ['is-active', 'is-enabled']}
try:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.settimeout(5)
        s.connect('/run/robotd.sock')
        with s.makefile('rb') as f:
            for ident, method, params in [(1, 'hello', {'api_version': 42}), (2, 'robot.busStatus', {})]:
                s.sendall((json.dumps({'jsonrpc':'2.0','id':ident,'method':method,'params':params})+'\n').encode())
                while True:
                    line = f.readline()
                    if not line:
                        raise RuntimeError('RPC disconnected')
                    response = json.loads(line)
                    if response.get('id') == ident:
                        break
                if 'error' in response:
                    raise RuntimeError(response['error'])
            r['bus_status'] = response['result']
except Exception as e:
    r['bus_status_error'] = repr(e)
try:
    with urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=5) as response:
        r['studio_health'] = {'status':response.status, 'body':response.read().decode()}
except Exception as e:
    r['studio_health_error'] = repr(e)
paths = [p for pattern in ['hold-home-baseline3-20261101*.json', 'hold-home-baseline3-20261101*.log',
                          'hold-home-servo-first-20261101.json', 'hold-home-servo-first-20261101.log',
                          'servo-first-deployment-20261101.json'] for p in root.glob(pattern)]
r['evidence_sha256'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(set(paths))}
paths = ['/opt/robot/daemon/current/bin/robotd', '/etc/robot/feetech-ft5/robotd.toml',
         '/etc/robot/feetech-ft5/hd1910-calibration.toml']
r['installed_sha256'] = {p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in paths}
print(json.dumps(r, ensure_ascii=False))
'''


def main():
    output = ROOT / 'hold-repetitions-final-20261101.json'
    if output.exists():
        raise SystemExit('Existing final snapshot retained; do not overwrite')
    proc = subprocess.run(['ssh', '-o', 'ConnectTimeout=8', 'radxa', 'python3 -'],
                          input=REMOTE, capture_output=True, encoding='utf-8', timeout=45)
    proc.check_returncode()
    result = json.loads(proc.stdout)
    result['ssh_stderr'] = proc.stderr
    result['local_evidence_match'] = {
        name: (ROOT / name).is_file() and hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == value
        for name, value in result['evidence_sha256'].items()
    }
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    state = result.get('bus_status', {})
    print(json.dumps({'output': str(output), 'build': state.get('build'),
                      'phase': state.get('phase'), 'torque': state.get('torque_state'),
                      'services': result['services'], 'old_servo_web': result['old_servo_web'],
                      'studio_health': result.get('studio_health'),
                      'evidence_hashes': result['local_evidence_match'],
                      'errors': {k:v for k,v in result.items() if k.endswith('_error')}}, ensure_ascii=False))


if __name__ == '__main__':
    main()
