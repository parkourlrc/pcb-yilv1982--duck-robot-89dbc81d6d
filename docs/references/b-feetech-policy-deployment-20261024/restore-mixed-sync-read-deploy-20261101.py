"""Radxa：按用户要求恢复通信原件，切换到 servo-web；不发送动作。"""

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess

STAGE = Path('/home/radxa/restore-mixed-sync-20261101')
WEB = Path('/home/radxa/servo-web')
BIN = Path('/opt/robot/daemon/current/bin')
LOG = STAGE / 'deployment.json'
BACKUP = STAGE / 'before'
EXPECTED = {
    'server.py': ('229bf37c24af05926682c0212097158bea2139273bc430b2f6139e2c0f80689e', '1885da8345abac5efb570faeb99409c84a795216f70f11b2ce6475d5a1716e7f'),
    'imu_bus.py': ('cca0956fa8ac80f973f7f4d2e27d9ec847c5539f4d0e6b3d466b0c48406787ef', '60fea9614732bd72bf062566afc8f3510f4e2e8bf08c4f92e24640e3172c36dd'),
    'index.html': ('f9c04df38f3519661d3f6909165442c0be407a11331b2e4ee24e0bc3d80b2dde', '6ce2d1f868f83334688623f024d812de90e6553da8f90a69ab5fe9620bd1dae8'),
}
ROBOTD_BEFORE = '9f9fa71723339b80f97d7be065dec04855bb0d31a3ed7c5978e8605c22db3e5b'
ROBOTD_AFTER = '725b74cd93660a312970a44879abe5b75e8becf108499a1b8798961e48ca5f00'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def command(args, check=True):
    p = subprocess.run(args, text=True, capture_output=True, timeout=25)
    value = {'args': args, 'returncode': p.returncode, 'stdout': p.stdout, 'stderr': p.stderr}
    if check and p.returncode:
        raise RuntimeError(value)
    return value


def status():
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.settimeout(4)
        s.connect('/run/robotd.sock')
        s.sendall(b'{"jsonrpc":"2.0","id":1,"method":"robot.busStatus","params":{}}\n')
        with s.makefile('rb') as f:
            return json.loads(f.readline())


def holders():
    result = []
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():
            continue
        try:
            for fd in (proc / 'fd').iterdir():
                try:
                    if os.readlink(fd) == '/dev/ttyS2':
                        result.append({'pid': int(proc.name), 'fd': fd.name,
                                       'cmdline': (proc / 'cmdline').read_bytes().replace(b'\0', b' ').decode()})
                except FileNotFoundError:
                    pass
        except FileNotFoundError:
            pass
    return result


def main():
    assert os.geteuid() == 0
    assert not LOG.exists() and not BACKUP.exists(), 'Do not repeat one-time deployment'
    before = status()
    state = before['result']
    assert state['torque_state'] == 'off' and not state['motion'] and not state['policy_motion_enabled'], 'Robot must already be off and idle'
    for name, (before_sha, after_sha) in EXPECTED.items():
        assert sha(WEB / name) == before_sha, name
        assert sha(STAGE / name) == after_sha, name
    assert sha(BIN / 'robotd') == ROBOTD_BEFORE
    assert sha(BIN / 'robotd.upstream-control47') == ROBOTD_AFTER
    protected = [Path('/etc/robot/feetech-ft5/robotd.toml'),
                 Path('/etc/robot/feetech-ft5/hd1910-calibration.toml'),
                 WEB / 'directions.json', WEB / 'feetech.py', BIN / 'robotctl']
    record = {'started_utc_board_clock': datetime.now(timezone.utc).isoformat(),
              'scope': 'Restore host communication code; no robot motion; keep service enablement unchanged',
              'before_rpc': before, 'before_holders': holders(),
              'protected_before': {str(p): sha(p) for p in protected}, 'steps': []}
    BACKUP.mkdir()

    def save():
        LOG.write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    try:
        # Pause both entry points before releasing the serial port.
        record['steps'].append(command(['systemctl', 'stop', 'microduck-studio.service']))
        state = status()['result']
        assert state['torque_state'] == 'off' and not state['motion'], 'State changed before stopping robotd'
        record['steps'].append(command(['systemctl', 'stop', 'robotd.service']))
        record['after_stop_holders'] = holders()
        assert not record['after_stop_holders'], 'UART still held'
        for name in EXPECTED:
            shutil.copy2(WEB / name, BACKUP / name)
            tmp = WEB / (name + '.restore-mixed-tmp')
            assert not tmp.exists()
            shutil.copy2(STAGE / name, tmp)
            os.chown(tmp, 1000, 1000)
            os.replace(tmp, WEB / name)
        shutil.copy2(BIN / 'robotd', BACKUP / 'robotd.v03')
        tmp = BIN / 'robotd.restore-mixed-tmp'
        assert not tmp.exists()
        shutil.copy2(BIN / 'robotd.upstream-control47', tmp)
        os.replace(tmp, BIN / 'robotd')
        record['after_sha256'] = {name: sha(WEB / name) for name in EXPECTED}
        record['robotd_sha256'] = sha(BIN / 'robotd')
        record['deployment_info'] = command([str(BIN / 'robotd'), 'deployment-info'])
        record['protected_after'] = {str(p): sha(p) for p in protected}
        assert record['protected_before'] == record['protected_after']
        uid = command(['id', '-u', 'radxa'])['stdout'].strip()
        record['steps'].append(command(['runuser', '-u', 'radxa', '--', 'env', 'XDG_RUNTIME_DIR=/run/user/' + uid,
                                        'systemctl', '--user', 'start', 'duck-servo-web.service']))
        record['status'] = 'restored; servo-web started; robotd and Studio stopped'
    except Exception as exc:
        record['error'] = f'{type(exc).__name__}: {exc}'
        record['status'] = 'incomplete; preserve backups and inspect before retrying'
        raise
    finally:
        record['finished_utc_board_clock'] = datetime.now(timezone.utc).isoformat()
        record['final_holders_at_exit'] = holders()
        save()
    print(json.dumps({'status': record['status'], 'robotd_sha256': record['robotd_sha256'],
                      'after_sha256': record['after_sha256']}, indent=2))


if __name__ == '__main__':
    main()
