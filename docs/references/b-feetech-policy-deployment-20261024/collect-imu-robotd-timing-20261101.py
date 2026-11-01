#!/usr/bin/env python3
"""Archive timing implementation and existing trace excerpts. SSH reads Python source only."""
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
NATIVE = REPO / 'training/logs/b-feetech-walk-20261024/controller-preparation-20261031/controller-source/fanhao375-Microduck-kissqy-27d7921/microduck-hd1910/firmware'
FW = REPO / 'references/microduck-replica/hardware/imu_to_dxl/firmware'


def excerpt(path, ranges):
    lines = path.read_text(encoding='utf-8-sig').splitlines()
    return {'path': str(path.relative_to(REPO)), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'snippets': [{'start': a, 'end': b, 'text': '\n'.join(lines[a-1:b])} for a,b in ranges]}


def main():
    files = [
        (FW / 'Core/Inc/protocol.h', [(9, 46)]),
        (FW / 'Core/Inc/board_config.h', [(6, 23)]),
        (FW / 'Core/Src/main.c', [(31, 65)]),
        (FW / 'Core/Src/protocol.c', [(98, 130), (152, 190), (233, 302), (315, 412)]),
        (FW / 'Core/Src/board.c', [(113, 138), (196, 267)]),
        (NATIVE / 'duck-control/src/feetech.rs', [(169, 182), (557, 600), (693, 706), (733, 817)]),
        (NATIVE / 'robotd/src/feetech_commissioning.rs', [(608, 641), (1490, 1495), (1517, 1536), (1640, 1651), (1768, 1770)]),
        (NATIVE / 'robotd/src/main.rs', [(4300, 4305)]),
        (REPO / 'tools/robotd-v03/patches/v03-unicast.patch', [(57, 181)]),
        (REPO / 'tools/servo-web/feetech.py', [(73, 104), (109, 145), (159, 166), (199, 212)]),
    ]
    report = {'date': '2026-11-01', 'source_excerpts': [excerpt(p, r) for p,r in files],
              'controller_scope': 'Archived fixed upstream code plus deployed v03-unicast.patch; experiment order is covered by prior trial records',
              'hardware_operations': 'None; remote command only imports serial/inspect and reads library source'}
    wsl = r'''
import hashlib,json
from pathlib import Path
base=Path('/opt/duck-robot/cargo/registry/src/rsproxy.cn-e3de039b2554c837/serialport-4.9.0/src/posix')
out=[]
for name,ranges in [('tty.rs',[(466,504),(732,735),(761,781)]),('poll.rs',[(14,65)])]:
    p=base/name; lines=p.read_text().splitlines()
    out.append({'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
                'snippets':[{'start':a,'end':b,'text':'\n'.join(lines[a-1:b])} for a,b in ranges]})
print(json.dumps(out))
'''
    proc = subprocess.run(['wsl', '-d', 'Ubuntu-24.04', '-u', 'root', '--', 'python3', '-'],
                          input=wsl, capture_output=True, encoding='utf-8', timeout=30)
    proc.check_returncode()
    report['serialport_library'] = json.loads(proc.stdout)
    remote = r'''
import hashlib,inspect,json
import serial,serial.serialposix
from pathlib import Path
p=Path(serial.serialposix.__file__)
out={'version':serial.VERSION,'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'methods':[]}
for name in ['read','write','flush','reset_input_buffer']:
    f=getattr(serial.serialposix.Serial,name); lines,start=inspect.getsourcelines(f)
    out['methods'].append({'name':name,'start':start,'text':''.join(lines)})
print(json.dumps(out))
'''
    proc = subprocess.run(['ssh', '-o', 'ConnectTimeout=8', 'radxa', 'python3 -'], input=remote,
                          capture_output=True, encoding='utf-8', timeout=25)
    report['pyserial_remote_read'] = {'returncode': proc.returncode, 'stderr': proc.stderr}
    if proc.returncode == 0:
        report['pyserial'] = json.loads(proc.stdout)
    else:
        report['pyserial_remote_read']['stdout'] = proc.stdout
    comparison = json.loads((HERE / 'hold-repetitions-comparison-20261101.json').read_text(encoding='utf-8'))
    report['captured_failure_windows'] = []
    for entry in comparison['rows']:
        stem = entry['experiment']
        name = 'hold-home-replay-summary-20261101.json' if stem == 'hold-home-replay-20261101' else stem + '-summary.json'
        summary = json.loads((HERE / name).read_text(encoding='utf-8'))
        failed = summary['failed_reads'][0]
        off = next(t for t in summary['torque_writes'] if Decimal(t['timestamp']) > Decimal(failed['timestamp']))
        trace = (HERE / (stem + '.log')).read_text(encoding='utf-8').splitlines()
        window = trace[failed['line']-1:off['line']-1]
        rd = failed['reads'][0]
        before_bad_return = [line for line in window if Decimal(line.split()[0]) <= Decimal(rd['timestamp'])]
        report['captured_failure_windows'].append({
            'experiment': stem, 'request_write_count_before_native_off': sum('write(11,' in line for line in window),
            'read_syscall_count': sum('read(11,' in line for line in window),
            'poll_timeout_count': sum('ppoll(' in line and '(Timeout)' in line for line in window),
            'ioctl_between_request_and_bad_read': [line for line in before_bad_return if 'ioctl(11,' in line],
            'read_bytes': failed['rx_bytes'], 'first_read_start_us': failed['first_read_start_us'],
            'read_duration_us': rd['duration_us'], 'read_complete_us_from_request': failed['first_read_start_us'] + rd['duration_us'],
            'prior_goal_return_to_imu_write_us': summary['failed_read_after_previous_goal_return_us'],
            'trace_start_line': failed['line'], 'trace_end_line_exclusive': off['line'], 'trace_text': '\n'.join(window),
            'source_sha256': summary['source_sha256'],
        })
    output = HERE / 'imu-robotd-timing-sources-20261101.json'
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'output': str(output), 'pyserial_version': report.get('pyserial', {}).get('version'),
                      'windows': [{k:v for k,v in w.items() if k not in ['trace_text','source_sha256']} for w in report['captured_failure_windows']]}, ensure_ascii=False))


if __name__ == '__main__':
    main()
