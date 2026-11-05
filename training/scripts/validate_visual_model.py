#!/usr/bin/env python3
"""一次性核对显示模型动力学不变，并生成可检查的四视图；不接实物。"""

from __future__ import annotations

import hashlib
import json
import platform
from pathlib import Path

import mujoco
import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
MODELS = ROOT / "training" / "models"
EVIDENCE = ROOT / "docs" / "references" / "物理仿真查看工具优化"


def names(model, kind, count):
    return [mujoco.mj_id2name(model, kind, index) for index in range(count)]


def main():
    paths = [MODELS / "duck_v0.xml", MODELS / "duck_visual.xml"]
    base, visual = [mujoco.MjModel.from_xml_path(str(path)) for path in paths]
    dimensions = ("nbody", "njnt", "nq", "nv", "nu", "nkey", "nexclude")
    for name in dimensions:
        assert getattr(base, name) == getattr(visual, name), name
    for kind, count in ((mujoco.mjtObj.mjOBJ_BODY, base.nbody),
                        (mujoco.mjtObj.mjOBJ_JOINT, base.njnt),
                        (mujoco.mjtObj.mjOBJ_ACTUATOR, base.nu)):
        assert names(base, kind, count) == names(visual, kind, count)
    fields = (
        "body_parentid body_pos body_quat body_ipos body_iquat body_mass body_inertia "
        "body_gravcomp jnt_type jnt_bodyid jnt_qposadr jnt_dofadr jnt_pos jnt_axis "
        "jnt_limited jnt_range jnt_margin jnt_stiffness jnt_solref jnt_solimp "
        "dof_bodyid dof_jntid dof_parentid dof_damping dof_armature dof_frictionloss "
        "dof_solref dof_solimp actuator_trntype actuator_dyntype actuator_gaintype "
        "actuator_biastype actuator_trnid actuator_gear actuator_ctrllimited "
        "actuator_forcelimited actuator_ctrlrange actuator_forcerange "
        "actuator_dynprm actuator_gainprm actuator_biasprm actuator_lengthrange "
        "qpos0 qpos_spring key_time key_qpos key_qvel key_act key_ctrl exclude_signature"
    ).split()
    for name in fields:
        assert np.array_equal(getattr(base, name), getattr(visual, name)), name
    option_fields = ("timestep", "gravity", "integrator", "solver", "iterations",
                     "tolerance", "cone", "jacobian", "enableflags", "disableflags")
    for name in option_fields:
        assert np.array_equal(getattr(base.opt, name), getattr(visual.opt, name)), name

    geom_fields = (
        "geom_type geom_bodyid geom_size geom_pos geom_quat geom_contype "
        "geom_conaffinity geom_condim geom_friction geom_solmix geom_solref "
        "geom_solimp geom_margin geom_gap geom_priority"
    ).split()
    for index, name in enumerate(names(base, mujoco.mjtObj.mjOBJ_GEOM, base.ngeom)):
        other = mujoco.mj_name2id(visual, mujoco.mjtObj.mjOBJ_GEOM, name)
        assert other >= 0, name
        for field in geom_fields:
            assert np.array_equal(getattr(base, field)[index], getattr(visual, field)[other]), (name, field)
    visual_ids = np.flatnonzero(visual.geom_group == 2)
    assert len(visual_ids) == 70
    assert np.all(visual.geom_contype[visual_ids] == 0)
    assert np.all(visual.geom_conaffinity[visual_ids] == 0)

    # 在相同状态和输入下短跑 100 个物理步，覆盖碰撞接触与求解结果。
    data = [mujoco.MjData(model) for model in (base, visual)]
    for model, item in zip((base, visual), data):
        mujoco.mj_resetDataKeyframe(model, item, 0)
        item.qvel[6:] = np.linspace(-0.01, 0.01, model.nu)
        item.ctrl[:] = np.sin(np.arange(model.nu)) * 0.01
        mujoco.mj_forward(model, item)
    forward_error = float(np.max(np.abs(data[0].qacc - data[1].qacc)))
    assert forward_error < 1e-10, forward_error
    max_qpos_error = max_qvel_error = 0.0
    for _ in range(100):
        for model, item in zip((base, visual), data):
            mujoco.mj_step(model, item)
        max_qpos_error = max(max_qpos_error, float(np.max(np.abs(data[0].qpos - data[1].qpos))))
        max_qvel_error = max(max_qvel_error, float(np.max(np.abs(data[0].qvel - data[1].qvel))))
    assert max_qpos_error < 1e-10 and max_qvel_error < 1e-10

    EVIDENCE.mkdir(parents=True, exist_ok=True)
    width, height = 800, 600
    montage = Image.new("RGB", (width * 2, (height + 40) * 2), "#161a20")
    font_path = Path("C:/Windows/Fonts/msyh.ttc")
    font = ImageFont.truetype(str(font_path), 20) if font_path.exists() else ImageFont.load_default()
    previews = [
        ("HOME / 三分之四视角", 135, -18, False, False),
        ("HOME / 侧面", 90, -12, False, False),
        ("关节挂接：左腿与头部转动", 135, -18, True, False),
        ("原有碰撞体 / 独立 group 3", 135, -18, False, True),
    ]
    item = mujoco.MjData(visual)
    with mujoco.Renderer(visual, height, width) as renderer:
        for panel, (label, azimuth, elevation, articulated, collision) in enumerate(previews):
            mujoco.mj_resetDataKeyframe(visual, item, 0)
            if articulated:
                for name, delta in (("left_hip_pitch", -0.25), ("left_knee", 0.4),
                                    ("left_ankle", -0.15), ("head_yaw", 0.5), ("head_pitch", -0.2)):
                    joint = mujoco.mj_name2id(visual, mujoco.mjtObj.mjOBJ_JOINT, name)
                    item.qpos[visual.jnt_qposadr[joint]] += delta
            mujoco.mj_forward(visual, item)
            camera = mujoco.MjvCamera()
            camera.lookat[:] = (0, 0, 0.135)
            camera.distance = 0.55
            camera.azimuth, camera.elevation = azimuth, elevation
            options = mujoco.MjvOption()
            options.geomgroup[:] = 0
            options.geomgroup[0] = 1
            options.geomgroup[3 if collision else 2] = 1
            options.sitegroup[:] = 0
            renderer.update_scene(item, camera=camera, scene_option=options)
            frame = Image.fromarray(renderer.render())
            x, y = (panel % 2) * width, (panel // 2) * (height + 40)
            montage.paste(frame, (x, y + 40))
            ImageDraw.Draw(montage).text((x + 12, y + 8), label, fill="#eef2f6", font=font)
    preview = EVIDENCE / "model-preview.png"
    montage.save(preview)
    manifest = json.loads((MODELS / "visual" / "manifest.json").read_text(encoding="utf-8"))
    report = {
        "date": "2026-10-21", "status": "passed", "scope": "simulation display only; no hardware",
        "runtime": {"platform": platform.platform(), "python": platform.python_version(),
                    "mujoco": mujoco.__version__},
        "model_sha256": {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths},
        "unchanged_dimensions": {name: getattr(base, name) for name in dimensions},
        "equal_compiled_model_fields": fields, "equal_option_fields": list(option_fields),
        "equal_original_geom_fields_by_name": geom_fields,
        "new_visual_geoms": len(visual_ids), "new_meshes": visual.nmesh,
        "groups": {"0": "floor", "2": "visual mesh", "3": "original robot collision"},
        "dynamics_check": {"physics_steps": 100, "timestep_s": base.opt.timestep,
                           "initial_qacc_max_abs_error": forward_error,
                           "qpos_max_abs_error": max_qpos_error, "qvel_max_abs_error": max_qvel_error},
        "assets": manifest["summary"],
        "render": {"path": preview.relative_to(ROOT).as_posix(), "pixels": list(montage.size),
                   "panels": [row[0] for row in previews], "visual_review": "pending"},
        "limitations": ["XL330 upstream appearance, not measured HD-1910 C-line CAD",
                        "No new mouth DOF", "No claim of matching physical hardware dynamics"],
    }
    (EVIDENCE / "visual-validation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "dynamics": report["dynamics_check"],
                      "preview": str(preview)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
