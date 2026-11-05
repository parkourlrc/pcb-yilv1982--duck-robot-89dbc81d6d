#!/usr/bin/env python3
"""从本项目参数表生成自建 v0 仿真模型（MJCF）。

输入：training/params/{microduck_geometry,hd1910_bam_m6,home_pose}.json
输出：training/models/duck_v0.xml

自建内容：XML 结构、简化几何（胶囊/盒，端点=关节中心）、执行器、场景、地面。
借鉴参数（均记录于参数表）：连杆质量/质心/惯量、关节安装位形（pos/quat/axis/range）、
HOME 站姿、HD-1910 BAM 的 armature/摩擦（简化映射）与堵转力矩上限。
"""

from __future__ import annotations

import json
from pathlib import Path

TRAIN = Path(__file__).resolve().parents[1]
PARAMS = TRAIN / "params"
OUT = TRAIN / "models" / "duck_v0.xml"

GEO = json.loads((PARAMS / "microduck_geometry.json").read_text(encoding="utf-8"))
BAM = json.loads((PARAMS / "hd1910_bam_m6.json").read_text(encoding="utf-8"))["params"]
HOME = json.loads((PARAMS / "home_pose.json").read_text(encoding="utf-8"))["joint_pos"]

# 自建几何参数（胶囊半径/盒子半尺寸按连杆质量与关节间距目测估计，非 CAD 数据）。
CAPSULE_RADIUS = {
    "yaw2roll": 0.008, "bearing_roll": 0.008,
    "hip_l": 0.008, "hip_l_2": 0.008,
    "upper_leg_left": 0.011, "upper_leg_right": 0.011,
    "leg": 0.009, "leg_2": 0.009,
    "neck": 0.008, "neck_pitch": 0.006, "yaw_roll_motion": 0.007,
}
TRUNK_BOX_HALF = (0.045, 0.036, 0.035)     # 主躯干（含电池/主控估算包络）
HEAD_BOX_HALF = (0.030, 0.028, 0.026)      # 头部（相机/HAT/扬声器估算包络）
HEAD_BOX_LOCAL = (-0.004, 0.0, -0.020)     # 头盒中心相对 head_roll 关节（取上游头壳 mesh 平均位置）
# 脚盒：上游 sole 碰撞 mesh 的 HOME 世界位形与 AABB 半尺寸（MuJoCo 只读对照导出，
# 见参数表文档第 4 节；反解到踝局部系，HOME 下底面水平，随踝转动）。
FOOT_WORLD_CENTER = {
    "left": (0.0068, 0.0407, 0.0086),
    "right": (0.0068, -0.0407, 0.0086),
}
FOOT_HALF = (0.0272, 0.0217, 0.0068)  # AABB 半尺寸：长(x) 宽(y) 厚(z)，世界系


def foot_local_pos(side):
    """世界中心反解到踝局部系（HOME 位形）。"""
    ank = "ankle_left" if side == "left" else "ankle_right"
    w = WORLD_HOME[ank]
    m = quat_to_mat(w["world_quat"])
    delta = [FOOT_WORLD_CENTER[side][k] - w["world_pos"][k] for k in range(3)]
    return tuple(sum(m[k][i] * delta[k] for k in range(3)) for i in range(3))

# 执行器 v0.1：力矩源（motor）+ 环境内一阶电机模型（见 duckstand/env.py）：
#   V_pwm = clip(KV·(q_target−q), ±vin)；i = (V_pwm − kt·ω)/R；τ = kt·i。
#   大误差电压饱和 → 反电动势把空载速度钳在 vin/kt ≈ 11.9 rad/s @7.4V（BAM 推算），
#   修复 v0 position 执行器"无速度上限"的 sim2real 缺陷（关节曾达 792 rad/s）。
#   ctrlrange = ±kt·vin/R（电压满幅时的力矩饱和，BAM 口径 0.94 N·m @7.4V）。
ACT_FORCELIMIT = round(BAM["kt"] * 7.4 / BAM["R"], 3)
# joint 动力学：HD-1910 BAM M6 参数的简化映射
#   armature = BAM armature（转子折算）；frictionloss = BAM friction_base（库仑摩擦近似）；
#   BAM 的负载相关摩擦/Stribeck/电压 sag/延迟属完整 BAM 行为，v0.1 不实现，留待 v1。
JOINT_ARMATURE = round(BAM["armature"], 5)
JOINT_FRICTION = round(BAM["friction_base"], 5)

# 自碰撞排除：自建包络盒与腿/颈胶囊几何重叠（真实鸭壳包着髋/颈根部，腿从壳中伸出），
# 排除壳-肢体重叠对，保留肢体之间与地面接触。
EXCLUDE_PAIRS = [
    ("trunk_base", "yaw2roll"), ("trunk_base", "bearing_roll"),
    ("trunk_base", "hip_l"), ("trunk_base", "hip_l_2"),
    ("trunk_base", "upper_leg_left"), ("trunk_base", "upper_leg_right"),
    ("jaw_soft", "neck_pitch"), ("jaw_soft", "yaw_roll_motion"), ("jaw_soft", "neck"),
]

TIMESTEP = 0.002  # 50 Hz 控制 × decimation 10，与上游控制周期口径一致

BODIES = GEO["bodies"]
WORLD_HOME = GEO["world_pose_at_home"]
ACT_ORDER = GEO["actuator_order"]

JOINT_RANGE = {
    j["name"]: j["range"]
    for b in BODIES.values() for j in b["joints"] if j["type"] == "hinge"
}


def fmt(vals):
    return " ".join(f"{x:.6g}" for x in vals)


def quat_to_mat(q):
    w, x, y, z = q
    return [
        [1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
        [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
        [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)],
    ]


def hinge(b):
    return next((j for j in b["joints"] if j["type"] == "hinge"), None)


CHILDREN = {name: [] for name in BODIES}
for name, b in BODIES.items():
    if b["parent"]:
        CHILDREN[b["parent"]].append(name)
# 保持与上游 XML 声明一致的分枝顺序（左腿、颈、右腿）
ORDER = ["yaw2roll", "neck", "bearing_roll"]
CHILDREN["trunk_base"] = sorted(CHILDREN["trunk_base"], key=lambda n: ORDER.index(n) if n in ORDER else 99)
for name in CHILDREN:
    if name != "trunk_base":
        CHILDREN[name].sort(key=lambda n: list(BODIES).index(n))


def quat_conj(q):
    return (q[0], -q[1], -q[2], -q[3])


def foot_fix_quat(side):
    """补偿旋转：使 HOME 姿态下脚盒底面水平（踝动作时随踝转）。

    q_fix = conj(q_ankle_home)：脚盒局部系经此旋转后，在 HOME 下与世界系对齐。
    """
    q = WORLD_HOME["ankle_left" if side == "left" else "ankle_right"]["world_quat"]
    return quat_conj(q)


def emit_body(name, lines, indent):
    """递归输出子树。trunk_base 由 main 特判（初始位形不同）。"""
    b = BODIES[name]
    pad = "  " * indent
    lines.append(
        f'{pad}<body name="{name}" pos="{fmt(b["pos"])}" quat="{fmt(b["quat"])}">')
    j = hinge(b)
    if j:
        lines.append(
            f'{pad}  <joint name="{j["name"]}" type="hinge" axis="{fmt(j["axis"])}" '
            f'range="{fmt(j["range"])}" class="servo"/>')
    inert = b["inertial"]
    lines.append(
        f'{pad}  <inertial pos="{fmt(inert["pos"])}" mass="{inert["mass"]:.6g}" '
        f'fullinertia="{fmt(inert["fullinertia"])}"/>')

    if name in ("ankle_left", "ankle_right"):
        side = "left" if "left" in name else "right"
        lines.append(
            f'{pad}  <geom name="{side}_foot_collision" type="box" size="{fmt(FOOT_HALF)}" '
            f'pos="{fmt(foot_local_pos(side))}" quat="{fmt(foot_fix_quat(side))}" class="foot"/>')
    elif name == "jaw_soft":
        lines.append(
            f'{pad}  <geom name="head_collision" type="box" size="{fmt(HEAD_BOX_HALF)}" '
            f'pos="{fmt(HEAD_BOX_LOCAL)}" class="collision"/>')
    elif CHILDREN[name]:
        child_pos = BODIES[CHILDREN[name][0]]["pos"]
        lines.append(
            f'{pad}  <geom name="{j["name"]}_link" type="capsule" '
            f'size="{CAPSULE_RADIUS[name]}" fromto="0 0 0 {fmt(child_pos)}" class="collision"/>')

    for c in CHILDREN[name]:
        emit_body(c, lines, indent + 1)
    lines.append(f"{pad}</body>")


def compute_home_trunk_z():
    """HOME 关节角下，让脚盒底面贴地的 trunk_base 世界高度。"""
    z_bottom = min(c[2] for c in FOOT_WORLD_CENTER.values()) - FOOT_HALF[2]
    return round(GEO["trunk_base_init"]["pos"][2] - z_bottom, 4)


def main():
    trunk_z = compute_home_trunk_z()
    home_line = " ".join(f"{HOME[n]:.4f}" for n in ACT_ORDER)

    L = []
    A = L.append
    A('<?xml version="1.0" ?>')
    A('<!-- duck v0 — 本项目自建学习模型（2026-10-15）。')
    A('     结构/几何/执行器为本项目自行编写：胶囊+盒简化几何，端点=关节中心。')
    A('     质量与惯量来自 Pollen Microduck 官方 CAD（XL330 版，非 C 线 HD-1910 实测）；')
    A('     关节安装位形/限位来自同一 CAD；HOME 站姿来自上游 STAND2；')
    A('     joint armature/frictionloss 为 LuwuDynamics 公开 HD-1910 BAM M6 参数的简化映射；')
    A('     全部数值溯源见 docs/references/动作训练软件研究/physical-params.md')
    A('     与 training/params/。生成脚本：training/scripts/build_model_v0.py。 -->')
    A('<mujoco model="duck_v0">')
    A('  <compiler angle="radian" autolimits="true"/>')
    A('  <visual>')
    A('    <global offwidth="800" offheight="600"/>')
    A('  </visual>')
    A(f'  <option timestep="{TIMESTEP}" gravity="0 0 -9.81" integrator="implicitfast"/>')
    A('  <default>')
    A('    <default class="servo">')
    A(f'      <joint damping="0" armature="{JOINT_ARMATURE}" frictionloss="{JOINT_FRICTION}"/>')
    A(f'      <motor ctrllimited="true" ctrlrange="-{ACT_FORCELIMIT} {ACT_FORCELIMIT}"/>')
    A('    </default>')
    A('    <default class="collision">')
    A('      <geom contype="1" conaffinity="1" condim="3" friction="1.0 0.005 0.0001" density="0"/>')
    A('    </default>')
    A('    <default class="foot">')
    A('      <geom contype="1" conaffinity="1" condim="3" friction="1.0 0.005 0.0001" priority="1" density="0"/>')
    A('    </default>')
    A('  </default>')
    A('  <worldbody>')
    A('    <geom name="floor" type="plane" size="2 2 0.1" condim="3" friction="1.0 0.005 0.0001"/>')
    A(f'    <body name="trunk_base" pos="0 0 {trunk_z}" quat="1 0 0 0">')
    A('      <freejoint name="trunk_base_freejoint"/>')
    inert = BODIES["trunk_base"]["inertial"]
    A(f'      <inertial pos="{fmt(inert["pos"])}" mass="{inert["mass"]:.6g}" '
      f'fullinertia="{fmt(inert["fullinertia"])}"/>')
    A(f'      <geom name="trunk_collision" type="box" size="{fmt(TRUNK_BOX_HALF)}" pos="0 0 0" class="collision"/>')
    A('      <site name="imu" pos="-0.021 0 -0.0147" size="0.005"/>')
    for c in CHILDREN["trunk_base"]:
        emit_body(c, L, 3)
    A('    </body>')
    A('  </worldbody>')
    A('  <contact>')
    for b1, b2 in EXCLUDE_PAIRS:
        A(f'    <exclude body1="{b1}" body2="{b2}"/>')
    A('  </contact>')
    A('  <actuator>')
    for n in ACT_ORDER:
        A(f'    <motor class="servo" name="{n}" joint="{n}" gear="1"/>')
    A('  </actuator>')
    A('  <keyframe>')
    A(f'    <key name="home" qpos="0 0 {trunk_z} 1 0 0 0 {home_line}"/>')
    A('  </keyframe>')
    A('</mujoco>')

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"wrote {OUT}  (trunk home z={trunk_z}, joints={len(ACT_ORDER)})")


if __name__ == "__main__":
    main()
