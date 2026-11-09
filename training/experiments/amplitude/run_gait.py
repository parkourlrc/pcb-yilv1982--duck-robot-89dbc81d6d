"""明确四组百轮奖励对照的监督器；状态、失败、预算均独立保存。"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import threading
from prepare_gait import GAIT_PRESETS, prepare_gait
from run_batch import archive


def main(a):
    raise SystemExit("历史足部对照启动器已停用。请在训练平台选择 gait010/gait020/rawramp/gait010_rawramp 配方并登记预算。")
    stop_launching = threading.Event()
    tag = ("-"+a.suffix) if a.suffix else ""
    bases = {name:a.work_root/f"amplitude-20261107-{name}-s{a.seed}{tag}" for name in a.presets}
    if len(bases) != len(a.presets) or any(p.exists() for p in bases.values()):
        raise ValueError("Duplicate preset or existing destination")
    for name, base in bases.items():
        prepare_gait(a.source, base, name, a.seed)
    def run(name, base):
        status_file = base/"supervisor-status.json"
        def status(phase, **kw):
            data = {"utc":datetime.now(timezone.utc).isoformat(),"preset":name,"base":str(base),"phase":phase,**kw}
            status_file.write_text(json.dumps(data,indent=2)+"\n")
            print(json.dumps(data),flush=True)
        if stop_launching.is_set():
            status("not_started_after_failure")
            return {"preset":name,"code":1}
        try:
            command = [sys.executable,"-u","-m","mjlab_duck.train_locomotion","--config",str(base/"config.json"),
                       "--output",str(base/"run"),"--experiment-dir",str(base/"experiment"),"--run-id",base.name]
            with (base/"train.log").open("xb") as log:
                child = subprocess.Popen(command,cwd=base/"frozen/training",stdout=log,stderr=subprocess.STDOUT)
                (base/"launch.json").write_text(json.dumps({"pid":child.pid,"command":command,"utc":datetime.now(timezone.utc).isoformat()},indent=2)+"\n")
                status("training",pid=child.pid)
                code=child.wait()
            if code:
                raise RuntimeError(f"training exited {code}")
            status("diagnosing")
            command=[sys.executable,"-u",str(base/"frozen/training/experiments/amplitude/diagnose.py"),
                     "--base",str(base),"--output",str(base/"diagnostic"),"--render"]
            with (base/"diagnose.log").open("xb") as log:
                code=subprocess.call(command,cwd=base,stdout=log,stderr=subprocess.STDOUT)
            if code:
                raise RuntimeError(f"diagnostic exited {code}")
            status("complete")
            return {"preset":name,"code":0}
        except Exception as exc:
            stop_launching.set()
            status("failed",error=repr(exc))
            return {"preset":name,"code":1,"error":repr(exc)}
        finally:
            archive(base,a.evidence)
            if status_file.exists():
                import shutil
                shutil.copy2(status_file,a.evidence/base.name/status_file.name)
    results=[]
    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        jobs=[pool.submit(run,n,b) for n,b in bases.items()]
        for future in as_completed(jobs):
            results.append(future.result())
            (a.work_root/f"amplitude-20261107-gait-results{tag}.json").write_text(json.dumps(results,indent=2)+"\n")
    if any(r["code"] for r in results):
        raise SystemExit(1)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--work-root",type=Path,required=True)
    p.add_argument("--evidence",type=Path,required=True)
    p.add_argument("--presets",choices=GAIT_PRESETS,nargs="+",default=list(GAIT_PRESETS))
    p.add_argument("--seed",type=int,default=42)
    p.add_argument("--workers",type=int,choices=(1,2,3,4),default=4)
    p.add_argument("--suffix",default="",choices=("","r1"))
    main(p.parse_args())
