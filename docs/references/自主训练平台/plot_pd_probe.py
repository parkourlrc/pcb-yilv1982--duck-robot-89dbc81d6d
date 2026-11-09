"""绘制同一已记录目标序列的CPU执行器响应；不混作重训效果。"""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

root=Path(__file__).with_name('amplitude-experiments-20261107')/'recorded-target-pd-probe'
report=json.loads((root/'report.json').read_text(encoding='utf-8'))
plt.rcParams['font.sans-serif']=['Microsoft YaHei','SimHei','DejaVu Sans']
plt.rcParams['axes.unicode_minus']=False
fig,axes=plt.subplots(2,2,figsize=(14,8),layout='constrained')
joint=3 # left_knee, joint order recorded in source.py
for case in report['cases']:
    a=np.load(root/(case['name']+'.npz'))['samples']
    time=a[:,0];steady=time>=3;window=(time>=5)&(time<5.1)
    label=f"Kd={case['kd']:g}，dt={case['dt']*1000:g}ms"
    axes[0,0].plot(time[window],a[window,15+joint],label=label)
    axes[0,1].plot(time[window],a[window,43+joint],label=label)
    v=a[steady,15+joint];power=np.abs(np.fft.rfft(v-v.mean()))**2
    freq=np.fft.rfftfreq(len(v),case['dt'])
    axes[1,0].semilogy(freq,np.maximum(power/max(power.sum(),1e-30),1e-14),label=label)
    axes[1,1].plot(time[window],np.rad2deg(a[window,1+joint]),label=label)
axes[0,0].set(title='左膝速度：每个物理子步',ylabel='rad/s',xlabel='仿真时间 / s')
axes[0,1].set(title='左膝实际输出力矩',ylabel='N·m',xlabel='仿真时间 / s')
axes[1,0].set(title='左膝速度频谱（t ≥ 3s）',ylabel='各频点能量 / 总能量',xlabel='Hz',xlim=(0,260),ylim=(1e-10,1))
axes[1,1].set(title='左膝角度：去除高频不等于形成大摆幅',ylabel='°',xlabel='仿真时间 / s')
for ax in axes.flat:
    ax.grid(alpha=.2);ax.legend(fontsize=9)
fig.suptitle('同一alpha=0.5策略目标序列的CPU开环响应\n仅比较执行器响应；没有重新训练或闭环策略反馈',fontsize=16)
fig.savefig(root/'pd-response.png',dpi=140)
