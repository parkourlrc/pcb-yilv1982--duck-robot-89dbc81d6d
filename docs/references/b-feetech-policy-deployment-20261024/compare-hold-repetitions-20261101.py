#!/usr/bin/env python3
"""Summarize saved baseline and servo-first trials; no hardware access."""
import datetime
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
names=['hold-home-replay-20261101']+['hold-home-baseline3-20261101-r'+str(i) for i in range(1,4)]+['hold-home-servo-first-20261101']
rows=[]
for name in names:
    source=ROOT/(name+'.json')
    result=json.loads(source.read_text(encoding='utf-8'))
    summary_name='hold-home-replay-summary-20261101.json' if name==names[0] else name+'-summary.json'
    summary=json.loads((ROOT/summary_name).read_text(encoding='utf-8'))
    failures=summary['failed_reads']
    assert len(failures)==1, 'This comparison expects the one observed failed IMU request in each trace'
    failed=failures[0]
    frames=failed['rx_decoded']['frames']
    assert len(frames)==1 and not frames[0]['checksum_ok']
    frame=frames[0]
    begin=datetime.datetime.fromisoformat(result['hold_request_utc'])
    end=datetime.datetime.fromisoformat(result['hold_response_utc'])
    rows.append({
        'experiment':name,'beijing_time':begin.astimezone(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),
        'read_order':'servo_first' if name.endswith('servo-first-20261101') else 'imu_first',
        'stage':'Ramping','ramp_goal_writes_before_failure':len(summary['goal_writes'])-1,
        'first_read_start_us':failed['first_read_start_us'],'rx_bytes':failed['rx_bytes'],
        'bad_frame_hex':frame['hex'],'checksum_expected':frame['expected_checksum'],
        'checksum_received':frame['received_checksum'],'frame_id_byte':frame['hex'][4:6],
        'checksum_sum_mod256':frame['sum_mod256'],
        'previous_goal_return_to_imu_write_us':summary['failed_read_after_previous_goal_return_us'],
        'imu_write_to_native_off_us':summary['failed_read_to_native_off_write_us'],
        'rpc_duration_ms':round((end-begin).total_seconds()*1000,3),
        'diagnostic_delta':summary['diagnostic_delta'],
        'initial_position_words':{ident:int.from_bytes(bytes.fromhex(v)[:2],'little') for ident,v in summary['goal_writes'][0]['targets'].items()},
        'off_readback':result['post_readback']['torque_off']['replies'],
        'source_sha256':summary['source_sha256'],
        'capture_tail_incomplete':summary.get('capture_tail_incomplete'),
    })
r={'date':'2026-11-01','rows':rows,
   'limitations':['Host syscall timing under strace, not electrical waveforms',
                  'Repeated on the same robot without resetting exactly the same physical pose; no independence or rate model assumed',
                  'Wrong checksum does not locate the corrupted byte; variable sensor data naturally changes correct checksum',
                  'The EC byte in run 2 is part of an invalid frame; it does not establish a responding device ID 236'],
   'trial_scope':'Strict commissioning/read-only changed to servo-first; 20ms, decoder, hold, and off protections unchanged; partial entry keeps prior order',
   'wait_and_error_comparison':{
       'servo_web':{'serial_timeout_ms':20,'header_loop_nominal_ms':60,'header_empty_read_breaks_early':True,
                    'id_length_read_separate_timeout':True,'body_read_separate_timeout':True,
                    'aggregate_imu_plus_servos_deadline':False,'checksum_error':'immediate BusError',
                    'outer_imu_error':'catch, feed missing, no torque-off from this poll path','poll_hz':10},
       'robotd':{'aggregate_imu_plus_servos_deadline_ms':20,'per_poll_timeout_ms_max':2,
                 'checksum_error_only_frame':'discard invalid frame; await another valid response until deadline; generic timeout if none',
                 'ramping_read_error':'cancel hold and torque off, verify register 40','poll_hz':50}},
   'references':['tools/servo-web/feetech.py:109-145','tools/servo-web/server.py:1535-1544',
                 'tools/robotd-v03/patches/v03-unicast.patch:91-181','tools/robotd-v03/patches/v03-servo-first-experiment.patch']}
path=ROOT/'hold-repetitions-comparison-20261101.json'
path.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps([{k:x[k] for k in ['experiment','ramp_goal_writes_before_failure','first_read_start_us','checksum_expected','checksum_received']} for x in rows],indent=2))
