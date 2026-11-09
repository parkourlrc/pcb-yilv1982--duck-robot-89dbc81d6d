"""从归档的冻结策略轨迹提取奖励贡献和关节幅度，不运行新训练。"""
import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np


def main(evidence):
    rows = json.loads((evidence / "comparison/summary.json").read_text(encoding="utf-8"))
    result = []
    dev9 = []
    legs = [f"{side}_{joint}" for side in ("left", "right") for joint in ("hip_pitch", "knee", "ankle")]
    for row in rows:
        evaluation = evidence / row["run"] / "evaluation_000100.json"
        if evaluation.exists():
            episodes = json.loads(evaluation.read_text(encoding="utf-8"))["episodes"]
            for speed in sorted({float(e["name"].split("_")[1]) for e in episodes}):
                group = [e for e in episodes if float(e["name"].split("_")[1]) == speed]
                ranges = {}
                for key in ("forward_rmse", "straight_heading", "straight_lateral"):
                    values = [e["checks"].get("motion_0/" + key, {}).get("observed") for e in group]
                    values = [v for v in values if isinstance(v, (int, float))]
                    if key == "straight_heading":
                        values = list(map(math.degrees, values))
                    ranges[key] = [min(values), max(values)] if values else None
                dev9.append({"run": row["run"], "command_vx": speed, "completed": sum(e["completed"] for e in group), "failed": sum(e["failed"] for e in group), "passed": sum(e["passed"] for e in group), "total": len(group), "ranges": ranges})
        for diag in row["diagnostics"]:
            m = diag["metrics"]
            if not m.get("valid"):
                continue
            folder = evidence / row["run"] / "diagnostic" / diag["scenario"]
            with np.load(folder / "trace.npz") as trace:
                steady = trace["time"] >= 3
                names = ("forward", "yaw", "stand", "lateral", "straight_yaw", "anchor", "posture", "smooth", "late")
                rewards = dict(zip(names, map(float, trace["reward_terms"][steady].mean(axis=0))))
                if "gait_reward_terms" in trace:
                    rewards.update(zip(("air", "clearance", "swing", "slip"), map(float, trace["gait_reward_terms"][steady].mean(axis=0))))
            gaps = {}
            with np.load(folder / "substeps.npz") as sub:
                for j, side in enumerate(("left", "right")):
                    air = sub["contact_count"][:, j] == 0
                    edges = np.diff(np.r_[False, air, False].astype(int))
                    closed = []
                    for start, end in zip(np.where(edges == 1)[0], np.where(edges == -1)[0]):
                        if start == 0 or end == len(air) or (start + 1) * .002 < 3:
                            continue
                        closed.append({"duration_s": float((end - start) * .002), "peak_clearance_mm": float(sub["clearance"][start:end, j].max() * 1000)})
                    long = [g for g in closed if g["duration_s"] >= .125]
                    gaps[side] = {"closed_gap_count": len(closed), "closed_gaps_at_least_125ms": long, "at_least_125ms_but_peak_at_most_3mm_count": sum(g["peak_clearance_mm"] <= 3 for g in long)}
            result.append({
                "run": row["run"], "scenario": diag["scenario"],
                "reward_rate_steady_mean": rewards,
                "contact_gap_audit": gaps,
                "actual_range_deg": {k: m["joints"][k]["actual_range_deg"] for k in legs},
                "verified_cycle_median_range_deg": {k: m["joints"][k]["verified_cycle_median_range_deg"] for k in legs},
                "leg_torque_saturation_fraction": {k: m["joints"][k]["torque_saturation_fraction"] for k in legs},
                "leg_velocity_peak_hz": {k: m["joints"][k]["substep_velocity_peak_hz"] for k in legs},
                "feet": {k: {f: m["feet"][k][f] for f in ("clearance_min_max_mm", "contact_fraction", "contact_point_horizontal_speed_mean_m_s")} for k in ("left", "right")},
            })
    output = evidence / "comparison/details.json"
    output.write_text(json.dumps({"scope": "time >= 3s; reward rates before dt scaling; extrema are not per-step amplitudes; dev9 heading is whole-episode max degrees", "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "summary_sha256": hashlib.sha256((evidence / "comparison/summary.json").read_bytes()).hexdigest(), "dev9": dev9, "reports": result}, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"reports": len(result), "output": str(output)}, ensure_ascii=True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, required=True)
    main(parser.parse_args().evidence)
