"""原队列结束后补原基线场景102/103；不训练、不追加PPO预算。"""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys
import time

project=Path('/mnt/c/Projects/duck-robot')
work=Path('/root/duck-training-runs')
evidence=project/'docs/references/自主训练平台/amplitude-experiments-20261107'
while True:
    status=json.loads((work/'amplitude-20261107-batch-status.json').read_text())
    if status['phase']=='batch_complete':break
    if status['phase']=='failed':raise RuntimeError('original batch failed; inspect before launching')
    if not Path('/proc/58794/cmdline').exists():raise RuntimeError('original supervisor exited without completion')
    time.sleep(5)
base=work/'amplitude-20261107-baseline'
output=base/'diagnostic-102-103'
command=[sys.executable,'-u',str(project/'training/experiments/amplitude/diagnose.py'),
         '--base',str(base),'--output',str(output),'--seeds','102','103']
with (base/'diagnose-102-103.log').open('xb') as log:
    code=subprocess.call(command,cwd=base,stdout=log,stderr=subprocess.STDOUT)
target=evidence/'baseline-diagnostic-102-103'
if output.exists():shutil.copytree(output,target)
target.mkdir(exist_ok=True)
shutil.copy2(base/'diagnose-102-103.log',target/'diagnose.log')
(target/'completion.json').write_text(json.dumps({'exit_code':code,'command':command,'supervisor_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},indent=2)+'\n')
raise SystemExit(code)
