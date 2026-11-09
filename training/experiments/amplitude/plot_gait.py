"""用已归档结果绘图；训练探索统计与确定性回放分图展示。"""
import argparse
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

LABELS={"baseline-reference":"原基线","gait010":"足底10mm","gait020":"足底20mm",
        "rawramp":"渐进平滑","gait010_rawramp":"10mm＋渐进平滑"}
COLORS=["#777777","#287bb5","#db9635","#438960","#a2579b"]


def name(run):
    return run.replace("amplitude-20261107-","").split("-s42")[0]


def main(a):
    plt.rcParams['font.sans-serif']=['Microsoft YaHei','DejaVu Sans']
    plt.rcParams['axes.unicode_minus']=False
    out=a.evidence/'comparison'
    rows=json.loads((out/'summary.json').read_text(encoding='utf-8'))
    selection={}
    for row in rows:
        if 'failure' in row:continue
        for diag in row['diagnostics']:
            if diag['scenario'].endswith('_101') and diag['metrics'].get('valid'):
                selection[name(row['run'])]=diag
    order=[k for k in LABELS if k in selection]
    if order:
        fig,axes=plt.subplots(2,2,figsize=(12,8),constrained_layout=True)
        x=np.arange(len(order));labels=[LABELS[k] for k in order]
        for j,side in enumerate(('left','right')):
            axes[0,0].bar(x+(j-.5)*.35,[selection[k]['metrics']['feet'][side]['clearance_min_max_mm'][1] for k in order],.35,label=('左脚','右脚')[j])
            axes[0,1].bar(x+(j-.5)*.35,[len(selection[k]['metrics']['verified_foot_events'][side]) for k in order],.35,label=('左脚','右脚')[j])
        axes[0,0].set(title='稳态最大足底净空（不是目标值）',ylabel='毫米')
        axes[0,0].axhline(3,color='red',linestyle='--',linewidth=1)
        axes[0,0].legend()
        axes[0,1].set(title='合格离地—落地次数',ylabel='次')
        axes[0,1].axhline(5,color='red',linestyle='--',linewidth=1)
        axes[1,0].bar(x,[selection[k]['metrics']['body_vx_mean_m_s'] for k in order],color=COLORS[:len(order)])
        axes[1,0].axhline(.06,color='red',linestyle='--',linewidth=1,label='目标0.06 m/s')
        axes[1,0].set(title='机体系平均前速',ylabel='m/s');axes[1,0].legend()
        axes[1,1].bar(x,[selection[k]['heading_max_deg'] if selection[k]['heading_max_deg'] is not None else np.nan for k in order],color=COLORS[:len(order)])
        axes[1,1].axhline(10,color='red',linestyle='--',linewidth=1,label='航向偏差门槛10°')
        axes[1,1].set(title='最大航向偏差',ylabel='度');axes[1,1].legend()
        for ax in axes.flat:
            ax.set_xticks(x,labels,rotation=10);ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
        fig.suptitle('冻结策略回放：0.06 m/s，场景101\n训练seed42；起落须真实接触转换且净空>3mm持续≥40ms',fontsize=13)
        fig.savefig(out/'gait-comparison.png',dpi=150);plt.close(fig)
    fig,axes=plt.subplots(2,2,figsize=(12,8),constrained_layout=True)
    for k in list(LABELS)[1:]:
        path=a.evidence/f'amplitude-20261107-{k}-s42-r1/updates.jsonl'
        if not path.exists():continue
        data=[json.loads(line) for line in path.read_text().splitlines()]
        if not data:continue
        x=[r['model_iteration'] for r in data]
        series=([r['action_std_rank0'] for r in data],
                [r['statistics']['raw_action_clip_fraction']*100 for r in data],
                [r['gait']['air_reward_rate'] for r in data],
                [r['gait']['smooth_reward_rate'] for r in data])
        for ax,y in zip(axes.flat,series):ax.plot(x,y,label=LABELS[k])
    titles=('动作探索标准差','训练raw越界比例（%）','训练腾空奖励率','训练平滑奖励率')
    for ax,title in zip(axes.flat,titles):ax.set(title=title,xlabel='PPO更新');ax.grid(alpha=.2);ax.legend(fontsize=8)
    fig.suptitle('训练过程：随机探索统计，不代替确定性步态验收',fontsize=13)
    fig.savefig(out/'training-curves.png',dpi=150);plt.close(fig)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--evidence',type=Path,required=True)
    main(p.parse_args())
