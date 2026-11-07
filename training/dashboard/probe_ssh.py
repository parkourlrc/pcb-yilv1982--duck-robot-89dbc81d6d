import json
import subprocess
import time
from pathlib import Path

from dashboard.config import ROOT


def main():
    records = []
    for extra, command in [([], 'hostname'), (['-o', 'ControlMaster=no', '-o', 'ControlPath=none', '-o', 'LogLevel=DEBUG1'], 'hostname; sudo -n docker info --format {{.ServerVersion}}')]:
        argv = ['ssh', '-T', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=6', *extra, 'spark2', command]
        started = time.monotonic()
        try:
            process = subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True, timeout=15)
            record = {'exit_code': process.returncode, 'stdout': process.stdout.decode(errors='replace'), 'stderr': process.stderr.decode(errors='replace')}
        except subprocess.TimeoutExpired as error:
            record = {'timeout': True, 'stdout': (error.stdout or b'').decode(errors='replace'), 'stderr': (error.stderr or b'').decode(errors='replace')}
        records.append({'options': extra, 'command': command, 'elapsed_s': time.monotonic() - started, **record})
    destination = ROOT / 'training/.dashboard/spark2-probe-private.json'
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(records, indent=2), encoding='utf-8')
    for record in records:
        print(json.dumps({key: value for key, value in record.items() if key != 'stderr'}))


if __name__ == '__main__':
    main()
