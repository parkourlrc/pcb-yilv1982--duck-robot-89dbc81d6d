#!/usr/bin/env python3
"""Bounded fixed-payload READ comparisons with all servos torque-off.

Diagnostic collector, not robotd. Never invokes the archived write experiment.
"""
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import time
import serial

ROOT = Path('/home/radxa/duck-runtime-stage-20261031')
OUT = ROOT / 'root-cause-fixed-read-20261101.json'
MARKER = OUT.with_suffix('.started')


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


d = load('fixed_diag', 'imu-diagnostic-read-20261101.py')
b = load('fixed_bus_helpers', 'imu-traffic-isolation-20261101.py')


class ReadOnlyPort:
    def __init__(self, port):
        self.port = port

    def __getattr__(self, name):
        return getattr(self.port, name)

    def write(self, packet):
        if (packet[:2] != b'\xff\xff' or packet[4] not in (2, 130)
                or len(packet) != packet[3] + 4 or sum(packet[2:]) & 255 != 255):
            raise RuntimeError('Only valid READ/SYNC_READ requests are allowed')
        return self.port.write(packet)


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def check_off():
    s = d.status()
    if (s.get('mode') != 'commissioning' or s.get('torque_state') != 'off'
            or s.get('motion') is not None or s.get('hold') is not None
            or Path('/run/microduck-helper/bus-held').exists()):
        raise RuntimeError('Requires idle commissioning, torque-off, Studio bus not held')
    return s


def main():
    if os.geteuid() != 0 or OUT.exists() or MARKER.exists():
        raise SystemExit('Requires root and a fresh evidence filename')
    with MARKER.open('x') as f:
        f.write(now() + ' READ-only comparison, no automatic repetition\n')
    r = {'started_utc': now(), 'scope': 'READ-only external diagnostic collector; not a native robotd run',
         'known_payload_source': 'replica 0.2.0 control_table.c: table[71:124] initialized to zero',
         'budget_ms': 20, 'period_ms': 20, 'cycles_per_condition': 1000, 'conditions': []}
    stopped = []
    try:
        r['before'] = check_off()
        r['helper_sha256'] = {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
                             for name in ['imu-diagnostic-read-20261101.py', 'imu-traffic-isolation-20261101.py']}
        for unit in ['microduck-studio', 'robotd']:
            if d.run(['systemctl', 'is-active', '--quiet', unit], False)['returncode'] == 0:
                stopped.append(unit)
                d.run(['systemctl', 'stop', unit])
                if unit == 'microduck-studio':
                    check_off()
        if d.run(['fuser', '/dev/ttyS2'], False)['stdout'].strip():
            raise RuntimeError('UART remains owned')
        with serial.Serial('/dev/ttyS2', 1000000, timeout=.001, write_timeout=.02, exclusive=True) as raw:
            port = ReadOnlyPort(raw)
            r['torque_before'] = b.require_off(port)
            r['imu_identity'] = d.read(port, 0, 9, .1)
            r['diagnostics_before'] = d.read(port, 124, 124, .1)
            for name, address, length, servo_first, gap_us in [
                ('dynamic_imu_first', 56, 15, False, 0),
                ('fixed_imu_first', 71, 53, False, 0),
                ('fixed_servo_first', 71, 53, True, 0),
                ('fixed_servo_first_gap500', 71, 53, True, 500),
            ]:
                phase = {'name': name, 'address': address, 'length': length,
                         'servo_first': servo_first, 'gap_us': gap_us, 'cycles': [],
                         'uart_before': Path('/proc/tty/driver/serial').read_text()}
                r['conditions'].append(phase)
                print(json.dumps({'condition_started': name, 'utc': now()}), flush=True)
                next_tick = time.monotonic()
                for index in range(1000):
                    time.sleep(max(0, next_tick - time.monotonic()))
                    started = time.monotonic()
                    deadline = started + .02
                    row = {'index': index, 'monotonic_ns': time.monotonic_ns()}
                    servo_request = b.packet(254, 130, [56, 15] + b.IDS)
                    imu_request = b.packet(200, 2, [address, length])
                    if servo_first:
                        row['servo'] = b.collect(port, servo_request, b.IDS, 15, deadline)
                        if row['servo']['ok']:
                            if gap_us:
                                time.sleep(gap_us / 1e6)
                            row['imu'] = b.collect(port, imu_request, [200], length, deadline)
                    else:
                        row['imu'] = b.collect(port, imu_request, [200], length, deadline)
                        if row['imu']['ok']:
                            row['servo'] = b.collect(port, servo_request, b.IDS, 15, deadline)
                    if address == 71 and row.get('imu', {}).get('ok'):
                        row['fixed_payload_matches'] = row['imu']['replies'][200] == '00' * length
                    for device in ['imu', 'servo']:
                        if row.get(device, {}).get('ok'):
                            row[device].pop('chunks', None)
                    phase['cycles'].append(row)
                    next_tick = max(started + .02, time.monotonic())
                phase['uart_after'] = Path('/proc/tty/driver/serial').read_text()
                phase['diagnostics_after'] = d.read(port, 124, 124, .1)
                phase['torque_after'] = b.require_off(port)
                phase['summary'] = {
                    'cycles': len(phase['cycles']),
                    'imu_attempts': sum('imu' in x for x in phase['cycles']),
                    'imu_failures': sum(not x['imu']['ok'] for x in phase['cycles'] if 'imu' in x),
                    'imu_bad_checksums': sum(x.get('imu', {}).get('bad_checksum', 0) for x in phase['cycles']),
                    'fixed_payload_mismatches': sum(x.get('fixed_payload_matches') is False for x in phase['cycles']),
                    'servo_failures': sum(not x['servo']['ok'] for x in phase['cycles'] if 'servo' in x),
                }
                OUT.write_text(json.dumps(r, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
                print(json.dumps({'condition_complete': name, **phase['summary']}), flush=True)
    except Exception as e:
        r['error'] = repr(e)
    finally:
        r['restored'] = {}
        for unit in reversed(stopped):
            r['restored'][unit] = d.run(['systemctl', 'start', unit], False)
        if stopped:
            time.sleep(2)
        try:
            r['after'] = d.status()
        except Exception as e:
            r['restore_status_error'] = repr(e)
        r['finished_utc'] = now()
        OUT.write_text(json.dumps(r, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
        os.chown(OUT, 1000, 1000)
        print(json.dumps({'output': str(OUT), 'error': r.get('error'), 'restored': r['restored'],
                          'torque_after_restore': r.get('after', {}).get('torque_state')}), flush=True)


if __name__ == '__main__':
    main()
