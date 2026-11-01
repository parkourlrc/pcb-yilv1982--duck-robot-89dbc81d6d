#!/usr/bin/env python3
"""Bounded ptrace of the native control thread; no bus commands or service changes.

ptrace can change syscall timing. Treat captured delays as instrumented observations.
"""
import datetime
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import time

sp=importlib.util.spec_from_file_location('diag',Path(__file__).with_name('imu-diagnostic-read-20261101.py'))
d=importlib.util.module_from_spec(sp)
sp.loader.exec_module(d)
ROOT=Path('/home/radxa/duck-runtime-stage-20261031')
TRACE=ROOT/'native-read-trace-20261101.log'
OUT=ROOT/'native-read-trace-20261101.json'
r={'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
   'scope':'Trace control thread only; no motor commands; ptrace may alter timing.', 'samples':[]}
proc=None
try:
    r['before']=d.status()
    if r['before'].get('torque_state')!='off' or r['before'].get('motion') is not None:
        raise RuntimeError('Start only when robot is off and motion-idle.')
    pid=int(d.run(['systemctl','show','robotd','-p','MainPID','--value'])['stdout'])
    tasks=[p for p in (Path('/proc')/str(pid)/'task').iterdir() if (p/'comm').read_text().strip()=='control']
    if len(tasks)!=1:
        raise RuntimeError('Expected exactly one control thread.')
    r['pid']=pid
    r['control_tid']=int(tasks[0].name)
    r['trace_args']=[str(ROOT/'diagnostic-tools/strace/usr/bin/strace'),'-qq','-ttt','-T','-xx','-s','512',
                     '-e','trace=read,write,ioctl,poll,ppoll','-p',str(r['control_tid']),'-o',str(TRACE)]
    proc=subprocess.Popen(r['trace_args'],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True)
    print(json.dumps({'tracing_tid':r['control_tid'],'maximum_seconds':45}),flush=True)
    end=time.monotonic()+45
    baseline=r['before']['total_communication_failures']
    while time.monotonic()<end:
        time.sleep(1)
        s=d.status()
        r['samples'].append({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
                             **{k:s.get(k) for k in ['total_cycles','total_communication_failures','last_failure','torque_state','motion']}})
        if s['total_communication_failures']>baseline:
            r['new_failure_seen']=True
            break
        if proc.poll() is not None:
            raise RuntimeError('strace exited early.')
except Exception as e:
    r['error']=repr(e)
finally:
    if proc:
        if proc.poll() is None:
            proc.send_signal(signal.SIGINT)
        try:
            _,r['trace_stderr']=proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            _,r['trace_stderr']=proc.communicate(timeout=5)
        r['trace_exit']=proc.returncode
    try:
        r['after']=d.status()
    except Exception as e:
        r['after_error']=repr(e)
    r['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    since=datetime.datetime.fromisoformat(r['started_utc']).strftime('%Y-%m-%d %H:%M:%S UTC')
    r['journal']=d.run(['journalctl','-u','robotd','--since',since,'-o','short-iso-precise','--no-pager'],False)
    OUT.write_text(json.dumps(r,ensure_ascii=False,indent=2))
    os.chown(OUT,1000,1000)
    if TRACE.exists():os.chown(TRACE,1000,1000)
    print(json.dumps({'output':str(OUT),'new_failure_seen':r.get('new_failure_seen'),
                      'error':r.get('error'),'trace_exit':r.get('trace_exit'),
                      'after_torque':r.get('after',{}).get('torque_state')}),flush=True)
