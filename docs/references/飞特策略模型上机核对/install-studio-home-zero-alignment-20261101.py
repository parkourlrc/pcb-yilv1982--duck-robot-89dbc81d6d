"""Approved zero-only correction; service startup relaxes, no stand/model command."""
from datetime import datetime, timezone
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import time
import tomllib
import urllib.request

STAGE = Path('/home/radxa/studio-home-zero-alignment-20261101-retry1')
OUT = STAGE/'deployment.json'
CAL = Path('/etc/robot/feetech-ft5/hd1910-calibration.toml')
PARAMS = CAL.parent/'robotd.toml'
STATE = Path('/home/radxa/studio-dev/state')
EXPECTED = {20:2035,21:2176,22:1977,23:1392,24:1893,30:2526,31:2228,32:1952,33:1599,
            34:1372,10:1974,11:1760,12:1799,13:1908,14:1611}

def sha(path):
    p = Path(path)
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None

def command(args, check=True):
    p = subprocess.run(args,capture_output=True,text=True,timeout=25)
    out = {'args':args,'returncode':p.returncode,'stdout':p.stdout.strip(),'stderr':p.stderr.strip()}
    if check and p.returncode: raise RuntimeError(out)
    return out

def rpc(method, params):
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as s:
        s.settimeout(6);s.connect('/run/robotd.sock')
        s.sendall(json.dumps({'jsonrpc':'2.0','id':1,'method':method,'params':params}).encode()+b'\n')
        with s.makefile('rb') as f:
            data=json.loads(f.readline())
    if 'error' in data:raise RuntimeError(data)
    return data['result']

def main():
    assert os.geteuid()==0
    assert not OUT.exists(),'One-time deployment already recorded'
    STAGE.mkdir(exist_ok=True)
    protected = [PARAMS, STATE/'servo-centered.json', STATE/'servo-directions.json',
                 Path('/opt/robot/daemon/current/bin/robotd')]
    record = {'date':'2026-11-01','started_board_utc_clock':datetime.now(timezone.utc).isoformat(),
              'authorization':'用户确认已托稳，按 zero_raw=2048 方案修正；只读验收，不试站姿',
              'protected_before':{str(p):sha(p) for p in protected},'steps':[]}
    backup = None
    written = False

    def save():
        OUT.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        os.chown(OUT,1000,1000)

    try:
        record['services_before']={n:command(['systemctl','is-active',n],False) for n in ['robotd.service','microduck-studio.service']}
        record['steps'].append(command(['systemctl','stop','microduck-studio.service']))
        record['steps'].append(command(['systemctl','stop','robotd.service']))
        current_bytes=CAL.read_bytes()
        current=current_bytes.decode('utf-8')
        old=tomllib.loads(current)
        joints=old['joints']
        assert len(joints)==15 and {j['id'] for j in joints}==set(EXPECTED)
        centered=json.loads((STATE/'servo-centered.json').read_text())
        assert set(centered)>={str(i) for i in EXPECTED},'All 15 center records required'
        dirs_path=STATE/'servo-directions.json'
        dirs=json.loads(dirs_path.read_text()) if dirs_path.exists() else {}
        for j in joints:
            assert j['zero_raw'] in (EXPECTED[j['id']],2048),'Zero changed since analysis; preserve it'
            assert j['direction']==dirs.get(str(j['id']),-1),'Directions no longer match Studio'
        record['calibration_before']=old
        record['before_sha256']=hashlib.sha256(current_bytes).hexdigest()
        stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        backup=CAL.parent/('backup-before-zero-alignment-'+stamp)
        backup.mkdir()
        shutil.copy2(CAL,backup/CAL.name)
        record['backup']=str(backup/CAL.name)
        new,count=re.subn(r'(?P<key>"?zero_raw"?\s*=\s*)\d+',lambda m:m['key']+'2048',current)
        assert count==15
        expected=copy.deepcopy(old)
        for j in expected['joints']:j['zero_raw']=2048
        assert tomllib.loads(new)==expected
        temporary=CAL.with_name(CAL.name+'.zero-align-tmp')
        assert not temporary.exists()
        shutil.copy2(CAL,temporary)
        temporary.write_text(new,encoding='utf-8')
        os.replace(temporary,CAL)
        written=True
        record['after_sha256']=sha(CAL)
        record['calibration_after']=tomllib.loads(CAL.read_text())
        record['only_zero_values_changed']=record['calibration_after']==expected
        save()
        record['steps'].append(command(['systemctl','start','robotd.service']))
        record['steps'].append(command(['systemctl','start','microduck-studio.service']))
        for attempt in range(15):
            try:
                bus=rpc('robot.busStatus',{})
                if bus.get('phase')=='ready' and bus.get('torque_state')=='off':break
            except (OSError,RuntimeError) as exc:
                record['startup_wait_last_error']=str(exc)
            time.sleep(1)
        else:raise RuntimeError('robotd not ready/off after restart')
        record['bus_status_after']=bus
        calibration=rpc('robot.busCommand',{'action':'calibration-status'})
        record['calibration_status_after']=calibration
        assert calibration['calibration']['joints']==expected['joints']
        assert calibration['calibration']['imu_mount_quat']==old['imu_mount_quat']
        assert calibration['calibration']['imu_mount_verified']==old['imu_mount_verified']
        assert calibration['calibration']['motion_enabled']==old['motion_enabled']
        assert bus['policy_motion_enabled'] is False and bus['motion'] is None
        for attempt in range(15):
            try:
                with urllib.request.urlopen('http://127.0.0.1:8000/',timeout=2) as response:
                    record['studio_http_status']=response.status
                if record['studio_http_status']==200:
                    record['studio_startup_attempts']=attempt+1
                    break
            except OSError as exc:
                record['studio_startup_wait_last_error']=str(exc)
            time.sleep(1)
        else:raise RuntimeError('Studio HTTP not ready after bounded startup wait')
        record['protected_after']={str(p):sha(p) for p in protected}
        assert record['protected_before']==record['protected_after']
        record['services_after']={n:command(['systemctl','is-active',n],False) for n in ['robotd.service','microduck-studio.service']}
        assert all(s['stdout']=='active' for s in record['services_after'].values())
        record['status']='installed and read back; no stand or model command'
    except Exception as exc:
        record['error']=f'{type(exc).__name__}: {exc}'
        record['status']='failed; services stopped for inspection'
        command(['systemctl','stop','microduck-studio.service','robotd.service'],False)
        if written and backup is not None:
            shutil.copy2(backup/CAL.name,CAL)
            record['restored_backup']=True
        raise
    finally:
        record['finished_board_utc_clock']=datetime.now(timezone.utc).isoformat()
        save()
    print(json.dumps({'status':record['status'],'only_zero_values_changed':record['only_zero_values_changed'],
                      'protected_files_unchanged':record['protected_before']==record['protected_after'],
                      'zero_raw':{j['id']:j['zero_raw'] for j in record['calibration_after']['joints']},
                      'phase':bus['phase'],'torque':bus['torque_state'],'studio_http_status':record['studio_http_status'],
                      'backup':record['backup']},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
