"""首轮联合策略只读诊断回放；不创建训练器或更新预算。"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import sys

os.environ.setdefault("MUJOCO_GL", "egl")
import numpy as np
import torch
from tensordict import TensorDict
from rsl_rl.models import MLPModel
from mjlab.envs import ManagerBasedRlEnv

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "training"))
from mjlab_duck.locomotion_cfg import locomotion_env_cfg
from mjlab_duck.locomotion_evaluator import development_scenarios, evaluate_trace, causal_mean
from mjlab_duck.locomotion_checkpoint import CONTRACT_FILES


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+"\n", encoding="utf-8")


def replay(directory, output, iteration):
    manifest = json.loads((directory / "manifest.json").read_text())
    checkpoint = directory / manifest["rank_files"]["0"]["path"]
    if digest(checkpoint) != manifest["rank_files"]["0"]["sha256"]:
        raise ValueError("checkpoint SHA differs from manifest")
    payload = torch.load(checkpoint, map_location="cpu", weights_only=False)
    mismatches = [name for name, sha in payload["contract"]["sources"].items() if digest(ROOT / name) != sha]
    if mismatches or payload["iter"] != iteration or payload["rank"] != 0:
        raise ValueError(f"checkpoint identity or source mismatch: {mismatches}")
    actor = MLPModel(TensorDict({"actor": torch.zeros(1, 61)}, batch_size=[1]),
                     {"actor": ["actor"]}, "actor", 14, hidden_dims=(128, 128),
                     activation="elu", obs_normalization=True,
                     distribution_cfg={"class_name": "GaussianDistribution", "init_std": .3, "std_type": "log"})
    actor.load_state_dict(payload["actor_state_dict"], strict=True)
    actor.to("cuda:0").eval()
    before = {key: value.clone() for key, value in actor.state_dict().items()}
    scenario = next(item for item in development_scenarios(1) if item.name == "straight_0.06_101")
    config = locomotion_env_cfg(1, evaluation=True, seed=scenario.seed)
    config.is_finite_horizon = True
    env = ManagerBasedRlEnv(config, device="cuda:0")
    records = {name: [] for name in ("physics", "time", "command", "action", "reward", "reward_terms", "qpos")}
    try:
        with torch.inference_mode():
            obs, _ = env.reset(seed=scenario.seed)
            obs = env.command_manager.get_term("velocity").set_fixed_schedule(scenario.segments)
            state = env.locomotion
            initial_xy = state.xy[0].cpu().clone()
            initial_yaw = state.last_yaw[0].cpu().clone()
            failed, completed, reason = False, False, 0
            for control in range(1150):
                action = actor(TensorDict(obs, batch_size=[1]), stochastic_output=False)
                used_command = state.cmd[0].cpu().clone()
                obs, reward, terminated, truncated, _ = env.step(action)
                values = {"physics": state.physics_trace[0], "time": state.time[0],
                          "command": used_command, "action": action[0], "reward": reward[0],
                          "reward_terms": state.reward_terms[0], "qpos": env.sim.data.qpos[0]}
                for name, value in values.items():
                    records[name].append(value.detach().cpu().clone())
                failed = bool(state.failed[0]) or not bool(torch.isfinite(reward).all())
                reason = int(state.reason[0]) if bool(state.failed[0]) else (4 if failed else 0)
                done = bool((terminated | truncated)[0])
                if done or failed:
                    completed = done and not failed and control+1 == 1150 and bool(truncated[0]) and not bool(terminated[0])
                    break
        tensors = {name: torch.stack(values) for name, values in records.items()}
        trace = {**tensors, "initial_xy": initial_xy, "initial_yaw": initial_yaw}
        report = asdict(evaluate_trace(scenario, trace, completed=completed, failed=failed, reason=reason))
        frozen = all(torch.equal(value, actor.state_dict()[key]) for key, value in before.items())
        if not frozen:
            raise RuntimeError("replay mutated actor or normalization")
        np.savez_compressed(output / f"trace-{iteration}.npz", **{name: value.numpy() for name, value in trace.items()})
        deviation = [value for key, value in actor.state_dict().items() if "log_std" in key]
        summary = {"iteration": iteration, "checkpoint_sha256": digest(checkpoint), "scenario": asdict(scenario),
                   "actor_and_normalization_frozen": frozen, "deterministic_action_clip_fraction": float((tensors["action"].abs()>1).float().mean()),
                   "deterministic_action_max_abs": float(tensors["action"].abs().max()),
                   "distribution_std_mean": float(deviation[0].exp().mean()) if deviation else None,
                   "report": report, "video": render(env.sim.mj_model, tensors["qpos"].numpy(), output, iteration)}
        write_json(output / f"replay-{iteration}.json", summary)
        return summary, trace
    finally:
        env.close()


def render(model, positions, output, iteration):
    try:
        import mujoco
        import imageio.v2 as imageio
        data = mujoco.MjData(model)
        camera = mujoco.MjvCamera()
        center = positions[:, :2].mean(0)
        camera.lookat[:] = [float(center[0]), float(center[1]), .07]
        camera.distance = max(.7, float(np.ptp(positions[:, :2], axis=0).max())*1.8)
        camera.azimuth = 115
        camera.elevation = -35
        renderer = mujoco.Renderer(model, height=480, width=640)
        path = output / f"replay-{iteration}.mp4"
        try:
            with imageio.get_writer(path, fps=10, macro_block_size=None) as writer:
                for frame_index in range(0, len(positions), 5):
                    data.qpos[:] = positions[frame_index]
                    mujoco.mj_forward(model, data)
                    renderer.update_scene(data, camera=camera)
                    frame = renderer.render()
                    writer.append_data(frame)
                    if frame_index == 0:
                        imageio.imwrite(output / f"preview-{iteration}.png", frame)
        finally:
            renderer.close()
        return {"status": "rendered", "path": path.name, "fps": 10, "seconds": len(positions)*.02,
                "scope": "offline qpos rendering of the physical model; no additional integration"}
    except Exception as error:
        return {"status": "failed", "error": f"{type(error).__name__}: {error}"}


def plot_traces(traces, output):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    font_path = Path("/mnt/c/Windows/Fonts/msyh.ttc")
    if font_path.exists():
        font_manager.fontManager.addfont(str(font_path))
        plt.rcParams["font.family"] = font_manager.FontProperties(fname=str(font_path)).get_name()
        plt.rcParams["axes.unicode_minus"] = False
    figure, axes = plt.subplots(2, 2, figsize=(12, 8))
    for iteration, trace in traces.items():
        physical = trace["physics"].numpy()
        times = trace["time"].numpy()
        xy = physical[:, -1, :2]
        axes[0, 0].plot(xy[:, 0], xy[:, 1], label=f"第{iteration}轮")
        yaw = np.unwrap(physical.reshape(-1, 12)[:, 2]).reshape(-1, 10)[:, -1]
        axes[0, 1].plot(times, np.rad2deg(yaw-float(trace["initial_yaw"])))
        velocity = causal_mean(trace["physics"][:, :, 10:12].mean(1)).numpy()
        axes[1, 0].plot(times, velocity[:, 0])
        axes[1, 1].plot(times, (trace["action"].abs()>1).float().mean(-1).numpy())
    axes[0, 0].set(title="机身平面轨迹", xlabel="世界坐标 x (m)", ylabel="世界坐标 y (m)", aspect="equal")
    axes[0, 0].legend()
    axes[0, 1].set(title="相对初始航向的累计偏转", xlabel="时间 (s)", ylabel="角度 (°)")
    axes[1, 0].axhline(.06, color="black", linestyle="--", label="目标前速 0.06 m/s")
    axes[1, 0].set(title="当前航向坐标前速（0.2秒均值）", xlabel="时间 (s)", ylabel="m/s")
    axes[1, 0].legend()
    axes[1, 1].set(title="确定性动作超出 [-1, 1] 的比例", xlabel="时间 (s)", ylabel="比例")
    for axis in axes.flat:
        axis.grid(alpha=.25)
    figure.suptitle("诊断回放对比：前进 0.06 m/s、目标偏航 0、seed 101；蓝=100轮，橙=1000轮")
    figure.tight_layout()
    figure.savefig(output / "replay-comparison.png", dpi=160)
    plt.close(figure)


def training_windows(path):
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    result = []
    for start in range(0, len(rows), 100):
        window = rows[start:start+100]
        transitions = sum(row["statistics"]["transitions"] for row in window)
        result.append({"updates": [window[0]["model_iteration"], window[-1]["model_iteration"]],
                       "action_std_first": window[0]["action_std_rank0"], "action_std_last": window[-1]["action_std_rank0"],
                       "clip_fraction": sum(row["statistics"]["clipped_actions"] for row in window)/(14*transitions),
                       "learning_rate_last": window[-1]["learning_rate"],
                       "reward_terms_per_transition": {name: sum(row["statistics"]["reward_terms_sum"][name] for row in window)/transitions
                                                       for name in window[0]["statistics"]["reward_terms_sum"]}})
    return result


def contact_sheet(output):
    import imageio.v2 as imageio
    from PIL import Image, ImageDraw, ImageFont
    font = ImageFont.truetype("/mnt/c/Windows/Fonts/msyh.ttc", 21)
    sheet = Image.new("RGB", (1280, 1040), "white")
    draw = ImageDraw.Draw(sheet)
    for row, iteration in enumerate((100, 1000)):
        reader = imageio.get_reader(output / f"replay-{iteration}.mp4")
        try:
            for column, seconds in enumerate((0, 7, 15, 22)):
                frame = Image.fromarray(reader.get_data(seconds*10)).resize((320, 240))
                sheet.paste(frame, (column*320, row*520+45))
                draw.text((column*320+8, row*520+12), f"第{iteration}轮 / {seconds}秒", fill="black", font=font)
                draw.text((column*320+8, row*520+300), "物理模型 / qpos几何回放", fill="black", font=font)
        finally:
            reader.close()
    sheet = sheet.crop((0, 0, 1280, 860))
    sheet.save(output / "contact-sheet.png")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoints", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--postprocess-only", action="store_true")
    args = parser.parse_args()
    if args.postprocess_only:
        traces = {iteration: {name: torch.as_tensor(value) for name, value in np.load(args.output / f"trace-{iteration}.npz").items()}
                  for iteration in (100, 1000)}
        plot_traces(traces, args.output)
        contact_sheet(args.output)
        report_path = args.output / "diagnosis.json"
        report = json.loads(report_path.read_text())
        report["script_sha256_at_report_write"] = report.pop("script_sha256", report.get("script_sha256_at_report_write"))
        report["script_hash_limitation"] = "Plot labels were edited while the already-loaded replay process was running; this hash is file content at report write, not an executed-source snapshot. Simulation functions were not edited."
        report["postprocess_script_sha256"] = digest(__file__)
        report["postprocess_scope"] = "Chinese plots and contact sheet only; no new simulation"
        write_json(report_path, report)
        return
    args.output.mkdir(parents=True, exist_ok=False)
    summaries, traces = [], {}
    for iteration in (100, 1000):
        summary, trace = replay(args.checkpoints / f"checkpoint{iteration}", args.output, iteration)
        summaries.append(summary)
        traces[iteration] = trace
    plot_traces(traces, args.output)
    log = ROOT / "docs/specs/20261105-原地转圈策略/checks/step5-run-001/updates.jsonl"
    write_json(args.output / "diagnosis.json", {"scope": "two deterministic diagnostic replays, not a new full acceptance suite",
               "versions": {name: importlib.metadata.version(name) for name in ("torch", "rsl-rl-lib", "mjlab", "mujoco", "mujoco-warp")},
               "sources": {name: digest(ROOT / name) for name in CONTRACT_FILES},
               "script_sha256": digest(__file__), "training_log_sha256": digest(log),
               "training_windows": training_windows(log), "replays": summaries})
    print(json.dumps({"output": str(args.output), "replays": len(summaries)}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
