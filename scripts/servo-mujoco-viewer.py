#!/usr/bin/env python3
"""舵机实时 3D 数字孪生查看器（2026-10-20）。

从板上 hls_servo_debugger(:8765) 实时读 14 颗关节位置，驱动本工程
MuJoCo 模型（training/models/duck_v0.xml），实物手掰时 3D 模型跟着动。
mouth(34) 不在模型中，不显示。

用法（仓库根目录）：
    py scripts/servo-mujoco-viewer.py [--url http://192.168.1.35:8765]

角度换算：qpos = sign * (计数-2048) * 2*pi/4096，sign 默认全 -1
（duck-control POSITION_DIRECTION）；若个别关节方向看着反了，
改 SIGNS 表。读数折回单圈显示（手掰出窗时不跳圈）。
"""
import argparse
import json
import time
import urllib.request
from pathlib import Path

import mujoco
import mujoco.viewer

# 模型 joint 名 -> 舵机 ID（2026-10-24 起对齐上游 microduck_feetech：20-24 左腿 / 10-14 右腿；30=neck_pitch、31=head_pitch）
JOINTS = [
    ("left_hip_yaw", 20), ("left_hip_roll", 21), ("left_hip_pitch", 22),
    ("left_knee", 23), ("left_ankle", 24),
    ("right_hip_yaw", 10), ("right_hip_roll", 11), ("right_hip_pitch", 12),
    ("right_knee", 13), ("right_ankle", 14),
    ("neck_pitch", 30), ("head_pitch", 31), ("head_yaw", 32),
    ("head_roll", 33),
]
SIGNS = {name: -1.0 for name, _ in JOINTS}

COUNTS_PER_TURN = 4096.0
CENTER = 2048
# 软件零位表保持空：旧 {22:1198} 是 2026-10-23 #22（当时右髋 pitch）的临时零位，
# 22 号当日已重校，且 2026-10-24 改号后 ID 语义变化，硬编码会错挂到左髋 pitch。
ZERO_COUNTS = {}


def read_pos(url, sid):
    req = urllib.request.Request(
        url + "/api/read",
        data=json.dumps({"id": sid, "addr": 56, "length": 2}).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=1.5) as r:
        d = json.loads(r.read())["data"]
        raw = d["data"][0] | (d["data"][1] << 8)
    pos = -(raw & 0x7FFF) if raw & 0x8000 else raw
    return ((pos % COUNTS_PER_TURN) + COUNTS_PER_TURN) % COUNTS_PER_TURN


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://192.168.1.35:8765")
    default_model = Path(__file__).resolve().parent.parent / \
        "training" / "models" / "duck_v0.xml"
    ap.add_argument("--model", default=str(default_model))
    a = ap.parse_args()

    model = mujoco.MjModel.from_xml_path(a.model)
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)

    print("模型：%s（%d 关节）" % (a.model, len(JOINTS)))
    print("数据源：%s —— 实物动，模型跟。关窗口退出。" % a.url)
    with mujoco.viewer.launch_passive(model, data) as v:
        while v.is_running():
            for name, sid in JOINTS:
                try:
                    counts = read_pos(a.url, sid)
                    rad = SIGNS[name] * (counts - ZERO_COUNTS.get(sid, CENTER)) * 2 * 3.14159265 \
                        / COUNTS_PER_TURN
                    data.joint(name).qpos[0] = rad
                except Exception:
                    pass  # 单颗读失败保持上次角度
            mujoco.mj_forward(model, data)
            v.sync()
            time.sleep(0.02)


if __name__ == "__main__":
    main()
