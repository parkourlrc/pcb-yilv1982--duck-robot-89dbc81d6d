#!/usr/bin/env python3
"""One native hold-home timing comparison, runtime-only 10 Hz, restore 50 Hz."""
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import time
import tomllib

ROOT = Path('/home/radxa/duck-runtime-stage-20261031')
OUT = ROOT / 'root-cause-native-hz10-deployment-20261101.json'
CONFIG = Path('/run/robotd-root-cause-hz10-20261101.toml')
OVERRIDE = Path('/run/systemd/system/robotd.service.d/zzzzzz-root-cause-hz10-20261101.conf')
PRODUCTION = Path('/etc/robot/feetech-ft5/robotd.toml')
EXPECTED = '9f9fa71723339b80f97d7be065dec04855bb0d31a3ed7c5978e8605c22db3e5b'
AUTHORIZATION = 'User goal: find and fix root cause; user confirmed robot fixed and short stand comparisons allowed'


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def main():
    if os.geteuid() != 0 or OUT.exists() or CONFIG.exists() or OVERRIDE.exists():
        raise SystemExit('Requires root and fresh experiment paths')
    spec = importlib.util.spec_from_file_location('replay_hz10', ROOT/'hold-home-replay-20261101.py')
    replay = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(replay)
    stem = 'root-cause-native-hz10-20261101'
    replay.OUT = ROOT / (stem + '.json')
    replay.TRACE = ROOT / (stem + '.log')
    replay.MARKER = ROOT / (stem + '.attempted')
    r = {'started_utc': now(), 'authorization': AUTHORIZATION, 'maximum_attempts': 1,
         'variable': 'control.hz 50 to 10 for this experiment only',
         'limitations': '100 ms control interval also changes motion step spacing and fault detection cadence; not a production fix',
         'telemetry_deadline_ms': 20, 'hold_duration_ms': 3000,
         'production_before_sha256': hashlib.sha256(PRODUCTION.read_bytes()).hexdigest()}
    made_config = made_override = False
    try:
        r['before'] = replay.ready_off()
        r['uart_before'] = Path('/proc/tty/driver/serial').read_text()
        if r['before'].get('target_hz') != 50.0:
            raise RuntimeError('Expected original 50 Hz commissioning')
        if hashlib.sha256(Path('/usr/local/bin/robotd').read_bytes()).hexdigest() != EXPECTED:
            raise RuntimeError('Baseline robotd binary changed')
        original = PRODUCTION.read_text()
        before = tomllib.loads(original)
        candidate = original.replace('[control]\nhz = 50\n', '[control]\nhz = 10\n')
        after = tomllib.loads(candidate)
        expected = tomllib.loads(original)
        expected['control']['hz'] = 10
        if after != expected or before['control']['hz'] != 50:
            raise RuntimeError('Experimental config must change only control.hz')
        with CONFIG.open('x') as f:
            f.write(candidate)
        made_config = True
        CONFIG.chmod(0o600)
        OVERRIDE.parent.mkdir(parents=True, exist_ok=True)
        with OVERRIDE.open('x') as f:
            f.write('[Service]\nExecStart=\nExecStart=/opt/robot/daemon/current/bin/robotd '
                    f'--params {CONFIG} --socket /run/robotd.sock --commissioning\n')
        made_override = True
        r['experimental_config'] = candidate
        r['runtime_override'] = OVERRIDE.read_text()
        replay.d.run(['systemctl', 'daemon-reload'])
        # Existing helper performs the exclusive handoff, one native RPC, bounded wait,
        # native relax, physical torque-off readback and service restoration.
        replay.main()
        result = json.loads(replay.OUT.read_text())
        result['authorization'] = AUTHORIZATION
        result['experiment_control_hz'] = 10
        replay.OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        r['attempt_result'] = {'request_utc': result.get('hold_request_utc'),
                               'response': result.get('hold_response'), 'error': result.get('error'),
                               'observed_target_hz': result.get('before_hold', {}).get('target_hz'),
                               'torque_off': result.get('post_readback', {}).get('torque_off', {}).get('ok')}
        if r['attempt_result']['observed_target_hz'] != 10.0:
            raise RuntimeError('Requested comparison frequency was not observed')
    except Exception as e:
        r['error'] = repr(e)
    finally:
        if made_override:
            r['stop_studio'] = replay.d.run(['systemctl', 'stop', 'microduck-studio'], False)
            r['stop_robotd'] = replay.d.run(['systemctl', 'stop', 'robotd'], False)
            OVERRIDE.unlink()
            r['reload'] = replay.d.run(['systemctl', 'daemon-reload'], False)
        if made_config:
            CONFIG.unlink()
        if made_override:
            r['restore_robotd'] = replay.d.run(['systemctl', 'start', 'robotd'], False)
            r['restore_studio'] = replay.d.run(['systemctl', 'start', 'microduck-studio'], False)
            time.sleep(2)
        try:
            r['after'] = replay.wait_ready()
        except Exception as e:
            r['final_status_error'] = repr(e)
        r['production_after_sha256'] = hashlib.sha256(PRODUCTION.read_bytes()).hexdigest()
        r['uart_after'] = Path('/proc/tty/driver/serial').read_text()
        r['production_unchanged'] = r['production_before_sha256'] == r['production_after_sha256']
        r['runtime_override_removed'] = not OVERRIDE.exists()
        r['finished_utc'] = now()
        OUT.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding='utf-8')
        os.chown(OUT, 1000, 1000)
        print(json.dumps({'output': str(OUT), 'error': r.get('error'), 'attempt': r.get('attempt_result'),
                          'restored_hz': r.get('after', {}).get('target_hz'),
                          'final_torque': r.get('after', {}).get('torque_state'),
                          'production_unchanged': r['production_unchanged'],
                          'override_removed': r['runtime_override_removed']}), flush=True)


if __name__ == '__main__':
    main()
