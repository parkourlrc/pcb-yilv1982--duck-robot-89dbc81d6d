"""Verify captured wire packets and replay IMU payloads through the restored parser."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys

here = Path(__file__).resolve().parent
repo = here.parents[2]
sys.path.insert(0, str(repo / 'tools/servo-web'))
import imu_bus

parser = argparse.ArgumentParser()
parser.add_argument('trace', type=Path)
parser.add_argument('out', type=Path)
args = parser.parse_args()
expected = [200, 20, 21, 22, 23, 24, 30, 31, 32, 33, 34, 10, 11, 12, 13, 14]
tx = Counter()
rx = Counter()
checksums = Counter()
cycles = []
imu_bits = Counter()
replayed = Counter()
windows = set()
counter_steps = Counter()
previous_counter = None
service = imu_bus.BusImuService(poll_hz=10)
payloads = []
unknown = []
for number, line in enumerate(args.trace.read_text(encoding='utf-8').splitlines(), 1):
    match = re.search(r'(ff ff(?: [0-9a-f]{2})+)', line)
    if not match:
        unknown.append({'line': number, 'text': line})
        continue
    packet = bytes.fromhex(match.group(1))
    checksums['valid' if sum(packet[2:]) % 256 == 255 and len(packet) == packet[3]+4 else 'invalid'] += 1
    if '→' in line:
        tx[f'id={packet[2]} instruction=0x{packet[4]:02x}'] += 1
        if packet[4] == 0x82:
            cycles.append({'address': packet[5], 'length': packet[6], 'ids': list(packet[7:-1]), 'received': []})
    elif '←' in line:
        rx[str(packet[2])] += 1
        if cycles:
            cycles[-1]['received'].append(packet[2])
        if packet[2] == 200 and packet[3] == 17:
            block = packet[5:-1]
            imu_bits[block[13]] += 1
            payloads.append(block)
            windows.add(block[:12])
            if previous_counter is not None:
                counter_steps[(block[12]-previous_counter) % 256] += 1
            previous_counter = block[12]
            replayed[service.feed(block, now=len(payloads)*0.1)['status']] += 1

result = {'source_trace': args.trace.name, 'tx_by_kind': dict(tx), 'rx_by_id': dict(rx),
          'packet_checks': dict(checksums), 'mixed_sync_requests': len(cycles),
          'all_requests_expected': all(c['address']==56 and c['length']==15 and c['ids']==expected for c in cycles),
          'complete_16_reply_cycles': sum(c['received']==expected for c in cycles),
          'incomplete_cycles': [dict(index=i, **c) for i,c in enumerate(cycles) if c['received']!=expected],
          'imu_blocks': len(payloads), 'imu_unique_first12': len(windows),
          'imu_bits': dict(imu_bits), 'imu_counter_steps_mod256': dict(counter_steps),
          'restored_legacy_replay_status': dict(replayed), 'unparsed_lines': unknown,
          'limitations': 'Application bus logger timestamps are not wire edge timings; WebSocket IMU broadcasts may repeat samples.'}
args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps(result, ensure_ascii=False, indent=2))
