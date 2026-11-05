"""Render the recorded solder access envelopes without editing KiCad files."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle


p=argparse.ArgumentParser()
p.add_argument('audit',type=Path)
p.add_argument('--output',type=Path,required=True)
a=p.parse_args()
d=json.loads(a.audit.read_text(encoding='utf-8'))
plt.rcParams['font.sans-serif']=['Microsoft YaHei','SimHei','DejaVu Sans']
fig,axes=plt.subplots(2,1,figsize=(15,13),layout='constrained')
bad={c['neighbor'] for c in d['rule_failures']}
for ax,side in zip(axes,['F.Cu','B.Cu']):
    ax.add_patch(Rectangle((100,100),65,30,fill=False,color='#234155',lw=1.5))
    for pad in d['tht_pads']:
        if pad['welding_face']!=side:
            continue
        l,t,r,b=pad['bbox_mm']
        ax.add_patch(Rectangle((l,t),r-l,b-t,facecolor='#93b5c6',edgecolor='#335b72',lw=.5))
    for c in d['components']:
        if c['side']!=side or not c['body_bbox_mm']:
            continue
        l,t,r,b=c['body_bbox_mm']
        color='#c44949' if c['ref'] in bad else '#24755a'
        ax.add_patch(Rectangle((l,t),r-l,b-t,facecolor=color,alpha=.18,edgecolor=color,lw=.8))
        ax.text((l+r)/2,(t+b)/2,c['ref'],ha='center',va='center',fontsize=7,color='#16232e')
    for pair in d['nearest_pairs']:
        if pair['welding_face']!=side or pair['gap_mm']>pair['required_mm']+.5:
            continue
        pad=next(x for x in d['tht_pads'] if x['pad']==pair['pad'])
        comp=next(x for x in d['components'] if x['ref']==pair['neighbor'])
        l,t,r,b=pad['bbox_mm']; cl,ct,cr,cb=comp['body_bbox_mm']
        ax.plot([(l+r)/2,(cl+cr)/2],[(t+b)/2,(ct+cb)/2],color='#bd671c',lw=.6,alpha=.5)
    ax.set_xlim(99,166);ax.set_ylim(131,99);ax.set_aspect('equal')
    ax.set_title(('正面：背面40P母座的焊接空间' if side=='F.Cu' else '背面：正面插座的焊接空间')+'（统一从正面投影，非翻板视图）',fontsize=12)
    ax.set_xlabel('mm');ax.set_ylabel('mm');ax.grid(alpha=.13)
fig.suptitle('Rev B 插件焊接空间：名义焊盘与器件Fab包络\n几何筛查不代表工厂工艺接受或实物验收 | 源 '+d['pcb_sha256'][:12],fontsize=14)
fig.savefig(a.output,dpi=160)
print(a.output)
