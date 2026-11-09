"""顺序执行明确指定的已批准候选；每组独立账本并归档，不自动增加轮数。"""
from pathlib import Path
import argparse
import datetime
import json
import shutil
import subprocess
import sys
import time

from prepare import prepare, PRESETS


def archive(base, evidence):
    target = evidence/base.name
    target.mkdir(parents=True, exist_ok=True)
    for name in ("config.json","preparation.json","launch.json","train.log","diagnose.log"):
        if (base/name).exists():shutil.copy2(base/name,target/name)
    for name in ("run.json","updates.jsonl","result.json","evaluation_000100.json","failure.json","amplitude_stop.json"):
        if (base/"run"/name).exists():shutil.copy2(base/"run"/name,target/name)
    if (base/"experiment/budget.jsonl").exists():shutil.copy2(base/"experiment/budget.jsonl",target/"budget.jsonl")
    if (base/"run/result.json").exists():
        result=json.loads((base/"run/result.json").read_text())
        shutil.copy2(result["checkpoint_manifest"],target/"manifest.json")
    if (base/"diagnostic").exists():
        shutil.copytree(base/"diagnostic",target/"diagnostic",dirs_exist_ok=True)


def main(args):
    raise SystemExit("历史批处理启动器已停用。请从平台导入历史档案，以版本化配置创建新实验；旧源码与预算档案保留。")
    args.status.parent.mkdir(parents=True, exist_ok=True)
    if args.existing_first:
        base=args.existing_first
        launch=json.loads((base/'launch.json').read_text())
        while True:
            process=Path('/proc')/str(launch['pid'])/'cmdline'
            if not process.exists():break
            command=process.read_bytes()
            if b'mjlab_duck.train_locomotion' not in command or str(base/'run').encode() not in command:break
            args.status.write_text(json.dumps({'phase':'waiting_existing_training','base':str(base),'pid':launch['pid']})+'\n')
            time.sleep(5)
        if not (base/'run/result.json').exists():
            archive(base,args.evidence)
            raise RuntimeError('existing training exited without result; not continuing batch')
        args.status.write_text(json.dumps({'phase':'diagnosing','base':str(base)})+'\n')
        command=[sys.executable,'-u',str(base/'frozen/training/experiments/amplitude/diagnose.py'),
                 '--base',str(base),'--output',str(base/'diagnostic'),'--render']
        with (base/'diagnose.log').open('xb') as log:
            code=subprocess.call(command,cwd=base,stdout=log,stderr=subprocess.STDOUT)
        archive(base,args.evidence)
        if code:raise SystemExit(code)
    for preset in args.presets:
        base=args.work_root/f"amplitude-20261107-{preset}-s{args.seed}"
        prepare(args.source,base,preset,args.seed)
        def status(phase,**details):
            data={"utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"preset":preset,"seed":args.seed,"base":str(base),"phase":phase,**details}
            temporary=args.status.with_suffix('.tmp')
            temporary.write_text(json.dumps(data,indent=2)+'\n')
            temporary.replace(args.status)
            print(json.dumps(data),flush=True)
        command=[sys.executable,'-u','-m','mjlab_duck.train_locomotion','--config',str(base/'config.json'),
                 '--output',str(base/'run'),'--experiment-dir',str(base/'experiment'),'--run-id',base.name]
        with (base/'train.log').open('xb') as log:
            child=subprocess.Popen(command,cwd=base/'frozen/training',stdout=log,stderr=subprocess.STDOUT)
            launch={'pid':child.pid,'command':command,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
            (base/'launch.json').write_text(json.dumps(launch,indent=2)+'\n')
            status('training',pid=child.pid)
            code=child.wait()
        archive(base,args.evidence)
        if code:
            status('failed',exit_code=code,step='training')
            raise SystemExit(code)
        status('diagnosing')
        command=[sys.executable,'-u',str(base/'frozen/training/experiments/amplitude/diagnose.py'),
                 '--base',str(base),'--output',str(base/'diagnostic'),'--render']
        with (base/'diagnose.log').open('xb') as log:
            code=subprocess.call(command,cwd=base,stdout=log,stderr=subprocess.STDOUT)
        archive(base,args.evidence)
        if code:
            status('failed',exit_code=code,step='diagnostic')
            raise SystemExit(code)
        status('candidate_complete')
    status('batch_complete')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--existing-first',type=Path)
    parser.add_argument('--work-root',type=Path,required=True)
    parser.add_argument('--presets',choices=PRESETS,nargs='+',required=True)
    parser.add_argument('--seed',type=int,default=42)
    parser.add_argument('--status',type=Path,required=True)
    parser.add_argument('--evidence',type=Path,required=True)
    main(parser.parse_args())
