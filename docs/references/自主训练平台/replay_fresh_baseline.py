"""只读调用冻结版本的既有回放函数，并分析新百轮模型；不创建训练器。"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import os

os.environ.setdefault("MUJOCO_GL", "egl")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.base / "frozen"
    result = json.loads((args.base / "run/result.json").read_text())
    manifest = Path(result["checkpoint_manifest"])
    args.output.mkdir(parents=True, exist_ok=False)
    source = root / "training/scripts/diagnose_locomotion_run.py"
    spec = importlib.util.spec_from_file_location("frozen_replay", source)
    replay = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(replay)
    # 复用完整现有物理回放；显示独立提高至 50 fps，避免旧视频的 10 fps 混叠。
    def render50(model, positions, output, iteration):
        import imageio.v2 as imageio
        import mujoco
        import numpy as np
        camera = mujoco.MjvCamera()
        camera.azimuth, camera.elevation, camera.distance = 115, -25, .55
        camera.lookat[:] = [0., 0., .08]
        data = mujoco.MjData(model)
        path = output / f"replay-{iteration}-50fps.mp4"
        renderer = mujoco.Renderer(model, height=480, width=640)
        try:
            with imageio.get_writer(path, fps=50, macro_block_size=None) as writer:
                for i, position in enumerate(positions):
                    data.qpos[:] = position
                    mujoco.mj_forward(model, data)
                    camera.lookat[:2] = position[:2]
                    renderer.update_scene(data, camera=camera)
                    frame = renderer.render()
                    writer.append_data(frame)
                    if i in (0, 250, 500, 750, 1000):
                        imageio.imwrite(output / f"frame-{i:04d}.png", frame)
        finally:
            renderer.close()
        return {"status": "rendered", "path": path.name, "fps": 50,
                "seconds": len(positions)*.02, "scope": "qpos geometry rendering, following camera"}
    replay.render = render50
    summary, trace = replay.replay(manifest.parent, args.output, 100)
    analyze(root, args.output, trace)
    replay.write_json(args.output / "provenance.json", {
        "source": str(source), "source_sha256": replay.digest(source),
        "analysis_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "manifest": str(manifest), "manifest_sha256": replay.digest(manifest),
        "scope": "existing deterministic straight_0.06_101 replay and offline kinematics; training unchanged",
    })
    print(json.dumps(summary, ensure_ascii=False), flush=True)


def analyze(root, output, trace):
    import mujoco
    import numpy as np
    from mjlab_duck.locomotion_env import JOINT_ORDER, HOME
    model = mujoco.MjModel.from_xml_path(str(root / "training/models/duck_v0.xml"))
    data = mujoco.MjData(model)
    times = trace["time"].numpy()
    qpos = trace["qpos"].numpy()
    raw = trace["action"].numpy()
    physics = trace["physics"].numpy()
    steady = times >= 3
    if steady.sum() < 3:
        (output / "amplitude.json").write_text(json.dumps({"valid": False, "reason": "insufficient steady duration"}))
        return
    joints = {}
    for a, name in enumerate(JOINT_ORDER):
        joint = model.joint(name).id
        actual = qpos[:, model.jnt_qposadr[joint]]
        target = np.clip(HOME[name] + .5*np.clip(raw[:, a], -1, 1), *model.jnt_range[joint])
        def spectrum(values):
            values = values[steady]
            power = np.abs(np.fft.rfft(values-values.mean()))**2
            freq = np.fft.rfftfreq(len(values), .02)
            return {"dominant_hz": float(freq[1+np.argmax(power[1:])]),
                    "power_fraction_above_5hz": float(power[freq > 5].sum()/max(power.sum(), 1e-30))}
        joints[name] = {"actual_range_deg": float(np.rad2deg(np.ptp(actual[steady]))),
                        "target_range_deg": float(np.rad2deg(np.ptp(target[steady]))),
                        "actual_spectrum": spectrum(actual), "target_spectrum": spectrum(target)}
    clearance, centers = [], []
    feet = [model.geom(f"{side}_foot_collision").id for side in ("left", "right")]
    for position in qpos:
        data.qpos[:] = position
        mujoco.mj_kinematics(model, data)
        centers.append([data.geom_xpos[g].copy() for g in feet])
        clearance.append([data.geom_xpos[g, 2] - np.abs(data.geom_xmat[g].reshape(3,3)[2]) @ model.geom_size[g] for g in feet])
    clearance = np.asarray(clearance)
    feet_metrics = {}
    for f, side in enumerate(("left", "right")):
        values = clearance[steady, f]
        feet_metrics[side] = {"bottom_min_max_mm": (1000*np.array([values.min(),values.max()])).tolist(),
                              "fraction_above_2mm": float(np.mean(values > .002)),
                              "fraction_above_3mm": float(np.mean(values > .003))}
    metrics = {"valid": True, "steady_interval_s": [float(times[steady][0]), float(times[-1])],
               "joints": joints, "feet": feet_metrics,
               "body_vx_mean_m_s": float(physics[steady,:,10].mean()),
               "max_tilt_deg": float(np.rad2deg(physics[:,:,5].max())),
               "deterministic_raw_clip_fraction": float(np.mean(np.abs(raw)>1)),
               "limitations": "50 Hz samples, range is not per-cycle amplitude; box-bottom geometry is not contact force; no substep torques"}
    np.savez_compressed(output / "kinematics.npz", time=times, centers=centers, clearance=clearance)
    (output / "amplitude.json").write_text(json.dumps(metrics, indent=2)+"\n", encoding="utf-8")


if __name__ == "__main__":
    main()
