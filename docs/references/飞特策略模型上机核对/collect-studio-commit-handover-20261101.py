"""Read-only evidence for Studio calibration commit; never switch mode or torque."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import socket
import subprocess

ROOT = Path('/home/radxa/studio-dev')

def read_file(path):
    p = Path(path)
    if not p.exists():
        return {'path': str(p), 'exists': False}
    raw = p.read_bytes()
    return {'path': str(p), 'exists': True, 'sha256': hashlib.sha256(raw).hexdigest(),
            'text': raw.decode('utf-8')}

def command(args, input_text=None):
    p = subprocess.run(args, input=input_text, capture_output=True, text=True, timeout=15)
    return {'args': args, 'returncode': p.returncode, 'stdout': p.stdout, 'stderr': p.stderr}

def rpc(method, params):
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(5)
            s.connect('/run/robotd.sock')
            s.sendall(json.dumps({'jsonrpc':'2.0', 'id':1, 'method':method, 'params':params}).encode()+b'\n')
            with s.makefile('rb') as f:
                return json.loads(f.readline())
    except (OSError, ValueError) as exc:
        return {'read_error': f'{type(exc).__name__}: {exc}'}

record = {'date':'2026-11-01', 'board_utc_clock':datetime.now(timezone.utc).isoformat(),
          'scope':'Read-only: files, service configuration, calib-read, busStatus, calibration-status',
          'sources': {}, 'state': {}, 'service_files': {}}
for rel in ['studio/commit.py', 'studio/imu.py', 'studio/onboard.py', 'web/commit.js', 'web/onboard.js']:
    record['sources'][rel] = read_file(ROOT/rel)
record['sources']['microduck-helper'] = read_file('/usr/local/sbin/microduck-helper')
for rel in ['servo-centered.json', 'servo-directions.json', 'imu-pending.json']:
    record['state'][rel] = read_file(ROOT/'state'/rel)
unit = Path('/etc/systemd/system/robotd.service')
for path in [unit, *sorted(unit.with_name('robotd.service.d').glob('*.conf'))]:
    record['service_files'][str(path)] = read_file(path)
record['expected_commissioning_file'] = read_file('/etc/systemd/system/robotd.service.d/zzzz-zz-microduck-commissioning.conf')
record['calibration_file'] = read_file('/etc/robot/feetech-ft5/hd1910-calibration.toml')
record['params_file'] = read_file('/etc/robot/feetech-ft5/robotd.toml')
record['helper_read'] = command(['sudo','-n','/usr/local/sbin/microduck-helper','calib-read'], '{"by":"codex-read-only"}')
record['bus_status'] = rpc('robot.busStatus', {})
record['calibration_status'] = rpc('robot.busCommand', {'action':'calibration-status'})
record['services'] = {name:command(['systemctl','show',name,'-p','ActiveState','-p','SubState','-p','UnitFileState','-p','ExecStart'])
                      for name in ['robotd.service','microduck-studio.service']}
record['log_matches'] = []
for p in sorted((ROOT/'logs').glob('studio-2026-11-01.log')):
    for i,line in enumerate(p.read_text().splitlines(),1):
        if re.search('写进主程序|foreign_commissioning|calib-commit|不是镜像|标定模式站姿', line):
            record['log_matches'].append({'path':str(p), 'line':i, 'text':line})
record['log_matches'] = record['log_matches'][-35:]
print(json.dumps(record, ensure_ascii=True, indent=2))
