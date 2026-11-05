"""Verify two capacitor relocations and all unchanged routing/reference copper."""
import csv
import argparse
import json
from pathlib import Path
import subprocess
import sys

import pcbnew
import pipeline
from verify_release_metadata import snapshot
from search_remaining_thermal_pads import covered


EVIDENCE=pipeline.BASE.parents[1]/'docs/references/归档扩展板贴片与层叠复核'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate',default='c305-relocate-05-combined')
    parser.add_argument('--output-name',default='capacitor-relocation-verification.json')
    parser.add_argument('--project',type=Path)
    arguments=parser.parse_args()
    checkpoint=pipeline.current_checkpoint()
    candidate=json.loads((pipeline.BASE.parents[1]/'docs/references/归档扩展板贴片规范复查'/arguments.candidate/'candidate.json').read_text(encoding='utf-8'))
    c310=json.loads((EVIDENCE/'c310-relocate-01/candidate.json').read_text(encoding='utf-8'))
    work=pipeline.managed(arguments.project or Path(candidate['project']));before=pipeline.prepare(pipeline.PRIMARY)
    runs={};samples={}
    for label,project in (('before',before),('after',work)):
        path=project/(pipeline.STEM+'.kicad_pcb');report=project.parent/('remaining-capacitors-'+label+'.json')
        result=subprocess.run(list(map(str,[pipeline.find_cli(),'pcb','drc','--format','json','--severity-all','--schematic-parity','--refill-zones','--save-board','--output',report,path])),capture_output=True,encoding='utf-8',errors='replace')
        (EVIDENCE/('capacitors-'+label+'.log')).write_text(result.stdout+result.stderr,encoding='utf-8');result.check_returncode()
        drc=json.loads(report.read_text(encoding='utf-8'))
        runs[label]={'project':str(project),'pcb_sha256':pipeline.digest(path),'violations':len(drc['violations']),'unconnected':len(drc['unconnected_items']),'parity':len(drc['schematic_parity'])}
        result=subprocess.run([sys.executable,'-X','utf8',str(Path(__file__).with_name('inspect_i2s_reference_planes.py')),'--project',str(project),'--prefix','relocate-'+label,'--evidence',str(EVIDENCE)],capture_output=True,encoding='utf-8',errors='replace')
        (EVIDENCE/('relocate-'+label+'-reference.log')).write_text(result.stdout+result.stderr,encoding='utf-8');result.check_returncode()
        with (EVIDENCE/('relocate-'+label+'-plane-samples.csv')).open(encoding='utf-8',newline='') as stream:
            samples[label]={(row['segment'],row['x_mm'],row['y_mm']):row for row in csv.DictReader(stream)}
    original=snapshot(before/(pipeline.STEM+'.kicad_pcb'));updated=snapshot(work/(pipeline.STEM+'.kicad_pcb'))
    moved={identifier for identifier,pad in original['pads'].items() if pad['reference'] in {'C305','C310'}}
    changed_pads=[identifier for identifier,pad in original['pads'].items() if pad!=updated['pads'].get(identifier)]
    allowed_tracks={row['uuid'] for row in c310['changed_tracks']}
    changed_tracks=[identifier for identifier,track in original['tracks'].items() if track!=updated['tracks'].get(identifier)]
    added=set(updated['tracks'])-set(original['tracks'])
    lost=[identifier for identifier,group in original['connections'].items() if not set(group).issubset(updated['connections'].get(identifier,[]))]
    original_board=pcbnew.LoadBoard(str(before/(pipeline.STEM+'.kicad_pcb')));new_board=pcbnew.LoadBoard(str(work/(pipeline.STEM+'.kicad_pcb')))
    zone_loss=[];real_loss=[]
    for key,row in samples['before'].items():
        for plane in ('F.Cu:POWER_GND','In1.Cu:POWER_GND','In2.Cu:+3V3','B.Cu:POWER_GND'):
            if plane.split(':')[0]==row['source_layer']:continue
            point=pcbnew.VECTOR2I(pcbnew.FromMM(float(row['x_mm'])),pcbnew.FromMM(float(row['y_mm'])))
            layer=new_board.GetLayerID(plane.split(':')[0]);net=plane.split(':')[1]
            if row[plane]=='True' and samples['after'].get(key,{}).get(plane)!='True':zone_loss.append({'net':row['net'],'plane':plane,'point':key[1:],'length_mm':float(row['represented_mm'])})
            if covered(original_board,point,layer,net) and not covered(new_board,point,layer,net):real_loss.append({'net':row['net'],'plane':plane,'point':key[1:],'length_mm':float(row['represented_mm'])})
    reports,summary=pipeline.check(work)
    record={'runs':runs,'changed_pad_ids':changed_pads,'allowed_moved_pad_ids':sorted(moved),'pad_nets_preserved':original['nets']==updated['nets'],
        'changed_track_ids':changed_tracks,'allowed_changed_track_ids':sorted(allowed_tracks),'added_track_ids':sorted(added),'expected_added':candidate['route']['added_tracks'],
        'lost_connections':lost,'reference_sample_keys_equal':samples['before'].keys()==samples['after'].keys(),'zone_only_reference_loss':zone_loss,'actual_copper_reference_loss':real_loss,
        'summary':str(reports/'summary.json'),'native_status':summary['status'],'source_unchanged':pipeline.fingerprints(pipeline.PRIMARY)==checkpoint['design_hashes'],'promoted':False}
    record['accepted']=all((set(changed_pads)==moved,record['pad_nets_preserved'],set(changed_tracks)==allowed_tracks,added==set(candidate['route']['added_tracks']),not lost,
        not real_loss,record['reference_sample_keys_equal'],summary['status']=='checks_clean_not_manufacturing_release'))
    pipeline.write_json(EVIDENCE/arguments.output_name,record)
    pipeline.write_json(EVIDENCE/'candidate.json',{**candidate,'project':str(work),'summary':str(reports/'summary.json')})
    print(json.dumps({key:value for key,value in record.items() if key not in {'zone_only_reference_loss','actual_copper_reference_loss'}}))
    print('Zone-only loss',len(zone_loss),'Actual copper loss',len(real_loss),sum(row['length_mm'] for row in real_loss))


if __name__=='__main__':main()
