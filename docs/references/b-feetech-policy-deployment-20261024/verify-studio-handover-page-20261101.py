"""Verify the actual Studio preview route; do not submit calibration or motion."""
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import urllib.request

import websockets

HERE = Path(__file__).resolve().parent
OUT = HERE/'studio-handover-page-preview-20261101.json'
record = {'date':'2026-11-01', 'captured_at_utc':datetime.now(timezone.utc).isoformat(),
          'scope':'Studio calib.op preview only, then read-only service/file verification',
          'sent':[]}

async def preview():
    origin = 'http://192.168.1.35:8000'
    with urllib.request.urlopen(origin+'/',timeout=5) as response:
        record['http_status'] = response.status
    async with asyncio.timeout(20):
        async with websockets.connect('ws://192.168.1.35:8000/ws',origin=origin,
                                      open_timeout=5,max_size=4*1024*1024) as ws:
            for cmd in [{'t':'hb','seq':1,'visible':True,'route':'/'},
                        {'t':'cmd','id':'codex-preview-20261101','name':'calib.op','args':{'op':'preview'}}]:
                await ws.send(json.dumps(cmd))
                record['sent'].append(cmd)
            while True:
                msg = json.loads(await ws.recv())
                if msg.get('t') == 'state':
                    record['page_state'] = {k:msg.get(k) for k in ['t','robotd_ok','mode','phase','posture','hold','commit']}
                if msg.get('t') == 'result' and msg.get('id') == 'codex-preview-20261101':
                    record['preview_result'] = msg
                    assert msg.get('ok') is True, msg
                    return

try:
    asyncio.run(preview())
    deployment = json.loads((HERE/'studio-handover-deployment-20261101.json').read_text(encoding='utf-8'))
    paths = list(deployment['protected_before'])
    code = '''import hashlib,json,subprocess
from pathlib import Path
paths = PATHS
out={'files':{p:hashlib.sha256(Path(p).read_bytes()).hexdigest() if Path(p).exists() else None for p in paths},'services':{}}
for name in ['robotd.service','microduck-studio.service']:
 p=subprocess.run(['systemctl','show',name,'-p','MainPID','-p','ActiveState','-p','UnitFileState'],capture_output=True,text=True,check=True)
 out['services'][name]=dict(line.split('=',1) for line in p.stdout.splitlines())
app=Path('/home/radxa/studio-dev/studio/app.py').read_bytes()
out['app_source']={'path':'/home/radxa/studio-dev/studio/app.py','sha256':hashlib.sha256(app).hexdigest(),'preview_route_excerpt':'\\n'.join(app.decode().splitlines()[915:941])}
print(json.dumps(out,ensure_ascii=True))
'''.replace('PATHS',repr(paths))
    p = subprocess.run(['ssh','radxa','python3','-'],input=code,text=True,capture_output=True,check=True,timeout=15)
    record['after'] = json.loads(p.stdout)
    assert record['after']['files'] == deployment['protected_before']
    for name,row in record['after']['services'].items():
        assert row['MainPID'] == deployment['services_before'][name]['MainPID']
        assert row['ActiveState'] == 'active' and row['UnitFileState'] == 'enabled'
    record['status'] = 'actual Studio page preview passed; processes and protected files unchanged'
finally:
    OUT.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

print(json.dumps({'status':record['status'],'http_status':record['http_status'],
                  'preview_ok':record['preview_result']['ok'],
                  'readiness':(record.get('page_state',{}).get('commit') or {}).get('ready'),
                  'services':record['after']['services']},ensure_ascii=False,indent=2))
