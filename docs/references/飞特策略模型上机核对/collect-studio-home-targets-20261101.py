"""Read-only snapshot of the two Studio stand paths; no UART or motion commands."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import socket
import subprocess

root = Path('/home/radxa/studio-dev')

def read_file(path):
    p = Path(path)
    if not p.exists():
        return {'path': str(p), 'exists': False}
    data = p.read_bytes()
    return {'path': str(p), 'exists': True, 'sha256': hashlib.sha256(data).hexdigest(),
            'text': data.decode('utf-8')}

def rpc(method, params):
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(6)
            s.connect('/run/robotd.sock')
            s.sendall(json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}).encode()+b'\n')
            with s.makefile('rb') as f:
                return json.loads(f.readline())
    except (OSError, ValueError) as exc:
        return {'read_error': f'{type(exc).__name__}: {exc}'}

record = {'date': '2026-11-01', 'board_utc_clock': datetime.now(timezone.utc).isoformat(),
          'user_report': 'Studio 舵机页站姿能站住，IMU 页站姿关节角度不对',
          'scope': 'Read existing files, logs, busStatus and calibration-status only; no motion',
          'sources': {}, 'state': {}}
for rel in ['studio/servo.py', 'studio/servo_ops.py', 'studio/commit.py', 'studio/imu.py',
            'web/servo.js', 'web/imu.js']:
    record['sources'][rel] = read_file(root/rel)
for rel in ['servo-directions.json', 'servo-centered.json', 'imu-pending.json']:
    record['state'][rel] = read_file(root/'state'/rel)
record['poses'] = [read_file(p) for p in sorted((root/'state'/'servo-poses').glob('*.json'))]
record['calibration_file'] = read_file('/etc/robot/feetech-ft5/hd1910-calibration.toml')
record['params_file'] = read_file('/etc/robot/feetech-ft5/robotd.toml')
record['bus_status'] = rpc('robot.busStatus', {})
record['calibration_status'] = rpc('robot.busCommand', {'action': 'calibration-status'})
record['services'] = {name: subprocess.run(['systemctl','is-active',name],capture_output=True,text=True).stdout.strip()
                      for name in ['robotd.service','microduck-studio.service']}
record['log_matches'] = []
for p in sorted((root/'logs').glob('studio-2026-11-01.log')):
    lines=p.read_text().splitlines()
    record['log_matches'].extend({'file':str(p), 'line':i, 'text':line}
                                for i,line in enumerate(lines,1)
                                if re.search('站姿|hold-home|预置|官方站|go_pose|preset|写进主程序', line))
record['robotd_binary_sha256'] = hashlib.sha256(Path('/opt/robot/daemon/current/bin/robotd').read_bytes()).hexdigest()
# Keep the SSH/PowerShell pipeline ASCII so source text and its hash remain reproducible.
print(json.dumps(record, ensure_ascii=True, indent=2))
