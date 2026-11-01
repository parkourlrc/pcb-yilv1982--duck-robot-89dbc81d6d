#!/usr/bin/env python3
"""Run archived protocol.c/control_table.c against virtual timing in WSL, without hardware."""
import ctypes as c
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
FW = REPO / 'references/microduck-replica/hardware/imu_to_dxl/firmware'
READ = bytes.fromhex('ffffc80402380fea')


def main():
    sources = [FW / p for p in ['Core/Src/protocol.c', 'Core/Src/control_table.c', 'Tests/bus_sim_shim.c']]
    results = []
    with tempfile.TemporaryDirectory(prefix='duck-imu-timing-') as temporary:
        library = Path(temporary) / 'protocol.so'
        command = ['cc', '-shared', '-fPIC', '-std=c11', '-O0', '-Wall', '-Wextra',
                   '-I', str(FW / 'Core/Inc'), *map(str, sources), '-o', str(library)]
        build = subprocess.run(command, cwd=temporary, capture_output=True, text=True)
        build.check_returncode()
        lib = c.CDLL(str(library))
        lib.shim_feed.argtypes = [c.c_uint8, c.c_uint32]
        lib.shim_poll.argtypes = [c.c_uint32]
        lib.shim_take_tx.argtypes = [c.POINTER(c.c_uint8), c.c_int]
        lib.shim_counters.argtypes = [c.POINTER(c.c_uint32)]
        lib.shim_set_snapshot.argtypes = [c.c_int, c.c_int, c.c_int16, c.c_int16, c.c_int16,
                                          c.c_uint16, c.c_uint16, c.c_uint16, c.c_uint32]

        def reset():
            lib.shim_init()
            lib.shim_set_snapshot(1, 0, 1, 2, 3, 0x3000, 0x3000, 0x3000, 10)

        def feed(packet, now=1000, special_gap=None):
            for i, byte in enumerate(packet):
                now += special_gap if special_gap is not None and i == 4 else 10
                lib.shim_feed(byte, now)
            return now

        def outcome(label, expected_tx, expected_cancel=0, expected_rx_timeout=0, **details):
            data = (c.c_uint8 * 300)()
            length = lib.shim_take_tx(data, 300)
            counters = (c.c_uint32 * 7)()
            lib.shim_counters(counters)
            counts = dict(zip(['rx_packets', 'tx_packets', 'crc_errors', 'malformed_packets',
                               'receive_timeouts', 'cancelled_replies', 'skipped_slots'], counters))
            packet = bytes(data[:length])
            valid = length == 21 and sum(packet[2:]) % 256 == 255 and packet[2] == 200
            assert bool(length) == expected_tx, (label, length)
            assert not length or valid, (label, packet.hex())
            assert counts['cancelled_replies'] == expected_cancel, (label, counts)
            assert counts['receive_timeouts'] == expected_rx_timeout, (label, counts)
            results.append({'case': label, 'tx_bytes': length, 'tx_hex': packet.hex(),
                            'checksum_valid': valid if length else None,
                            'counters': counts, 'expected_result_met': True, **details})

        for delay in [49, 50, 500, 2000, 2050, 2051]:
            reset()
            end = feed(READ)
            lib.shim_poll(end + delay)
            outcome('first_poll_after_read_' + str(delay), 50 <= delay <= 2050,
                    expected_cancel=int(delay > 2050), last_byte_to_first_poll_us=delay)

        for gap in [499, 500, 501]:
            reset()
            end = feed(READ, special_gap=gap)
            lib.shim_poll(end + 50)
            outcome('request_interbyte_gap_' + str(gap), gap <= 500,
                    expected_rx_timeout=int(gap > 500), one_request_interbyte_gap_us=gap)

        for byte in [0xff, 0x55]:
            reset()
            end = feed(READ)
            lib.shim_feed(byte, end + 20)
            lib.shim_poll(end + 50)
            outcome('foreign_byte_before_reply_' + format(byte, '02x'), False, expected_cancel=1)

        comparison = json.loads((HERE / 'hold-repetitions-comparison-20261101.json').read_text(encoding='utf-8'))
        for entry in comparison['rows']:
            stem = entry['experiment']
            name = 'hold-home-replay-summary-20261101.json' if stem == 'hold-home-replay-20261101' else stem + '-summary.json'
            summary = json.loads((HERE / name).read_text(encoding='utf-8'))
            goal = bytes.fromhex(summary['goal_writes'][-1]['raw_hex'])
            for idle in [0, 50, 12000]:
                reset()
                end = feed(goal)
                lib.shim_poll(end)
                end = feed(READ, end + idle)
                lib.shim_poll(end + 50)
                outcome(stem + '_goal_then_read_gap_' + str(idle), True,
                        goal_bytes=len(goal), synthetic_idle_us=idle)

        # Feed an actual servo-only SYNC_READ plus its 15 valid responses; 200 is not listed.
        stem = 'hold-home-servo-first-20261101'
        summary = json.loads((HERE / (stem + '-summary.json')).read_text(encoding='utf-8'))
        failing_time = summary['failed_reads'][0]['timestamp']
        prior = [e for e in summary['event_window'] if e['opcode'] == 0x82 and e['address'] == 56 and e['timestamp'] < failing_time][-1]
        reset()
        end = feed(bytes.fromhex(prior['raw_hex']))
        for frame in prior['rx_decoded']['frames']:
            assert frame['checksum_ok']
            end = feed(bytes.fromhex(frame['hex']), end + 30)
            lib.shim_poll(end)
        lib.shim_poll(end + 1000)
        outcome('servo_only_sync_and_15_replies_do_not_queue_imu', False)
        end = feed(READ, end + 1200)
        lib.shim_poll(end + 50)
        outcome('unicast_after_servo_only_sync_and_15_replies', True)

    files = sources + [FW / 'Core/Inc/protocol.h', FW / 'Core/Inc/control_table.h']
    report = {'date': '2026-11-01', 'kind': 'Deterministic virtual-time experiment, not hardware measurement',
              'source_files_sha256': {str(p.relative_to(REPO)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
              'compiler': subprocess.check_output(['cc', '--version'], text=True).splitlines()[0],
              'build_stdout': build.stdout, 'build_stderr': build.stderr, 'cases': results,
              'scope': 'Unmodified archived protocol.c and control_table.c with existing bus_sim_shim.c, temporary build output outside read-only references',
              'limitations': ['Does not execute board.c, MCU UART, interrupts, HAT, Linux UART or physical line.',
                             'Synthetic byte times and fixture sensor data; does not claim reconstruction of actual wire timing.',
                             'A protocol branch cancelling a response is not a reproduction of the observed 21-byte checksum corruption.',
                             'Never opens a serial device or connects to the robot.']}
    (HERE / 'imu-protocol-timing-simulation-20261101.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'cases': len(results), 'all_expected': all(r['expected_result_met'] for r in results),
                      'invalid_generated_frames': sum(r['checksum_valid'] is False for r in results),
                      'output': 'imu-protocol-timing-simulation-20261101.json'}))


if __name__ == '__main__':
    main()
