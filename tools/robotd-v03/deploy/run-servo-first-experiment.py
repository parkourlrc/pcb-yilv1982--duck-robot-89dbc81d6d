#!/usr/bin/env python3
"""Install the authorized order experiment, replay ONE hold, retain only on success.

A failed trial restores the previous binary. Configuration and calibration are
never written. Reuses the previously verified bounded native-RPC capture.
"""
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil

ROOT=Path('/home/radxa/duck-runtime-stage-20261031')
OUT=ROOT/'servo-first-deployment-20261101.json'
MARKER=ROOT/'servo-first-deployment-20261101.started'
TRIAL=ROOT/'robotd-servo-first-20261101'
OLD_SHA='9f9fa71723339b80f97d7be065dec04855bb0d31a3ed7c5978e8605c22db3e5b'
NEW_SHA='595cb3781b032d0a9547a4362daba6be8beef40727ebe7f2811ab65f31d2430e'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def main():
    if os.geteuid()!=0 or OUT.exists() or MARKER.exists():
        raise SystemExit('Root required, and prior experiment must not exist')
    spec=importlib.util.spec_from_file_location('replay',ROOT/'hold-home-replay-20261101.py')
    replay=importlib.util.module_from_spec(spec); spec.loader.exec_module(replay)
    binary=Path('/opt/robot/daemon/current/bin/robotd').resolve()
    backup=binary.with_name('robotd.pre-servo-first-20261101')
    temporary=binary.with_name('robotd.servo-first-tmp-20261101')
    if sha(binary)!=OLD_SHA or sha(TRIAL)!=NEW_SHA or backup.exists() or temporary.exists():
        raise SystemExit('Unexpected baseline/trial file identity or existing backup')
    before=replay.ready_off()
    with MARKER.open('x',encoding='utf-8') as f:
        f.write(now()+' One servo-first hold comparison authorized after three baseline trials\n')
        f.flush(); os.fsync(f.fileno())
    r={'started_utc':now(),'authorization':'User explicitly requested three repeats, wait/error comparison, then servo-first trial',
       'before':before,'binary':str(binary),'backup':str(backup),'old_sha256':OLD_SHA,'trial_sha256':NEW_SHA,
       'scope':'Strict commissioning/read-only telemetry order only; shared budget and guards unchanged'}
    configs=[Path('/etc/robot/feetech-ft5/robotd.toml'),Path('/etc/robot/feetech-ft5/hd1910-calibration.toml')]
    r['config_sha_before']={str(p):sha(p) for p in configs}
    switched=False
    keep=False

    def save():
        OUT.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8'); os.chown(OUT,1000,1000)

    def install(source):
        replay.d.run(['systemctl','stop','microduck-studio'])
        replay.ready_off()
        replay.d.run(['systemctl','stop','robotd'])
        shutil.copyfile(source,temporary)
        os.chmod(temporary,0o755)
        os.chown(temporary,0,0)
        os.replace(temporary,binary)
        replay.d.run(['systemctl','start','robotd'])
        state=replay.wait_ready()
        replay.d.run(['systemctl','start','microduck-studio'])
        return state

    try:
        shutil.copy2(binary,backup)
        save()
        switched=True  # any failure after this point must restore the old program
        r['trial_startup']=install(TRIAL)
        if 'duck-v03.2-servo-first' not in r['trial_startup'].get('build',''):
            raise RuntimeError('Started program did not report expected trial build')
        print(json.dumps({'utc':now(),'trial_started':r['trial_startup']['build']}),flush=True)
        replay.OUT=ROOT/'hold-home-servo-first-20261101.json'
        replay.TRACE=ROOT/'hold-home-servo-first-20261101.log'
        replay.MARKER=ROOT/'hold-home-servo-first-20261101.attempted'
        replay.main()
        attempt=json.loads(replay.OUT.read_text(encoding='utf-8'))
        r['trial_response']=attempt.get('hold_response')
        r['trial_error']=attempt.get('error')
        keep=(bool((r['trial_response'] or {}).get('result',{}).get('holding'))
              and attempt.get('final',{}).get('torque_state')=='off'
              and attempt.get('post_readback',{}).get('torque_off',{}).get('ok') is True
              and not any(attempt.get(k) for k in ['error','relax_error','post_readback_error','off_confirmation_error','final_error']))
        r['trial_complete_stand']=keep
    except Exception as e:
        r['error']=repr(e)
    finally:
        if switched and not keep:
            try:
                try:
                    replay.ready_off()
                except Exception:
                    # The existing native relax is the first recovery for lost hold status.
                    r['recovery_relax']=replay.rpc('robot.relax',{},5)
                    replay.wait_ready()
                r['restored_startup']=install(backup)
                r['rolled_back']=sha(binary)==OLD_SHA
                print(json.dumps({'utc':now(),'rolled_back':r['rolled_back'],'response':r.get('trial_response'),'error':r.get('error')}),flush=True)
            except Exception as e:
                r['rollback_error']=repr(e)
        try:
            r['final']=replay.wait_ready()
        except Exception as e:
            r['final_error']=repr(e)
        r['active_binary_sha256']=sha(binary)
        r['config_sha_after']={str(p):sha(p) for p in configs}
        r['services']={u:replay.d.run(['systemctl','is-active',u],False) for u in ['robotd','microduck-studio']}
        r['finished_utc']=now()
        r['kept_trial_binary']=keep
        save()
        print(json.dumps({'output':str(OUT),'kept_trial':keep,'rolled_back':r.get('rolled_back'),
                          'final_torque':r.get('final',{}).get('torque_state'),'error':r.get('error'),
                          'rollback_error':r.get('rollback_error')}),flush=True)


if __name__=='__main__':
    main()
