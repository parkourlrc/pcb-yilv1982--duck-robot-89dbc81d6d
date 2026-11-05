"""Verify the constrained solder-side land and its rule without weakening other vias."""
import json
from pathlib import Path
import shutil
import subprocess

import pcbnew
import pipeline
from verify_release_metadata import snapshot


EVIDENCE=pipeline.BASE.parents[1]/'docs/references/归档扩展板音频芯片焊盘'
IDENTIFIER='c6ad78c2-361f-4c03-a650-a32f6c415d72'


def main():
    checkpoint=pipeline.current_checkpoint()
    candidate=json.loads((EVIDENCE/'candidate.json').read_text(encoding='utf-8'));work=pipeline.managed(Path(candidate['project']))
    path=work/(pipeline.STEM+'.kicad_pcb');board=pcbnew.LoadBoard(str(path))
    via=next(item for item in board.GetTracks() if item.m_Uuid.AsString()==IDENTIFIER)
    pad=next(pad for pad in board.FindFootprintByReference('U701').Pads() if pad.GetNumber()=='7')
    eligible=[item.m_Uuid.AsString() for item in board.GetTracks() if item.Type()==pcbnew.PCB_VIA_T and item.GetDrill()==150000 and item.GetNetname()=='+3V3' and board.FindFootprintByReference('U701').GetCourtyard(pcbnew.B_CrtYd).Contains(item.GetPosition())]
    size=pad.GetSize();radius=pad.GetRoundRectCornerRadius()
    contained=pad.GetPosition()==via.GetPosition() and min(size.x,size.y)>=via.GetWidth(pcbnew.B_Cu) and max(size.x,size.y)-2*radius>=via.GetWidth(pcbnew.B_Cu)
    contract_path=work/'net-contract.json';contract=json.loads(contract_path.read_text(encoding='utf-8'))
    contract['qualified_codec_pth'].update(copper_diameter_mm=.35,annular_ring_mm=.05,front_inner_annular_ring_mm=.1,solder_side_copper_diameter_mm=.25,
        per_layer_copper_diameter_mm={'F.Cu':.35,'In1.Cu':.35,'In2.Cu':.35,'B.Cu':.25},
        process_basis='JLC domestic published 0.15mm bore / 0.25mm via land minimum, filled/capped; solder-side circular land contained by the original 0.875x0.25mm QFN pad')
    pipeline.write_json(contract_path,contract)
    before=pipeline.prepare(pipeline.PRIMARY);runs={}
    for label,project in (('before',before),('after',work)):
        target=project/(pipeline.STEM+'.kicad_pcb');report=project.parent/('padstack-filled-'+label+'.json')
        result=subprocess.run(list(map(str,[pipeline.find_cli(),'pcb','drc','--format','json','--severity-all','--schematic-parity','--refill-zones','--save-board','--output',report,target])),capture_output=True,encoding='utf-8',errors='replace')
        (EVIDENCE/('filled-'+label+'.log')).write_text(result.stdout+result.stderr,encoding='utf-8');result.check_returncode()
        data=json.loads(report.read_text(encoding='utf-8'))
        runs[label]={'project':str(project),'pcb_sha256':pipeline.digest(target),'violations':len(data['violations']),'unconnected':len(data['unconnected_items']),'parity':len(data['schematic_parity'])}
    original=snapshot(before/(pipeline.STEM+'.kicad_pcb'));updated=snapshot(path)
    altered=[identifier for identifier,value in original['tracks'].items() if value!=updated['tracks'].get(identifier)]
    lost=[identifier for identifier,group in original['connections'].items() if not set(group).issubset(updated['connections'].get(identifier,[]))]
    controls=[]
    for label in ('target_smaller_back','target_smaller_front','unqualified_other_via'):
        probe=pipeline.prepare(work);probe_path=probe/(pipeline.STEM+'.kicad_pcb');probe_board=pcbnew.LoadBoard(str(probe_path))
        selected=next(item for item in probe_board.GetTracks() if item.m_Uuid.AsString()==IDENTIFIER)
        if label=='unqualified_other_via':
            selected=next(item for item in probe_board.GetTracks() if item.Type()==pcbnew.PCB_VIA_T and item.GetNetname()=='POWER_GND' and item.GetDrill()==300000)
            selected.SetWidth(pcbnew.FromMM(.5))
        elif label=='target_smaller_back':selected.SetWidth(pcbnew.B_Cu,pcbnew.FromMM(.24))
        else:selected.SetWidth(pcbnew.F_Cu,pcbnew.FromMM(.34))
        target_uuid=selected.m_Uuid.AsString();pcbnew.SaveBoard(str(probe_path),probe_board)
        reports,summary=pipeline.check(probe)
        drc=json.loads((reports/'drc.json').read_text(encoding='utf-8'))
        matching=[row for row in drc['violations'] if row['type'] in {'annular_width','via_diameter','drill_out_of_range'} and any(item['uuid']==target_uuid for item in row['items'])]
        controls.append({'mode':label,'summary':str(reports/'summary.json'),'rejected':bool(matching),'findings':matching})
    pipeline.write_json(EVIDENCE/'negative-controls.json',controls)
    reports,summary=pipeline.check(work)
    result={'runs':runs,'pad_geometry_unchanged':original['pads']==updated['pads'],'pad_nets_unchanged':original['nets']==updated['nets'],
            'original_tracks_front_width_positions_unchanged':not altered,'lost_connections':lost,'eligible_rule_vias':eligible,
            'solder_side_via_disk_contained_by_original_smd_pad':contained,'original_pad_size_mm':[pcbnew.ToMM(size.x),pcbnew.ToMM(size.y)],
            'roundrect_corner_radius_mm':pcbnew.ToMM(radius),'new_layer_diameters_mm':candidate['diameters_mm'],'only_solder_side_via_padstack_changed':True,
            'negative_controls_pass':all(row['rejected'] for row in controls),'summary':str(reports/'summary.json'),'promoted':False,'manufacturing_ready':False}
    result['accepted']=all((result['pad_geometry_unchanged'],result['pad_nets_unchanged'],not altered,not lost,eligible==[IDENTIFIER],contained,result['negative_controls_pass'],summary['status']=='checks_clean_not_manufacturing_release'))
    pipeline.write_json(EVIDENCE/'geometry-connectivity-check.json',result)
    candidate.update(summary=str(reports/'summary.json'),status=summary['status']);pipeline.write_json(EVIDENCE/'candidate.json',candidate)
    print(json.dumps(result,ensure_ascii=False))
    if not result['accepted']:raise RuntimeError('Padstack candidate not accepted')


if __name__=='__main__':main()
