#!/usr/bin/env python3
"""Read-only service/journal capture. Does not access the UART or change services."""
import datetime
import importlib.util
import json
import os
from pathlib import Path

sp=importlib.util.spec_from_file_location('diag',Path(__file__).with_name('imu-diagnostic-read-20261101.py'))
d=importlib.util.module_from_spec(sp)
sp.loader.exec_module(d)
r={'checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
   'user_power':{'source':'bench supply','voltage_set_v':7.4,'current_limit_a':3,
                 'cc_observation':'not observed'},
   'services':d.run(['systemctl','show','robotd','microduck-studio','-p','MainPID','-p','ActiveState','-p','UnitFileState']),
   'status':d.status(),
   'bus_held':Path('/run/microduck-helper/bus-held').exists(),
   'uart_driver':Path('/proc/tty/driver/serial').read_text(),
   'journal':d.run(['journalctl','-u','robotd','--since','2026-11-01 03:10:00 UTC','-o','short-iso-precise','--no-pager'])}
p=Path('/home/radxa/duck-runtime-stage-20261031/hold-timeout-final-read-20261101.json')
p.write_text(json.dumps(r,indent=2,ensure_ascii=False))
os.chown(p,1000,1000)
print(json.dumps({'output':str(p),'services':r['services'],
                  'status':{k:r['status'].get(k) for k in ['mode','phase','torque_state','motion','total_communication_failures']},
                  'bus_held':r['bus_held']}),flush=True)
