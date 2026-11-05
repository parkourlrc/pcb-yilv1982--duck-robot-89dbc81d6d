"""Verify documented TI stencil changes and preservation of non-target geometry."""
from collections import Counter
import argparse
import copy
import csv
import json
import math
from pathlib import Path
import subprocess

import pcbnew
import pipeline
from align_codec_stencil import EVIDENCE,LIBRARY_NAMES
from export_jlc_rs274x import drawing_commands
from finalize_remaining_smt_candidate import identified
from generate_rev_a import children,first,parse
from search_remaining_thermal_pads import covered
from verify_outward_power_header import normalize_angles
from verify_release_metadata import snapshot


def area(width,height,radius):
    return width*height-(4-math.pi)*radius*radius


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--attempt',default='codec-ldo-04')
    arguments=parser.parse_args()
    checkpoint=pipeline.current_checkpoint()
    candidate=json.loads((EVIDENCE/arguments.attempt/'candidate.json').read_text(encoding='utf-8'))
    work=pipeline.managed(Path(candidate['project']))
    before=pipeline.prepare(pipeline.PRIMARY)
    name=pipeline.STEM+'.kicad_pcb'
    runs={}
    for label,project in [('before',before),('after',work)]:
        report=project.parent/('stencil-filled-'+label+'.json')
        command=[pipeline.find_cli(),'pcb','drc','--format','json','--severity-all','--schematic-parity','--refill-zones','--save-board','--output',report,project/name]
        result=subprocess.run(list(map(str,command)),capture_output=True,timeout=180)
        (EVIDENCE/('filled-'+label+'.log')).write_bytes(result.stdout+result.stderr)
        result.check_returncode()
        data=json.loads(report.read_text(encoding='utf-8'))
        runs[label]={'project':str(project),'pcb_sha256':pipeline.digest(project/name),'violations':len(data['violations']),'unconnected':len(data['unconnected_items']),'parity':len(data['schematic_parity'])}
    old=snapshot(before/name)
    new=snapshot(work/name)
    original_board=pcbnew.LoadBoard(str(before/name))
    board=pcbnew.LoadBoard(str(work/name))
    original_nodes=identified(parse((before/name).read_text(encoding='utf-8')))
    updated_nodes=identified(parse((work/name).read_text(encoding='utf-8')))
    expected_refs={'U701','U702'}
    unexpected_objects=[]
    for identifier,node in original_nodes.items():
        if node[0]=='footprint' and any(prop[1]=='Reference' and prop[2] in expected_refs for prop in children(node,'property')):
            continue
        current=updated_nodes.get(identifier,['missing'])
        if node[0]=='zone':
            node=[child for child in node if not isinstance(child,list) or child[0]!='filled_polygon']
            current=[child for child in current if not isinstance(child,list) or child[0]!='filled_polygon']
        if normalize_angles(node)!=normalize_angles(current):
            unexpected_objects.append(identifier)
    numbered_pad_changes=[]
    ep_id=next(identifier for identifier,pad in old['pads'].items() if pad['reference']=='U701' and pad['pin']=='33')
    for identifier,pad in old['pads'].items():
        expected=copy.deepcopy(pad)
        if pad['reference']=='U702' and pad['pin']=='2' and pad['size']==[2200000,1200000]:
            expected['layers']='00000000_00000000_00000000_0000000c'
        if pad['pin'] and identifier!=ep_id and new['pads'].get(identifier)!=expected:
            numbered_pad_changes.append(identifier)
    lost=[identifier for identifier,group in old['connections'].items() if not set(group).issubset(new['connections'].get(identifier,[]))]
    net_changes=[identifier for identifier,net in old['nets'].items() if net!=new['nets'].get(identifier)]
    shape_checks=[]
    for reference in ['U701','U702']:
        footprint=board.FindFootprintByReference(reference)
        paste=[pad for pad in footprint.Pads() if not pad.GetNumber() and pad.IsOnLayer(pcbnew.B_Paste)]
        if reference=='U701':
            pad=next(pad for pad in footprint.Pads() if pad.GetNumber()=='33')
            expected_size=(1.49,1.49)
            expected_count=4
            metal=3.45*3.45
            required_points={(round(pcbnew.ToMM(footprint.GetPosition().x)+xoffset,4),round(pcbnew.ToMM(footprint.GetPosition().y)+yoffset,4)) for xoffset in [-.845,.845] for yoffset in [-.845,.845]}
            ep_check=list(pad.GetSize())==[3450000,3450000] and abs(pcbnew.ToMM(pad.GetRoundRectCornerRadius())-.05)<5e-6
        else:
            lead=next(pad for pad in footprint.Pads() if pad.GetNumber()=='1')
            center=(pcbnew.ToMM(lead.GetPosition().x)+6.665,pcbnew.ToMM(footprint.GetPosition().y))
            required_points={(round(center[0]+(column-1.5)*1.35,4),round(center[1]+(row-1.5)*1.32,4)) for column in range(4) for row in range(4)}
            expected_size=(1.15,1.12)
            expected_count=16
            metal=5.7*5.5
            ep_check=all(not pad.IsOnLayer(pcbnew.B_Paste) for pad in footprint.Pads() if pad.GetNumber()=='2')
        positions={(round(pcbnew.ToMM(pad.GetPosition().x),4),round(pcbnew.ToMM(pad.GetPosition().y),4)) for pad in paste}
        sizes=all(tuple(pcbnew.ToMM(value) for value in pad.GetSize())==expected_size and abs(pcbnew.ToMM(pad.GetRoundRectCornerRadius())-.05)<1e-6 for pad in paste)
        aperture_area=sum(area(pcbnew.ToMM(pad.GetSize().x),pcbnew.ToMM(pad.GetSize().y),pcbnew.ToMM(pad.GetRoundRectCornerRadius())) for pad in paste)
        shape_checks.append({'reference':reference,'paste_count':len(paste),'size_mm':expected_size,'position_matches_drawing':positions==required_points,
            'sizes_and_radii_match':sizes,'central_land_or_optional_stub_policy':ep_check,'total_window_area_mm2':aperture_area,'coverage_of_ti_example_metal':aperture_area/metal,
            'accepted':len(paste)==expected_count and positions==required_points and sizes and ep_check})
    samples=pipeline.BASE.parents[1]/'docs/references/归档扩展板贴片与层叠复核/relocate-after-plane-samples.csv'
    losses=[]
    with samples.open(encoding='utf-8',newline='') as stream:
        for row in csv.DictReader(stream):
            point=pcbnew.VECTOR2I(pcbnew.FromMM(float(row['x_mm'])),pcbnew.FromMM(float(row['y_mm'])))
            for layer_name,net in [('F.Cu','POWER_GND'),('In1.Cu','POWER_GND'),('In2.Cu','+3V3'),('B.Cu','POWER_GND')]:
                if layer_name==row['source_layer']:
                    continue
                layer=board.GetLayerID(layer_name)
                if covered(original_board,point,layer,net) and not covered(board,point,layer,net):
                    losses.append({'net':row['net'],'plane':layer_name,'point':[row['x_mm'],row['y_mm']]})
    plots={}
    for label,project in [('before',before),('after',work)]:
        output=EVIDENCE/(arguments.attempt+'-plot-'+label)
        output.mkdir(exist_ok=False)
        result=subprocess.run(list(map(str,[pipeline.find_cli(),'pcb','export','gerbers','--no-x2','--no-netlist','--layers','F.Cu,In1.Cu,In2.Cu,B.Cu,F.Mask,B.Mask,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,Edge.Cuts','--output',output,project/name])),capture_output=True,timeout=180)
        (EVIDENCE/('plot-'+label+'.log')).write_bytes(result.stdout+result.stderr)
        result.check_returncode()
        plots[label]={file.name:drawing_commands(file) for file in output.iterdir() if file.suffix!='.gbrjob'}
    changed_layers=[name for name,commands in plots['before'].items() if commands!=plots['after'].get(name)]
    permitted_layers={pipeline.STEM+'-B_Cu.gbl',pipeline.STEM+'-B_Mask.gbs',pipeline.STEM+'-B_Paste.gbp'}
    original_hashes=pipeline.fingerprints(pipeline.PRIMARY)
    new_hashes=pipeline.fingerprints(work)
    changed_files={name for name,value in new_hashes.items() if original_hashes.get(name)!=value}
    expected_files={pipeline.STEM+'.kicad_pcb','audio.kicad_sch','power.kicad_sch',*('duck.pretty/'+name+'.kicad_mod' for name in LIBRARY_NAMES.values())}
    reports,summary=pipeline.check(work)
    result={'runs':runs,'source_unchanged':original_hashes==checkpoint['design_hashes'],'unexpected_objects':unexpected_objects,
        'object_set_equal':original_nodes.keys()==updated_nodes.keys(),'changed_files':sorted(changed_files),'changed_files_expected':changed_files==expected_files,
        'numbered_pad_changes_other_than_U701_EP':numbered_pad_changes,'original_net_changes':net_changes,'lost_connections':lost,
        'all_tracks_vias_unchanged':old['tracks']==new['tracks'],'i2s_actual_reference_copper_loss':losses,'shape_checks':shape_checks,
        'changed_gerber_layers':changed_layers,'only_expected_layers_changed':set(changed_layers)<=permitted_layers,
        'summary':str(reports/'summary.json'),'native_status':summary['status'],'manufacturing_released':False,'hardware_tested':False}
    result['accepted']=all((not unexpected_objects,result['object_set_equal'],result['changed_files_expected'],not numbered_pad_changes,not net_changes,not lost,
        result['all_tracks_vias_unchanged'],not losses,all(row['accepted'] for row in shape_checks),result['only_expected_layers_changed'],
        summary['status']=='checks_clean_not_manufacturing_release',result['source_unchanged']))
    pipeline.write_json(EVIDENCE/'geometry-connectivity-check.json',result)
    pipeline.write_json(EVIDENCE/'candidate.json',{**candidate,'summary':str(reports/'summary.json')})
    print(json.dumps({key:value for key,value in result.items() if key!='i2s_actual_reference_copper_loss'}))
    if not result['accepted']:
        raise RuntimeError('Stencil verification failed')


if __name__=='__main__':
    main()
