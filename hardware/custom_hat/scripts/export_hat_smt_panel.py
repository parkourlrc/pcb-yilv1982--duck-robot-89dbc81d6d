"""Export an explicitly unapproved SMT panel with DNP paste preservation."""
from collections import Counter
import argparse
import csv
import json
import math
from pathlib import Path
import shutil
import subprocess

import pcbnew
import pipeline
from export_dnp_stencil import LAYERS, paste_flashes
from export_jlc_rs274x import drawing_commands


EVIDENCE = pipeline.BASE.parents[1] / "docs/references/归档扩展板贴片规范复查"


def execute(command, logfile):
    result = subprocess.run(list(map(str, command)),capture_output=True,encoding="utf-8",errors="replace",timeout=180)
    logfile.write_text(result.stdout+result.stderr,encoding="utf-8")
    if result.returncode:
        raise RuntimeError("Export failed: "+str(logfile))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suffix',default='')
    arguments=parser.parse_args()
    checkpoint=pipeline.current_checkpoint()
    contract=json.loads((EVIDENCE/'panel-candidate.json').read_text(encoding='utf-8'))
    verification=json.loads((EVIDENCE/'panel-verification.json').read_text(encoding='utf-8'))
    if any(record.get('source_pcb_sha256')!=checkpoint['pcb_sha256'] for record in (contract,verification)):
        raise RuntimeError('Panel and verification do not match the current source identity')
    path=Path(contract['panel'])
    if not verification['replication_and_panel_drc_pass'] or pipeline.digest(path)!=verification['panel_sha256']:
        raise RuntimeError('Panel verification does not match source')
    if not verification.get('both_units_netclasses_and_original_project_settings_preserved') or not verification.get('edge_copper_reference_check_pass'):
        raise RuntimeError('Both-unit rule inheritance and edge/reference audit must pass')
    if pipeline.digest(path.with_suffix('.kicad_pro'))!=verification.get('panel_project_sha256') or pipeline.digest(path.with_suffix('.kicad_dru'))!=verification.get('panel_rules_sha256'):
        raise RuntimeError('Panel project or custom rules changed after verification')
    if pipeline.digest(path.parent/'edge-copper-reference-check.json')!=verification.get('edge_audit_sha256'):
        raise RuntimeError('Edge audit changed after verification')
    output=path.parent/('fabrication-candidate'+arguments.suffix)
    output.mkdir(exist_ok=False)
    reference=path.parent/('reference-unfiltered-paste'+arguments.suffix)
    reference.mkdir(exist_ok=False)
    cli=pipeline.find_cli()
    execute([cli,'pcb','export','gerbers','--no-x2','--no-netlist','--layers',LAYERS,'--output',reference,path],EVIDENCE/'panel-raw-export.log')
    plot_directory=path.parent/('plot-copy'+arguments.suffix)
    plot_directory.mkdir(exist_ok=False)
    for source in path.parent.iterdir():
        if source.is_file() and source.suffix in {'.kicad_pcb','.kicad_pro','.kicad_dru'}:
            shutil.copy2(source,plot_directory/source.name)
    board=pcbnew.LoadBoard(str(plot_directory/path.name))
    removed=[]
    bmi_pad_positions=[]
    dnp_positions=[]
    for footprint in board.GetFootprints():
        if footprint.GetReference() in {'U501','B2_U501'}:
            for pad in footprint.Pads():
                if pad.GetNumber() and pad.IsOnLayer(pcbnew.F_Paste):
                    pad.SetLocalSolderPasteMarginRatio(-.05)
                    position=pad.GetPosition()
                    bmi_pad_positions.append((position.x,-position.y))
        if footprint.GetReference() not in {'C307','B2_C307'}:
            continue
        for pad in footprint.Pads():
            layers=pad.GetLayerSet()
            for layer in (pcbnew.F_Paste,pcbnew.B_Paste):
                if layers.Contains(layer):
                    layers.RemoveLayer(layer)
                    removed.append([footprint.GetReference(),pad.GetNumber(),board.GetLayerName(layer)])
                    position=pad.GetPosition()
                    dnp_positions.append((position.x,-position.y))
            pad.SetLayerSet(layers)
    if len(removed)!=4:
        raise RuntimeError('Expected four DNP paste pads')
    pcbnew.SaveBoard(str(plot_directory/path.name),board)
    execute([cli,'pcb','export','gerbers','--no-x2','--no-netlist','--layers',LAYERS,'--output',output,plot_directory/path.name],EVIDENCE/'panel-dnp-export.log')
    nonpaste=[file for file in output.iterdir() if file.suffix in {'.gtl','.gbl','.g1','.g2','.gts','.gbs','.gto','.gbo','.gm1'}]
    if len(nonpaste)!=9 or any(drawing_commands(file)!=drawing_commands(reference/file.name) for file in nonpaste):
        raise RuntimeError('DNP plotting changed non-paste geometry')
    original_paste,_=paste_flashes(reference/(path.stem+'-F_Paste.gtp'))
    final_paste,_=paste_flashes(output/(path.stem+'-F_Paste.gtp'))
    def area(definition):
        if not definition.startswith('RoundRect,'):
            raise RuntimeError('Unreviewed BMI088 aperture shape')
        values=[float(value) for value in definition.split(',')[1].split('X')]
        radius=values[0]
        width=max(values[1:9:2])-min(values[1:9:2])+2*radius
        height=max(values[2:9:2])-min(values[2:9:2])+2*radius
        return width*height-(4-math.pi)*radius*radius
    bmi_checks=[]
    for xpos,ypos in bmi_pad_positions:
        old=next(key for key in original_paste if key[1:3]==(xpos,ypos))
        new=next(key for key in final_paste if key[1:3]==(xpos,ypos))
        ratio=area(new[3])/area(old[3])
        bmi_checks.append({'x_mm':xpos/1e6,'cam_y_mm':ypos/1e6,'paste_to_original_pad_area_ratio':ratio,'accepted':.7<=ratio<=.9})
    if len(bmi_checks)!=32 or not all(row['accepted'] for row in bmi_checks):
        raise RuntimeError('BMI088 stencil area does not meet manufacturer guidance')
    ignored=set(bmi_pad_positions)|set(dnp_positions)
    unchanged_before=Counter({key:count for key,count in original_paste.items() if key[1:3] not in ignored})
    unchanged_after=Counter({key:count for key,count in final_paste.items() if key[1:3] not in ignored})
    bottom_before,bottom_macros_before=paste_flashes(reference/(path.stem+'-B_Paste.gbp'))
    bottom_after,bottom_macros_after=paste_flashes(output/(path.stem+'-B_Paste.gbp'))
    if unchanged_before!=unchanged_after or any(key[1:3] in set(dnp_positions) for key in final_paste) or bottom_before!=bottom_after or bottom_macros_before!=bottom_macros_after:
        raise RuntimeError('Unintended paste geometry change')
    execute([cli,'pcb','export','drill','--output',output,'--format','excellon','--excellon-separate-th',path],EVIDENCE/'panel-drill-export.log')
    source_package=pipeline.BASE.parents[1]/checkpoint['review_binding']['production_package']
    for name in ('bom-fitted.csv','bom-smt.csv','bom-tracking.csv'):
        with (source_package/name).open(encoding='utf-8-sig',newline='') as stream:
            reader=csv.DictReader(stream);columns=reader.fieldnames;rows=list(reader)
        with (output/name).open('w',encoding='utf-8-sig',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=columns);writer.writeheader()
            for row in rows:
                writer.writerow({**row,'Reference':row['Reference']+','+','.join('B2_'+reference for reference in row['Reference'].split(',')), 'Qty':str(int(row['Qty'])*2)})
    for name in ('panel-positions-smt.csv','unit-reference-map.csv','ASSEMBLY-NOTES.txt'):
        shutil.copy2(path.parent/name,output/name)
    review_folder=(pipeline.BASE.parents[1]/checkpoint['review_binding']['checkpoint']).parent
    for name in ('material-process-matrix.csv','assembly-process-basis.md','manufacturing-spec.md','manufacturing-spec.json'):
        if (review_folder/name).is_file():
            shutil.copy2(review_folder/name,output/name)
    with (source_package/'via-process-requirements.csv').open(encoding='utf-8-sig',newline='') as stream:
        reader=csv.DictReader(stream);columns=reader.fieldnames;rows=list(reader)
    track_map={row['source']:row['panel'] for row in contract['maps']['tracks']}
    with (output/'via-process-requirements.csv').open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=['Unit',*columns]);writer.writeheader()
        writer.writerows({'Unit':'A1',**row} for row in rows)
        writer.writerows({'Unit':'A2',**row,'UUID':track_map[row['UUID']],'Net':'B2/'+row['Net'],'Y_mm':float(row['Y_mm'])+32,'CAM_Y_nominal_mm':float(row['CAM_Y_nominal_mm'])-32} for row in rows)
    for job in output.glob('*.gbrjob'):
        job.rename(path.parent/(job.name+arguments.suffix+'.not-for-order'))
    if pipeline.digest(path)!=verification['panel_sha256'] or pipeline.fingerprints(pipeline.PRIMARY)!=checkpoint['design_hashes']:
        raise RuntimeError('Panel or primary changed')
    record={'panel_sha256':verification['panel_sha256'],'source_pcb_sha256':checkpoint['pcb_sha256'],'outputs':{file.name:pipeline.digest(file) for file in output.iterdir() if file.is_file()},
            'dnp_paste_removed':removed,'non_paste_geometry_unchanged':True,'smt_count':104,'tht_count':12,'fitted_count':116,'pofv_count':12,
            'bmi088_stencil_area':bmi_checks,
            'non_bmi_fitted_paste_unchanged':True,'bottom_paste_unchanged':True,
            'manufacturing_released':False,'panel_candidate':True,'unresolved_source_findings_retained':True}
    pipeline.write_json(output/'manifest.json',record)
    pipeline.write_json(EVIDENCE/'panel-export.json',record)
    print(json.dumps({key:value for key,value in record.items() if key!='outputs'},ensure_ascii=False))


if __name__=='__main__':
    main()
