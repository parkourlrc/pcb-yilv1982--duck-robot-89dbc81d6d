"""Independently check marker coverage and limit all source changes to silkscreen."""
import copy
import json
from pathlib import Path
import subprocess

import pcbnew
import pipeline
from complete_polarity_markers import EVIDENCE, rectangle
from finalize_remaining_smt_candidate import identified
from generate_rev_a import parse, first
from verify_release_metadata import snapshot
from export_jlc_rs274x import drawing_commands


def main():
    candidate = json.loads((EVIDENCE/'candidate.json').read_text(encoding='utf-8'))
    work = pipeline.managed(Path(candidate['project']))
    name = pipeline.STEM+'.kicad_pcb'
    source, target = pipeline.PRIMARY/name, work/name
    before_root, after_root = parse(source.read_text(encoding='utf-8')), parse(target.read_text(encoding='utf-8'))
    old_nodes, new_nodes = identified(before_root), identified(after_root)
    changed = [identifier for identifier,node in old_nodes.items() if node!=new_nodes.get(identifier)]
    expected = copy.deepcopy(old_nodes['5f5103a9-38f9-4bb7-8e3f-9856e70ea2f2'])
    first(first(first(expected,'effects'),'font'),'size')[1:] = ['1.27','1.27']
    permitted_added = {mark['uuid'] for mark in candidate['marks'] if mark['reference']!='D301'}
    source_contract = {'changed_objects':changed,'only_K_resized':changed==['5f5103a9-38f9-4bb7-8e3f-9856e70ea2f2'] and new_nodes[changed[0]]==expected,
        'added_objects_match':new_nodes.keys()-old_nodes.keys()==permitted_added,'removed_objects':sorted(old_nodes.keys()-new_nodes.keys()),
        'added_only_silk':all(first(new_nodes[identifier],'layer')[1] in {'F.SilkS','B.SilkS'} for identifier in permitted_added),
        'root_settings_unchanged':[node for node in before_root[1:] if not isinstance(node,list) or not first(node,'uuid')]==[node for node in after_root[1:] if not isinstance(node,list) or not first(node,'uuid')]}
    before = snapshot(source)
    after = snapshot(target)
    same_electrical = all(before[key]==after[key] for key in ('pads','nets','tracks','connections'))
    board = pcbnew.LoadBoard(str(target))
    drawings = {item.m_Uuid.AsString():item for item in board.GetDrawings()}
    bodies=[]
    for footprint in board.GetFootprints():
        side=footprint.GetLayer()
        fab=pcbnew.F_Fab if side==pcbnew.F_Cu else pcbnew.B_Fab
        boxes=[item.GetBoundingBox() for item in footprint.GraphicalItems() if item.GetLayer()==fab and item.Type()==pcbnew.PCB_SHAPE_T]
        if boxes:
            bounds=[min(box.GetLeft() for box in boxes),min(box.GetTop() for box in boxes),max(box.GetRight() for box in boxes),max(box.GetBottom() for box in boxes)]
            bodies.append((footprint.GetReference(),side,rectangle([pcbnew.ToMM(value) for value in bounds])))
    mark_checks=[]
    for record in candidate['marks']:
        item=drawings[record['uuid']]
        side=pcbnew.F_Cu if item.GetLayer()==pcbnew.F_SilkS else pcbnew.B_Cu
        shape=item.GetEffectiveShape()
        body_conflicts=[reference for reference,body_side,body in bodies if side==body_side and body.Collide(shape,pcbnew.FromMM(.05))]
        pad_conflicts=[footprint.GetReference()+'.'+pad.GetNumber() for footprint in board.GetFootprints() for pad in footprint.Pads()
                       if pad.IsOnLayer(side) and pad.GetEffectiveShape(side).Collide(shape,pcbnew.FromMM(.3))]
        size_ok=abs(item.GetRadius()/1e6*2-record['diameter_mm'])<.00001 and item.IsSolidFill() if record['reference'].startswith('U') else (
            pcbnew.ToMM(item.GetTextSize().y)>=(1.27 if record['reference']=='D301' else 1) and pcbnew.ToMM(item.GetTextThickness())>=.15)
        mark_checks.append({'reference':record['reference'],'body_conflicts':body_conflicts,'pad_conflicts':pad_conflicts,'size_verified':size_ok,'same_side':board.FindFootprintByReference(record['reference']).GetLayer()==side})
    plots={}
    for label,project in [('before',pipeline.PRIMARY),('after',work)]:
        output=EVIDENCE/('plot-'+label)
        output.mkdir(exist_ok=False)
        command=[pipeline.find_cli(),'pcb','export','gerbers','--no-x2','--no-netlist','--layers','F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.Mask,B.Mask,Edge.Cuts','--output',output,project/name]
        result=subprocess.run(list(map(str,command)),capture_output=True,timeout=180)
        (EVIDENCE/('plot-'+label+'.log')).write_bytes(result.stdout+result.stderr)
        result.check_returncode()
        plots[label]={file.name:drawing_commands(file) for file in output.iterdir() if file.suffix in {'.gtl','.gbl','.g1','.g2','.gtp','.gbp','.gts','.gbs','.gm1'}}
    plot_equal=plots['before']==plots['after'] and len(plots['before'])==9
    reports,summary=pipeline.check(work)
    result={'runs':{'before':{'pcb_sha256':pipeline.digest(source)},'after':{'pcb_sha256':pipeline.digest(target)}},
        'source_contract':source_contract,'electrical_snapshot_unchanged':same_electrical,'nine_non_silk_gerbers_equal':plot_equal,
        'mark_checks':mark_checks,'mark_count':len(mark_checks),'summary':str(reports/'summary.json'),'native_status':summary['status'],'manufacturing_ready':False}
    result['accepted']=all((source_contract['only_K_resized'],source_contract['added_objects_match'],not source_contract['removed_objects'],
        source_contract['added_only_silk'],source_contract['root_settings_unchanged'],same_electrical,plot_equal,len(mark_checks)==18,
        all(not row['body_conflicts'] and not row['pad_conflicts'] and row['size_verified'] and row['same_side'] for row in mark_checks),
        summary['status']=='checks_clean_not_manufacturing_release'))
    pipeline.write_json(EVIDENCE/'geometry-connectivity-check.json',result)
    candidate['summary']=str(reports/'summary.json')
    pipeline.write_json(EVIDENCE/'candidate.json',candidate)
    print(json.dumps(result))
    if not result['accepted']:
        raise RuntimeError('Silkscreen-only change verification failed')


if __name__=='__main__':
    main()
