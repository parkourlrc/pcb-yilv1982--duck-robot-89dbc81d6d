#!/usr/bin/env python3
"""One authorized native Studio hold-home replay with bounded syscall capture.

User confirmed support and ONE attempt on 2026-11-01. The exclusive marker is
created before sending that request; never remove it to retry this experiment.
No direct goal writes. Production robotd retains all its existing protections.
"""
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import threading
import time
import tomllib

import serial

ROOT = Path('/home/radxa/duck-runtime-stage-20261031')
OUT = ROOT / 'hold-home-replay-20261101.json'
TRACE = ROOT / 'hold-home-replay-20261101.log'
MARKER = ROOT / 'hold-home-replay-20261101.attempted'
IDS = [20, 21, 22, 23, 24, 30, 31, 32, 33, 34, 10, 11, 12, 13, 14]


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


d = load('diag', 'imu-diagnostic-read-20261101.py')
b = load('busread', 'imu-traffic-isolation-20261101.py')


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def rpc(method, params, timeout=3):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        sock.connect('/run/robotd.sock')
        with sock.makefile('rb') as f:
            for ident, meth, par in [(1, 'hello', {'api_version': 42}), (2, method, params)]:
                sock.sendall((json.dumps({'jsonrpc': '2.0', 'id': ident, 'method': meth, 'params': par})+'\n').encode())
                while True:
                    line = f.readline()
                    if not line:
                        raise RuntimeError('RPC connection closed')
                    result = json.loads(line)
                    if result.get('id') == ident:
                        break
                if ident == 1 and 'error' in result:
                    raise RuntimeError(result['error'])
            return result


def ready_off():
    s = d.status()
    if (s.get('mode') != 'commissioning' or s.get('phase') != 'ready'
            or s.get('torque_state') != 'off' or s.get('motion') is not None
            or s.get('hold') is not None or s.get('policy_motion_enabled')
            or Path('/run/microduck-helper/bus-held').exists()):
        raise RuntimeError('Robot must be commissioning/ready/off without a hold or bus owner')
    servos = s.get('last_sample', {}).get('servos', [])
    if {x['id'] for x in servos} != set(IDS):
        raise RuntimeError('Expected telemetry from all 15 servos')
    return s


def wait_ready():
    deadline = time.monotonic()+8
    while True:
        try:
            return ready_off()
        except Exception:
            if time.monotonic() >= deadline:
                raise
            time.sleep(.2)


def read_snapshot():
    if d.run(['fuser', '/dev/ttyS2'], False)['stdout'].strip():
        raise RuntimeError('UART is still owned; refuse independent READ')
    with serial.Serial('/dev/ttyS2', 1000000, timeout=.001, write_timeout=.02, exclusive=True) as port:
        snap = {'utc': now(), 'torque_off': b.require_off(port)}
        snap['servo_registers_9_39'] = b.sync_read(port, 9, 31)
        snap['servo_registers_40_52'] = b.sync_read(port, 40, 13)
        snap['imu_diagnostics'] = d.read(port, 124, 124, .1)
        return snap


def main():
    if os.geteuid() != 0:
        raise SystemExit('Root required for tracing and service handoff')
    if MARKER.exists() or OUT.exists() or TRACE.exists():
        raise SystemExit('Existing experiment output/attempt marker; automatic repetition refused')
    r = {'started_utc': now(), 'authorization': 'User: supported, one attempt allowed',
         'scope': 'Native hold-home RPC, one attempt, duration_ms=3000; no production changes',
         'instrumentation_limit': 'ptrace changes syscall timing; Studio stopped to exclude concurrent commands',
         'status_samples': [], 'events': []}
    active = []
    trace = None
    attempted = False
    hold_thread = None

    def save():
        OUT.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding='utf-8')
        os.chown(OUT, 1000, 1000)

    def event(name, **data):
        item = {'utc': now(), 'name': name, **data}
        r['events'].append(item)
        print(json.dumps(item), flush=True)

    try:
        r['before'] = ready_off()
        for unit in ['microduck-studio', 'robotd']:
            if d.run(['systemctl', 'is-active', '--quiet', unit], False)['returncode'] == 0:
                active.append(unit)
        if set(active) != {'microduck-studio', 'robotd'}:
            raise RuntimeError('Both existing services must start active')
        for unit in active:
            d.run(['systemctl', 'stop', unit])
            if unit == 'microduck-studio':
                ready_off()
        r['pre_readback'] = read_snapshot()
        for key in ['servo_registers_9_39', 'servo_registers_40_52']:
            if not r['pre_readback'][key]['ok']:
                raise RuntimeError('Preflight register read incomplete: '+key)
        calibration = Path('/etc/robot/feetech-ft5/hd1910-calibration.toml')
        r['calibration_text'] = calibration.read_text(encoding='utf-8')
        c = tomllib.loads(r['calibration_text'])
        if [j['id'] for j in c['joints']] != IDS or any(j['direction'] != -1 for j in c['joints']):
            raise RuntimeError('Calibration directions/order differ from verified Studio payload')
        if Path('/home/radxa/studio-dev/state/servo-directions.json').exists():
            raise RuntimeError('New Studio direction override requires inspection before replay')
        r['file_sha256'] = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in [
            calibration, Path('/etc/robot/feetech-ft5/robotd.toml'),
            Path('/opt/robot/daemon/current/bin/robotd')]}
        d.run(['systemctl', 'start', 'robotd'])
        r['before_hold'] = wait_ready()
        pid = int(d.run(['systemctl', 'show', 'robotd', '-p', 'MainPID', '--value'])['stdout'])
        cmdline = (Path('/proc')/str(pid)/'cmdline').read_bytes().replace(b'\x00', b' ').decode()
        r['cmdline'] = cmdline
        if '--commissioning' not in cmdline:
            raise RuntimeError('Unexpected daemon mode')
        tasks = [p for p in (Path('/proc')/str(pid)/'task').iterdir() if (p/'comm').read_text().strip() == 'control']
        if len(tasks) != 1:
            raise RuntimeError('Expected one control thread')
        r['pid'], r['control_tid'] = pid, int(tasks[0].name)
        r['trace_args'] = [str(ROOT/'diagnostic-tools/strace/usr/bin/strace'), '-qq', '-ttt', '-T', '-xx',
                           '-s', '512', '-e', 'trace=read,write,ioctl,poll,ppoll', '-p', str(r['control_tid']), '-o', str(TRACE)]
        trace = subprocess.Popen(r['trace_args'], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        deadline = time.monotonic()+3
        while 'TracerPid:\t'+str(trace.pid) not in (tasks[0]/'status').read_text():
            if trace.poll() is not None or time.monotonic() > deadline:
                raise RuntimeError('strace did not attach')
            time.sleep(.02)
        time.sleep(.4)
        ready_off()
        r['payload'] = {'action': 'hold-home', 'directions': [-1]*15, 'duration_ms': 3000}
        with MARKER.open('x', encoding='utf-8') as f:
            f.write(now()+' ONE authorized request reserved; do not repeat\n')
            f.flush()
            os.fsync(f.fileno())
        attempted = True

        def hold():
            r['hold_request_utc'] = now()
            try:
                r['hold_response'] = rpc('robot.busCommand', r['payload'], 20)
            except Exception as e:
                r['hold_exception'] = repr(e)
            finally:
                r['hold_response_utc'] = now()

        event('one_hold_home_request', payload=r['payload'])
        save()
        hold_thread = threading.Thread(target=hold, daemon=True)
        hold_thread.start()
        # Native settle limit is 5 seconds; stop this experiment at 6 seconds.
        deadline = time.monotonic()+6
        while hold_thread.is_alive() and time.monotonic() < deadline:
            s = d.status()
            r['status_samples'].append({'utc': now(), 'status': s})
            time.sleep(.1)
        event('hold_wait_finished', response=r.get('hold_response'), exception=r.get('hold_exception'))
    except Exception as e:
        r['error'] = repr(e)
        event('experiment_error', error=repr(e))
    finally:
        if attempted:
            try:
                r['relax_request_utc'] = now()
                r['relax_response'] = rpc('robot.relax', {}, 5)
                r['after_relax'] = wait_ready()
                event('native_off_confirmed', torque_state=r['after_relax']['torque_state'])
            except Exception as e:
                r['relax_error'] = repr(e)
                # Restarting commissioning performs its native verified torque-off startup.
                r['fallback_restart'] = d.run(['systemctl', 'restart', 'robotd'], False)
                try:
                    r['after_relax'] = wait_ready()
                except Exception as e2:
                    r['off_confirmation_error'] = repr(e2)
            if hold_thread:
                hold_thread.join(timeout=1)
        if trace:
            time.sleep(.3)
            if trace.poll() is None:
                trace.send_signal(signal.SIGINT)
            try:
                _, r['trace_stderr'] = trace.communicate(timeout=3)
            except subprocess.TimeoutExpired:
                trace.kill()
                _, r['trace_stderr'] = trace.communicate(timeout=3)
            r['trace_exit'] = trace.returncode
            if TRACE.exists():
                os.chown(TRACE, 1000, 1000)
        if attempted and 'off_confirmation_error' not in r:
            try:
                ready_off()
                d.run(['systemctl', 'stop', 'robotd'])
                r['post_readback'] = read_snapshot()
                event('physical_torque_readback', off=r['post_readback']['torque_off']['ok'])
            except Exception as e:
                r['post_readback_error'] = repr(e)
        r['restored'] = {u: d.run(['systemctl', 'start', u], False) for u in reversed(active)}
        try:
            r['final'] = wait_ready()
        except Exception as e:
            r['final_error'] = repr(e)
        r['finished_utc'] = now()
        since = datetime.datetime.fromisoformat(r['started_utc']).strftime('%Y-%m-%d %H:%M:%S UTC')
        r['journal'] = d.run(['journalctl', '-u', 'robotd', '--since', since, '-o', 'short-iso-precise', '--no-pager'], False)
        save()
        event('saved', output=str(OUT), attempted=attempted, final_torque=r.get('final', {}).get('torque_state'))
        save()


if __name__ == '__main__':
    main()
