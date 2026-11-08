"""读取本次独立运行的进度与GPU余量并归档快照。"""
from pathlib import Path
import datetime
import json
import subprocess

work=Path('/root/duck-training-runs')
evidence=Path('/mnt/c/Projects/duck-robot/docs/references/自主训练平台/amplitude-experiments-20261107')
rows=[]
for base in sorted(work.glob('amplitude-20261107-*')):
    if not base.is_dir() or not (base/'config.json').exists():continue
    row={'run':base.name,'phase':'initializing'}
    status=base/'run/status.rank0.json'
    if status.exists():
        s=json.loads(status.read_text());row.update(phase=s['phase'],iteration=s.get('model_iteration'),status_utc=s.get('utc'))
    updates=base/'run/updates.jsonl'
    if updates.exists() and updates.stat().st_size:
        lines=updates.read_text().splitlines()
        try:r=json.loads(lines[-1])
        except json.JSONDecodeError:r=json.loads(lines[-2])
        row.update(iteration=r['model_iteration'],clip=r['statistics']['raw_action_clip_fraction'],fps=r['transitions_per_s'],last_update_utc=r['utc'])
    evaluation=base/'run/evaluation_000100.json'
    if evaluation.exists():
        e=json.loads(evaluation.read_text());row.update(dev_passed=e['passed_count'],dev_total=e['total'])
    if (base/'run/result.json').exists():row['phase']='training_and_dev_complete'
    if (base/'diagnostic/summary.json').exists():row['phase']='diagnostic_complete'
    rows.append(row)
gpu=subprocess.check_output(['nvidia-smi','--query-gpu=utilization.gpu,memory.used,memory.total,power.draw','--format=csv,noheader,nounits'],text=True).strip()
snapshot={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'gpu_columns':'utilization_pct,memory_used_MiB,memory_total_MiB,power_W','gpu':gpu,'runs':rows}
with (evidence/'progress-snapshots.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(snapshot)+'\n')
(evidence/'latest-progress.json').write_text(json.dumps(snapshot,indent=2)+'\n',encoding='utf-8')
print(json.dumps(snapshot,indent=2))
