"""只读训练状态并保存紧凑快照；不改变运行、预算或参数。"""
import json
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

root=Path('/root/duck-training-runs')
names=sys.argv[2:] or ['gait010','gait020','rawramp','gait010_rawramp']
rows=[]
for name in names:
    base=root/f'amplitude-20261107-{name}-s42'
    if name.endswith('-r1'):
        base=root/f'amplitude-20261107-{name[:-3]}-s42-r1'
    row={'preset':name}
    for file,key in [('supervisor-status.json','supervisor'),('run/result.json','result'),('run/failure.json','failure'),('run/amplitude_stop.json','stop')]:
        if (base/file).exists():row[key]=json.loads((base/file).read_text())
    path=base/'run/updates.jsonl'
    if path.exists():
        records=[]
        for line in path.read_text().splitlines():
            try:records.append(json.loads(line))
            except json.JSONDecodeError:pass
        if records:
            last=records[-1]
            row.update(updates=len(records),last=last)
    if (base/'run/evaluation_000100.json').exists():
        row['evaluation']=json.loads((base/'run/evaluation_000100.json').read_text())
    rows.append(row)
result={'utc':datetime.now(timezone.utc).isoformat(),'runs':rows}
result['gpu']=subprocess.run(['nvidia-smi','--query-gpu=memory.used,utilization.gpu','--format=csv,noheader'],capture_output=True,text=True).stdout.strip()
out=Path(sys.argv[1]);out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'utc':result['utc'],'gpu':result['gpu'],'runs':[
    {'preset':r['preset'],'updates':r.get('updates',0),'phase':r.get('supervisor',{}).get('phase'),
     'air':r.get('last',{}).get('gait',{}).get('air_reward_rate'),
     'batch_peak_mm':1000*r.get('last',{}).get('gait',{}).get('mean_batch_max_clearance_m',0),
     'single_support':r.get('last',{}).get('gait',{}).get('single_support_fraction'),
     'clip':r.get('last',{}).get('statistics',{}).get('raw_action_clip_fraction'),
     'std':r.get('last',{}).get('action_std_rank0'),
     'collect_s':r.get('last',{}).get('collect_s'),
     'failure':r.get('failure'),'stop':r.get('stop')} for r in rows]}))
