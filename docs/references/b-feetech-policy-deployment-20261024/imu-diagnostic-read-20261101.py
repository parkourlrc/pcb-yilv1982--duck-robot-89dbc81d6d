#!/usr/bin/env python3
"""Bounded, READ-only diagnostic capture; requires robotd already torque-off."""
import datetime
import json
import os
from pathlib import Path
import socket
import subprocess
import time
import serial

OUT = Path('/home/radxa/duck-runtime-stage-20261031/imu-diagnostic-read-20261101.json')
FIELDS = dict(zip(range(148, 236, 4), [
    'samples', 'gyro_count', 'accel_count', 'uptime_ms', 'gyro_age_ms',
    'quat_age_ms', 'spi_errors', 'fifo_overflows', 'invalid_quaternions',
    'recovery_count', 'rx_overflows', 'uart_errors', 'crc_errors',
    'malformed_packets', 'receive_timeouts', 'rx_packets', 'tx_packets',
    'cancelled_replies', 'reset_flags', 'clock_hz', 'tx_timeouts', 'log_dropped']))
FIELDS.update({240: 'skipped_slots', 244: 'tx_busy_drops'})

def run(args, check=True):
    p = subprocess.run(args, capture_output=True, text=True, timeout=15)
    if check and p.returncode:
        raise RuntimeError(f'{args}: {p.returncode}: {p.stderr}')
    return {'returncode': p.returncode, 'stdout': p.stdout, 'stderr': p.stderr}

def status():
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.settimeout(3)
        s.connect('/run/robotd.sock')
        s.sendall(b'{"jsonrpc":"2.0","id":1,"method":"robot.busStatus","params":{}}\n')
        with s.makefile('rb') as f:
            r = json.loads(f.readline())
    if 'error' in r:
        raise RuntimeError(r['error'])
    return r['result']

def read(port, address, length, budget=0.02):
    body = bytes([200, 4, 2, address, length])
    request = b'\xff\xff' + body + bytes([(~sum(body)) & 255])
    port.reset_input_buffer()
    start = time.monotonic()
    port.write(request)
    raw, buf, chunks = bytearray(), bytearray(), []
    reply = None
    while time.monotonic() - start < budget:
        chunk = port.read(port.in_waiting or 1)
        if not chunk:
            continue
        chunks.append({'us': int((time.monotonic()-start)*1e6), 'hex': chunk.hex()})
        raw.extend(chunk)
        buf.extend(chunk)
        while len(buf) >= 4:
            if buf[:2] != b'\xff\xff':
                del buf[0]
                continue
            size = buf[3] + 4
            if size < 6:
                del buf[0]
                continue
            if len(buf) < size:
                break
            packet = bytes(buf[:size])
            del buf[:size]
            if sum(packet[2:]) & 255 != 255 or packet == request:
                continue
            if packet[2] == 200:
                reply = packet
                break
        if reply:
            break
    result = {'address': address, 'length': length, 'request': request.hex(),
              'raw': raw.hex(), 'elapsed_us': int((time.monotonic()-start)*1e6),
              'chunks': chunks, 'ok': bool(reply and reply[4] == 0 and len(reply) == length+6)}
    if reply:
        result['reply'] = reply.hex()
    if result['ok'] and address == 124 and length == 124:
        data = reply[5:-1]
        result['diagnostics'] = {name: int.from_bytes(data[a-124:a-120], 'little') for a, name in FIELDS.items()}
        result['diagnostics'].update({name: data[a-124] for a, name in [
            (144, 'whoami'), (145, 'imu_error'), (146, 'clock_status'),
            (147, 'watchdog'), (236, 'diagnostic_revision')]})
    return result

def main():
    r = {'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
         'scope': 'READ only; no torque/position/config writes', 'snapshots': [], 'reads': []}
    stopped = []
    try:
        if os.geteuid() != 0:
            raise RuntimeError('Requires root for service handoff and journal.')
        r['before'] = status()
        if r['before'].get('torque_state') != 'off' or r['before'].get('motion') is not None:
            raise RuntimeError('Robot is not confirmed torque-off and motion-idle.')
        if Path('/run/microduck-helper/bus-held').exists():
            raise RuntimeError('Studio owns bus; do not take over.')
        r['journal'] = run(['journalctl', '-u', 'robotd', '--since', '2026-11-01 02:45:00 UTC', '-o', 'short-iso-precise', '--no-pager'])
        for unit in ['microduck-studio', 'robotd']:
            if run(['systemctl', 'is-active', '--quiet', unit], False)['returncode'] == 0:
                # Stop Studio first so it cannot acquire the bus during the capture.
                stopped.append(unit)
                run(['systemctl', 'stop', unit])
                if unit == 'microduck-studio':
                    s = status()
                    if s.get('torque_state') != 'off' or s.get('motion') is not None:
                        raise RuntimeError('Robot changed state while stopping Studio.')
        holders = run(['fuser', '/dev/ttyS2'], False)
        if holders['stdout'].strip():
            raise RuntimeError('UART still owned: ' + holders['stdout'])
        with serial.Serial('/dev/ttyS2', 1000000, timeout=0.001, write_timeout=0.02, exclusive=True) as port:
            r['snapshots'].append(read(port, 124, 124, .1))
            for _ in range(200):
                begin = time.monotonic()
                r['reads'].append(read(port, 56, 15))
                time.sleep(max(0, .02-(time.monotonic()-begin)))
            r['snapshots'].append(read(port, 124, 124, .1))
    except Exception as e:
        r['error'] = repr(e)
    finally:
        r['restored'] = {}
        for unit in reversed(stopped):
            r['restored'][unit] = run(['systemctl', 'start', unit], False)
        if stopped:
            time.sleep(2)
            try:
                r['after'] = status()
            except Exception as e:
                r['restore_status_error'] = repr(e)
        r['finished_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        OUT.write_text(json.dumps(r, indent=2, ensure_ascii=False))
        os.chown(OUT, 1000, 1000)
        print(json.dumps({'output': str(OUT), 'error': r.get('error'),
                          'diagnostics': [x.get('diagnostics', x) for x in r['snapshots']],
                          'reads': len(r['reads']), 'failures': sum(not x['ok'] for x in r['reads']),
                          'after': {k: r.get('after', {}).get(k) for k in ['phase', 'mode', 'torque_state']},
                          'restored': r['restored']}, indent=2), flush=True)

if __name__ == '__main__':
    main()
