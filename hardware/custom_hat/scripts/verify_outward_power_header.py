"""Verify J301 assembly-side correction without copper or pin-map changes."""
from collections import Counter
import copy
import json
import re
from pathlib import Path
import subprocess

import pcbnew
import pipeline
from complete_polarity_markers import rectangle
from export_jlc_rs274x import drawing_commands
from finalize_remaining_smt_candidate import identified
from generate_rev_a import parse, first
from verify_release_metadata import snapshot


EVIDENCE=pipeline.BASE.parents[1]/'docs/references/归档扩展板机械适配复核'


def normalize_angles(node):
    value=copy.deepcopy(node)
    for child in value:
        if isinstance(child,list):
            if child[0]=='at' and len(child)==4:
                child[3]=float(child[3])%360
            else:
                replacement=normalize_angles(child)
                child[:]=replacement
    return value


def dark_plot_signature(commands):
    aperture=None
    position=None
    region=None
    mode='G01*'
    primitives=[]
    directives=[]
    for command in commands:
        if command=='%LPC*%':
            raise RuntimeError('Clear-polarity plots need ordered rendering')
        if command.startswith('APERTURE:'):
            aperture=command
        elif command in {'G01*','G02*','G03*'}:
            mode=command
        elif command=='G36*':
            region=[]
        elif command=='G37*':
            primitives.append(('region',tuple(region)))
            region=None
        elif command.startswith(('X','Y')):
            match=re.fullmatch(r'X(-?\d+)Y(-?\d+)(.*)D0([123])\*',command)
            if not match:
                raise RuntimeError('Unsupported coordinate command: '+command)
            point=(int(match[1]),int(match[2]))
            operation=match[4]
            if region is not None:
                region.append((mode,point,match[3],operation))
            elif operation=='3':
                primitives.append(('flash',aperture,point))
            elif operation=='1':
                primitives.append(('stroke',aperture,mode,position,point,match[3]))
            position=point
        else:
            directives.append(command)
    if region is not None:
        raise RuntimeError('Unclosed plot region')
    return directives,Counter(primitives)


def main():
    candidate=json.loads((EVIDENCE/'outward-power-candidate.json').read_text(encoding='utf-8'))
    work=pipeline.managed(Path(candidate['project']))
    name=pipeline.STEM+'.kicad_pcb'
    before_path=pipeline.PRIMARY/name
    after_path=work/name
    original=snapshot(before_path)
    updated=snapshot(after_path)
    old_board=pcbnew.LoadBoard(str(before_path))
    board=pcbnew.LoadBoard(str(after_path))
    original_root=parse(before_path.read_text(encoding='utf-8'))
    candidate_root=parse(after_path.read_text(encoding='utf-8'))
    original_nodes=identified(original_root)
    candidate_nodes=identified(candidate_root)
    footprint=board.FindFootprintByReference('J301')
    footprint_uuid=footprint.m_Uuid.AsString()
    marker_ids={'c9072b7c-569b-444e-a0ef-b58dfda363f1','2646fb3c-762d-4950-8661-bf6aa4b43575','c77d9b57-9a2b-4d2a-9220-f2f2c5d8023f'}
    changed=[identifier for identifier,node in original_nodes.items() if node!=candidate_nodes.get(identifier)]
    expected=marker_ids|{footprint_uuid}
    pad_changes=[]
    for identifier,pad in original['pads'].items():
        actual=updated['pads'].get(identifier)
        ignored={'orientation'} if pad['reference']=='J301' else set()
        if {key:value for key,value in pad.items() if key not in ignored}!={key:value for key,value in (actual or {}).items() if key not in ignored}:
            pad_changes.append(identifier)
    root_unchanged=[node for node in original_root[1:] if not isinstance(node,list) or not first(node,'uuid')]==[node for node in candidate_root[1:] if not isinstance(node,list) or not first(node,'uuid')]
    other_files_before={key:value for key,value in pipeline.fingerprints(pipeline.PRIMARY).items() if key!=name}
    other_files_after={key:value for key,value in pipeline.fingerprints(work).items() if key!=name}
    marker_checks=[]
    body_boxes=[]
    for part in board.GetFootprints():
        if part.GetLayer()!=pcbnew.B_Cu:
            continue
        shapes=[item.GetBoundingBox() for item in part.GraphicalItems() if item.GetLayer()==pcbnew.B_Fab and item.Type()==pcbnew.PCB_SHAPE_T]
        if shapes:
            box=[min(item.GetLeft() for item in shapes),min(item.GetTop() for item in shapes),max(item.GetRight() for item in shapes),max(item.GetBottom() for item in shapes)]
            body_boxes.append((part.GetReference(),rectangle([pcbnew.ToMM(value) for value in box])))
    for item in board.GetDrawings():
        if item.m_Uuid.AsString() not in marker_ids:
            continue
        shape=item.GetEffectiveShape()
        body_hits=[reference for reference,body in body_boxes if body.Collide(shape,50000)]
        pad_hits=[part.GetReference()+'.'+pad.GetNumber() for part in board.GetFootprints() for pad in part.Pads() if pad.IsOnLayer(pcbnew.B_Cu) and pad.GetEffectiveShape(pcbnew.B_Cu).Collide(shape,300000)]
        marker_checks.append({'uuid':item.m_Uuid.AsString(),'text':item.GetText(),'position_mm':[pcbnew.ToMM(value) for value in item.GetPosition()],
            'same_side':item.GetLayer()==pcbnew.B_SilkS,'mirrored':item.IsMirrored(),'body_hits':body_hits,'pad_hits':pad_hits})
    plots={}
    for label,project in [('before',pipeline.PRIMARY),('after',work)]:
        output=EVIDENCE/('power-header-plot-verified-'+label)
        output.mkdir(exist_ok=False)
        command=[pipeline.find_cli(),'pcb','export','gerbers','--no-x2','--no-netlist','--layers','F.Cu,In1.Cu,In2.Cu,B.Cu,F.Mask,B.Mask,F.Paste,B.Paste,Edge.Cuts','--output',output,project/name]
        completed=subprocess.run(list(map(str,command)),capture_output=True,timeout=180)
        (EVIDENCE/('power-header-plot-'+label+'.log')).write_bytes(completed.stdout+completed.stderr)
        completed.check_returncode()
        plots[label]={item.name:dark_plot_signature(drawing_commands(item)) for item in output.iterdir() if item.suffix in {'.gtl','.gbl','.g1','.g2','.gts','.gbs','.gtp','.gbp','.gm1'}}
    same_drawings=plots['before']==plots['after'] and len(plots['before'])==9
    restored=pipeline.prepare(work)
    restored_path=restored/name
    reverse=pcbnew.LoadBoard(str(restored_path))
    reverse_footprint=reverse.FindFootprintByReference('J301')
    reverse_footprint.Flip(reverse_footprint.GetPosition(),True)
    pcbnew.SaveBoard(str(restored_path),reverse)
    restored_node=identified(parse(restored_path.read_text(encoding='utf-8')))[footprint_uuid]
    footprint_roundtrip=normalize_angles(restored_node)==normalize_angles(original_nodes[footprint_uuid])
    reports,summary=pipeline.check(work)
    result={'runs':{'before':{'pcb_sha256':pipeline.digest(before_path)},'after':{'pcb_sha256':pipeline.digest(after_path),'project':str(work)}},
        'changed_objects':changed,'only_declared_objects_changed':set(changed)==expected,'object_set_equal':original_nodes.keys()==candidate_nodes.keys(),
        'root_settings_unchanged':root_unchanged,'other_design_files_unchanged':other_files_before==other_files_after,
        'j301_side':board.GetLayerName(footprint.GetLayer()),'j301_flip_roundtrip_equal_modulo_360_degree_text_angles':footprint_roundtrip,'unexpected_pad_changes':pad_changes,
        'nets_equal':original['nets']==updated['nets'],'tracks_equal':original['tracks']==updated['tracks'],'connections_equal':original['connections']==updated['connections'],
        'nine_non_silk_gerbers_equal':same_drawings,'marker_checks':marker_checks,'summary':str(reports/'summary.json'),'native_status':summary['status'],
        'manufacturing_released':False,'hardware_tested':False}
    result['accepted']=all((result['only_declared_objects_changed'],result['object_set_equal'],root_unchanged,result['other_design_files_unchanged'],
        footprint.GetLayer()==pcbnew.B_Cu,footprint_roundtrip,not pad_changes,result['nets_equal'],result['tracks_equal'],result['connections_equal'],same_drawings,
        len(marker_checks)==3,all(row['same_side'] and row['mirrored'] and not row['body_hits'] and not row['pad_hits'] for row in marker_checks),
        summary['status']=='checks_clean_not_manufacturing_release'))
    pipeline.write_json(EVIDENCE/'geometry-connectivity-check.json',result)
    pipeline.write_json(EVIDENCE/'candidate.json',{'project':str(work),'summary':str(reports/'summary.json'),'promoted':False})
    print(json.dumps(result))
    if not result['accepted']:
        raise RuntimeError('Power-header change contract failed')


if __name__=='__main__':
    main()
