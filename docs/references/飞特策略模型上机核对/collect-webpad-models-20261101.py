"""Read-only robotd handover/model inventory and deployed web-gamepad sources."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import tomllib

ROOT = Path('/home/radxa/studio-dev')
SLOTS = ['walk','sitstand','ground_pick','kick_left','kick_right','roulade']

def file(path):
    p = Path(path)
    if not p.exists():
        return {'path':str(p),'exists':False}
    raw = p.read_bytes()
    return {'path':str(p),'exists':True,'sha256':hashlib.sha256(raw).hexdigest(),'text':raw.decode()}

def rpc(method, params):
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as s:
        s.settimeout(5)
        s.connect('/run/robotd.sock')
        s.sendall(json.dumps({'jsonrpc':'2.0','id':1,'method':method,'params':params}).encode()+b'\n')
        with s.makefile('rb') as f:
            return json.loads(f.readline())

record = {'date':'2026-11-01','board_utc_clock':datetime.now(timezone.utc).isoformat(),
          'scope':'Read-only; no stand, policy enable, controls or model selection'}
record['sources'] = {rel:file(ROOT/rel) for rel in ['web/pad.js','web/stepper.js','studio/pad_drive.py',
                      'studio/onboard.py','studio/models.py','studio/pad.py']}
record['params'] = file('/etc/robot/feetech-ft5/robotd.toml')
record['calibration'] = file('/etc/robot/feetech-ft5/hd1910-calibration.toml')
record['official_commissioning_override'] = file('/etc/systemd/system/robotd.service.d/zzzz-zz-microduck-commissioning.conf')
record['bus_status'] = rpc('robot.busStatus',{})
record['calibration_status'] = rpc('robot.busCommand',{'action':'calibration-status'})
record['policies'] = rpc('robot.policies',{})
catalog = json.loads(Path('/home/radxa/duck-policies/hd1910-20261031/catalog.json').read_text())
expected = {m['slot']:m for m in catalog['models']}
params = tomllib.loads(record['params']['text'])
record['models'] = []
for slot in SLOTS:
    path = Path(params['policy'][slot])
    exists = path.is_file()
    row = {'slot':slot,'name':expected[slot]['name'],'configured_path':str(path),'exists':exists,
           'expected_sha256':expected[slot]['sha256']}
    if exists:
        row.update(bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        row['matches_uploaded_model'] = row['sha256'] == row['expected_sha256']
        row['sidecars'] = {p.name:file(p) for p in sorted(path.parent.glob('*.json'))}
    record['models'].append(row)
record['services'] = {name:subprocess.run(['systemctl','show',name,'-p','MainPID','-p','ActiveState','-p','UnitFileState','-p','ExecStart'],
                                        text=True,capture_output=True).stdout for name in ['robotd.service','microduck-studio.service']}
record['helper_last_result'] = file('/run/microduck-helper/last-result.json')
record['log_matches'] = []
for p in (ROOT/'logs').glob('studio-2026-11-01.log'):
    for i,line in enumerate(p.read_text().splitlines(),1):
        if any(s in line for s in ['写进主程序了','写进主程序没成','主程序进了运动模式']):
            record['log_matches'].append({'path':str(p),'line':i,'text':line})
record['log_matches'] = record['log_matches'][-8:]
print(json.dumps(record,ensure_ascii=True,indent=2))
