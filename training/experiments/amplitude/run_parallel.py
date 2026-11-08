"""按用户扩展指示并发运行既有参数族；每个候选独立预算和状态。"""
from pathlib import Path
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import datetime
import json
import subprocess
import sys
import threading

from prepare import PRESETS
from run_batch import main as run_batch

EXTRA_PRESETS={
    'kd075': {'alpha':1.,'smooth_weight':.05,'damping':.75},
    'kd050': {'alpha':1.,'smooth_weight':.05,'damping':.5},
    'ema010': {'alpha':.1,'smooth_weight':.05,'damping':2.},
    'ema025_kd100': {'alpha':.25,'smooth_weight':.05,'damping':1.},
    'ema050_kd100': {'alpha':.5,'smooth_weight':.05,'damping':1.},
    'ema025_kd075': {'alpha':.25,'smooth_weight':.05,'damping':.75},
}

def main(args):
    PRESETS.update(EXTRA_PRESETS)
    if args.worker:
        args.existing_first=None
        args.status=args.work_root/f'amplitude-20261107-{args.presets[0]}-s{args.seed}-status.json'
        run_batch(args)
        return
    # 先检查所有候选，防止部分启动后才发现目录重名。
    if len(set(args.presets))!=len(args.presets):raise ValueError('duplicate presets')
    for preset in args.presets:
        base=args.work_root/f'amplitude-20261107-{preset}-s{args.seed}'
        if base.exists():raise FileExistsError(base)
    stop_launching=threading.Event()
    def launch(preset):
        if stop_launching.is_set():
            return {'preset':preset,'exit_code':1,'skipped':'earlier worker failed; no budget consumed'}
        command=[sys.executable,'-u',str(Path(__file__).resolve()),'--worker','--presets',preset,
                 '--source',str(args.source),'--work-root',str(args.work_root),
                 '--evidence',str(args.evidence),'--seed',str(args.seed)]
        logpath=args.work_root/f'amplitude-20261107-{preset}-s{args.seed}-supervisor.log'
        with logpath.open('xb') as log:
            child=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,cwd=args.work_root)
            print(json.dumps({'preset':preset,'pid':child.pid,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':command}),flush=True)
            code=child.wait()
            if code:stop_launching.set()
        return {'preset':preset,'exit_code':code,'log':str(logpath)}
    results=[]
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures={pool.submit(launch,p):p for p in args.presets}
        for future in as_completed(futures):
            try:result=future.result()
            except Exception as exc:result={'preset':futures[future],'error':repr(exc),'exit_code':1}
            results.append(result)
            print(json.dumps(result),flush=True)
            (args.work_root/'amplitude-20261107-parallel-results.json').write_text(json.dumps(results,indent=2)+'\n')
    if any(r['exit_code'] for r in results):raise SystemExit(1)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--worker',action='store_true')
    p.add_argument('--workers',type=int,choices=(1,2,3),default=3)
    p.add_argument('--presets',choices=[name for name,value in EXTRA_PRESETS.items() if value['damping']==2.],nargs='+',required=True)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--work-root',type=Path,required=True)
    p.add_argument('--evidence',type=Path,required=True)
    p.add_argument('--seed',type=int,default=42)
    main(p.parse_args())
