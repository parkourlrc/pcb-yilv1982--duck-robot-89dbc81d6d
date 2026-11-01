"""Verify all accepted power changes against the unchanged original full project."""
from collections import Counter
import json
from pathlib import Path
import shutil
import tempfile

import pcbnew

import pipeline
import repair_u501
from power_repair_steps import load_state
from repair_power_connections import EVIDENCE
from verify_u501_connectivity import partitions


def main():
    state,work=load_state()
    reports,summary=pipeline.check(work)
    for name in ['summary.json','drc.json','erc.json']:
        shutil.copy2(reports/name,EVIDENCE/('after-'+name))
    path=work/(pipeline.STEM+'.kicad_pcb')
    shutil.copy2(path,EVIDENCE/'after.kicad_pcb')
    pipeline.write_json(EVIDENCE/'geometry-after.json',repair_u501.geometry(pcbnew.LoadBoard(str(path))))
    before=json.loads((EVIDENCE/'before-drc.json').read_text(encoding='utf-8'))
    after=json.loads((EVIDENCE/'after-drc.json').read_text(encoding='utf-8'))
    changes={}
    for category in ['violations','unconnected_items','schematic_parity']:
        old=Counter(repair_u501.signature(item) for item in before[category])
        new=Counter(repair_u501.signature(item) for item in after[category])
        changes[category]={'added':list((new-old).elements()),'removed':list((old-new).elements())}
    groups={};commands=[];power_groups={};identifiers={}
    with tempfile.TemporaryDirectory(prefix='hat-power-connectivity-') as temporary:
        for label,source in [('before',pipeline.PRIMARY),('after',work)]:
            copied=Path(temporary)/label
            copied.mkdir()
            for source_path in pipeline.design_files(source):
                target=copied/source_path.relative_to(source)
                target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(source_path,target)
            copied_board=copied/path.name
            report=copied/'filled-drc.json'
            pipeline.run_command([pipeline.find_cli(),'pcb','drc','--format','json','--severity-all','--refill-zones','--save-board','--output',report,copied_board],EVIDENCE,'connectivity-'+label,commands,report)
            board=pcbnew.LoadBoard(str(copied_board))
            groups[label]=partitions(board)
            pad_names={pad.m_Uuid.AsString():footprint.GetReference()+'.'+pad.GetNumber() for footprint in board.GetFootprints() for pad in footprint.Pads()}
            identifiers[label]=pad_names
            power_groups[label]={}
            for net in ['+3V3','POWER_GND']:
                unique={tuple(sorted(pad_names[identifier] for identifier in groups[label][pad.m_Uuid.AsString()])) for footprint in board.GetFootprints() for pad in footprint.Pads() if pad.GetNetname()==net}
                power_groups[label][net]=sorted(unique)
    splits={identifiers['before'][identifier]:connected for identifier,connected in groups['before'].items() if not set(connected).issubset(groups['after'].get(identifier,[]))}
    accepted=not changes['violations']['added'] and not changes['schematic_parity']['added'] and not splits
    accepted=accepted and not summary['netlist_check']['mismatches'] and not summary['netlist_check']['contract_differences']
    accepted=accepted and len(after['unconnected_items'])<len(before['unconnected_items'])
    pipeline.write_json(EVIDENCE/'connectivity-verification.json',{'commands':commands,'groups':groups,'lost_connections':splits,'power_groups':power_groups})
    outcome={'local_acceptance':bool(accepted),'work':str(work),'changes':changes,'before_hash':state['before_hash'],'candidate_hash':pipeline.digest(path),'promoted':False,'remaining_unconnected':len(after['unconnected_items']),'remaining_ordinary_warnings':len(after['violations'])}
    pipeline.write_json(EVIDENCE/'result.json',outcome)
    print(json.dumps({'accepted':bool(accepted),'lost_connections':len(splits),'power_group_counts':{label:{net:len(value) for net,value in nets.items()} for label,nets in power_groups.items()},'drc':summary['drc']}))
    if not accepted:raise SystemExit('Candidate rejected; main unchanged')


if __name__=='__main__':main()
