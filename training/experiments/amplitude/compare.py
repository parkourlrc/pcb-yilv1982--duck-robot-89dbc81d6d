"""从原始子步轨迹复核完整腾空-落地事件，并汇总独立百轮实验。"""
from pathlib import Path
import argparse
import hashlib
import json
import numpy as np


LEG_NAMES = [f"{side}_{joint}" for side in ("left","right") for joint in ("hip_pitch","knee","ankle")]


def verified_metrics(folder, names):
    original=json.loads((folder/'metrics.json').read_text())
    if not original.get('valid'):
        return original
    data=np.load(folder/'substeps.npz')
    count=len(data['q_post']); times=np.arange(1,count+1)*.002
    events_by_side={}; all_events=[]; ranges={name:[] for name in names}
    for j,side in enumerate(('left','right')):
        contact=data['contact_count'][:,j]>0
        in_air=~contact
        edges=np.diff(np.r_[False,in_air,False].astype(int))
        events=[]
        for start,end in zip(np.where(edges==1)[0],np.where(edges==-1)[0]):
            # 必须由实际接触离开并再次接触，不能把高度阈值回落冒充落地。
            if start==0 or end==count or times[start]<3 or not contact[start-1] or not contact[end]:continue
            above=data['clearance'][start:end,j]>.003
            runs=np.diff(np.r_[False,above,False].astype(int))
            lengths=np.where(runs==-1)[0]-np.where(runs==1)[0]
            if not len(lengths) or lengths.max()<20:continue
            event={'start':int(start),'landing':int(end),'start_s':float(times[start]),'landing_s':float(times[end]),
                   'max_clearance_mm':float(data['clearance'][start:end,j].max()*1000),'continuous_above_3mm_s':float(lengths.max()*.002)}
            events.append(event);all_events.append((float(times[start]),side))
        events_by_side[side]=events
        for first,second in zip(events,events[1:]):
            for k,name in enumerate(names):
                if name.startswith(side+'_'):
                    ranges[name].append(float(np.rad2deg(np.ptp(data['q_post'][first['start']:second['start'],k]))))
    all_events.sort()
    alternates=[a[1]!=b[1] and b[0]-a[0]>=.04 for a,b in zip(all_events,all_events[1:])]
    ratio=float(np.mean(alternates)) if alternates else 0.
    original['verified_foot_events']=events_by_side
    original['verified_alternation_fraction']=ratio
    original['verified_foot_gate_passed']=all(len(e)>=5 for e in events_by_side.values()) and ratio>=.8
    contact=data['contact_count'][times>=3]>0
    support_count=contact.sum(axis=1)
    original['support_fractions']={'both_contact':float(np.mean(support_count==2)),
                                   'one_contact':float(np.mean(support_count==1)),
                                   'neither_contact':float(np.mean(support_count==0))}
    for name in names:
        original['joints'][name]['verified_cycle_count']=len(ranges[name])
        original['joints'][name]['verified_cycle_median_range_deg']=float(np.median(ranges[name])) if ranges[name] else None
    # 使用500 Hz原始速度，不能用50 Hz控制记录推断子步振荡。
    for j,name in enumerate(names):
        velocity=data['qd_pre'][times>=3,j]
        torque=data['torque'][times>=3,j]
        freq=np.fft.rfftfreq(len(velocity),.002)
        power=np.abs(np.fft.rfft(velocity-velocity.mean()))**2
        original['joints'][name]['substep_velocity_rms_rad_s']=float(np.sqrt(np.mean(velocity**2)))
        original['joints'][name]['substep_velocity_peak_hz']=float(freq[1+np.argmax(power[1:])])
        original['joints'][name]['substep_velocity_power_above_100hz']=float(power[freq>100].sum()/max(power.sum(),1e-30))
        original['joints'][name]['substep_torque_flip_fraction']=float(np.mean(torque[1:]*torque[:-1]<0))
    original['verification']={'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                              'substeps_sha256':hashlib.sha256((folder/'substeps.npz').read_bytes()).hexdigest(),
                              'criterion':'contact -> no contact with continuous height>3mm for >=40ms -> contact; threshold excursions are not independent landings'}
    (folder/'verified-metrics.json').write_text(json.dumps(original,indent=2)+'\n')
    return original


def main(args):
    rows=[]
    for summary_path in sorted(args.evidence.rglob('summary.json')):
        summary=json.loads(summary_path.read_text())
        if 'joint_order' not in summary or 'reports' not in summary:continue
        for report in summary['reports']:
            folder=summary_path.parent/report['scenario']
            metrics=verified_metrics(folder,summary['joint_order'])
            row={'run':summary_path.parent.relative_to(args.evidence).as_posix(),'scenario':report['scenario'],
                 'completed':report['evaluation']['completed'],'failed':report['evaluation']['failed'],
                 'behavior_passed':report['evaluation']['passed'],'metrics':metrics}
            rows.append(row)
    args.output.mkdir(parents=True,exist_ok=True)
    (args.output/'comparison.json').write_text(json.dumps(rows,indent=2)+'\n')
    lines=['# 百轮参数对照：原始子步复核','',
           '事件计数要求真实接触→无接触且连续离地超过3mm至少40ms→再次接触；不把高度阈值抖动当落地。逐周期摆幅缺少合格周期时为未定义。','',
           '| 运行 / 场景 | 前速 m/s | 左/右完整离地事件 | 交替率 | 足部门槛 | 行为门槛 |',
           '|---|---:|---:|---:|---|---|']
    for row in rows:
        m=row['metrics']
        if not m.get('valid'):
            lines.append(f"| {row['run']} / {row['scenario']} | — | 轨迹过短 | — | 未通过 | 未通过 |")
            continue
        counts='/'.join(str(len(m['verified_foot_events'][s])) for s in ('left','right'))
        lines.append(f"| {row['run']} / {row['scenario']} | {m['body_vx_mean_m_s']:.5f} | {counts} | {m['verified_alternation_fraction']:.1%} | {'通过' if m['verified_foot_gate_passed'] else '未通过'} | {'通过' if row['behavior_passed'] else '未通过'} |")
    (args.output/'comparison.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'episodes':len(rows),'output':str(args.output)},ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    main(parser.parse_args())
