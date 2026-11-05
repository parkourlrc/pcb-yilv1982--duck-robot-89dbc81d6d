"""Freeze reviewable manufacturing choices separately from any order or factory acceptance."""
import argparse
import csv
from datetime import datetime
import json
from pathlib import Path

import pipeline


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence',required=True,type=Path)
    parser.add_argument('--panel-contract',type=Path)
    arguments=parser.parse_args()
    checkpoint=pipeline.current_checkpoint()
    root=pipeline.BASE.parents[1]
    package=root/checkpoint['review_binding']['production_package']
    with (package/'via-process-requirements.csv').open(encoding='utf-8-sig',newline='') as stream:
        vias=list(csv.DictReader(stream))
    if len(vias)!=6 or sorted(float(row['Drill_mm']) for row in vias)!=[.15,.3,.3,.3,.3,.3]:
        raise RuntimeError('POFV list does not match intended design')
    sources=root/'docs/references/归档扩展板嘉立创规则自查/sources'
    capabilities=(sources/'pcb-capabilities.txt').read_text(encoding='utf-8')
    if not all(token in capabilities for token in ['沉金','绿色','0.15-0.55mm','盖帽铜厚≧10um']):
        raise RuntimeError('Manufacturing choices lack the expected archived official text')
    stackup=json.loads((root/'docs/references/归档扩展板贴片与层叠复核/stackup-design-basis.json').read_text(encoding='utf-8'))
    result={'date':datetime.now().strftime('%Y-%m-%d'),'pcb_sha256':checkpoint['pcb_sha256'],
        'status':'design_manufacturing_choices_only_no_order_or_factory_acceptance',
        'single_board_mm':[65,30],'panel_mm':[85,82],'units_per_panel':2,'copper_layers':4,'substrate':'FR-4',
        'nominal_board_mm':1.6,'requested_stackup':stackup['structure'],
        'published_stackup_copper_um':stackup['copper_um'],'published_stackup_dielectrics_mm':stackup['dielectrics_mm'],
        'published_finished_thickness_mm':1.57,'published_finished_tolerance_percent':10,'dk':None,'df':None,
        'finish_design_choice':'ENIG / 沉金','soldermask_design_choice':'green / 绿色','legend_design_choice':'white / 白色',
        'surface_choice_basis':'Published JLC options; project choice for planar fine-pitch assembly, not a measured finish quality or guaranteed process result',
        'via_process':'resin fill plus copper cap / 树脂塞孔+电镀盖帽',
        'required_pofv_count_per_unit':6,'required_via_uuids':[row['UUID'] for row in vias],
        'cap_copper_published_min_um':10,'other_vias':'Follow supplied mask layers; any batch-wide filling expansion needs manufacturing review',
        'outline':'milled slots plus mouse-bite tabs; no V-score','castellated_holes':False,'blind_or_buried_vias':False,
        'plated_round_holes_per_unit':159,'nonplated_round_holes_per_unit':4,
        'smt_service':'standard dual-side','stencil_nominal_mm':.125,'stencil_area_ratio_screen':.66,
        'stencil_upper_thickness_for_current_minimum_aperture_mm':.12942059614205548,
        'stencil_surface':'rounded laser-cut aperture design; actual wall process and thickness to be accepted by fabrication',
        'paste_design_basis':'lead-free no-clean; Type3 or finer printing class per cited leaded-package guidance, actual alloy/flux not selected',
        'assembly_sequence':['B-side SMT first','F-side SMT second','Supported tab cutting and burr inspection before THT installation','All six THT parts manually point-soldered after depaneling'],
        'depaneling_process_design_choice':'Support the populated board and cut the tabs; do not hand-break; THT connectors are not installed at this stage',
        'tht_process_design_choice':'Local manual point soldering; no board-wide wave soldering and no pin-in-paste reflow',
        'tht_process_limits':'Tip access, temperature/time, support fixtures and joint inspection require actual process acceptance',
        'tht_sides':{'J301':'bottom','J101':'top','J401':'top','J402':'top','J403':'top','J802':'top'},
        'fitted_components_per_unit':58,'smt_per_unit':52,'tht_per_unit':6,'dnp':['C307'],
        'functional_validation':'not performed; no new board exists',
        'remaining_process_acceptance':['Specific SH reflow window or JST-required application evaluation',
            'Actual paste/alloy/flux, stencil tolerance and SPI transfer','Second-side component retention and actual thermal profile',
            'Actual laminate/material and order selections including fee-bearing0.15mm drill/POFV',
            'Incoming parts/packing/MSL records; no substitution by footprint alone',
            'Cable bends/chassis/accessories and actual board spacing','First-article electrical and functional acceptance after fabrication'],
        'official_sources':[{'path':str((sources/name).relative_to(root)),'sha256':pipeline.digest(sources/name)} for name in ['pcb-capabilities.txt','smt-capabilities.txt','via-process.txt']],
        'order_created':False,'uploaded':False,'paid':False,'manufacturing_released':False}
    if arguments.panel_contract:
        panel=json.loads(arguments.panel_contract.read_text(encoding='utf-8'))
        panel_path=Path(panel['panel'])
        if panel['source_pcb_sha256']!=checkpoint['pcb_sha256'] or not panel['mouse_bites_centered_on_unit_outline']:
            raise RuntimeError('Requested manufacturing panel is stale or uses retired edge placement')
        result['panel_geometry']={'name':panel_path.parent.name,'pcb_sha256':pipeline.digest(panel_path),
            'project_sha256':pipeline.digest(panel_path.with_suffix('.kicad_pro')),
            'mouse_bite_centers_mm':panel['mouse_bite_holes_mm'],
            'mouse_bite_diameter_mm':panel['mouse_bite_diameter_mm'],
            'tab_copper_exclusions_mm':panel['tab_copper_exclusions_mm'],
            'trim_scope':'Only filled zones at perforation edge neighborhoods; original tracks and pad coordinates unchanged',
            'depaneling':'Nominal edge is perforation centerline; finish the tabs with support and inspect burrs; no hand-bending assumption'}
    pipeline.write_json(arguments.evidence.resolve()/'manufacturing-spec.json',result)
    print(json.dumps({'pcb_sha256':checkpoint['pcb_sha256'],'finish':result['finish_design_choice'],'mask':result['soldermask_design_choice'],'via_process':result['via_process'],'required_pofv':len(vias),'order_created':False}))


if __name__=='__main__':
    main()
