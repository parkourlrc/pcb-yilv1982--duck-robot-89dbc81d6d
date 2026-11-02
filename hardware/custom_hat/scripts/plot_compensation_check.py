"""Plot the isolated network verification; this is not a buck-loop stability plot."""
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties


ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "docs/references/hat-simulation-tools-20261029/power-acceptance-20261031"


def main():
    font = FontProperties(fname="C:/Windows/Fonts/msyh.ttc")
    plt.rcParams["font.family"] = font.get_name()
    plt.rcParams["axes.unicode_minus"] = False
    with (EVIDENCE / "compensation-ac.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    current = [row for row in rows if row["case"] == "current_board"]
    doubled = [row for row in rows if row["case"] == "same_ratio_double_resistance"]
    frequency = [float(row["frequency_hz"]) for row in current]
    figure, axes = plt.subplots(1, 2, figsize=(11, 4.3), constrained_layout=True)
    axes[0].semilogx(frequency, [float(row["derived_gain_db"]) for row in current], color="#176a8b", linewidth=2, label="按图示电路推导")
    axes[0].semilogx(frequency[::15], [float(row["spice_gain_db"]) for row in current[::15]], "o", color="#1d242d", markersize=3, label="ngspice独立网络")
    axes[0].semilogx(frequency, [float(row["printed_eq12_gain_db"]) for row in current], "--", color="#c76f16", label="按印刷Eq.12")
    axes[0].set_title("现有52.3k / 10k：印刷式偏高约2.92dB")
    axes[1].semilogx(frequency, [float(row["derived_gain_db"]) for row in current], color="#176a8b", linewidth=2, label="图示理想网络：分压比不变，曲线不变")
    axes[1].semilogx(frequency, [float(row["printed_eq12_gain_db"]) for row in current], "--", color="#c76f16", label="印刷式：原反馈电阻")
    axes[1].semilogx(frequency, [float(row["printed_eq12_gain_db"]) for row in doubled], ":", color="#7858a6", linewidth=2, label="印刷式：两电阻同时加倍")
    axes[1].set_title("同一分压比对照：印刷式却变化6.02dB")
    for axis in axes:
        axis.set_xlabel("频率 / Hz")
        axis.set_ylabel("反馈×补偿网络幅值 / dB")
        axis.grid(True, alpha=.25, which="both")
        axis.legend(fontsize=8, loc="upper right")
        axis.set_xlim(10, 1e7)
    figure.suptitle("AP64350 图27理想反馈/补偿网络核对\n不含功率级、采样/斜坡补偿；不是本板环路相位裕量或实测", fontsize=11)
    figure.savefig(EVIDENCE / "compensation-network-check.png", dpi=170)
    plt.close(figure)
    print(EVIDENCE / "compensation-network-check.png")


if __name__ == "__main__":
    main()
