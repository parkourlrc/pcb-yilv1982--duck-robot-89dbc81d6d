"""汇总足部奖励候选的实际预算、dev9及独立回放，保留失败记录。"""
from pathlib import Path
import argparse
import hashlib
import json
import math
from compare import verified_metrics


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main(a):
    rows=[]
    baseline=a.evidence/"baseline-reference"
    if (baseline/"diagnostic/summary.json").exists():
        s=read(baseline/"diagnostic/summary.json")
        row={"run":"baseline-reference","reference_only":True,"diagnostics":[]}
        for report in s["reports"]:
            m=verified_metrics(baseline/"diagnostic"/report["scenario"],s["joint_order"])
            row["diagnostics"].append({"scenario":report["scenario"],"behavior_passed":report["evaluation"]["passed"],
                "heading_max_deg":math.degrees(report["evaluation"]["checks"]["motion_0/straight_heading"]["observed"]),"metrics":m})
        if (baseline/"evaluation_000100.json").exists():
            episodes=read(baseline/"evaluation_000100.json")["episodes"]
            row["dev9"]={"passed":sum(x["passed"] for x in episodes),"total":len(episodes),
                         "completed":sum(x["completed"] for x in episodes),"failed":sum(x["failed"] for x in episodes)}
        rows.append(row)
    for base in sorted(a.evidence.glob("amplitude-20261107-*-s42*")):
        row={"run":base.name,"source":str(base.resolve())}
        if (base/"failure.json").exists():row["failure"]=read(base/"failure.json")
        if (base/"budget.jsonl").exists():
            budget=[json.loads(x) for x in (base/"budget.jsonl").read_text().splitlines()]
            row["charged_transitions"]=sum(r["transitions"] for r in budget if r["event"]=="begin")
            row["completed_updates"]=sum(r["event"]=="complete" for r in budget)
        if (base/"result.json").exists():row["result"]=read(base/"result.json")
        if (base/"updates.jsonl").exists():
            updates=[json.loads(line) for line in (base/"updates.jsonl").read_text().splitlines()]
            row["milestones"]={str(r["model_iteration"]):{
                "episodes":r["episodes"],"action_std":r["action_std_rank0"],
                "raw_clip_fraction":r["statistics"]["raw_action_clip_fraction"],"gait":r.get("gait")}
                for r in updates if r["model_iteration"] in (25,50,75,100)}
        evaluation=base/"evaluation_000100.json"
        if evaluation.exists():
            episodes=read(evaluation)["episodes"]
            row["dev9"]={"passed":sum(x["passed"] for x in episodes),"total":len(episodes),
                         "completed":sum(x["completed"] for x in episodes),"failed":sum(x["failed"] for x in episodes)}
            row["dev9_sha256"]=hashlib.sha256(evaluation.read_bytes()).hexdigest()
        diagnostic=base/"diagnostic/summary.json"
        row["diagnostics"]=[]
        if diagnostic.exists():
            s=read(diagnostic)
            for report in s["reports"]:
                folder=diagnostic.parent/report["scenario"]
                m=verified_metrics(folder,s["joint_order"])
                checks=report["evaluation"].get("checks",{})
                heading=checks.get("motion_0/straight_heading",{}).get("observed")
                row["diagnostics"].append({"scenario":report["scenario"],"behavior_passed":report["evaluation"]["passed"],
                    "heading_max_deg":math.degrees(heading) if isinstance(heading,(int,float)) else None,
                    "metrics":m})
        rows.append(row)
    out=a.evidence/"comparison";out.mkdir(exist_ok=True)
    (out/"summary.json").write_text(json.dumps(rows,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    lines=["# 足部奖励试验：完成与失败均计入预算","",
           "回放指标要求真实接触离开、连续净空>3mm至少40ms、再接触；短暂接触跳变不算合格步数。","",
           "| 运行 | 完成更新 | 消耗转换 | dev9 | 状态 |","|---|---:|---:|---|---|"]
    for r in rows:
        d=r.get("dev9",{})
        status='既有100轮参照，不计本轮消耗' if r.get('reference_only') else ('实现失败' if 'failure' in r else r.get('result',{}).get('status','未完成归档'))
        lines.append(f"| {r['run']} | {r.get('completed_updates','—')} | {r.get('charged_transitions','—')} | {d.get('passed','—')}/{d.get('total','—')} | {status} |")
    lines += ["","| 运行 / 0.06m/s场景 | 实际前速 m/s | 左/右有效起落 | 交替率 | 最大航向偏差° | 足部门槛 |","|---|---:|---|---:|---:|---|"]
    for r in rows:
        for d in r["diagnostics"]:
            m=d["metrics"]
            if not m.get("valid"):
                lines.append(f"| {r['run']} / {d['scenario']} | — | 轨迹过短 | — | — | 未通过 |")
                continue
            counts='/'.join(str(len(m['verified_foot_events'][side])) for side in ('left','right'))
            heading='—' if d['heading_max_deg'] is None else f"{d['heading_max_deg']:.2f}"
            lines.append(f"| {r['run']} / {d['scenario']} | {m['body_vx_mean_m_s']:.5f} | {counts} | {m['verified_alternation_fraction']:.1%} | {heading} | {'通过' if m['verified_foot_gate_passed'] else '未通过'} |")
    lines += ["","只有一个训练seed，不满足跨训练种子复核要求；即使单项改善，也不能据此宣布问题解决。"]
    (out/"summary.md").write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'runs':len(rows),'charged_transitions':sum(r.get('charged_transitions',0) for r in rows),'output':str(out)},ensure_ascii=True))


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--evidence",type=Path,required=True)
    main(p.parse_args())
