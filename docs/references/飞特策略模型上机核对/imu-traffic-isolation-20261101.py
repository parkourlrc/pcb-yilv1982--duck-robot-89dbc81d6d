#!/usr/bin/env python3
"""ARCHIVED EXPERIMENT, DO NOT RUN: goal writes were observed to enable torque.

The write arm only repeats the existing six volatile goal bytes at 42..47,
read beforehand. This did NOT guarantee absence of motion. See research.md.
"""
import datetime
import importlib.util
import json
import os
from pathlib import Path
import time
import serial

spec = importlib.util.spec_from_file_location('diag', Path(__file__).with_name('imu-diagnostic-read-20261101.py'))
d = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d)
IDS = [20, 21, 22, 23, 24, 30, 31, 32, 33, 34, 10, 11, 12, 13, 14]
OUT = Path('/home/radxa/duck-runtime-stage-20261031/imu-traffic-isolation-20261101.json')

def packet(ident, instruction, params):
    body = bytes([ident, len(params)+2, instruction]) + bytes(params)
    return b'\xff\xff' + body + bytes([(~sum(body)) & 255])

def collect(port, request, ids, length, deadline):
    start = time.monotonic()
    port.reset_input_buffer()
    port.write(request)
    buf, raw, chunks, replies = bytearray(), bytearray(), [], {}
    bad = 0
    while time.monotonic() < deadline:
        chunk = port.read(port.in_waiting or 1)
        if not chunk:
            continue
        chunks.append([int((time.monotonic()-start)*1e6), chunk.hex()])
        raw.extend(chunk)
        buf.extend(chunk)
        while len(buf) >= 4:
            if buf[:2] != b'\xff\xff' or buf[3] < 2:
                del buf[0]
                continue
            size = buf[3]+4
            if len(buf) < size:
                break
            frame = bytes(buf[:size])
            del buf[:size]
            if sum(frame[2:]) & 255 != 255:
                bad += 1
                continue
            if frame == request:
                continue
            if frame[2] in ids and frame[4] == 0 and len(frame) == length+6:
                replies[frame[2]] = frame[5:-1].hex()
        if len(replies) == len(ids):
            break
    return {'ok': len(replies) == len(ids), 'elapsed_us': int((time.monotonic()-start)*1e6),
            'request': request.hex(), 'raw': raw.hex(), 'chunks': chunks, 'bad_checksum': bad,
            'missing': [i for i in ids if i not in replies], 'replies': replies}

def sync_read(port, address, length):
    return collect(port, packet(254, 130, [address, length]+IDS), IDS, length, time.monotonic()+.02)

def require_off(port):
    r = sync_read(port, 40, 1)
    if not r['ok'] or any(v != '00' for v in r['replies'].values()):
        raise RuntimeError('All 15 torque-off register readbacks required: ' + str(r))
    return r

def snapshot(port):
    time.sleep(.004)
    r = d.read(port, 124, 124, .1)
    if not r['ok']:
        raise RuntimeError('Diagnostic snapshot did not reply: ' + str(r))
    return r

def main():
    r = {'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
         'scope': 'torque stays OFF; C repeats unchanged register 42..47 values; 50 Hz',
         'phases': []}
    stopped = []
    try:
        r['before'] = d.status()
        if r['before'].get('torque_state') != 'off' or r['before'].get('motion') is not None:
            raise RuntimeError('Robot is not off and idle.')
        if Path('/run/microduck-helper/bus-held').exists():
            raise RuntimeError('Studio owns bus.')
        for unit in ['microduck-studio', 'robotd']:
            if d.run(['systemctl', 'is-active', '--quiet', unit], False)['returncode'] == 0:
                stopped.append(unit)
                d.run(['systemctl', 'stop', unit])
                if unit == 'microduck-studio' and d.status().get('torque_state') != 'off':
                    raise RuntimeError('Robot changed torque state.')
        if d.run(['fuser', '/dev/ttyS2'], False)['stdout'].strip():
            raise RuntimeError('Another process owns UART.')
        with serial.Serial('/dev/ttyS2', 1000000, timeout=.001, write_timeout=.02, exclusive=True) as port:
            r['torque_before'] = require_off(port)
            r['goals_before'] = sync_read(port, 42, 6)
            if not r['goals_before']['ok']:
                raise RuntimeError('Cannot read existing goals.')
            params = bytearray([42, 6])
            for ident in IDS:
                params.append(ident)
                params.extend(bytes.fromhex(r['goals_before']['replies'][ident]))
            write = packet(254, 131, params)
            assert len(write) == 113
            r['unchanged_goal_write'] = write.hex()
            for mode, n in [('imu_only', 1000), ('imu_servo_read', 1500), ('imu_servo_read_goal_write', 1500)]:
                phase = {'mode': mode, 'before': snapshot(port), 'cycles': []}
                r['phases'].append(phase)
                print('Starting ' + mode, flush=True)
                origin = time.monotonic()
                for index in range(n):
                    time.sleep(max(0, origin+index*.02-time.monotonic()))
                    tick = time.monotonic()
                    deadline = tick+.02
                    row = {'index': index, 't_us': int((tick-origin)*1e6)}
                    row['imu'] = collect(port, packet(200, 2, [56, 15]), [200], 15, deadline)
                    if row['imu']['ok'] and mode != 'imu_only':
                        row['servo'] = collect(port, packet(254, 130, [56, 15]+IDS), IDS, 15, deadline)
                        if row['servo']['ok'] and mode.endswith('goal_write'):
                            port.reset_input_buffer()
                            row['write_us'] = int((time.monotonic()-tick)*1e6)
                            port.write(write)
                    phase['cycles'].append(row)
                    if not row['imu']['ok']:
                        row['failure_diagnostics'] = snapshot(port)
                    # Avoid catch-up bursts after a timeout or diagnostic capture.
                    if time.monotonic() > origin+(index+1)*.02:
                        origin = time.monotonic()-(index+1)*.02
                phase['after'] = snapshot(port)
                phase['torque_after'] = require_off(port)
                phase['summary'] = {
                    'cycles': len(phase['cycles']),
                    'imu_failures': sum(not x['imu']['ok'] for x in phase['cycles']),
                    'servo_failures': sum(not x['servo']['ok'] for x in phase['cycles'] if 'servo' in x),
                    'counter_delta': {k: phase['after']['diagnostics'][k]-v for k, v in phase['before']['diagnostics'].items()}}
                print(json.dumps({'mode': mode, **phase['summary']}), flush=True)
            r['goals_after'] = sync_read(port, 42, 6)
            r['goals_unchanged'] = r['goals_after']['replies'] == r['goals_before']['replies']
    except Exception as e:
        r['error'] = repr(e)
    finally:
        r['restored'] = {u: d.run(['systemctl', 'start', u], False) for u in reversed(stopped)}
        time.sleep(2)
        try:
            r['after'] = d.status()
        except Exception as e:
            r['restore_status_error'] = repr(e)
        r['finished_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        OUT.write_text(json.dumps(r, ensure_ascii=False, separators=(',', ':')))
        os.chown(OUT, 1000, 1000)
        print(json.dumps({'output': str(OUT), 'error': r.get('error'), 'goals_unchanged': r.get('goals_unchanged'),
                          'after': {k: r.get('after', {}).get(k) for k in ['phase', 'mode', 'torque_state']}}), flush=True)

if __name__ == '__main__':
    raise SystemExit('Archived: goal writes enabled torque; this experiment is disabled.')
