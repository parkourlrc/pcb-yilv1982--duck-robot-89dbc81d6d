"""Read native policy availability without changing configuration or motion state."""
from datetime import datetime, timezone
import json
from pathlib import Path
import socket
import subprocess
import urllib.request


def rpc(method):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.settimeout(5)
        s.connect('/run/robotd.sock')
        s.sendall(json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': {}}).encode() + b'\n')
        with s.makefile('rb') as f:
            return json.loads(f.readline())


result = {'captured_at_utc': datetime.now(timezone.utc).isoformat(),
          'scope': 'Read-only RPC and HTTP; no enable, reload, torque, stand or skill commands'}
for method in ['robot.policies', 'robot.skills', 'pad.bindings', 'robot.health', 'robot.busStatus']:
    result[method] = rpc(method)
try:
    with urllib.request.urlopen('http://127.0.0.1:8000/api/models', timeout=5) as r:
        result['studio_models'] = {'status': r.status, 'body': json.load(r)}
except Exception as e:
    result['studio_models'] = {'error': str(e)}
result['runtime'] = subprocess.run(['systemctl', 'show', 'robotd.service', '-p', 'MainPID',
                                    '-p', 'ActiveState', '-p', 'ExecStart'],
                                   capture_output=True, text=True).stdout
print(json.dumps(result, ensure_ascii=True, indent=2))
