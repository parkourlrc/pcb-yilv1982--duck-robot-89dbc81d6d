"""Create a self-consistent panel review bundle including manual through-hole assembly data."""
import argparse
import csv
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import zipfile

import pcbnew
import pipeline


def read_rows(path):
    with path.open(encoding='utf-8-sig',newline='') as stream:
        reader=csv.DictReader(stream)
        return list(reader.fieldnames),list(reader)


def write_rows(path,fields,rows):
    with path.open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--panel-package',type=Path,required=True)
    parser.add_argument('--evidence',type=Path,required=True)
    parser.add_argument('--package-version',default=datetime.now().strftime('%Y%m%d'))
    args=parser.parse_args()
    if not re.fullmatch(r'\d{8}(?:-[a-z0-9-]{1,24})?',args.package_version):
        raise ValueError('Package version must be YYYYMMDD with an optional lowercase revision suffix')
    checkpoint=pipeline.current_checkpoint()
    root=pipeline.BASE.parents[1]
    source_package=root/checkpoint['review_binding']['production_package']
    panel_package=args.panel_package.resolve()
    evidence=args.evidence.resolve()
    panel_manifest=json.loads((panel_package/'manifest.json').read_text(encoding='utf-8'))
    if panel_manifest['source_pcb_sha256']!=checkpoint['pcb_sha256']:
        raise RuntimeError('Panel package has another source identity')
    for name,digest in panel_manifest['outputs'].items():
        if pipeline.digest(panel_package/name)!=digest:
            raise RuntimeError('Panel output changed: '+name)
    panel_board_path=panel_package.parent/'hat_a1_smt_2up.kicad_pcb'
    if pipeline.digest(panel_board_path)!=panel_manifest['panel_sha256']:
        raise RuntimeError('Panel source changed')
    board=pcbnew.LoadBoard(str(panel_board_path))
    plan_fields,plan=read_rows(source_package/'assembly-plan.csv')
    position_fields,positions=read_rows(source_package/'positions.csv')
    source_manifest=json.loads((source_package/'manifest.json').read_text(encoding='utf-8'))
    for name in ['assembly-plan.csv','positions.csv','assembly-front.svg','assembly-back.svg']:
        if pipeline.digest(source_package/name)!=source_manifest['outputs'][name]:
            raise RuntimeError('Single-unit assembly source changed')
    destination=pipeline.BASE/'release-review'/('HAT-A1-JLC-PCBA-'+checkpoint['pcb_sha256'][:12]+'-'+args.package_version)
    destination.mkdir(exist_ok=False)
    for name in panel_manifest['outputs']:
        shutil.copy2(panel_package/name,destination/name)
    tht_process=None
    tht_report=evidence/'tht-soldering-plan.json'
    if tht_report.is_file():
        tht_process=json.loads(tht_report.read_text(encoding='utf-8'))
        if tht_process['pcb_sha256']!=checkpoint['pcb_sha256'] or tht_process['panel_sha256']!=panel_manifest['panel_sha256']:
            raise RuntimeError('THT process does not match the panel identity')
        if pipeline.digest(evidence/'tht-soldering-plan.csv')!=tht_process['csv_sha256']:
            raise RuntimeError('THT process CSV changed')
        for name in ['tht-soldering-plan.csv','tht-soldering-plan.json','tht-process-notes.md',
                     'assembly-process-basis.md','manufacturing-spec.md','manufacturing-spec.json']:
            shutil.copy2(evidence/name,destination/name)
    depaneling=None
    depanel_report=evidence/'depanel-process-check.json'
    if depanel_report.is_file():
        depaneling=json.loads(depanel_report.read_text(encoding='utf-8'))
        if not tht_process or depaneling['pcb_sha256']!=checkpoint['pcb_sha256'] or depaneling['panel_sha256']!=panel_manifest['panel_sha256']:
            raise RuntimeError('Depanel sequence does not match the current panel and THT plan')
        if not depaneling['three_mm_local_cut_screen_pass'] or depaneling['tht_installed_during_depaneling'] or depaneling['hand_breaking_allowed']:
            raise RuntimeError('Unreviewed depanel process')
        for name in ['depanel-process-check.json','depanel-process-notes.md','ASSEMBLY-NOTES.txt']:
            shutil.copy2(evidence/name,destination/name)
    expanded_plan=[]
    expanded_positions=[]
    mapping=[]
    for unit,prefix,offset in [('A1','',0),('A2','B2_',32)]:
        for row in plan:
            assembly=row['Assembly']
            if tht_process and assembly.startswith('THT'):
                assembly='THT / 分板后手工逐点焊接' if depaneling else 'THT / 双面SMT后手工逐点焊接'
            expanded_plan.append({'Unit':unit,**row,'Reference':prefix+row['Reference'],'Assembly':assembly})
            mapping.append({'Unit':unit,'PanelReference':prefix+row['Reference'],'SilkscreenReference':row['Reference'],'OffsetX_mm':0,'OffsetY_mm':offset,'Assembly':assembly,'Side':row['Side']})
        for row in positions:
            reference=prefix+row['Ref']
            adjusted={**row,'Ref':reference,'PosY':format(float(row['PosY'])-offset,'.6f')}
            footprint=board.FindFootprintByReference(reference)
            if footprint is None or abs(float(adjusted['PosX'])-pcbnew.ToMM(footprint.GetPosition().x))>1e-6 or abs(float(adjusted['PosY'])+pcbnew.ToMM(footprint.GetPosition().y))>1e-6:
                raise RuntimeError('Panel placement mismatch: '+reference)
            expected_side='top' if footprint.GetLayer()==pcbnew.F_Cu else 'bottom'
            if adjusted['Side']!=expected_side or abs((float(adjusted['Rot'])-footprint.GetOrientationDegrees()+180)%360-180)>1e-6:
                raise RuntimeError('Panel side/angle mismatch: '+reference)
            expanded_positions.append(adjusted)
    tht={row['Reference'] for row in expanded_plan if row['Assembly'].startswith('THT')}
    smt={row['Reference'] for row in expanded_plan if row['Assembly'].startswith('SMT')}
    dnp={row['Reference'] for row in expanded_plan if row['Assembly'].startswith('DNP')}
    _,existing_smt=read_rows(destination/'panel-positions-smt.csv')
    smt_positions={row['Ref']:row for row in expanded_positions if row['Ref'] in smt}
    for row in existing_smt:
        expected=smt_positions[row['Ref']]
        if any(row[key]!=expected[key] for key in ['Ref','Val','Package','Side']) or any(abs(float(row[key])-float(expected[key]))>1e-6 for key in ['PosX','PosY','Rot']):
            raise RuntimeError('SMT coordinates differ from expanded native positions')
    if len(tht)!=12 or len(smt)!=104 or dnp!={'C307','B2_C307'} or len(expanded_positions)!=116:
        raise RuntimeError('Unexpected assembly inventory')
    if tht_process:
        _,process_rows=read_rows(destination/'tht-soldering-plan.csv')
        if len(process_rows)!=12 or {row['Reference'] for row in process_rows}!=tht:
            raise RuntimeError('THT process plan does not cover all twelve placements')
        for row in process_rows:
            footprint=board.FindFootprintByReference(row['Reference'])
            component_side='top' if footprint.GetLayer()==pcbnew.F_Cu else 'bottom'
            solder_side='bottom' if component_side=='top' else 'top'
            pins=sum(bool(pad.GetDrillSize().x) for pad in footprint.Pads())
            if row['ComponentSide']!=component_side or row['SolderSide']!=solder_side or int(row['PinCount'])!=pins:
                raise RuntimeError('THT process side or pin count mismatch: '+row['Reference'])
            if row['BoardWideWaveAllowed']!='False' or row['PinInPasteReflowAllowed']!='False':
                raise RuntimeError('Unapproved THT soldering process: '+row['Reference'])
    write_rows(destination/'panel-assembly-plan.csv',['Unit',*plan_fields],expanded_plan)
    write_rows(destination/'panel-positions-all-fitted.csv',position_fields,expanded_positions)
    write_rows(destination/'panel-positions-tht.csv',position_fields,[row for row in expanded_positions if row['Ref'] in tht])
    write_rows(destination/'unit-reference-map.csv',list(mapping[0]),mapping)
    for side in ['front','back']:
        shutil.copy2(source_package/('assembly-'+side+'.svg'),destination/('unit-assembly-'+side+'.svg'))
    shutil.copy2(evidence/'panel-handoff-readme.md',destination/'README.md')
    files={path.name:pipeline.digest(path) for path in destination.iterdir() if path.is_file()}
    record={'created_at_utc':datetime.now(timezone.utc).isoformat(),'pcb_sha256':checkpoint['pcb_sha256'],
        'panel_sha256':panel_manifest['panel_sha256'],'derived_from_panel_manifest_sha256':pipeline.digest(panel_package/'manifest.json'),
        'files':files,'counts':{'smt':104,'tht':12,'fitted':116,'dnp':2,'pofv':12},
        'unit_views':'Native source-unit views; back mirrored; second unit same orientation offsetY32mm, refs mapped withB2_',
        'positions':'Native mm CAM coordinates, Y negative; never mirror the bottom CSV again',
        'tht_process_addendum':{'included':tht_process is not None,'source_report_sha256':pipeline.digest(tht_report) if tht_process else None,
            'overrides':['assembly-process-basis.md','manufacturing-spec.md','manufacturing-spec.json'] if tht_process else []},
        'depanel_process_addendum':{'included':depaneling is not None,'source_report_sha256':pipeline.digest(depanel_report) if depaneling else None,
            'tht_assembly_and_reference_map_process_labels_updated':depaneling is not None},
        'manufacturing_released':False,'uploaded':False,'order_created':False}
    pipeline.write_json(destination/'MANIFEST.json',record)
    archive=destination.with_suffix('.zip')
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED) as bundle:
        for path in sorted(destination.iterdir()):
            if path.is_file():
                bundle.write(path,path.name)
    with zipfile.ZipFile(archive) as bundle:
        if bundle.testzip() or set(bundle.namelist())!=set(files)|{'MANIFEST.json'}:
            raise RuntimeError('Package archive integrity failed')
        if any(hashlib.sha256(bundle.read(name)).hexdigest()!=digest for name,digest in files.items()):
            raise RuntimeError('Archive member mismatch')
    result={'archive':str(archive.relative_to(root)),'sha256':pipeline.digest(archive),'pcb_sha256':checkpoint['pcb_sha256'],
        'panel_sha256':panel_manifest['panel_sha256'],'smt':104,'tht':12,'all_placement_sides_and_angles_match_native':True,
        'mapping_includes_tht_and_dnp':True,'manufacturing_released':False,'uploaded':False}
    pipeline.write_json(evidence/'pcba-review-bundle.json',result)
    print(json.dumps(result))


if __name__=='__main__':
    main()
