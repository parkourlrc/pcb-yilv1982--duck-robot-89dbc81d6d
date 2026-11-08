from pathlib import Path
import hashlib
import importlib.metadata
import json

import cv2
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import mujoco
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance


ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / 'docs/specs/20261105-原地转圈策略/checks/step5-diagnostic-replay'
OUTPUT = Path(__file__).with_name('replay100-analysis-20261107')
OUTPUT.mkdir(exist_ok=True)
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
trace = np.load(SOURCE / 'trace-100.npz')
capture = cv2.VideoCapture(str(SOURCE / 'replay-100.mp4'))
frames = []
while True:
    success, frame = capture.read()
    if not success:
        break
    frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
capture.release()


def cropped(frame):
    mask = np.max(np.abs(frame.astype(float) - np.array([80, 80, 80])), axis=-1) > 9
    mask[:125] = False
    coordinates = np.argwhere(mask)
    center_y, center_x = (coordinates.min(axis=0) + coordinates.max(axis=0)) / 2
    left, top = int(center_x - 65), int(center_y - 70)
    picture = Image.fromarray(frame).crop((left, top, left + 130, top + 140))
    picture = ImageEnhance.Brightness(picture).enhance(2.0)
    return picture.resize((260, 280))


for label, indices in [('overview', list(range(0, 230, 10))),
                       ('startup', list(range(20))),
                       ('middle', list(range(100, 120))),
                       ('end', list(range(210, 230)))]:
    sheet = Image.new('RGB', (260 * 5, 310 * ((len(indices) + 4) // 5)), 'white')
    draw = ImageDraw.Draw(sheet)
    for tile, frame_index in enumerate(indices):
        left, top = tile % 5 * 260, tile // 5 * 310
        sheet.paste(cropped(frames[frame_index]), (left, top + 30))
        draw.text((left + 8, top + 8), f'{frame_index / 10:.1f}s | x2 brightness', fill='black')
    sheet.save(OUTPUT / f'{label}.png')

model = mujoco.MjModel.from_xml_path(str(ROOT / 'training/models/duck_v0.xml'))
data = mujoco.MjData(model)
positions = trace['qpos']
home = json.loads((ROOT / 'training/params/home_pose.json').read_text(encoding='utf-8'))['joint_pos']
assert positions.shape[1] == model.nq == 21
feet = {side: model.geom(f'{side}_foot_collision').id for side in ['left', 'right']}
centers, clearances = [], []
for position in positions:
    data.qpos[:] = position
    mujoco.mj_kinematics(model, data)
    centers.append([data.geom_xpos[identifier].copy() for identifier in feet.values()])
    clearances.append([float(data.geom_xpos[identifier, 2] - np.abs(data.geom_xmat[identifier].reshape(3, 3)[2]) @ model.geom_size[identifier]) for identifier in feet.values()])
centers = np.asarray(centers)
clearances = np.asarray(clearances)
physics = trace['physics'].reshape(-1, 12)
times = trace['time']
steady = times >= 3
yaw = np.unwrap(physics[:, 2]) - float(trace['initial_yaw'])
result = {
    'analysis_versions': {name: importlib.metadata.version(name) for name in ['mujoco', 'numpy', 'opencv-python', 'matplotlib', 'pillow']},
    'source_video_sha256': hashlib.sha256((SOURCE / 'replay-100.mp4').read_bytes()).hexdigest(),
    'source_trace_sha256': hashlib.sha256((SOURCE / 'trace-100.npz').read_bytes()).hexdigest(),
    'physics_model_sha256': hashlib.sha256((ROOT / 'training/models/duck_v0.xml').read_bytes()).hexdigest(),
    'scope': 'archived deterministic replay; offline frames and qpos kinematics; no new dynamics or training',
    'frames': len(frames), 'video_fps': 10, 'trace_hz': 50,
    'timeline': [], 'joints': {}, 'feet': {},
    'max_tilt_deg': float(np.rad2deg(physics[:, 5].max())),
    'height_min_max_m': [float(physics[:, 6].min()), float(physics[:, 6].max())],
    'steady_body_vx_mean_m_s': float(trace['physics'][steady, :, 10].mean()),
    'deterministic_raw_clip_fraction': float(np.mean(np.abs(trace['action']) > 1)),
}
for seconds in [0, 1, 3, 5, 10, 15, 20, 23]:
    index = int(np.argmin(np.abs(times - max(.02, seconds))))
    sample = trace['physics'][index, -1]
    result['timeline'].append({'time_s': float(times[index]), 'xy_m': sample[:2].tolist(),
                               'yaw_deg': float(np.rad2deg(yaw[index * 10 + 9])),
                               'body_vx_m_s': float(sample[10])})
for joint_index in range(1, model.njnt):
    name = model.joint(joint_index).name
    values = positions[:, model.jnt_qposadr[joint_index]]
    frequencies = np.fft.rfftfreq(np.count_nonzero(steady), .02)
    spectrum = np.abs(np.fft.rfft(values[steady] - values[steady].mean())) ** 2
    peak = int(np.argmax(spectrum[1:]) + 1)
    unclipped_target = home[name] + .5 * np.clip(trace['action'][:, joint_index - 1], -1, 1)
    target = np.clip(unclipped_target, *model.jnt_range[joint_index])
    target_spectrum = np.abs(np.fft.rfft(target[steady] - target[steady].mean())) ** 2
    target_peak = int(np.argmax(target_spectrum[1:]) + 1)
    result['joints'][name] = {'steady_range_deg': float(np.rad2deg(np.ptp(values[steady]))),
                            'steady_mean_deg': float(np.rad2deg(values[steady].mean())),
                            'dominant_frequency_hz': float(frequencies[peak]),
                            'reconstructed_target_range_deg': float(np.rad2deg(np.ptp(target[steady]))),
                            'target_dominant_frequency_hz': float(frequencies[target_peak]),
                            'target_joint_limit_clip_fraction': float(np.mean(target[steady] != unclipped_target[steady])),
                            'end_step_target_error_rms_deg': float(np.rad2deg(np.sqrt(np.mean((target[steady] - values[steady]) ** 2)))),
                            'target_note': 'reconstructed from recorded raw action and OrderedAction; qpos is end of same control interval; no torque/qvel trace',
                            'step_change_rms_deg': float(np.rad2deg(np.sqrt(np.mean(np.diff(values[steady]) ** 2))))}
for side_index, side in enumerate(feet):
    values = clearances[steady, side_index]
    result['feet'][side] = {'kinematic_bottom_clearance_min_max_mm': (1000 * np.array([values.min(), values.max()])).tolist(),
                            'fraction_above_2mm': float(np.mean(values > .002)),
                            'limitation': 'geometric box bottom, not force/contact or swing-leg classification'}
np.savez_compressed(OUTPUT / 'kinematics.npz', time=times, foot_centers=centers, box_bottom_clearance=clearances)
figure, axes = plt.subplots(2, 2, figsize=(12, 8), constrained_layout=True)
axes[0, 0].plot(positions[:, 0] * 100, positions[:, 1] * 100)
axes[0, 0].axhline(0, color='gray', linestyle='--', label='初始直走方向')
axes[0, 0].set(xlabel='世界 X（cm）', ylabel='世界 Y（cm）', title='已有位姿：前进时逐渐偏离直线', aspect='equal')
axes[0, 0].legend()
axes[0, 1].plot(times, np.rad2deg(yaw.reshape(-1, 10)[:, -1]))
axes[0, 1].axhline(10, color='red', linestyle='--', label='航向偏差阈值 10°')
axes[0, 1].set(xlabel='时间（s）', ylabel='相对航向（°）', title='持续方向偏移')
axes[0, 1].legend()
window = (times >= 10) & (times <= 12)
for side in ['left', 'right']:
    values = positions[:, model.jnt_qposadr[model.joint(f'{side}_knee').id]]
    axes[1, 0].plot(times[window], np.rad2deg(values[window] - values[steady].mean()), label='左膝' if side == 'left' else '右膝')
axes[1, 0].set(xlabel='时间（s），原轨迹 50 Hz', ylabel='相对各膝稳态均值（°）', title='小幅快速振荡：10 fps 视频容易漏看')
axes[1, 0].legend()
for side_index, side in enumerate(['左脚', '右脚']):
    axes[1, 1].plot(times[window], clearances[window, side_index] * 1000, label=side)
axes[1, 1].axhline(0, color='gray', linestyle='--')
axes[1, 1].set(xlabel='时间（s）', ylabel='碰撞盒最低点离地（mm）', title='离线运动学重建：不是接触力测量')
axes[1, 1].legend()
figure.suptitle('第100轮：0.06 m/s 直走场景 / seed 101 / 原始轨迹分析')
figure.savefig(OUTPUT / 'findings.png', dpi=150)
plt.close(figure)
(OUTPUT / 'analysis.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(result, ensure_ascii=False, indent=2))
