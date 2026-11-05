"""Qualify the final RESET capacitor position, including the missed via-overlap guard."""
import copy
import csv
import json
import math
from pathlib import Path
import subprocess
import sys

import pcbnew
import pipeline
from generate_rev_a import parse, first
from finalize_remaining_smt_candidate import identified
from search_remaining_thermal_pads import covered
from verify_release_metadata import snapshot


EVIDENCE = pipeline.BASE.parents[1] / 'docs/references/归档扩展板贴片与层叠复核'


def main():
    folder = EVIDENCE / 'final'
    folder.mkdir(exist_ok=False)
    checkpoint = pipeline.current_checkpoint()
    search = json.loads((EVIDENCE / 'c310-clearance-search-south.json').read_text(encoding='utf-8'))
    selected = next(row for row in search['candidates'] if row['accepted'])
    work = pipeline.managed(Path(selected['project']))
    path = work / (pipeline.STEM + '.kicad_pcb')
    source_path = pipeline.PRIMARY / path.name
    original_root = parse(source_path.read_text(encoding='utf-8'))
    updated_root = parse(path.read_text(encoding='utf-8'))
    original_nodes, updated_nodes = identified(original_root), identified(updated_root)
    expected = copy.deepcopy(original_nodes)
    first(expected['5e2f1b0e-b11f-49a0-a0fd-0f2e54d3f411'], 'at')[1:3] = ['147.6', '114.4']
    track_ids = {'83669e25-22e2-4b64-9124-63e7934ed8a2', 'b094fe1c-af98-4390-acfb-715dd2e88014'}
    for identifier in track_ids:
        first(expected[identifier], 'end')[1:3] = ['147.12', '114.4']
    def normalized(node):
        return [part for part in node if not isinstance(part, list) or part[0] != 'filled_polygon'] if node[0] == 'zone' else node
    mismatches = [identifier for identifier, node in expected.items() if normalized(node) != normalized(updated_nodes.get(identifier, ['missing']))]
    root_equal = [node for node in original_root[1:] if not isinstance(node,list) or not first(node,'uuid')] == [node for node in updated_root[1:] if not isinstance(node,list) or not first(node,'uuid')]
    old_snapshot, new_snapshot = snapshot(source_path), snapshot(path)
    old_board, new_board = pcbnew.LoadBoard(str(source_path)), pcbnew.LoadBoard(str(path))
    changed_pads = {identifier for identifier, pad in old_snapshot['pads'].items() if pad != new_snapshot['pads'].get(identifier)}
    expected_pads = {identifier for identifier, pad in old_snapshot['pads'].items() if pad['reference'] == 'C310'}
    changed_tracks = {identifier for identifier, track in old_snapshot['tracks'].items() if track != new_snapshot['tracks'].get(identifier)}
    lost = [identifier for identifier, group in old_snapshot['connections'].items() if not set(group).issubset(new_snapshot['connections'].get(identifier, []))]
    actual_loss = []
    sample_count = 0
    with (EVIDENCE / 'relocate-after-plane-samples.csv').open(encoding='utf-8', newline='') as stream:
        for row in csv.DictReader(stream):
            sample_count += 1
            point = pcbnew.VECTOR2I(pcbnew.FromMM(float(row['x_mm'])),pcbnew.FromMM(float(row['y_mm'])))
            for layer_name, net in [('F.Cu','POWER_GND'),('In1.Cu','POWER_GND'),('In2.Cu','+3V3'),('B.Cu','POWER_GND')]:
                if layer_name == row['source_layer']:
                    continue
                layer = new_board.GetLayerID(layer_name)
                if covered(old_board,point,layer,net) and not covered(new_board,point,layer,net):
                    actual_loss.append({'net':row['net'],'plane':layer_name,'point_mm':[row['x_mm'],row['y_mm']]})
    via_clearances = []
    for pad in new_board.FindFootprintByReference('C310').Pads():
        box = pad.GetBoundingBox()
        for via in new_board.GetTracks():
            if via.Type() != pcbnew.PCB_VIA_T:
                continue
            position = via.GetPosition()
            dx = max(box.GetLeft()-position.x,position.x-box.GetRight(),0)
            dy = max(box.GetTop()-position.y,position.y-box.GetBottom(),0)
            distance = math.hypot(dx,dy)
            via_clearances.append({'pad':pad.GetNumber(),'via':via.m_Uuid.AsString(),
                'copper_gap_lower_bound_mm':(distance-via.GetWidth(pcbnew.B_Cu)/2)/1e6,
                'hole_gap_lower_bound_mm':(distance-via.GetDrill()/2)/1e6})
    minimum = min(via_clearances,key=lambda row:row['copper_gap_lower_bound_mm'])
    reports, summary = pipeline.check(work)
    happy_script = Path.home() / 'AppData/Local/Temp/kicad-happy-review-20261030-new/skills/kicad/scripts/analyze_pcb.py'
    process = subprocess.run([sys.executable,'-X','utf8',str(happy_script),str(path),'--full','--output',str(folder/'candidate-pcb.json')],capture_output=True,timeout=600)
    (folder/'candidate-happy.log').write_bytes(process.stdout+process.stderr)
    process.check_returncode()
    findings = json.loads((folder/'candidate-pcb.json').read_text(encoding='utf-8'))['findings']
    via_findings = [row for row in findings if row.get('rule_id') == 'VP-001' and 'C310' in row.get('components',[])]
    result = {'runs':{'before':{'pcb_sha256':pipeline.digest(source_path)},'after':{'pcb_sha256':pipeline.digest(path),'project':str(work)}},
        'source_objects_preserved':original_nodes.keys()==updated_nodes.keys(),'unexpected_changes':mismatches,'root_settings_unchanged':root_equal,
        'changed_pad_ids':sorted(changed_pads),'only_c310_pads_moved':changed_pads==expected_pads,
        'only_reset_endpoints_changed':changed_tracks==track_ids,'all_pad_nets_preserved':old_snapshot['nets']==new_snapshot['nets'],
        'lost_connections':lost,'sample_rows':sample_count,'actual_reference_copper_loss':actual_loss,'minimum_via_clearance':minimum,
        'c310_via_findings':via_findings,'native_status':summary['status'],'summary':str(reports/'summary.json'),
        'source_unchanged':pipeline.fingerprints(pipeline.PRIMARY)==checkpoint['design_hashes'],'manufacturing_released':False}
    result['accepted'] = all((not mismatches,root_equal,result['source_objects_preserved'],result['only_c310_pads_moved'],
        result['only_reset_endpoints_changed'],result['all_pad_nets_preserved'],not lost,not actual_loss,not via_findings,
        minimum['copper_gap_lower_bound_mm']>=.15,summary['status']=='checks_clean_not_manufacturing_release',result['source_unchanged']))
    pipeline.write_json(folder/'geometry-connectivity-check.json',result)
    pipeline.write_json(folder/'candidate.json',{'project':str(work),'summary':str(reports/'summary.json'),'promoted':False})
    print(json.dumps(result))
    if not result['accepted']:
        raise RuntimeError('Final RESET capacitor candidate failed')


if __name__ == '__main__':
    main()
