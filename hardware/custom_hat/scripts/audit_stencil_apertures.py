"""Measure actual Gerber apertures against explicitly scoped release-ratio guidance."""
import argparse
from collections import Counter
import csv
import json
import math
from pathlib import Path

import pipeline
from export_dnp_stencil import paste_flashes


def aperture_geometry(definition):
    if definition.startswith('R,'):
        width,height=map(float,definition[2:].split('X'))
        radius=0
    elif definition.startswith('C,'):
        diameter=float(definition[2:])
        return {'width_mm':diameter,'height_mm':diameter,'radius_mm':diameter/2,
            'area_mm2':math.pi*diameter*diameter/4,'perimeter_mm':math.pi*diameter}
    elif definition.startswith('RoundRect,'):
        values=list(map(float,definition.split(',')[1].split('X')))
        if len(values)!=10 or values[-1]!=0:
            raise RuntimeError('Unsupported rounded rectangle transform')
        radius=values[0]
        width=max(values[1:9:2])-min(values[1:9:2])+2*radius
        height=max(values[2:9:2])-min(values[2:9:2])+2*radius
    else:
        raise RuntimeError('Unsupported aperture: '+definition)
    return {'width_mm':width,'height_mm':height,'radius_mm':radius,
            'area_mm2':width*height-(4-math.pi)*radius*radius,
            'perimeter_mm':2*(width+height)+(2*math.pi-8)*radius}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--evidence',required=True,type=Path)
    arguments=parser.parse_args()
    checkpoint=pipeline.current_checkpoint()
    output=arguments.output.resolve()
    evidence=arguments.evidence.resolve()
    evidence.mkdir(exist_ok=True)
    manifest=json.loads((output/'manifest.json').read_text(encoding='utf-8'))
    source=manifest.get('source_pcb_sha256') or manifest.get('design_hashes',{}).get(pipeline.STEM+'.kicad_pcb')
    if source!=checkpoint['pcb_sha256']:
        raise RuntimeError('Stencil directory belongs to another PCB')
    files=list(output.glob('*.gtp'))+list(output.glob('*.gbp'))
    if len(files)!=2:
        raise RuntimeError('Expected front and back paste files')
    rows=[]
    minimum_rows=[]
    for file in files:
        if pipeline.digest(file)!=manifest['outputs'][file.name]:
            raise RuntimeError('Paste file changed after export')
        flashes,macros=paste_flashes(file)
        if any(not macro.startswith('%AMRoundRect*') for macro in macros):
            raise RuntimeError('Unreviewed aperture macro')
        for key,count in flashes.items():
            reference,xpos,ypos,definition=key
            geometry=aperture_geometry(definition)
            rows.append({'file':file.name,'reference':reference or '', 'x_mm':xpos/1e6,'cam_y_mm':ypos/1e6,'count':count,**geometry,
                'area_ratio_125um':geometry['area_mm2']/(geometry['perimeter_mm']*.125),
                'aspect_ratio_125um':min(geometry['width_mm'],geometry['height_mm'])/.125,
                'maximum_thickness_for_area_ratio_0p66_mm':geometry['area_mm2']/(geometry['perimeter_mm']*.66)})
        for thickness in [.08,.1,.12,.125,.13,.15]:
            selected=[row for row in rows if row['file']==file.name]
            worst=min(selected,key=lambda row:row['area_mm2']/row['perimeter_mm'])
            area_min=worst['area_mm2']/(worst['perimeter_mm']*thickness)
            aspect_min=min(min(row['width_mm'],row['height_mm'])/thickness for row in selected)
            minimum_rows.append({'file':file.name,'thickness_mm':thickness,'minimum_area_ratio':area_min,'minimum_aspect_ratio':aspect_min,
                'screen_pass':area_min>=.66 and aspect_min>1.5,'scope':'TI SLUA271C printing-screen guidance; not universal factory acceptance or actual paste-transfer result'})
    with (evidence/'stencil-apertures.csv').open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    record={'pcb_sha256':checkpoint['pcb_sha256'],'source_directory':str(output),'paste_file_sha256':{file.name:pipeline.digest(file) for file in files},
        'flash_count':sum(row['count'] for row in rows),'candidate_thicknesses':minimum_rows,'design_basis_thickness_mm':.125,
        'area_ratio_screen':.66,'aspect_ratio_screen_strictly_greater_than':1.5,
        'limiting_thickness_mm':min(row['maximum_thickness_for_area_ratio_0p66_mm'] for row in rows),
        'basis':'TI TLV320AIC3104 and LP38691 package drawings use0.125mm; BMI088 allows80-150um; TI SLUA271C p11 explains area and aspect ratio',
        'manufacturing_released':False,'actual_solder_transfer_verified':False,
        'limits':['Roundrect actual area and perimeter used, not bounding-box area','Nickel-formed and other stencil processes may have different verified capabilities',
                  '0.125mm is a design basis; actual thickness and transfer must be controlled by the stencil process',
                  'These ratios do not approve component-specific solder volume, voiding or actual thermal performance']}
    import pcbnew
    source_board=pcbnew.LoadBoard(str(pipeline.PRIMARY/(pipeline.STEM+'.kicad_pcb')))
    buck=source_board.FindFootprintByReference('U301')
    thermal=next(pad for pad in buck.Pads() if pad.GetNumber()=='9')
    windows=[pad for pad in buck.Pads() if not pad.GetNumber() and pad.IsOnLayer(pcbnew.F_Paste)]
    record['u301_source_paste_policy']={'direct_ep_paste':thermal.IsOnLayer(pcbnew.F_Paste),
        'independent_window_count':len(windows),'source_footprint':str(buck.GetFPID().GetLibItemName()),
        'project_selected_not_factory_qualified':bool(windows)}
    record['design_basis_screen_pass']=all(row['screen_pass'] for row in minimum_rows if row['thickness_mm']==.125)
    pipeline.write_json(evidence/'stencil-apertures.json',record)
    print(json.dumps(record))
    if not record['design_basis_screen_pass']:
        raise RuntimeError('Selected stencil thickness fails the documented geometric screen')


if __name__=='__main__':
    main()
