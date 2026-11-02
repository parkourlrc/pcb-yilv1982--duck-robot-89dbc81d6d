#!/usr/bin/env python3
"""Read-only OS/RPC/source audit; never opens the UART or changes services."""
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess

ROOT = Path('/home/radxa/duck-runtime-stage-20261031')
OUT = ROOT/'port-serialization-audit-20261101.json'
if OUT.exists():
    raise SystemExit('Preserve existing evidence; refuse overwrite')
if os.geteuid() != 0:
    raise SystemExit('Root is needed only to inspect other processes open descriptors')


def command(args):
    p = subprocess.run(args, capture_output=True, text=True, timeout=5)
    return {'exit':p.returncode, 'stdout':p.stdout, 'stderr':p.stderr}


r = {'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
     'scope':'Read-only /proc, source hashes, service status and robot.busStatus; no UART open',
     'uart_holders':[], 'scan_errors':[], 'board_sources':{}}
for proc in Path('/proc').iterdir():
    if not proc.name.isdigit():
        continue
    try:
        for fd in (proc/'fd').iterdir():
            try:
                target = os.readlink(fd)
                if target != '/dev/ttyS2':
                    continue
                r['uart_holders'].append({'pid':int(proc.name),'fd':int(fd.name),'target':target,
                    'cmdline':(proc/'cmdline').read_bytes().replace(b'\x00',b' ').decode(),
                    'tasks':[{'tid':int(t.name),'comm':(t/'comm').read_text().strip()} for t in (proc/'task').iterdir()],
                    'fdinfo':(proc/'fdinfo'/fd.name).read_text()})
            except FileNotFoundError:
                pass  # process/fd can disappear during a read-only snapshot
    except FileNotFoundError:
        pass
    except Exception as e:
        r['scan_errors'].append({'pid':proc.name,'error':repr(e)})
for name in ['feetech.py','server.py']:
    p=Path('/home/radxa/servo-web')/name
    lines=p.read_text(encoding='utf-8').splitlines()
    ranges=[(72,84),(96,150),(158,212)] if name=='feetech.py' else [(1517,1547)]
    r['board_sources'][str(p)]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
                              'snippets':[{'start':a,'end':b,'text':'\n'.join(lines[a-1:b])} for a,b in ranges]}
r['robotd']=command(['systemctl','show','robotd','-p','MainPID','-p','ActiveState','-p','ExecStart'])
r['studio']=command(['systemctl','show','microduck-studio','-p','MainPID','-p','ActiveState'])
r['servo_web_user_service']=command(['runuser','-u','radxa','--','env','XDG_RUNTIME_DIR=/run/user/1000','systemctl','--user','is-active','duck-servo-web'])
spec=importlib.util.spec_from_file_location('diag',ROOT/'imu-diagnostic-read-20261101.py')
d=importlib.util.module_from_spec(spec)
spec.loader.exec_module(d)
r['status']=d.status()
OUT.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
os.chown(OUT,1000,1000)
print(json.dumps({'output':str(OUT),'uart_holders':r['uart_holders'],'scan_errors':r['scan_errors'],
                  'servo_web':r['servo_web_user_service'],'torque':r['status'].get('torque_state')}),flush=True)
