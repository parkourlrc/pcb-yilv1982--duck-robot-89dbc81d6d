"""Approved systemd migration; daemon-reload and native dry-run only, no restart."""
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import stat
import subprocess
import tomllib

HERE = Path(__file__).resolve().parent
OUT = HERE / 'deployment.json'
UNIT = Path('/etc/systemd/system/robotd.service')
OLD = UNIT.with_name('robotd.service.d') / '30-studio-commissioning.conf'
NEW = OLD.with_name('zzzz-zz-microduck-commissioning.conf')
LOCK = Path('/run/microduck-helper/helper.lock')
CAL = Path('/etc/robot/feetech-ft5/hd1910-calibration.toml')
STATE = Path('/home/radxa/studio-dev/state')
HELPER = '/usr/local/sbin/microduck-helper'
SERVICES = ['robotd.service', 'microduck-studio.service']

def sha(path):
    p = Path(path)
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None

def command(args, payload=None, check=True):
    p = subprocess.run(args, input=None if payload is None else json.dumps(payload),
                       text=True, capture_output=True, timeout=25)
    row = {'args':args, 'returncode':p.returncode, 'stdout':p.stdout, 'stderr':p.stderr}
    if check and p.returncode:
        raise RuntimeError(row)
    return row

def services():
    out = {}
    for name in SERVICES:
        p = command(['systemctl','show',name,'-p','MainPID','-p','ActiveState','-p','UnitFileState','-p','ExecStart'])
        row = dict(line.split('=',1) for line in p['stdout'].splitlines() if '=' in line)
        pid = int(row['MainPID'])
        assert pid > 0 and row['ActiveState'] == 'active' and row['UnitFileState'] == 'enabled'
        row['proc_cmdline'] = Path(f'/proc/{pid}/cmdline').read_bytes().decode().split('\0')[:-1]
        row['start_ticks'] = Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[19]
        row['configured_argv'] = re.search(r'argv\[\]=(.*?) ;', row['ExecStart']).group(1)
        out[name] = row
    return out

def same_processes(before, after):
    for name in SERVICES:
        for key in ['MainPID','start_ticks','proc_cmdline','configured_argv','ActiveState','UnitFileState']:
            assert before[name][key] == after[name][key], (name,key,before[name][key],after[name][key])

def rpc(method, params):
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as s:
        s.settimeout(5)
        s.connect('/run/robotd.sock')
        s.sendall(json.dumps({'jsonrpc':'2.0','id':1,'method':method,'params':params}).encode()+b'\n')
        with s.makefile('rb') as f:
            r = json.loads(f.readline())
    if 'error' in r:
        raise RuntimeError(r)
    return r['result']

def helper_result(row):
    lines = [json.loads(line) for line in row['stdout'].splitlines() if line.strip()]
    done = [line for line in lines if line.get('step') == 'done'][-1]
    assert row['returncode'] == 0 and done['detail']['exit'] == 0, done
    return done['detail']

def atomic(path, raw, metadata):
    temp = path.with_name(path.name + '.studio-handover-tmp')
    with temp.open('xb') as f:
        f.write(raw)
        f.flush()
        os.fsync(f.fileno())
    os.chmod(temp, stat.S_IMODE(metadata.st_mode))
    os.chown(temp, metadata.st_uid, metadata.st_gid)
    os.replace(temp,path)

def idle_handover():
    assert not Path('/run/microduck-helper/bus-held').exists(), 'Studio owns the bus'
    assert not OLD.with_name('zzzzzz-studio-imu-recalibrate.conf').exists(), 'IMU redo override is active'
    manifest = Path('/var/lib/microduck-helper/imu-recalibrate/manifest.json')
    if manifest.exists():
        assert json.loads(manifest.read_text()).get('active') is False, 'IMU redo session is active/unknown'

def main():
    assert os.geteuid() == 0, 'root is required'
    assert not OUT.exists(), 'One-time migration already has a result'
    source = json.loads((HERE/'source-manifest.json').read_text())
    candidates = {UNIT:(HERE/'robotd.service').read_bytes(), NEW:(HERE/NEW.name).read_bytes()}
    protected = [CAL, CAL.parent/'robotd.toml', STATE/'servo-centered.json', STATE/'servo-directions.json',
                 STATE/'imu-pending.json', OLD.with_name('zzzz-studio-bus.conf'), Path(HELPER),
                 Path('/opt/robot/daemon/current/bin/robotd'), Path('/home/radxa/studio-dev/studio/commit.py')]
    record = {'date':'2026-11-01', 'started_board_utc_clock':datetime.now(timezone.utc).isoformat(),
              'authorization':'User approved systemd migration and dry-run; no restart, torque or real commit',
              'steps':[], 'source_manifest':source}
    originals, metadata = {}, {}
    fd, locked, changed = None, False, False

    def save():
        OUT.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        os.chown(OUT,1000,1000)

    try:
        fd = os.open(LOCK, os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        locked = True
        idle_handover()
        assert not NEW.exists() and not NEW.is_symlink(), 'Official override already exists; inspect first'
        for path in [UNIT, OLD]:
            assert not path.is_symlink() and sha(path) == source['originals'][str(path)]['sha256'], path
            originals[path] = path.read_bytes()
            metadata[path] = path.stat()
        assert sha(HELPER) == source['helper_sha256'], 'Helper changed since analysis'
        assert candidates[UNIT] == originals[UNIT].replace(b' (v0.3 read-only commissioning)',b' (Studio calibration handover)').replace(b' --read-only\n',b'\n')
        assert candidates[NEW] == originals[OLD], 'Preserve exact current commissioning override'
        before = services()
        record['services_before'] = before
        assert before['robotd.service']['proc_cmdline'][-1] == '--commissioning'
        bus_before = rpc('robot.busStatus',{})
        record['bus_before'] = bus_before
        assert bus_before['mode'] == 'commissioning'
        record['protected_before'] = {str(p):sha(p) for p in protected}
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        backup = CAL.parent / ('backup-before-studio-handover-'+stamp)
        backup.mkdir(mode=0o700)
        for path in [UNIT,*sorted(OLD.parent.glob('*.conf'))]:
            shutil.copy2(path,backup/path.name)
        record['backup'] = str(backup)
        record['originals'] = {str(p):{'sha256':sha(p),'text':originals[p].decode()} for p in originals}
        save()
        changed = True
        atomic(NEW,candidates[NEW],metadata[OLD])
        atomic(UNIT,candidates[UNIT],metadata[UNIT])
        assert sha(OLD) == source['originals'][str(OLD)]['sha256']
        OLD.unlink()
        record['steps'].append(command(['systemctl','daemon-reload']))
        record['services_after_reload'] = services()
        same_processes(before,record['services_after_reload'])
        read = command([HELPER,'calib-read'], {'by':'codex-handover-read'})
        record['helper_read'] = read
        detail = helper_result(read)
        assert detail['mode'] == 'commissioning' and detail['commissioning_present'] is True
        record['protected_after_reload'] = {str(p):sha(p) for p in protected}
        assert record['protected_after_reload'] == record['protected_before'], 'Protected data changed during migration'
        record['installed'] = {str(p):{'sha256':sha(p),'text':p.read_text()} for p in candidates}
        save()
        # Native dry-run takes this same lock itself. Release our migration lock first.
        fcntl.flock(fd, fcntl.LOCK_UN)
        locked = False
        data = tomllib.loads(CAL.read_text())
        dirs_path = STATE/'servo-directions.json'
        dirs = json.loads(dirs_path.read_text()) if dirs_path.exists() else {}
        rows = [{'id':j['id'],'direction':dirs.get(str(j['id']),j['direction'])} for j in data['joints']]
        assert len(rows) == 15 and len({j['id'] for j in rows}) == 15
        pending_path = STATE/'imu-pending.json'
        pending = json.loads(pending_path.read_text()) if pending_path.exists() else None
        bus = rpc('robot.busStatus',{})
        if pending:
            assert pending['source'] == 'bus'
            for key in ['protocol','profile','board']:
                assert pending['imu_bus'].get(key) == bus['imu_bus'].get(key), ('pending transport',key)
            imu = {'source':'bus','quat':pending['quat']}
        else:
            assert data['imu_mount_verified'] is True
            imu = {'source':'bus','quat':data['imu_mount_quat']}
        payload = {'by':'codex-handover-preview','joints':rows,'imu':imu,'dry_run':True}
        record['preview_payload'] = payload
        record['preview'] = command([HELPER,'calib-commit'],payload,check=False)
        preview = helper_result(record['preview'])
        assert preview['result'] == 'preview' and preview['dry_run'] is True and preview['mode'] == 'commissioning'
        preview_toml = tomllib.loads(preview['toml'])
        assert len(preview_toml['joints']) == 15 and all(j['zero_raw'] == 2048 for j in preview_toml['joints'])
        record['preview_calibration'] = preview_toml
        record['services_final'] = services()
        same_processes(before,record['services_final'])
        record['bus_final'] = rpc('robot.busStatus',{})
        assert record['bus_final']['mode'] == 'commissioning'
        record['protected_final'] = {str(p):sha(p) for p in protected}
        assert record['protected_final'] == record['protected_before'], 'Concurrent protected data change; inspect without overwriting it'
        record['status'] = 'installed; native preview passed; no restart or real commit'
        record['unchanged_processes'] = True
        record['protected_files_unchanged'] = True
    except Exception as exc:
        record['error'] = f'{type(exc).__name__}: {exc}'
        record['status'] = 'failed; no service restart attempted'
        if changed:
            try:
                if not locked:
                    fcntl.flock(fd,fcntl.LOCK_EX | fcntl.LOCK_NB)
                    locked = True
                # Never undo an intervening user commit or another configuration change.
                assert UNIT.read_bytes() in (originals[UNIT],candidates[UNIT])
                assert not OLD.exists() or OLD.read_bytes() == originals[OLD]
                assert NEW.exists() and NEW.read_bytes() == candidates[NEW]
                atomic(OLD,originals[OLD],metadata[OLD])
                atomic(UNIT,originals[UNIT],metadata[UNIT])
                NEW.unlink()
                record['steps'].append(command(['systemctl','daemon-reload']))
                record['rolled_back_configuration'] = True
                record['services_after_rollback'] = services()
            except Exception as rollback_error:
                record['rollback_error'] = f'{type(rollback_error).__name__}: {rollback_error}'
        raise
    finally:
        if fd is not None:
            os.close(fd)
        record['finished_board_utc_clock'] = datetime.now(timezone.utc).isoformat()
        save()
    print(json.dumps({'status':record['status'],'backup':record['backup'],
                      'pids':{n:record['services_final'][n]['MainPID'] for n in SERVICES},
                      'helper_mode':detail['mode'],'preview':preview['result'],
                      'phase':record['bus_final'].get('phase'),'torque':record['bus_final'].get('torque_state'),
                      'protected_files_unchanged':record['protected_files_unchanged']},indent=2))

if __name__ == '__main__':
    main()
