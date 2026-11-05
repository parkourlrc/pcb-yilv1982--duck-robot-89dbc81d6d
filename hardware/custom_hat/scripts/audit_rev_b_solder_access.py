"""Source-bound THT solder-access screen, with 3/5mm height classes."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

import pcbnew

from plan_rev_b_solder_access import box, graphic_box, gap


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('board',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    board=pcbnew.LoadBoard(str(args.board))
    components=[]
    for f in board.GetFootprints():
        ref=f.GetReference()
        if ref.startswith(('TP','FID','H')):
            continue
        side=f.GetLayer()
        body=graphic_box(f,pcbnew.F_Fab if side==pcbnew.F_Cu else pcbnew.B_Fab)
        # All connectors and the SWPA6045 inductor use the conservative tall
        # class. Remaining mounted parts use known <4mm package categories.
        tall=ref.startswith('J') or ref=='L301'
        components.append({'ref':ref,'side':board.GetLayerName(side),'body_bbox_mm':body,
                           'threshold_mm':5.0 if tall else 3.0,
                           'design_target_mm':5.2 if tall else 3.2,
                           'height_class':'tall or conservatively tall' if tall else 'low profile below4mm',
                           'xy':list(pcbnew.ToMM(f.GetPosition()))})
    comparisons=[]
    tht=[]
    for f in board.GetFootprints():
        weld='B.Cu' if f.GetLayer()==pcbnew.F_Cu else 'F.Cu'
        for p in f.Pads():
            if p.GetAttribute()!=pcbnew.PAD_ATTRIB_PTH or not p.GetNumber():
                continue
            pb=box(p)
            tht.append({'pad':f.GetReference()+'.'+p.GetNumber(),'welding_face':weld,'bbox_mm':pb,'net':p.GetNetname()})
            for c in components:
                if c['side']!=weld or c['ref']==f.GetReference() or c['body_bbox_mm'] is None:
                    continue
                distance=gap(pb,c['body_bbox_mm'])
                comparisons.append({'pad':tht[-1]['pad'],'welding_face':weld,'neighbor':c['ref'],
                                    'gap_mm':round(distance,6),'required_mm':c['threshold_mm'],
                                    'design_target_mm':c['design_target_mm'],
                                    'margin_mm':round(distance-c['threshold_mm'],6)})
    failures=[c for c in comparisons if c['gap_mm']<c['required_mm']]
    margin_failures=[c for c in comparisons if c['gap_mm']<c['design_target_mm']]
    result={'source':str(args.board),'pcb_sha256':hashlib.sha256(args.board.read_bytes()).hexdigest(),
            'basis':'Nominal pad bbox to opposite-face Fab envelope; fabrication graphics include conservative lead/body envelopes.',
            'confidence':'CAD screen; actual process acceptance remains subject to factory review',
            'trust_summary':{'geometry':'current KiCad','height_classes':'datasheet package class; connectors conservatively tall','factory_acceptance':False},
            'tht_pads':tht,'components':components,'rule_failures':failures,'design_margin_failures':margin_failures,
            'nearest_pairs':sorted(comparisons,key=lambda c:c['margin_mm'])[:30],
            'missing_body_envelopes':[c['ref'] for c in components if c['body_bbox_mm'] is None],
            'notes':['3/5mm nominal rule plus0.2mm project margin.','Height<4mm class covers R/C/FB,SOT23,SOIC16,QFN32,2520 oscillator,and2718MEMS; actual tolerances listed in research.',
                     'No physical measurement, individual billed-joint count, or guaranteed fee waiver.']}
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'rule_failures':len(failures),'margin_failures':len(margin_failures),
                      'missing':result['missing_body_envelopes'],'nearest':result['nearest_pairs'][:8]}))


if __name__=='__main__':
    main()
