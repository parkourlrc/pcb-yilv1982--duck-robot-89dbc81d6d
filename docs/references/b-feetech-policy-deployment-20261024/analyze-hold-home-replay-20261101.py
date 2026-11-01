#!/usr/bin/env python3
"""Offline decoding of the saved native syscall trace. Never accesses hardware."""
from collections import Counter
import datetime
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent
STEM = sys.argv[1] if len(sys.argv)>1 else 'hold-home-replay-20261101'
if not re.fullmatch(r'[a-z0-9-]+', STEM):
    raise SystemExit('Expected an experiment basename')
TRACE = ROOT/(STEM+'.log')
RESULT = ROOT/(STEM+'.json')
OUT = ROOT/('hold-home-replay-summary-20261101.json' if len(sys.argv)==1 else STEM+'-summary.json')
PATTERN = re.compile(r'^(\d+\.\d+) (read|write)\(11, "((?:\\x[0-9a-f]{2})*)", (\d+)\) = (\d+) <([\d.]+)>$')


def frame_decode(raw):
    frames, discarded = [], 0
    buf = raw
    while len(buf) >= 4:
        if buf[:2] != b'\xff\xff' or buf[3] < 2:
            discarded += 1
            buf = buf[1:]
            continue
        size = buf[3]+4
        if len(buf) < size:
            break
        f, buf = buf[:size], buf[size:]
        ok = sum(f[2:]) & 255 == 255
        row = {'hex': f.hex(), 'checksum_ok': ok, 'expected_checksum': f'{(~sum(f[2:-1])) & 255:02x}',
               'received_checksum': f'{f[-1]:02x}', 'sum_mod256': sum(f[2:]) & 255}
        if ok:
            row.update(id=f[2], error=f[4], data=f[5:-1].hex())
        frames.append(row)
    return {'frames': frames, 'discarded_bytes': discarded, 'trailing_hex': buf.hex()}


rows = []
for line_no, line in enumerate(TRACE.read_text(encoding='utf-8').splitlines(), 1):
    match = PATTERN.match(line)
    if not match:
        if re.match(r'^\d+\.\d+ (read|write)\(11,', line):
            raise ValueError(f'Unparsed UART syscall at line {line_no}')
        continue
    ts, op, escaped, requested, returned, duration = match.groups()
    raw = bytes.fromhex(escaped.replace('\\x', ''))
    if len(raw) != int(returned):
        raise ValueError(f'Unexpected syscall length at line {line_no}')
    row = {'line': line_no, 'timestamp': ts, 'operation': op, 'duration_us': int(Decimal(duration)*1000000),
           'raw_hex': raw.hex(), 'returned': int(returned)}
    if op == 'write':
        if len(raw) != int(requested) or sum(raw[2:]) & 255 != 255:
            raise ValueError(f'Incomplete/invalid write at line {line_no}')
        row.update(id=raw[2], opcode=raw[4], address=raw[5], length=raw[6])
        if raw[4] == 0x83:
            width = raw[6]
            row['targets'] = {str(raw[i]): raw[i+1:i+1+width].hex() for i in range(7, len(raw)-1, width+1)}
        row['reads'] = []
        rows.append(row)
    elif rows:
        rows[-1]['reads'].append(row)

for row in rows:
    rx = bytes.fromhex(''.join(x['raw_hex'] for x in row['reads']))
    row['rx_bytes'] = len(rx)
    row['rx_decoded'] = frame_decode(rx)
    if row['reads']:
        row['first_read_start_us'] = int((Decimal(row['reads'][0]['timestamp'])-Decimal(row['timestamp']))*1000000)

goals = [r for r in rows if r['opcode'] == 0x83 and r['address'] == 42]
torques = [r for r in rows if r['opcode'] == 0x83 and r['address'] == 40]
imu = [r for r in rows if r['id'] == 200 and r['opcode'] == 2]
servo_reads = [r for r in rows if r['opcode'] == 0x82 and r['address'] == 56]
expected_ids = {20,21,22,23,24,30,31,32,33,34,10,11,12,13,14}
servo_reads_valid = [r for r in servo_reads if r['rx_bytes'] == 315
                     and len(r['rx_decoded']['frames']) == 15
                     and all(f['checksum_ok'] and f.get('error') == 0 for f in r['rx_decoded']['frames'])
                     and {f.get('id') for f in r['rx_decoded']['frames']} == expected_ids]
tail_incomplete = (rows[-1] if rows and rows[-1] in servo_reads
                   and rows[-1] not in servo_reads_valid else None)
failed = [r for r in imu if not any(f.get('id') == 200 and f.get('error') == 0 and len(bytes.fromhex(f['data'])) == 15
                                  for f in r['rx_decoded']['frames'])]
meta = json.loads(RESULT.read_text(encoding='utf-8'))
pre = meta['pre_readback']['imu_diagnostics']['diagnostics']
post = meta['post_readback']['imu_diagnostics']['diagnostics']
origin = Decimal(goals[0]['timestamp'])
window = [r for r in rows if origin-Decimal('.02') <= Decimal(r['timestamp']) <= Decimal(torques[-1]['timestamp'])+Decimal('.01')]
for r in window:
    r['from_preload_us'] = int((Decimal(r['timestamp'])-origin)*1000000)
    r['beijing_time'] = datetime.datetime.fromtimestamp(float(r['timestamp']), datetime.timezone(datetime.timedelta(hours=8))).isoformat()
summary = {
    'source_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in [TRACE, RESULT]},
    'source_kind': 'Measured host syscalls with ptrace timing disturbance; not electrical waveforms',
    'hold_request_count': 1, 'rpc_response': meta['hold_response'],
    'counts': {'imu_reads': len(imu), 'imu_reads_with_valid_reply': len(imu)-len(failed),
               'imu_failed_reads': len(failed), 'goal_writes': len(goals),
               'servo_telemetry_reads': len(servo_reads), 'servo_telemetry_reads_valid': len(servo_reads_valid),
               'servo_read_incomplete_at_capture_tail': int(tail_incomplete is not None),
               'torque_writes': len(torques),
               'write_kinds': dict(Counter(f"id={r['id']} op={r['opcode']:02x} addr={r['address']} len={r['length']}" for r in rows))},
    'failed_reads': failed,
    'capture_tail_incomplete': tail_incomplete,
    'goal_writes': goals,
    'torque_writes': torques,
    'event_window': window,
    'diagnostic_delta': {k: post[k]-v for k,v in pre.items()},
    'pre_protection_registers_raw': meta['pre_readback']['servo_registers_9_39'],
    'post_torque_readback': meta['post_readback']['torque_off'],
    'final_state': {k:meta['final'].get(k) for k in ['session','phase','mode','torque_state','motion','policy_motion_enabled']},
    'scope_limits': ['Bad checksum payload is not used as valid gyro/status data',
                     'No automatic second hold attempt', 'No electrical or power waveform captured',
                     'Diagnostic snapshots include service startup/shutdown and are not instantaneous bus-boundary samples']
}
if len(failed) == 1:
    f = failed[0]
    previous = max((g for g in goals if Decimal(g['timestamp']) < Decimal(f['timestamp'])), key=lambda g:Decimal(g['timestamp']))
    summary['failed_read_after_previous_goal_return_us'] = int((Decimal(f['timestamp'])-Decimal(previous['timestamp']))*1000000)-previous['duration_us']
    next_off = next(t for t in torques if Decimal(t['timestamp']) > Decimal(f['timestamp']))
    summary['failed_read_to_native_off_write_us'] = int((Decimal(next_off['timestamp'])-Decimal(f['timestamp']))*1000000)
    summary['native_off_write_to_next_valid_imu_us'] = int((Decimal(next(i['timestamp'] for i in imu if Decimal(i['timestamp']) > Decimal(next_off['timestamp'])))-Decimal(next_off['timestamp']))*1000000)
OUT.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({k: v for k,v in summary.items() if k in ['counts','diagnostic_delta','failed_read_after_previous_goal_return_us',
    'failed_read_to_native_off_write_us','native_off_write_to_next_valid_imu_us','final_state']}, indent=2))
print('FAILED FRAMES', json.dumps([f['rx_decoded'] for f in failed]))
