"""Restore the upstream legacy status parser; no motor commands or UART access."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from datetime import datetime, timezone

stage = Path('/home/radxa/restore-mixed-sync-20261101')
target = Path('/home/radxa/servo-web/imu_bus.py')
source = stage / 'imu_bus.legacy.py'
out = stage / 'legacy-parser-deployment.json'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

assert not out.exists(), 'Preserve prior deployment'
assert sha(target) == '60fea9614732bd72bf062566afc8f3510f4e2e8bf08c4f92e24640e3172c36dd'
for name in ['robotd.service', 'microduck-studio.service']:
    assert subprocess.run(['systemctl', 'is-active', '--quiet', name]).returncode != 0, name
compile(source.read_text(), str(source), 'exec')
before = sha(target)
subprocess.run(['systemctl', '--user', 'stop', 'duck-servo-web.service'], check=True)
try:
    shutil.copyfile(source, target)
finally:
    subprocess.run(['systemctl', '--user', 'start', 'duck-servo-web.service'], check=True)
record = {'date_utc_board_clock': datetime.now(timezone.utc).isoformat(),
          'before_sha256': before, 'after_sha256': sha(target),
          'scope': 'Restore original legacy flags only; preserve mixed sync, ready flags and statistics',
          'services_active': {n: subprocess.run(cmd, capture_output=True, text=True).stdout.strip()
                             for n, cmd in {
                                 'servo_web': ['systemctl', '--user', 'is-active', 'duck-servo-web.service'],
                                 'robotd': ['systemctl', 'is-active', 'robotd.service'],
                                 'studio': ['systemctl', 'is-active', 'microduck-studio.service']}.items()}}
out.write_text(json.dumps(record, indent=2)+'\n')
print(json.dumps(record, indent=2))
