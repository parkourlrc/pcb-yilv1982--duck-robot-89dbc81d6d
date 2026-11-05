"""Verify source invariants and reference-copper deltas for per-pad thermal reliefs."""
import csv
import argparse
import json
from pathlib import Path
import subprocess
import sys

import pcbnew
import pipeline
from verify_release_metadata import snapshot


EVIDENCE=pipeline.BASE.parents[1]/'docs/references/归档扩展板贴片规范复查'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--selective',action='store_true')
    arguments=parser.parse_args()
    suffix='-selective' if arguments.selective else ''
    checkpoint=pipeline.current_checkpoint()
    candidate=json.loads((EVIDENCE/('thermal-relief-candidate-angle45'+suffix+'.json')).read_text(encoding='utf-8'))
    work=pipeline.managed(Path(candidate['project']))
    before=pipeline.prepare(pipeline.PRIMARY)
    runs={}
    samples={}
    for label,project in (('before',before),('after',work)):
        path=project/(pipeline.STEM+'.kicad_pcb')
        report=project.parent/('thermal-filled-'+label+'.json')
        command=[pipeline.find_cli(),'pcb','drc','--format','json','--severity-all','--schematic-parity','--refill-zones','--save-board','--output',report,path]
        result=subprocess.run(list(map(str,command)),capture_output=True,encoding='utf-8',errors='replace')
        (EVIDENCE/('thermal-filled-'+label+'.log')).write_text(result.stdout+result.stderr,encoding='utf-8')
        result.check_returncode()
        drc=json.loads(report.read_text(encoding='utf-8'))
        runs[label]={'project':str(project),'pcb_sha256':pipeline.digest(path),'violations':len(drc['violations']),'unconnected':len(drc['unconnected_items']),'parity':len(drc['schematic_parity'])}
        result=subprocess.run([sys.executable,'-X','utf8',str(Path(__file__).with_name('inspect_i2s_reference_planes.py')),'--project',str(project),'--prefix','thermal-'+label,'--evidence',str(EVIDENCE)],capture_output=True,encoding='utf-8',errors='replace')
        (EVIDENCE/('thermal-'+label+'-reference.log')).write_text(result.stdout+result.stderr,encoding='utf-8')
        result.check_returncode()
        with (EVIDENCE/('thermal-'+label+'-plane-samples.csv')).open(encoding='utf-8',newline='') as stream:
            samples[label]={(row['segment'],row['x_mm'],row['y_mm']):row for row in csv.DictReader(stream)}
    original=snapshot(before/(pipeline.STEM+'.kicad_pcb'))
    updated=snapshot(work/(pipeline.STEM+'.kicad_pcb'))
    lost=[identifier for identifier,group in original['connections'].items() if not set(group).issubset(updated['connections'].get(identifier,[]))]
    lost_samples=[]
    for key,row in samples['before'].items():
        for plane in ('F.Cu:POWER_GND','In1.Cu:POWER_GND','In2.Cu:+3V3','B.Cu:POWER_GND'):
            if plane.split(':')[0]!=row['source_layer'] and row[plane]=='True' and samples['after'].get(key,{}).get(plane)!='True':
                lost_samples.append({'net':row['net'],'source_layer':row['source_layer'],'plane':plane,'position_mm':list(key[1:]),'represented_mm':float(row['represented_mm'])})
    reports,summary=pipeline.check(work)
    record={'runs':runs,'pads_unchanged':original['pads']==updated['pads'],'pad_nets_unchanged':original['nets']==updated['nets'],'tracks_unchanged':original['tracks']==updated['tracks'],
            'lost_connections':lost,'reference_sample_keys_equal':samples['before'].keys()==samples['after'].keys(),'lost_i2s_reference_samples':lost_samples,
            'lost_reference_sample_length_mm':sum(row['represented_mm'] for row in lost_samples),'summary':str(reports/'summary.json'),'native_status':summary['status'],
            'promoted':False,'primary_unchanged':pipeline.fingerprints(pipeline.PRIMARY)==checkpoint['design_hashes'],'manufacturing_released':False}
    record['accepted']=all((record['pads_unchanged'],record['pad_nets_unchanged'],record['tracks_unchanged'],not lost,not lost_samples,record['reference_sample_keys_equal'],summary['status']=='checks_clean_not_manufacturing_release'))
    pipeline.write_json(EVIDENCE/('thermal-relief-verification'+suffix+'.json'),record)
    print(json.dumps({key:value for key,value in record.items() if key!='lost_i2s_reference_samples'},ensure_ascii=False))


if __name__=='__main__':
    main()
