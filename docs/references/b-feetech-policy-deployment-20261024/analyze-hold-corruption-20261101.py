#!/usr/bin/env python3
"""Offline byte/decoder diagnosis of existing captures. No hardware or serial opens."""
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import time

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
SERVO_WEB = REPO / 'tools/servo-web/feetech.py'
FIRMWARE = REPO / 'references/microduck-replica/hardware/imu_to_dxl/firmware'


class BusError(Exception):
    pass


class BusTimeout(BusError):
    pass


class MemorySerial:
    timeout = .02

    def __init__(self, data):
        self.data = data

    def read(self, length):
        out, self.data = self.data[:length], self.data[length:]
        return out


def load_web_status_reader():
    # Execute the current project's exact method against an in-memory byte stream.
    tree = ast.parse(SERVO_WEB.read_text(encoding='utf-8-sig'))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'FeetechBus')
    method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == '_read_status')
    namespace = {'time': time, 'BusError': BusError, 'BusTimeout': BusTimeout,
                 'hexs': lambda data: data.hex(' ')}
    exec(compile(ast.Module(body=[method], type_ignores=[]), str(SERVO_WEB), 'exec'), namespace)
    return namespace['_read_status']


def main():
    read_status = load_web_status_reader()
    comparisons = json.loads((ROOT / 'hold-repetitions-comparison-20261101.json').read_text(encoding='utf-8'))
    rows = []
    for entry in comparisons['rows']:
        stem = entry['experiment']
        name = 'hold-home-replay-summary-20261101.json' if stem == 'hold-home-replay-20261101' else stem + '-summary.json'
        summary = json.loads((ROOT / name).read_text(encoding='utf-8'))
        bad = summary['failed_reads'][0]
        raw = bytes.fromhex(entry['bad_frame_hex'])
        memory = SimpleNamespace(ser=MemorySerial(raw), stats=Counter(), trace=None)
        try:
            result = read_status(memory, 200)
            verdict = {'accepted': True, 'result': repr(result)}
        except BusError as exc:
            verdict = {'accepted': False, 'exception': type(exc).__name__, 'message': str(exc)}
        verdict['stats'] = dict(memory.stats)
        assert verdict['stats'].get('bad_checksum') == 1 and not verdict['accepted']
        # These field constraints come from replica 0.2.0 source, not from accepting the bad frame.
        violations = []
        if raw[2] != 200:
            violations.append({'offset': 2, 'field': 'ID', 'observed': f'{raw[2]:02x}', 'expected': 'c8'})
        if raw[18] & 0xf0:
            violations.append({'offset': 18, 'register': 69, 'field': 'status', 'observed': f'{raw[18]:02x}', 'expected': 'bits 4..7 zero'})
        if raw[19] != 0:
            violations.append({'offset': 19, 'register': 70, 'field': 'reserved', 'observed': f'{raw[19]:02x}', 'expected': '00'})
        valid_count = 0
        valid_statuses = Counter()
        neighbor_frames = []
        for transaction in summary['event_window']:
            if transaction['id'] != 200 or transaction['opcode'] != 2:
                continue
            for frame in transaction['rx_decoded']['frames']:
                if not frame['checksum_ok'] or frame.get('id') != 200:
                    continue
                packet = bytes.fromhex(frame['hex'])
                mock = SimpleNamespace(ser=MemorySerial(packet), stats=Counter(), trace=None)
                sid, err, data = read_status(mock, 200)
                assert sid == 200 and err == 0 and len(data) == 15
                assert data[13] & 0xf0 == 0 and data[14] == 0
                valid_statuses[f'{data[13]:02x}'] += 1
                valid_count += 1
                neighbor_frames.append({'time': transaction['timestamp'], 'frame': frame['hex'],
                                        'sequence': data[12], 'status': data[13], 'reserved': data[14]})
        rows.append({'experiment': stem, 'bad_frame_hex': raw.hex(),
                     'bad_frame_is_one_read_syscall': len(bad['reads']) == 1,
                     'read_returned_bytes': [r['returned'] for r in bad['reads']],
                     'read_durations_us': [r['duration_us'] for r in bad['reads']],
                     'fixed_field_violations': violations, 'servo_web_offline_verdict': verdict,
                     'nearby_valid_frames_accepted_by_servo_web': valid_count,
                     'nearby_valid_statuses': dict(valid_statuses), 'nearby_valid_frames': neighbor_frames,
                     'sources': summary['source_sha256']})
    source_files = [SERVO_WEB] + [FIRMWARE / p for p in [
        'Core/Src/main.c', 'Core/Src/protocol.c', 'Core/Src/board.c', 'Core/Src/control_table.c',
        'Core/Src/imu.c', 'Core/Inc/protocol.h', 'Core/Inc/control_table.h', 'Build/imu_to_dxl.hex']]
    report = {'date': '2026-11-01', 'method': 'Offline existing host syscall captures and current local source only',
              'rows': rows, 'source_sha256': {str(p.relative_to(REPO)): hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files},
              'limits': [
                  'Invalid frames are not sensor samples; fixed-field comparisons do not identify original bytes or the corruption location.',
                  'Block 56/15 contains gyro int16 x3, quaternion FP16 x3, sequence, status, reserved; not four int16 quaternion components.',
                  'Memory replay verifies byte acceptance only; it does not reproduce servo-web live timing or electrical load.',
                  'Firmware analysis uses archived replica 0.2.0 source and deployment history; no fresh flash/RAM readback in this analysis.',
                  'Firmware receive error counters do not validate its outgoing bytes at the host; TX routine disables USART2 IRQ and clears flags before re-enabling.',
                  'No packet is repaired, passed to robotd, or used to move the robot.'
              ]}
    output = ROOT / 'hold-corruption-analysis-20261101.json'
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'output': str(output), 'bad_rejected': len(rows),
                      'valid_accepted': sum(r['nearby_valid_frames_accepted_by_servo_web'] for r in rows),
                      'fixed_field_violations': {r['experiment']:r['fixed_field_violations'] for r in rows}}, ensure_ascii=False))


if __name__ == '__main__':
    main()
