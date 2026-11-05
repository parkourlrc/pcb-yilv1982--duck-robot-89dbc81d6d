"""Check four-window U301 stencil with unchanged copper, routing, nets and other paste."""
from collections import Counter
import copy
import json
import math
from pathlib import Path
import subprocess

import pcbnew
import pipeline
from audit_stencil_apertures import aperture_geometry
from export_dnp_stencil import paste_flashes
from export_jlc_rs274x import drawing_commands
from finalize_remaining_smt_candidate import identified
from generate_rev_a import children,first,parse
from repair_release_metadata import properties
from segment_buck_stencil import EVIDENCE,LIBRARY_NAME,DESCRIPTION
from verify_release_metadata import snapshot
from verify_outward_power_header import normalize_angles


def main():
    checkpoint=pipeline.current_checkpoint()
    candidate=json.loads((EVIDENCE/'candidate.json').read_text(encoding='utf-8'))
    work=pipeline.managed(Path(candidate['project']))
    before=pipeline.prepare(pipeline.PRIMARY)
    name=pipeline.STEM+'.kicad_pcb'
    runs={}
    for label,project in [('before',before),('after',work)]:
        report=project.parent/('buck-stencil-filled-'+label+'.json')
        completed=subprocess.run(list(map(str,[pipeline.find_cli(),'pcb','drc','--format','json','--severity-all','--schematic-parity','--refill-zones','--save-board','--output',report,project/name])),capture_output=True,timeout=180)
        (EVIDENCE/('filled-'+label+'.log')).write_bytes(completed.stdout+completed.stderr)
        completed.check_returncode()
        document=json.loads(report.read_text(encoding='utf-8'))
        runs[label]={'project':str(project),'pcb_sha256':pipeline.digest(project/name),'violations':len(document['violations']),'unconnected':len(document['unconnected_items']),'parity':len(document['schematic_parity'])}
    board=pcbnew.LoadBoard(str(work/name))
    footprint=board.FindFootprintByReference('U301')
    ep=next(pad for pad in footprint.Pads() if pad.GetNumber()=='9')
    windows=[pad for pad in footprint.Pads() if not pad.GetNumber() and pad.IsOnLayer(pcbnew.F_Paste)]
    expected_positions={(125175000,113350000),(125175000,114650000),(126825000,113350000),(126825000,114650000)}
    window_checks=[]
    for pad in windows:
        bounds=pad.GetBoundingBox()
        copper_bounds=ep.GetBoundingBox()
        window_checks.append({'uuid':pad.m_Uuid.AsString(),'size_mm':[pcbnew.ToMM(value) for value in pad.GetSize()],
            'radius_mm':pcbnew.ToMM(pad.GetRoundRectCornerRadius()),'paste_only':pad.GetLayerSet().FmtHex()=='00000000_00000000_00000000_00002000',
            'no_net':not pad.GetNetname(),'within_ep_rectangle':bounds.GetLeft()>=copper_bounds.GetLeft() and bounds.GetRight()<=copper_bounds.GetRight() and bounds.GetTop()>=copper_bounds.GetTop() and bounds.GetBottom()<=copper_bounds.GetBottom()})
    old_root=parse((before/name).read_text(encoding='utf-8'))
    new_root=parse((work/name).read_text(encoding='utf-8'))
    old_nodes=identified(old_root)
    new_nodes=identified(new_root)
    restored=copy.deepcopy(new_root)
    restored_nodes=identified(restored)
    identifier=footprint.m_Uuid.AsString()
    target=restored_nodes[identifier]
    original=old_nodes[identifier]
    target[1]=original[1]
    first(target,'descr')[:]=first(original,'descr')
    original_pads={first(pad,'uuid')[1]:pad for pad in children(original,'pad')}
    for pad in list(children(target,'pad')):
        pad_id=first(pad,'uuid')[1]
        if pad_id not in original_pads:
            if pad[1]!='' or first(pad,'layers')!=['layers','F.Paste'] or first(pad,'net'):
                raise RuntimeError('Added object is not a paste-only aperture')
            target.remove(pad)
        elif pad[1]=='9':
            first(pad,'layers')[:]=first(original_pads[pad_id],'layers')
    ast_unchanged=normalize_angles(restored)==normalize_angles(old_root)
    old_schematic=parse((pipeline.PRIMARY/'power.kicad_sch').read_text(encoding='utf-8'))
    new_schematic=parse((work/'power.kicad_sch').read_text(encoding='utf-8'))
    old_symbol=next(symbol for symbol in children(old_schematic,'symbol') if properties(symbol).get('Reference')=='U301')
    new_symbol=next(symbol for symbol in children(new_schematic,'symbol') if properties(symbol).get('Reference')=='U301')
    next(prop for prop in children(new_symbol,'property') if prop[1]=='Footprint')[:]=next(prop for prop in children(old_symbol,'property') if prop[1]=='Footprint')
    schematic_only_id=new_schematic==old_schematic
    old_snapshot=snapshot(before/name)
    new_snapshot=snapshot(work/name)
    net_changes=[identifier for identifier,net in old_snapshot['nets'].items() if net!=new_snapshot['nets'].get(identifier)]
    lost=[identifier for identifier,connected in old_snapshot['connections'].items() if not set(connected).issubset(new_snapshot['connections'].get(identifier,[]))]
    original_hashes=pipeline.fingerprints(pipeline.PRIMARY)
    changed_files={name for name,value in pipeline.fingerprints(work).items() if original_hashes.get(name)!=value}
    expected_files={pipeline.STEM+'.kicad_pcb','power.kicad_sch','duck.pretty/'+LIBRARY_NAME+'.kicad_mod'}
    plots={}
    plot_paths={}
    for label,project in [('before',before),('after',work)]:
        output=EVIDENCE/('plot-'+label)
        output.mkdir(exist_ok=False)
        result=subprocess.run(list(map(str,[pipeline.find_cli(),'pcb','export','gerbers','--no-x2','--no-netlist','--layers','F.Cu,In1.Cu,In2.Cu,B.Cu,F.Mask,B.Mask,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,Edge.Cuts','--output',output,project/name])),capture_output=True,timeout=180)
        (EVIDENCE/('plot-'+label+'.log')).write_bytes(result.stdout+result.stderr)
        result.check_returncode()
        plot_paths[label]=output
        plots[label]={path.name:drawing_commands(path) for path in output.iterdir() if path.suffix!='.gbrjob'}
    changed_layers=[filename for filename,commands in plots['before'].items() if commands!=plots['after'].get(filename)]
    before_flashes,_=paste_flashes(plot_paths['before']/(pipeline.STEM+'-F_Paste.gtp'))
    after_flashes,_=paste_flashes(plot_paths['after']/(pipeline.STEM+'-F_Paste.gtp'))
    removed=before_flashes-after_flashes
    added=after_flashes-before_flashes
    expected_cam={(xpos,-ypos) for xpos,ypos in expected_positions}
    selected=[]
    for key,count in added.items():
        geometry=aperture_geometry(key[3])
        selected.append({'cam_xy':[key[1],key[2]],'count':count,**geometry,'area_ratio_125um':geometry['area_mm2']/(geometry['perimeter_mm']*.125)})
    area=sum(row['area_mm2']*row['count'] for row in selected)
    old_area=3.502*2.613
    semantic_paste_check=removed.total()==1 and next(iter(removed))[1:3]==(126000000,-114000000) and added.total()==4 and {key[1:3] for key in added}==expected_cam
    dimensions=all(row['size_mm']==[1.45,1.1] and abs(row['radius_mm']-.05)<5e-6 and row['paste_only'] and row['no_net'] and row['within_ep_rectangle'] for row in window_checks)
    reports,summary=pipeline.check(work)
    record={'runs':runs,'window_checks':window_checks,'window_count':len(windows),'positions_match':{tuple(pad.GetPosition()) for pad in windows}==expected_positions,
        'ep_paste_removed':not ep.IsOnLayer(pcbnew.F_Paste),'exact_target_field_contract':ast_unchanged,'schematic_only_library_id_changed':schematic_only_id,
        'original_net_changes':net_changes,'lost_connections':lost,'all_tracks_vias_equal':old_snapshot['tracks']==new_snapshot['tracks'],
        'changed_files':sorted(changed_files),'changed_files_expected':changed_files==expected_files,'changed_gerber_layers':changed_layers,
        'only_front_paste_changed':changed_layers==[pipeline.STEM+'-F_Paste.gtp'],'paste_semantics_expected':semantic_paste_check,'added_apertures':selected,
        'new_area_mm2':area,'original_area_mm2':old_area,'coverage_ratio':area/old_area,'paste_volume_at_125um_mm3':area*.125,
        'old_volume_at_125um_mm3':old_area*.125,'cross_web_width_mm':.2,'outer_margins_mm':{'x':(3.502-3.1)/2,'y':(2.613-2.4)/2},
        'summary':str(reports/'summary.json'),'native_status':summary['status'],'source_unchanged':pipeline.fingerprints(pipeline.PRIMARY)==checkpoint['design_hashes'],
        'manufacturing_released':False,'hardware_tested':False}
    record['accepted']=all((len(windows)==4,dimensions,record['positions_match'],record['ep_paste_removed'],ast_unchanged,schematic_only_id,not net_changes,not lost,
        record['all_tracks_vias_equal'],record['changed_files_expected'],record['only_front_paste_changed'],semantic_paste_check,.6<=area/old_area<=.8,
        summary['status']=='checks_clean_not_manufacturing_release',record['source_unchanged']))
    pipeline.write_json(EVIDENCE/'geometry-connectivity-check.json',record)
    candidate['summary']=str(reports/'summary.json')
    pipeline.write_json(EVIDENCE/'candidate.json',candidate)
    print(json.dumps(record))
    if not record['accepted']:
        raise RuntimeError('U301 stencil verification failed')


if __name__=='__main__':
    main()
