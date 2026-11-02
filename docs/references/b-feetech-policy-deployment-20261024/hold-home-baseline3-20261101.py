#!/usr/bin/env python3
"""Three newly user-authorized native hold attempts; preserve the prior one-shot.

Each attempt uses the already reviewed native-RPC capture and ends torque-off.
No automatic rerun/resume. This batch never modifies robotd or its configuration.
"""
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import time

ROOT=Path('/home/radxa/duck-runtime-stage-20261031')
OUT=ROOT/'hold-home-baseline3-20261101.json'
MARKER=ROOT/'hold-home-baseline3-20261101.started'
EXPECTED='9f9fa71723339b80f97d7be065dec04855bb0d31a3ed7c5978e8605c22db3e5b'


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def main():
    if os.geteuid()!=0:
        raise SystemExit('Root required by the existing capture wrapper')
    if OUT.exists() or MARKER.exists():
        raise SystemExit('Batch already reserved; refuse automatic repetition')
    with MARKER.open('x',encoding='utf-8') as f:
        f.write(now()+' Three further baseline attempts explicitly requested by user\n')
        f.flush(); os.fsync(f.fileno())
    r={'started_utc':now(),'authorization':'User requested three further baseline attempts, compare servo-web, then try servo-first',
       'maximum_attempts':3,'unchanged_robotd_sha256':EXPECTED,'attempts':[]}
    try:
        for index in range(1,4):
            actual=hashlib.sha256(Path('/opt/robot/daemon/current/bin/robotd').read_bytes()).hexdigest()
            if actual!=EXPECTED:
                raise RuntimeError('Baseline binary changed; no further baseline requests')
            spec=importlib.util.spec_from_file_location('replay',ROOT/'hold-home-replay-20261101.py')
            replay=importlib.util.module_from_spec(spec); spec.loader.exec_module(replay)
            stem=f'hold-home-baseline3-20261101-r{index}'
            replay.OUT=ROOT/(stem+'.json')
            replay.TRACE=ROOT/(stem+'.log')
            replay.MARKER=ROOT/(stem+'.attempted')
            replay.ready_off()
            print(json.dumps({'utc':now(),'baseline_attempt':index,'maximum':3}),flush=True)
            replay.main()
            attempt=json.loads(replay.OUT.read_text(encoding='utf-8'))
            attempt['batch_authorization']=r['authorization']
            attempt['batch_attempt']=index
            replay.OUT.write_text(json.dumps(attempt,ensure_ascii=False,indent=2),encoding='utf-8')
            row={'index':index,'path':str(replay.OUT),'request_utc':attempt.get('hold_request_utc'),
                 'response':attempt.get('hold_response'),'error':attempt.get('error'),
                 'final_torque':attempt.get('final',{}).get('torque_state'),
                 'physical_off_readback':attempt.get('post_readback',{}).get('torque_off',{}).get('ok')}
            r['attempts'].append(row)
            OUT.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8'); os.chown(OUT,1000,1000)
            print(json.dumps(row),flush=True)
            if (not row['request_utc'] or row['error'] or row['final_torque']!='off'
                    or row['physical_off_readback'] is not True or attempt.get('relax_error')
                    or attempt.get('post_readback_error') or attempt.get('off_confirmation_error')):
                raise RuntimeError('Stop batch: attempt did not finish with verified torque-off')
            response=row['response'] or {}
            if 'error' in response and 'imu_to_dxl ID200' not in response['error'].get('message',''):
                raise RuntimeError('Stop batch on a different native hold failure for inspection')
            if index<3:
                time.sleep(2)
    except Exception as e:
        r['error']=repr(e)
    finally:
        r['finished_utc']=now()
        OUT.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8'); os.chown(OUT,1000,1000)
        print(json.dumps({'output':str(OUT),'completed':len(r['attempts']),'error':r.get('error')}),flush=True)


if __name__=='__main__':
    main()
