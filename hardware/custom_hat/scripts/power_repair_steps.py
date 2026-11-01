"""Apply individually checked power changes only inside the recorded full workspace."""
from collections import Counter
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pcbnew

import pipeline
import repair_u501
from repair_power_connections import EVIDENCE


def load_state():
    state=json.loads((EVIDENCE/'state.json').read_text(encoding='utf-8'))
    work=pipeline.managed(Path(state['work']))
    if pipeline.digest(pipeline.PRIMARY/(pipeline.STEM+'.kicad_pcb'))!=state['before_hash']:
        raise ValueError('Primary changed since baseline')
    return state,work


def run_drc(work,label):
    report_dir=work.parent/'power-checks'/label
    report_dir.mkdir(parents=True,exist_ok=False)
    report=report_dir/'drc.json'
    commands=[]
    pipeline.run_command([pipeline.find_cli(),'pcb','drc','--format','json','--severity-all','--schematic-parity','--refill-zones','--save-board','--output',report,work/(pipeline.STEM+'.kicad_pcb')],report_dir,'drc',commands,report)
    pipeline.write_json(report_dir/'commands.json',commands)
    return report,json.loads(report.read_text(encoding='utf-8'))


def signature_counts(report,category):
    return Counter(repair_u501.signature(item) for item in report[category])


def attempt(state,work,label,edit,allow_warning_reduction=False,board=None):
    board_path=work/(pipeline.STEM+'.kicad_pcb')
    old=board_path.read_bytes()
    baseline=json.loads(Path(state['latest_drc']).read_text(encoding='utf-8'))
    if board is None:board=pcbnew.LoadBoard(str(board_path))
    try:
        edit(board)
        board.BuildConnectivity()
        pcbnew.SaveBoard(str(board_path),board)
        report_path,report=run_drc(work,label)
    except Exception as error:
        board_path.write_bytes(old)
        pipeline.write_json(EVIDENCE/(label+'-tool-error.json'),{'label':label,'error':str(error),'workspace_restored':True})
        raise
    added={key:list((signature_counts(report,key)-signature_counts(baseline,key)).elements()) for key in ['violations','schematic_parity']}
    improved=len(report['unconnected_items'])<len(baseline['unconnected_items'])
    if allow_warning_reduction:
        improved=improved or (len(report['unconnected_items'])==len(baseline['unconnected_items']) and len(report['violations'])<len(baseline['violations']))
    accepted=improved and not any(added.values())
    record={'label':label,'accepted':accepted,'before_unconnected':len(baseline['unconnected_items']),'after_unconnected':len(report['unconnected_items']),'before_violations':len(baseline['violations']),'after_violations':len(report['violations']),'added':added,'report':str(report_path)}
    state['attempts'].append(record)
    if accepted:
        state['accepted'].append(label)
        state['latest_drc']=str(report_path)
        shutil.copy2(board_path,report_path.parent/'accepted.kicad_pcb')
    else:
        shutil.copy2(board_path,report_path.parent/'rejected.kicad_pcb')
        board_path.write_bytes(old)
    pipeline.write_json(EVIDENCE/'state.json',state)
    print(json.dumps(record),flush=True)
    return accepted


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--step')
    args=parser.parse_args()
    state,work=load_state()
    if 'latest_drc' not in state:
        report,_=run_drc(work,'00-refill-baseline')
        state['latest_drc']=str(report)
        pipeline.write_json(EVIDENCE/'state.json',state)
    fixes=[
        ('01-remove-duplicate-5v-stub','ef520862-ce5a-4f07-8a3c-4a76ee032e79','remove'),
        ('02-c313-bottom-stub','fe73aac9-b8f5-4d20-b2e7-c8b4a17d27fc','bottom'),
        ('03-c315-bottom-stub','7f86c3a5-44ea-4ce8-98d8-6b90981883c5','bottom'),
        ('04-c320-bottom-stub','c1e10eb3-326a-4a09-9c55-5322c45938c8','bottom'),
    ]
    for label,identifier,action in fixes:
        if any(item['label']==label for item in state['attempts']):continue
        if args.step and args.step!=label:continue
        if not args.step:
            subprocess.run([sys.executable,__file__,'--step',label],check=True)
            state,work=load_state()
            continue
        def edit(board):
            item=next(item for item in board.GetTracks() if item.m_Uuid.AsString()==identifier)
            if item.GetLayer()!=pcbnew.F_Cu:raise ValueError('Wrong baseline layer')
            if action=='remove':board.Remove(item)
            else:item.SetLayer(pcbnew.B_Cu)
        attempt(state,work,label,edit,True)


if __name__=='__main__':main()
