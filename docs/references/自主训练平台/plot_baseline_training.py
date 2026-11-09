"""由已归档的百轮更新日志生成曲线；不执行训练。"""
from pathlib import Path
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

folder = Path(__file__).with_name("amplitude-20261107-baseline")
rows = [json.loads(line) for line in (folder / "updates.jsonl").read_text(encoding="utf-8").splitlines()]
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
x = [row["model_iteration"] for row in rows]
figure, axes = plt.subplots(2, 2, figsize=(11, 7), constrained_layout=True)
panels = [
    ([row["episodes"]["natural_completed_count"] / max(row["episodes"]["samples"], 1) * 100 for row in rows], "训练回合完整结束比例", "最近 100 回合（%）"),
    ([row["episodes"]["length_mean"] * .02 for row in rows], "训练回合平均时长", "最近 100 回合（秒）"),
    ([row["action_std_rank0"] for row in rows], "随机探索标准差", "std"),
    ([row["statistics"]["raw_action_clip_fraction"] * 100 for row in rows], "训练 raw 动作越界率", "动作分量比例（%）"),
]
for axis, (values, title, ylabel) in zip(axes.flat, panels):
    axis.plot(x, values, color="#176B96", linewidth=2)
    axis.set(title=title, xlabel="PPO 更新次数", ylabel=ylabel)
    axis.grid(alpha=.2)
figure.suptitle("本机新基线：100 更新 / 4096 环境 / seed 42\n随机训练回合统计，不等同确定性行走验收", fontsize=14)
figure.savefig(folder / "training-curves.png", dpi=150)
plt.close(figure)
print(folder / "training-curves.png")
