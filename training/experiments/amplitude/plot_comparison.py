"""绘制同训练seed42、同回放场景seed101的参数影响；不将极差称作逐步摆幅。"""
from pathlib import Path
import argparse
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main(args):
    rows=json.loads((args.input/'comparison.json').read_text(encoding='utf-8'))
    selected={}
    for row in rows:
        run=row['run'].replace('\\','/')
        if not row['scenario'].endswith('_101') or not row['metrics'].get('valid'):continue
        if run.startswith('baseline-'):name='baseline'
        elif '-s42/' in run:name=run.split('amplitude-20261107-')[1].split('-s42/')[0]
        else:continue
        selected[name]=row['metrics']
    order=[name for name in ('baseline','ema025','ema050','smooth020','kd100') if name in selected]
    labels={'baseline':'基线','ema025':'滤波 0.25','ema050':'滤波 0.5','smooth020':'平滑权重 0.2','kd100':'阻尼 Kd=1'}
    colors=['#777777','#267db3','#2e996e','#d9902c','#a35f9b']
    plt.rcParams['font.sans-serif']=['Microsoft YaHei','DejaVu Sans']
    plt.rcParams['axes.unicode_minus']=False
    figure,axes=plt.subplots(2,2,figsize=(12,8),constrained_layout=True)
    joints=[f'{side}_{joint}' for side in ('left','right') for joint in ('hip_pitch','knee','ankle')]
    x=np.arange(6); width=.8/max(len(order),1)
    for i,name in enumerate(order):
        axes[0,0].bar(x+(i-(len(order)-1)/2)*width,[selected[name]['joints'][j]['actual_range_deg'] for j in joints],width,color=colors[i],label=labels[name])
    axes[0,0].set_xticks(x,['左髋','左膝','左踝','右髋','右膝','右踝'])
    axes[0,0].set(title='实际关节稳态峰峰范围（非逐步摆幅）',ylabel='角度（°）')
    axes[0,0].legend(fontsize=8)
    labels_x=[labels[n] for n in order]; x=np.arange(len(order))
    axes[0,1].bar(x-.17,[selected[n]['feet']['left']['clearance_min_max_mm'][1] for n in order],.34,label='左脚',color='#267db3')
    axes[0,1].bar(x+.17,[selected[n]['feet']['right']['clearance_min_max_mm'][1] for n in order],.34,label='右脚',color='#d9902c')
    axes[0,1].axhline(3,color='red',linestyle='--',linewidth=1,label='3 mm 高度门槛')
    axes[0,1].set(title='脚底碰撞盒最大离地（还须持续并确认落地）',ylabel='高度（mm）')
    axes[0,1].legend(fontsize=8)
    axes[1,0].bar(x,[selected[n]['body_vx_mean_m_s'] for n in order],color=colors[:len(order)])
    axes[1,0].axhline(.06,color='red',linestyle='--',linewidth=1,label='目标 0.06 m/s')
    axes[1,0].set(title='机体系平均前速（需另查航向）',ylabel='速度（m/s）')
    axes[1,0].legend(fontsize=8)
    axes[1,1].bar(x,[np.mean([selected[n]['joints'][j]['torque_saturation_fraction'] for j in joints])*100 for n in order],color=colors[:len(order)])
    axes[1,1].set(title='六个腿部俯仰关节力矩触顶比例均值',ylabel='500 Hz 子步（%）')
    for axis in (axes[0,1],axes[1,0],axes[1,1]):axis.set_xticks(x,labels_x,rotation=10)
    for axis in axes.flat:axis.grid(axis='y',alpha=.2);axis.set_axisbelow(True)
    figure.suptitle('独立100更新：训练seed42 / 0.06 m/s、场景seed101\n500 Hz子步诊断；单个训练种子，不能外推实机或多种子稳定性',fontsize=13)
    figure.savefig(args.input/'parameter-effects.png',dpi=150)
    plt.close(figure)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    main(parser.parse_args())
