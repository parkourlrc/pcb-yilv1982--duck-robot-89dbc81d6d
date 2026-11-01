"""Approved one-field policy loading change; restart and read-only verification.

This does not issue robot.enable, robot.init, torque, skill or velocity RPCs.
The user must support the robot because the native daemon restarts limp.
"""
from datetime import datetime, timezone
import difflib
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
import time
import tomllib

HERE = Path(__file__).resolve().parent
OUT = HERE / 'deployment.json'
CFG = Path('/etc/robot/feetech-ft5/robotd.toml')
CAL = CFG.with_name('hd1910-calibration.toml')
SLOTS = ('walk', 'sitstand', 'ground_pick', 'kick_left', 'kick_right', 'roulade')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def command(args):
    p = subprocess.run(args, text=True, capture_output=True, timeout=30)
    return {'args': args, 'returncode': p.returncode, 'stdout': p.stdout, 'stderr': p.stderr}


def rpc(method):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.settimeout(3)
        s.connect('/run/robotd.sock')
        s.sendall(json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': {}}).encode() + b'\n')
        with s.makefile('rb') as f:
            row = json.loads(f.readline())
    if 'error' in row:
        raise RuntimeError(row)
    return row['result']


def services():
    return {s: command(['systemctl', 'show', s, '-p', 'MainPID', '-p', 'ActiveState', '-p', 'UnitFileState'])
            for s in ('robotd.service', 'microduck-studio.service')}


def atomic(raw, metadata):
    temp = CFG.with_name('robotd.toml.webpad-tmp')
    with temp.open('xb') as f:
        f.write(raw)
        f.flush()
        os.fsync(f.fileno())
    os.chmod(temp, stat.S_IMODE(metadata.st_mode))
    os.chown(temp, metadata.st_uid, metadata.st_gid)
    os.replace(temp, CFG)


def main():
    # Do not replay a one-time deployment automatically.
    assert not OUT.exists(), 'This deployment already has a record; inspect it instead of rerunning'
    assert os.geteuid() == 0, 'Run with sudo after explicit support/restart authorization'
    started = datetime.now(timezone.utc)
    record = {'date': '2026-11-01', 'started_board_utc': started.isoformat(),
              'authorization': 'User confirmed support and one-field loading change with restart; no motion',
              'status': 'preflight'}
    changed = False
    with open('/run/microduck-helper/helper.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            assert not Path('/run/microduck-helper/bus-held').exists(), 'Studio owns the bus'
            for name in ('zzzz-zz-microduck-commissioning.conf', '30-studio-commissioning.conf',
                         'zzzzzz-studio-imu-recalibrate.conf'):
                assert not Path('/etc/systemd/system/robotd.service.d', name).exists(), name
            before = CFG.read_bytes()
            metadata = CFG.stat()
            params = tomllib.loads(before.decode())
            assert params['policy']['enabled'] is False
            record['before_services'] = services()
            record['before_bus'] = rpc('robot.busStatus')
            assert record['before_bus']['mode'] == 'motion' and record['before_bus']['phase'] == 'control'
            assert record['before_bus']['policy_enabled'] is False, 'A policy is already running'
            protected = [CAL, Path('/etc/systemd/system/robotd.service'),
                         Path('/opt/robot/daemon/current/bin/robotd')]
            for slot in SLOTS:
                model = Path(params['policy'][slot])
                assert model.is_file(), model
                protected.append(model)
                protected.extend(sorted(model.parent.glob('*.json')))
            record['protected_before'] = {str(p): digest(p) for p in protected}
            text = before.decode()
            match = re.search(r'(?ms)^\[policy\][^\n]*\n(.*?)(?=^\[|\Z)', text)
            assert match is not None
            section, count = re.subn(r'(?m)^(enabled\s*=\s*)false(\s*(?:#.*)?)$', r'\g<1>true\2', match[1])
            assert count == 1
            proposed = (text[:match.start(1)] + section + text[match.end(1):]).encode()
            after_params = tomllib.loads(proposed.decode())
            after_params['policy']['enabled'] = False
            assert after_params == params, 'More than the approved field changed'
            record['diff'] = ''.join(difflib.unified_diff(text.splitlines(True), proposed.decode().splitlines(True),
                                                         fromfile='robotd.toml/before', tofile='robotd.toml/after'))
            backup = CFG.parent / ('backup-before-webpad-policy-' + started.strftime('%Y%m%dT%H%M%S%fZ'))
            backup.mkdir(mode=0o700)
            shutil.copy2(CFG, backup / CFG.name)
            shutil.copy2(CAL, backup / CAL.name)
            record['backup'] = str(backup)
            assert CFG.read_bytes() == before, 'Configuration changed during preflight'
            atomic(proposed, metadata)
            changed = True
            record['restart'] = command(['systemctl', 'restart', 'robotd.service'])
            assert record['restart']['returncode'] == 0, record['restart']
            deadline = time.monotonic() + 40
            attempts = []
            while time.monotonic() < deadline:
                try:
                    bus = rpc('robot.busStatus')
                    policies = rpc('robot.policies')
                    bindings = rpc('pad.bindings')
                    if (bus.get('mode') == 'motion' and bus.get('phase') == 'control'
                            and bus.get('loaded_models') and policies['enabled']
                            and len(bindings['bindings']) == 5
                            and all(not b.get('error') for b in bindings['bindings'])):
                        record['after_bus'] = bus
                        record['after_policies'] = policies
                        record['after_bindings'] = bindings
                        break
                    attempts.append({'mode': bus.get('mode'), 'phase': bus.get('phase'),
                                     'loaded_models': bus.get('loaded_models'), 'policies': policies})
                except Exception as e:
                    attempts.append({'error': str(e)})
                time.sleep(1)
            else:
                record['load_attempts'] = attempts
                raise RuntimeError('Model loading/read-only verification did not complete within 40 seconds')
            assert bus['policy_enabled'] is False, 'An external client enabled motion'
            assert bus['native']['torque_enabled'] is False, 'Torque unexpectedly on'
            # Option<bool>: False means confirmed OFF; None means unknown.
            assert bus['native']['torque_state_confirmed'] is False, 'Torque OFF is unconfirmed'
            assert all(not s.get('error') for s in policies['slots']), policies
            assert CFG.read_bytes() == proposed
            record['protected_after'] = {str(p): digest(p) for p in protected}
            assert record['protected_after'] == record['protected_before']
            record['after_health'] = rpc('robot.health')
            record['after_skills'] = rpc('robot.skills')
            record['after_services'] = services()
            assert record['after_services']['microduck-studio.service'] == record['before_services']['microduck-studio.service']
            for service in record['after_services'].values():
                assert 'ActiveState=active' in service['stdout'] and 'UnitFileState=enabled' in service['stdout']
            record['status'] = 'success: models loaded and bindings registered; torque off; motion not enabled'
        except Exception as e:
            record['error'] = str(e)
            record['status'] = 'failed before modification' if not changed else 'failed after modification'
            if changed:
                record['failure_journal'] = command(['journalctl', '-u', 'robotd.service', '--since',
                                                      started.strftime('%Y-%m-%d %H:%M:%S'), '--no-pager', '-n', '100'])
                if CFG.read_bytes() == proposed:
                    atomic(before, metadata)
                    record['rollback_restart'] = command(['systemctl', 'restart', 'robotd.service'])
                    record['status'] = 'failed; original config restored; see rollback_restart result'
                else:
                    record['rollback_skipped'] = 'Concurrent configuration edit: preserved user changes'
        finally:
            record['finished_board_utc'] = datetime.now(timezone.utc).isoformat()
            record['journal'] = command(['journalctl', '-u', 'robotd.service', '--since',
                                         started.strftime('%Y-%m-%d %H:%M:%S'), '--no-pager', '-n', '100'])
            OUT.write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'status': record['status'], 'error': record.get('error'), 'backup': record.get('backup'),
                      'record': str(OUT)}, ensure_ascii=True))
    return 0 if record['status'].startswith('success:') else 1


if __name__ == '__main__':
    raise SystemExit(main())
