"""汇总完整dev9，避免挑选单一速度或单一评估种子报告。"""
from pathlib import Path
from collections import Counter
import hashlib
import json
import math

root=Path(__file__).parent
evidence=root/'amplitude-experiments-20261107'
paths=[root/'amplitude-20261107-baseline/evaluation_000100.json',*sorted(evidence.glob('*/evaluation_000100.json'))]
rows=[]
lines=['# 独立百轮完整dev9比较','',
       '同一行汇总同训练seed的三个评估seed；速度误差为滤波后稳态RMSE，航向为全回合最大偏转。具体阈值与失败项保留原报告，不因平均值改善而放宽。','',
       '| 运行 | 指令m/s | 完整/跌倒或失败/行为通过 | 前速RMSE范围m/s | 最大航向范围° | 最大侧偏范围m |',
       '|---|---:|---|---:|---:|---:|']
for path in paths:
    data=json.loads(path.read_text(encoding='utf-8'))
    speeds=sorted({float(e['name'].split('_')[1]) for e in data['episodes'] if e['name'].startswith('straight_')})
    assert sum(e['name'].startswith('straight_') for e in data['episodes'])==data['total'], 'unexpected suite; do not silently omit episodes'
    for speed in speeds:
        episodes=[e for e in data['episodes'] if float(e['name'].split('_')[1])==speed]
        if not episodes:continue
        metrics={}
        for key in ('forward_rmse','straight_heading','straight_lateral'):
            values=[e['checks'].get('motion_0/'+key,{}).get('observed') for e in episodes]
            values=[v for v in values if isinstance(v,(int,float))]
            if key=='straight_heading':values=[math.degrees(v) for v in values]
            metrics[key]=[min(values),max(values)] if values else None
        failures=Counter(k for e in episodes for k,v in e['checks'].items() if not v['passed'])
        row={'run':path.parent.name,'command_vx':float(speed),'episodes':len(episodes),
             'completed':sum(e['completed'] for e in episodes),'failed':sum(e['failed'] for e in episodes),
             'passed':sum(e['passed'] for e in episodes),'ranges':metrics,'failed_checks':dict(failures),
             'source':path.relative_to(root).as_posix(),'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
        rows.append(row)
        values=['—' if v is None else f'{v[0]:.5f}–{v[1]:.5f}' for v in metrics.values()]
        lines.append(f"| {row['run']} | {row['command_vx']} | {row['completed']}/{row['failed']}/{row['passed']}（共{len(episodes)}） | "+' | '.join(values)+' |')
out=evidence/'comparison';out.mkdir(exist_ok=True)
(out/'dev9-summary.json').write_text(json.dumps({'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'rows':rows},indent=2)+'\n',encoding='utf-8')
(out/'dev9-summary.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('\n'.join(lines))
