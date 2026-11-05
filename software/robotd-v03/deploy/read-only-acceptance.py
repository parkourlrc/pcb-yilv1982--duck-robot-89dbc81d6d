#!/usr/bin/python3
"""One bounded native read-only window; always restore the original serial owner."""
import datetime
import json
import os
from pathlib import Path
import socket
import subprocess
import time

STAGE = Path('/home/radxa/duck-runtime-stage-20261031')
RESULT = STAGE / 'v03-read-only-acceptance.json'
USER_SERVICE = ['runuser', '-u', 'radxa', '--', 'env',
                'XDG_RUNTIME_DIR=/run/user/1000',
                'DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus',
                'systemctl', '--user']


def run(args, check=True):
    return subprocess.run(args, capture_output=True, text=True, check=check)


def read_status():
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as conn:
        conn.settimeout(3)
        conn.connect('/run/robotd.sock')
        conn.sendall(b'{"jsonrpc":"2.0","id":1,"method":"robot.busStatus","params":{}}\n')
        with conn.makefile('rb') as stream:
            reply = json.loads(stream.readline())
    if 'error' in reply:
        raise RuntimeError(reply['error'])
    return reply['result']


def main():
    if os.geteuid() != 0:
        raise SystemExit('Run as root.')
    unit = run(['systemctl', 'show', 'robotd', '-p', 'ExecStart', '--value']).stdout
    if '--read-only' not in unit:
        raise SystemExit('Installed service does not explicitly use --read-only.')
    if run(['systemctl', 'is-active', '--quiet', 'robotd'], check=False).returncode == 0:
        raise SystemExit('robotd is already running; owner handoff was not established.')
    was_active = run(USER_SERVICE + ['is-active', '--quiet', 'duck-servo-web'], check=False).returncode == 0
    result = {'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'servo_web_was_active': was_active, 'snapshots': []}
    try:
        if was_active:
            run(USER_SERVICE + ['stop', 'duck-servo-web'])
        holders = run(['fuser', '/dev/ttyS2'], check=False)
        if holders.stdout.strip():
            raise RuntimeError('Serial bus still has an owner: ' + holders.stdout.strip())
        run(['systemctl', 'start', 'robotd'])
        deadline = time.monotonic() + 10
        while True:
            try:
                state = read_status()
                if state.get('phase') == 'reading':
                    break
                result['startup_status'] = state
            except (OSError, RuntimeError) as error:
                result['startup_error'] = str(error)
            if time.monotonic() >= deadline:
                raise RuntimeError('No native reading status within 10 seconds.')
            time.sleep(0.25)
        for _ in range(7):
            state = read_status()
            if state.get('mode') != 'read_only' or not state.get('motor_writes_blocked'):
                raise RuntimeError('Read-only status not confirmed.')
            result['snapshots'].append(state)
            print(json.dumps({key: state.get(key) for key in [
                'build', 'phase', 'total_cycles', 'total_success',
                'total_communication_failures', 'total_imu_faults', 'achieved_hz'] }), flush=True)
            if len(result['snapshots']) < 7:
                time.sleep(5)
        result['read_window_completed'] = True
    except Exception as error:
        result['error'] = str(error)
    finally:
        stopped = run(['systemctl', 'stop', 'robotd'], check=False)
        result['robotd_stop_exit'] = stopped.returncode
        if was_active:
            restored = run(USER_SERVICE + ['start', 'duck-servo-web'], check=False)
            result['servo_web_restore_exit'] = restored.returncode
        result['robotd_active_after'] = run(['systemctl', 'is-active', 'robotd'], check=False).stdout.strip()
        result['servo_web_active_after'] = run(USER_SERVICE + ['is-active', 'duck-servo-web'], check=False).stdout.strip()
        result['finished_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        RESULT.write_text(json.dumps(result, ensure_ascii=False, indent=2))
        os.chown(RESULT, 1000, 1000)
    if 'error' in result or result.get('robotd_stop_exit') or result.get('servo_web_restore_exit'):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
