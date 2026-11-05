"""Install the approved recovery candidate once, while confirmed limp; no motion RPC."""
import argparse
import ast
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tarfile
import time

from probe import CFG, STUDIO, SLOTS, digest, inspect, rpc

HERE = Path(__file__).resolve().parent
PACKAGE_SHA = '23b6d73ac89a9a3494ddb0b4ca6758316e062e8c09ca3b7a338e42676273988d'
STUDIO_UNIT = 'microduck-studio.service'
ROBOT_UNIT = 'robotd.service'


def cmd(*args):
    process = subprocess.run(args, text=True, capture_output=True, timeout=40)
    if process.returncode:
        raise RuntimeError({'args': args, 'returncode': process.returncode, 'stderr': process.stderr})
    return process.stdout


def confirmed_idle(bus):
    return (bus.get('mode') == 'motion' and bus.get('phase') == 'control'
            and bus.get('policy_enabled') is False and bus.get('home_recovery') is False
            and bus.get('native', {}).get('torque_enabled') is False
            and bus.get('native', {}).get('torque_state_confirmed') is False)


def replace(path, data, metadata):
    temp = path.with_name(path.name + '.duck-recovery-install')
    with temp.open('xb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.chmod(temp, stat.S_IMODE(metadata.st_mode))
    os.chown(temp, metadata.st_uid, metadata.st_gid)
    os.replace(temp, path)
    fd = os.open(path.parent, os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def wait_ready(expected_recovery):
    end = time.monotonic() + 45
    last = None
    while time.monotonic() < end:
        try:
            bus = rpc('robot.busStatus')
            last = {'mode': bus.get('mode'), 'phase': bus.get('phase'), 'policy_enabled': bus.get('policy_enabled')}
            if bus.get('phase') == 'control':
                assert confirmed_idle(bus), 'Robot not confirmed limp after restart'
                loaded = bus.get('loaded_models') or {}
                assert all(loaded.get(slot) for slot in SLOTS), 'One or more of the six models is missing'
                assert bus.get('native', {}).get('imu_ready') is True
                assert bus.get('native', {}).get('all_joints_fresh') is True
                if expected_recovery:
                    assert bus.get('walk_recovery', {}).get('phase') == 'idle', 'Recovery state missing or unexpectedly active'
                    assert bus.get('build', '').endswith('+duck-recovery.1'), 'Wrong running build'
                return bus
        except (OSError, ValueError) as error:
            last = str(error)
        time.sleep(0.5)
    raise RuntimeError({'startup_timeout': last})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', required=True)
    args = parser.parse_args()
    assert args.apply and os.geteuid() == 0
    out = HERE / 'deployment.json'
    assert not out.exists(), 'Deployment already attempted; inspect the record before continuing'
    candidate = HERE / 'candidate.tar.gz'
    assert digest(candidate) == PACKAGE_SHA, 'Candidate archive SHA mismatch'
    manifest = json.loads((HERE / 'candidate-manifest.json').read_text())
    expected = manifest['candidate_files']
    with tarfile.open(candidate) as archive:
        names = {item.name for item in archive if item.isfile()}
        assert names == set(expected) | {'MANIFEST.json'}
        contents = {name: archive.extractfile(name).read() for name in expected}
    for name, data in contents.items():
        assert hashlib.sha256(data).hexdigest() == expected[name], name
        if name.endswith('.py'):
            ast.parse(data, filename=name)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    report = {'started_utc': datetime.now(timezone.utc).isoformat(), 'authorization': 'User requested deployment; confirmed torque OFF; no recovery or walking test', 'status': 'preflight', 'changed': []}
    originals, metadata, paths = {}, {}, {}
    studio_stopped = robot_stopped = False
    # /run is cleared on reboot; use the helper's ordinary root-owned runtime directory.
    Path('/run/microduck-helper').mkdir(mode=0o755, exist_ok=True)
    with open('/run/microduck-helper/helper.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            before = inspect()
            report['before'] = before
            assert not before['bus_held']
            assert confirmed_idle(before['robot.busStatus']), 'Require freshly confirmed torque OFF'
            assert before['configured_model_loading'] is True
            for name, value in before['files'].items():
                assert value == manifest['baseline_files'].get(name), f'Baseline drift: {name}'
            for unit, row in before['services'].items():
                assert row['ActiveState'] == 'active' and row['UnitFileState'] == 'enabled', unit
                assert '--commissioning' not in row.get('process_argv', []) and '--read-only' not in row.get('process_argv', [])
            for name in expected:
                paths[name] = Path(before['binary_resolved']) if name == 'bin/robotd' else STUDIO / name.removeprefix('studio/')
                originals[name] = paths[name].read_bytes() if paths[name].exists() else None
                metadata[name] = paths[name].stat() if paths[name].exists() else (STUDIO / 'studio/pad.py').stat()
            backup = CFG.parent / ('backup-before-duck-recovery-' + stamp)
            backup.mkdir(mode=0o700)
            report['backup'] = str(backup)
            for name, path in paths.items():
                if originals[name] is not None:
                    saved = backup / name
                    saved.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(path, saved)
            for path in before['protected']:
                if path.startswith('/etc/') and Path(path).is_file():
                    saved = backup / 'system' / path.lstrip('/')
                    saved.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(path, saved)
            (backup / 'before.json').write_text(json.dumps(before, indent=2) + '\n')
            cmd('systemctl', 'stop', STUDIO_UNIT)
            studio_stopped = True
            assert confirmed_idle(rpc('robot.busStatus')), 'State changed while stopping Studio; do not unload supporting torque'
            assert {path: digest(path) for path in before['protected']} == before['protected'], 'Protected files changed'
            cmd('systemctl', 'stop', ROBOT_UNIT)
            robot_stopped = True
            for name, path in paths.items():
                assert digest(path) == manifest['baseline_files'].get(name), f'File changed during preflight: {name}'
                replace(path, contents[name], metadata[name])
                report['changed'].append(name)
            cmd('systemctl', 'start', ROBOT_UNIT)
            robot_stopped = False
            report['startup_bus'] = wait_ready(True)
            cmd('systemctl', 'start', STUDIO_UNIT)
            studio_stopped = False
            after = inspect()
            report['after'] = after
            assert after['protected'] == before['protected'], 'Models, calibration or service/config files changed'
            assert after['files'] == expected, 'Installed file hashes differ'
            assert confirmed_idle(after['robot.busStatus'])
            for unit, row in after['services'].items():
                assert row['ActiveState'] == 'active' and row['UnitFileState'] == 'enabled', unit
            report['status'] = 'installed; six models loaded; recovery idle; confirmed torque OFF; no motion test'
        except Exception as error:
            report['error'] = str(error)
            if report['changed']:
                try:
                    cmd('systemctl', 'stop', STUDIO_UNIT)
                    cmd('systemctl', 'stop', ROBOT_UNIT)
                    for name in reversed(report['changed']):
                        path = paths[name]
                        assert digest(path) == expected[name], f'Concurrent edit prevents rollback: {name}'
                        if originals[name] is None:
                            path.unlink()
                        else:
                            replace(path, originals[name], metadata[name])
                    cmd('systemctl', 'start', ROBOT_UNIT)
                    report['rollback_bus'] = wait_ready(False)
                    cmd('systemctl', 'start', STUDIO_UNIT)
                    studio_stopped = robot_stopped = False
                    report['status'] = 'failed; original files restored and original services restarted'
                except Exception as rollback_error:
                    report['rollback_error'] = str(rollback_error)
                    report['status'] = 'failed; rollback needs attention'
            else:
                if robot_stopped:
                    cmd('systemctl', 'start', ROBOT_UNIT)
                if studio_stopped:
                    cmd('systemctl', 'start', STUDIO_UNIT)
                report['status'] = 'preflight failed; no file changes'
        finally:
            report['finished_utc'] = datetime.now(timezone.utc).isoformat()
            journal = subprocess.run(['journalctl', '-u', ROBOT_UNIT, '-u', STUDIO_UNIT, '--since', report['started_utc'], '--no-pager', '-n', '130'], text=True, capture_output=True, timeout=10)
            report['journal'] = journal.stdout
            out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
            os.chmod(out, 0o644)
    print(json.dumps({key: report.get(key) for key in ('status', 'error', 'backup', 'rollback_error')}))
    return 0 if report['status'].startswith('installed;') else 1


if __name__ == '__main__':
    raise SystemExit(main())
