"""Read-only board inventory for this deployment. No motor or service commands."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import tomllib

CFG = Path('/etc/robot/feetech-ft5/robotd.toml')
STUDIO = Path('/home/radxa/studio-dev')
SLOTS = ('walk', 'sitstand', 'ground_pick', 'kick_left', 'kick_right', 'roulade')


def digest(path):
    path = Path(path)
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def rpc(method):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as conn:
        conn.settimeout(5)
        conn.connect('/run/robotd.sock')
        conn.sendall(json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': {}}).encode() + b'\n')
        with conn.makefile('rb') as stream:
            answer = json.loads(stream.readline())
    if 'error' in answer:
        raise RuntimeError(answer['error'])
    return answer['result']


def inspect():
    cfg = tomllib.loads(CFG.read_text())
    result = {'time_utc': datetime.now(timezone.utc).isoformat(), 'services': {}, 'files': {}, 'protected': {}}
    for unit in ('robotd.service', 'microduck-studio.service'):
        output = subprocess.check_output(['systemctl', 'show', unit, '-p', 'MainPID', '-p', 'ActiveState', '-p', 'UnitFileState', '-p', 'ExecStart', '-p', 'WorkingDirectory'], text=True)
        row = dict(line.split('=', 1) for line in output.splitlines() if '=' in line)
        pid = int(row['MainPID'])
        if pid:
            row['process_argv'] = Path(f'/proc/{pid}/cmdline').read_bytes().decode().split('\0')[:-1]
        result['services'][unit] = row
    binary = Path('/opt/robot/daemon/current/bin/robotd')
    result['binary_resolved'] = str(binary.resolve())
    result['files']['bin/robotd'] = digest(binary)
    for relative in ('studio/pad.py', 'studio/pad_drive.py', 'studio/pad_recovery.py', 'studio/updates.py', 'web/pad.js'):
        result['files']['studio/' + relative] = digest(STUDIO / relative)
    protected = [CFG, CFG.with_name('hd1910-calibration.toml')]
    for slot in SLOTS:
        model = Path(cfg['policy'][slot])
        protected += [model, *sorted(model.parent.glob('*.json'))]
    for unit in ('robotd.service', 'microduck-studio.service'):
        protected.append(Path('/etc/systemd/system') / unit)
        protected.extend(sorted((Path('/etc/systemd/system') / (unit + '.d')).glob('*.conf')))
    result['protected'] = {str(path): digest(path) for path in protected}
    result['bus_held'] = Path('/run/microduck-helper/bus-held').exists()
    result['configured_model_loading'] = cfg['policy']['enabled']
    for method in ('robot.busStatus', 'robot.policies', 'robot.health', 'robot.skills', 'pad.bindings'):
        try:
            result[method] = rpc(method)
        except Exception as error:
            result[method] = {'probe_error': str(error)}
    return result


if __name__ == '__main__':
    print(json.dumps(inspect(), ensure_ascii=False, indent=2))
