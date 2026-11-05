"""Apply per-pad SMT thermal reliefs in a complete candidate without changing copper tracks."""
import json
import argparse
from pathlib import Path

import pcbnew
import pipeline


EVIDENCE=pipeline.BASE.parents[1]/'docs/references/归档扩展板贴片规范复查'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--c306-angle',type=float)
    parser.add_argument('--c306-gap',type=float,default=.2)
    parser.add_argument('--exclude',nargs='*',default=[])
    arguments=parser.parse_args()
    checkpoint=pipeline.current_checkpoint()
    audit=json.loads((EVIDENCE/'smt-layout-audit.json').read_text(encoding='utf-8'))
    work=pipeline.prepare(pipeline.PRIMARY)
    path=work/(pipeline.STEM+'.kicad_pcb')
    board=pcbnew.LoadBoard(str(path))
    selected={row['pad'] for row in audit['chip_pad_center_in_same_net_fill']}
    selected-=set(arguments.exclude)
    changed=[]
    for footprint in board.GetFootprints():
        for pad in footprint.Pads():
            reference=footprint.GetReference()+'.'+pad.GetNumber()
            if reference not in selected:
                continue
            changed.append({'pad':reference,'uuid':pad.m_Uuid.AsString(),'old_connection':int(pad.GetLocalZoneConnection()),'new_connection':'thermal','spoke_mm':.25,'gap_mm':.2})
            pad.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_THERMAL)
            pad.SetLocalThermalSpokeWidthOverride(pcbnew.FromMM(.25))
            pad.SetThermalGap(pcbnew.FromMM(.2))
            if reference=='C306.2' and arguments.c306_angle is not None:
                pad.SetThermalSpokeAngle(pcbnew.EDA_ANGLE(arguments.c306_angle,pcbnew.DEGREES_T))
            if reference=='C306.2':
                pad.SetThermalGap(pcbnew.FromMM(arguments.c306_gap))
                changed[-1]['gap_mm']=arguments.c306_gap
    pcbnew.SaveBoard(str(path),board)
    reports,summary=pipeline.check(work)
    record={'baseline_pcb_sha256':checkpoint['pcb_sha256'],'project':str(work),'changed_pads':changed,'summary':str(reports/'summary.json'),
            'drc':summary['drc'],'status':summary['status'],'promoted':False,'main_unchanged':pipeline.fingerprints(pipeline.PRIMARY)==checkpoint['design_hashes']}
    record['excluded_pads']=arguments.exclude
    suffix='' if arguments.c306_angle is None else '-angle'+str(int(arguments.c306_angle))
    if arguments.c306_gap!=.2:
        suffix+='-gap'+str(arguments.c306_gap)
    if arguments.exclude:
        suffix+='-selective'
    pipeline.write_json(EVIDENCE/('thermal-relief-candidate'+suffix+'.json'),record)
    print(json.dumps(record,ensure_ascii=False))


if __name__=='__main__':
    main()
