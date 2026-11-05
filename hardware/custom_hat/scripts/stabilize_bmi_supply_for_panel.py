"""Bridge existing BMI088 supply stubs without depending on marginal zone topology."""
import csv
import json
from pathlib import Path
import subprocess

import pcbnew
import pipeline
from add_i2c_pullups import vector
from generate_rev_a import parse,first
from finalize_remaining_smt_candidate import identified
from search_remaining_thermal_pads import covered
from verify_outward_power_header import normalize_angles
from verify_release_metadata import snapshot


EVIDENCE=pipeline.BASE.parents[1]/'docs/references/扩展板邮票孔与电源修复'


def main():
    EVIDENCE.mkdir(exist_ok=False)
    checkpoint=pipeline.current_checkpoint()
    before=pipeline.prepare(pipeline.PRIMARY)
    work=pipeline.prepare(pipeline.PRIMARY)
    name=pipeline.STEM+'.kicad_pcb'
    board=pcbnew.LoadBoard(str(work/name))
    pad=next(pad for pad in board.FindFootprintByReference('U501').Pads() if pad.GetNumber()=='15')
    segment=pcbnew.PCB_TRACK(board)
    segment.SetStart(vector((160.19,111.10)))
    segment.SetEnd(vector((160.69,111.10)))
    segment.SetLayer(pcbnew.F_Cu)
    segment.SetWidth(pcbnew.FromMM(.2))
    segment.SetNet(pad.GetNet())
    board.Add(segment)
    segment_uuid=segment.m_Uuid.AsString()
    pcbnew.SaveBoard(str(work/name),board)
    runs={}
    for label,project in [('before',before),('after',work)]:
        report=project.parent/('bmi-supply-filled-'+label+'.json')
        result=subprocess.run(list(map(str,[pipeline.find_cli(),'pcb','drc','--format','json','--severity-all','--schematic-parity','--refill-zones','--save-board','--output',report,project/name])),capture_output=True,timeout=180)
        (EVIDENCE/('filled-'+label+'.log')).write_bytes(result.stdout+result.stderr)
        result.check_returncode()
        doc=json.loads(report.read_text(encoding='utf-8'))
        runs[label]={'project':str(project),'pcb_sha256':pipeline.digest(project/name),'violations':len(doc['violations']),'unconnected':len(doc['unconnected_items']),'parity':len(doc['schematic_parity'])}
    original=snapshot(before/name)
    updated=snapshot(work/name)
    old_board=pcbnew.LoadBoard(str(before/name))
    new_board=pcbnew.LoadBoard(str(work/name))
    old_nodes=identified(parse((before/name).read_text(encoding='utf-8')))
    new_nodes=identified(parse((work/name).read_text(encoding='utf-8')))
    unexpected=[]
    for identifier,node in old_nodes.items():
        candidate=new_nodes.get(identifier,['missing'])
        if node[0]=='zone':
            node=[entry for entry in node if not isinstance(entry,list) or entry[0]!='filled_polygon']
            candidate=[entry for entry in candidate if not isinstance(entry,list) or entry[0]!='filled_polygon']
        if normalize_angles(node)!=normalize_angles(candidate):
            unexpected.append(identifier)
    loss=[]
    samples=pipeline.BASE.parents[1]/'docs/references/归档扩展板贴片与层叠复核/relocate-after-plane-samples.csv'
    with samples.open(encoding='utf-8',newline='') as stream:
        rows=list(csv.DictReader(stream))
    for row in rows:
        point=vector((float(row['x_mm']),float(row['y_mm'])))
        for layer_name,net in [('F.Cu','POWER_GND'),('In1.Cu','POWER_GND'),('In2.Cu','+3V3'),('B.Cu','POWER_GND')]:
            if layer_name==row['source_layer']:
                continue
            layer=new_board.GetLayerID(layer_name)
            if covered(old_board,point,layer,net) and not covered(new_board,point,layer,net):
                loss.append({'net':row['net'],'plane':layer_name,'point_mm':[row['x_mm'],row['y_mm']]})
    lost=[identifier for identifier,group in original['connections'].items() if not set(group).issubset(updated['connections'].get(identifier,[]))]
    all_existing_tracks=all(updated['tracks'].get(identifier)==entry for identifier,entry in original['tracks'].items())
    reports,summary=pipeline.check(work)
    result={'runs':runs,'added_segment':{'uuid':segment_uuid,'net':'+3V3','layer':'F.Cu','width_mm':.2,'start_mm':[160.19,111.10],'end_mm':[160.69,111.10],'length_mm':.5},
        'all_original_pads_equal':original['pads']==updated['pads'],'all_original_pad_nets_equal':original['nets']==updated['nets'],
        'all_original_tracks_vias_equal':all_existing_tracks,'lost_connections':lost,'unexpected_object_changes':unexpected,
        'only_expected_object_added':new_nodes.keys()-old_nodes.keys()=={segment_uuid},'i2s_samples':len(rows),'reference_copper_loss':loss,
        'summary':str(reports/'summary.json'),'native_status':summary['status'],'source_unchanged':pipeline.fingerprints(pipeline.PRIMARY)==checkpoint['design_hashes'],
        'manufacturing_released':False,'hardware_tested':False}
    result['accepted']=all((result['all_original_pads_equal'],result['all_original_pad_nets_equal'],all_existing_tracks,not lost,not unexpected,
        result['only_expected_object_added'],not loss,summary['status']=='checks_clean_not_manufacturing_release',result['source_unchanged']))
    pipeline.write_json(EVIDENCE/'geometry-connectivity-check.json',result)
    pipeline.write_json(EVIDENCE/'candidate.json',{'project':str(work),'summary':str(reports/'summary.json'),'promoted':False})
    print(json.dumps({key:value for key,value in result.items() if key!='reference_copper_loss'}))
    if not result['accepted']:
        raise RuntimeError('BMI supply bridge failed')


if __name__=='__main__':
    main()
