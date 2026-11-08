"""CPU MuJoCo 固定HOME目标诊断；不是PPO训练或GPU轨迹复现。"""
from pathlib import Path
import hashlib
import json
import mujoco
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).with_name('amplitude-experiments-20261107')/'fixed-home-pd-probe'
if OUT.exists() and any(OUT.iterdir()):
    raise FileExistsError(f'Output contains prior evidence: {OUT}')
OUT.mkdir(exist_ok=True)
names=('left_hip_yaw','left_hip_roll','left_hip_pitch','left_knee','left_ankle','neck_pitch','head_pitch','head_yaw','head_roll','right_hip_yaw','right_hip_roll','right_hip_pitch','right_knee','right_ankle')
home=json.loads((ROOT/'training/params/home_pose.json').read_text(encoding='utf-8'))['joint_pos']
source=ROOT/'training/models/duck_v0.xml'
initial_file=OUT.parent/'baseline-diagnostic-101/straight_0.06_101/substeps.npz'
initial=np.load(initial_file)['q_pre'][0]
results=[]
for kd,dt in [(2.,.002),(1.,.002),(2.,.001)]:
    spec=mujoco.MjSpec.from_file(str(source))
    for actuator in list(spec.actuators):spec.delete(actuator)
    # 对齐 mjlab 1.3.0 utils/spec.py:create_motor_actuator 的关节motor装配。
    for name in names:
        actuator=spec.add_actuator(name=name,target=name)
        actuator.trntype=mujoco.mjtTrn.mjTRN_JOINT
        actuator.dyntype=mujoco.mjtDyn.mjDYN_NONE
        actuator.gaintype=mujoco.mjtGain.mjGAIN_FIXED
        actuator.biastype=mujoco.mjtBias.mjBIAS_NONE
        actuator.gear[0]=1.
        actuator.forcelimited=True;actuator.forcerange[:]=[-.94,.94]
        actuator.ctrllimited=True;actuator.ctrlrange[:]=[-.94,.94]
        spec.joint(name).armature=.00178
        spec.joint(name).frictionloss=.0158
    model=spec.compile();model.opt.timestep=dt
    model.opt.integrator=mujoco.mjtIntegrator.mjINT_IMPLICITFAST
    data=mujoco.MjData(model)
    joints=[model.joint(name).id for name in names]
    qa=model.jnt_qposadr[joints];va=model.jnt_dofadr[joints]
    target=np.array([home[name] for name in names])
    data.qpos[:7]=[0,0,.1182,1,0,0,0];data.qpos[qa]=initial
    mujoco.mj_forward(model,data)
    mass=np.empty((model.nv,model.nv))
    try:mujoco.mj_fullM(model,mass,data.qM)
    except TypeError:mujoco.mj_fullM(model,data,mass)
    effective=mass[6:,6:]-mass[6:,:6]@np.linalg.solve(mass[:6,:6],mass[:6,6:])
    eigen=np.linalg.eigvalsh(effective)
    rows=[]
    for i in range(round(6/dt)):
        q=data.qpos[qa].copy();v=data.qvel[va].copy()
        raw=25*(target-q)-kd*v
        data.ctrl[:]=np.clip(raw,-.94,.94)
        rows.append(np.r_[data.time,q,v,raw,data.ctrl.copy(),data.qpos[2]])
        mujoco.mj_step(model,data)
    rows=np.asarray(rows);steady=rows[:,0]>=3
    freq=np.fft.rfftfreq(steady.sum(),dt)
    metrics=[]
    for j,name in enumerate(names):
        v=rows[steady,15+j];power=np.abs(np.fft.rfft(v-v.mean()))**2
        torque=rows[steady,43+j]
        metrics.append({'joint':name,'qd_rms':float(np.sqrt(np.mean(v*v))),
                        'velocity_peak_hz':float(freq[1+np.argmax(power[1:])]),
                        'velocity_power_above_100hz':float(power[freq>100].sum()/max(power.sum(),1e-30)),
                        'torque_flip_fraction':float(np.mean(torque[:-1]*torque[1:]<0)),
                        'saturation_fraction':float(np.mean(np.abs(rows[steady,29+j])>.94)),
                        'q_range_deg':float(np.rad2deg(np.ptp(rows[steady,1+j])))})
    label=f'kd{kd:g}-dt{dt:g}'
    np.savez_compressed(OUT/(label+'.npz'),samples=rows,target=target)
    results.append({'name':label,'kd':kd,'dt':dt,'seconds':6.,'height_min':float(rows[:,-1].min()),
                    'joint_effective_mass_eigen_min':float(eigen.min()),
                    'illustrative_dt_kd_over_min_mass':float(dt*kd/eigen.min()),
                    'metrics':metrics})
report={'scope':'CPU MuJoCo constant HOME target, no actor; same initial joints from recorded GPU pre-step; separate simulation, not GPU training reproduction',
        'mujoco_version':mujoco.__version__,'model_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'initial_sha256':hashlib.sha256(initial_file.read_bytes()).hexdigest(),
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'linearization_limit':'mass eigenvalue diagnostic ignores contact, friction, position stiffness and saturation; scalar explicit damping stability criterion is illustrative, not a fitted robot model',
        'sample_columns':'time,q14,qd14,raw_torque14,clipped_torque14,root_z', 'cases':results}
(OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
for case in results:
    legs=[r for r in case['metrics'] if r['joint'].endswith(('hip_pitch','knee','ankle'))]
    print(json.dumps({'name':case['name'],'height_min':case['height_min'],'dt_kd_mass':case['illustrative_dt_kd_over_min_mass'],'legs':legs},indent=2))
