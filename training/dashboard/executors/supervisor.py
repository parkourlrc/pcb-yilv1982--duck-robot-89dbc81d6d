from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path


def write(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value), encoding='utf-8')
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('job')
    args = parser.parse_args()
    job = json.loads(Path(args.job).read_text())
    output = Path(job['directory'])
    output.mkdir(parents=True, exist_ok=True)
    status = {'state': 'initializing', 'supervisor_pid': os.getpid(), 'started_utc': datetime.now(timezone.utc).isoformat(), 'job_id': job['job_id']}
    status_file = output / 'supervisor.json'
    try:
        with (output / 'process.log').open('ab', buffering=0) as log:
            child = subprocess.Popen(job['argv'], cwd=job['cwd'], env={**os.environ, **job.get('env', {})}, stdout=log, stderr=subprocess.STDOUT)
            status.update(pid=child.pid, state='running')
            while child.poll() is None:
                status['heartbeat_utc'] = datetime.now(timezone.utc).isoformat()
                write(status_file, status)
                time.sleep(1)
            status.update(exit_code=child.returncode, state='completed' if child.returncode == 0 else 'failed')
    except Exception as error:
        status.update(state='failed', error=str(error))
    status['ended_utc'] = datetime.now(timezone.utc).isoformat()
    write(status_file, status)


if __name__ == '__main__':
    main()
