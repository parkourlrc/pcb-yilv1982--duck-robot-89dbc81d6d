"""Read-only final deployment audit. Does not open the UART or start services."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import urllib.request

stage = Path('/home/radxa/restore-mixed-sync-20261101')
web = Path('/home/radxa/servo-web')
binary = Path('/opt/robot/daemon/current/bin/robotd')
deployment = json.loads((stage / 'deployment.json').read_text())

def command(args):
    p = subprocess.run(args, capture_output=True, text=True, timeout=10)
    return {'returncode': p.returncode, 'stdout': p.stdout.strip(), 'stderr': p.stderr.strip()}

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

result = {'date_utc_board_clock': datetime.now(timezone.utc).isoformat(), 'services': {}}
uid = subprocess.check_output(['id', '-u', 'radxa'], text=True).strip()
for name, prefix in [('robotd.service', ['systemctl']), ('microduck-studio.service', ['systemctl']),
                     ('duck-servo-web.service', ['runuser', '-u', 'radxa', '--', 'env',
                      'XDG_RUNTIME_DIR=/run/user/'+uid, 'systemctl', '--user'])]:
    result['services'][name] = {op: command(prefix + [op, name]) for op in ['is-active', 'is-enabled']}
result['uart_holders'] = []
for proc in Path('/proc').iterdir():
    if not proc.name.isdigit():
        continue
    try:
        for fd in (proc / 'fd').iterdir():
            try:
                if os.readlink(fd) == '/dev/ttyS2':
                    result['uart_holders'].append({'pid': int(proc.name), 'fd': fd.name,
                        'command': (proc/'cmdline').read_bytes().replace(b'\0', b' ').decode()})
            except FileNotFoundError:
                pass
    except FileNotFoundError:
        pass
result['web_sha256'] = {n: sha(web/n) for n in ['server.py', 'imu_bus.py', 'index.html', 'feetech.py']}
result['robotd_sha256'] = sha(binary)
result['deployment_info'] = command([str(binary), 'deployment-info'])
result['protected_sha256'] = {p: sha(p) for p in deployment['protected_before']}
result['protected_unchanged'] = result['protected_sha256'] == deployment['protected_before']
result['ipv4_addresses'] = [v for v in subprocess.check_output(['hostname', '-I'], text=True).split() if ':' not in v]
with urllib.request.urlopen('http://127.0.0.1:8080/api/info', timeout=5) as response:
    api = json.load(response)
result['api_info'] = {k: api[k] for k in ['version', 'present', 'fake', 'stats']}
result['completed_capture_summary'] = json.loads((stage/'servo-web-capture-legacy.json').read_text())['summary']
out = stage/'final-audit.json'
assert not out.exists(), 'Keep prior audit'
out.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
print(json.dumps(result, ensure_ascii=False, indent=2))
