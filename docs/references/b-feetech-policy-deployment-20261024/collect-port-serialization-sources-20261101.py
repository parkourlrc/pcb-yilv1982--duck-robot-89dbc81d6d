#!/usr/bin/env python3
"""Archive source excerpts and correlate the previous trace; local reads only."""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
FW=REPO/'training/logs/b-feetech-walk-20261024/controller-preparation-20261031/controller-source/fanhao375-Microduck-kissqy-27d7921/microduck-hd1910/firmware'
files=[
    (REPO/'tools/servo-web/feetech.py',[(72,102),(158,212)]),
    (REPO/'tools/servo-web/server.py',[(249,251),(1517,1547),(1555,1570)]),
    (FW/'robotd/src/main.rs',[(1321,1337),(1369,1392)]),
    (FW/'robotd/src/feetech_commissioning.rs',[(124,165),(190,224),(1433,1452),(1517,1536),(1640,1665),(1731,1770)]),
    (FW/'duck-control/src/feetech.rs',[(328,341),(557,600),(695,704)]),
    (REPO/'tools/robotd-v03/patches/v03-unicast.patch',[(57,89),(103,114),(147,181)]),
]
r={'date':'2026-11-01','scope':'Source verification and earlier trace correlation; no live bus commands','sources':[]}
for p,ranges in files:
    lines=p.read_text(encoding='utf-8').splitlines()
    r['sources'].append({'path':p.relative_to(REPO).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
        'snippets':[{'start':a,'end':b,'text':'\n'.join(lines[a-1:b])} for a,b in ranges]})
live=json.loads((HERE/'port-serialization-audit-20261101.json').read_text(encoding='utf-8'))
r['servo_web_board_local_sha_match']={p.name:hashlib.sha256(p.read_bytes()).hexdigest()==live['board_sources']['/home/radxa/servo-web/'+p.name]['sha256'] for p,_ in files[:2]}
old=json.loads((HERE/'hold-home-replay-summary-20261101.json').read_text(encoding='utf-8'))
failed=old['failed_reads'][0]
off=next(e for e in old['event_window'] if e['address']==40 and e['opcode']==131 and float(e['timestamp'])>float(failed['timestamp']))
r['prior_trace_failure_window']={
    'imu_write_timestamp':failed['timestamp'],'imu_write_line':failed['line'],
    'first_read':failed['reads'][0],'next_native_write':{'timestamp':off['timestamp'],'opcode':off['opcode'],'address':off['address'],'line':off['line']},
    'intervening_uart_writes':[{'timestamp':e['timestamp'],'line':e['line'],'opcode':e['opcode'],'address':e['address']} for e in old['event_window'] if float(failed['timestamp'])<float(e['timestamp'])<float(off['timestamp'])],
    'limitation':'Prior trace covers control TID 1713, not every process; current /proc scan is a later snapshot'}
r['current_uart_holders']=live['uart_holders']
r['attempted_external_verification']={'web':'Two web tool calls to official Python/serialport docs returned no readable content; no external page asserted as verified',
    'wsl_registry':'Expected /root/.cargo/registry/src/*/serialport-4.9.0/src/posix/tty.rs not found; crate internals not used as evidence'}
out=HERE/'port-serialization-source-evidence-20261101.json'
out.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'output':str(out),'board_local_sha_match':r['servo_web_board_local_sha_match'],
                  'intervening_writes':r['prior_trace_failure_window']['intervening_uart_writes']},indent=2))
