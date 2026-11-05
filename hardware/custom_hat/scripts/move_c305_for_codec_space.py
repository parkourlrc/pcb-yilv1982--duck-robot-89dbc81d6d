"""Relocate the output capacitor in a guarded candidate to free the codec escape area."""
import argparse
import json
from pathlib import Path

import pcbnew
import pipeline
from add_i2c_pullups import vector
from finish_ttl_local_bypass import route_layer


EVIDENCE=pipeline.BASE.parents[1]/'docs/references/归档扩展板贴片规范复查'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--attempt',required=True)
    parser.add_argument('--x',type=float,default=138.5)
    parser.add_argument('--y',type=float,default=108.5)
    parser.add_argument('--connect-inductor',action='store_true')
    parser.add_argument('--angle',type=float,default=0)
    parser.add_argument('--route-width',type=float,default=.6)
    parser.add_argument('--source',type=Path)
    parser.add_argument('--protect-reference',action='store_true')
    arguments=parser.parse_args()
    evidence=EVIDENCE/arguments.attempt;evidence.mkdir(exist_ok=False)
    checkpoint=pipeline.current_checkpoint();source=pipeline.managed(arguments.source) if arguments.source else pipeline.PRIMARY
    work=pipeline.prepare(source);path=work/(pipeline.STEM+'.kicad_pcb')
    board=pcbnew.LoadBoard(str(path))
    for zone in board.Zones():zone.UnFill()
    footprint=board.FindFootprintByReference('C305')
    pad=next(pad for pad in footprint.Pads() if pad.GetNumber()=='1')
    old_position=[pcbnew.ToMM(value) for value in pad.GetPosition()]
    footprint.SetPosition(vector((arguments.x,arguments.y)))
    footprint.SetOrientationDegrees(arguments.angle)
    new_position=[pcbnew.ToMM(value) for value in pad.GetPosition()]
    ground=next(pad for pad in footprint.Pads() if pad.GetNumber()=='2')
    ground.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    ground.SetLocalThermalSpokeWidthOverride(pcbnew.FromMM(.25))
    ground.SetThermalGap(pcbnew.FromMM(.2))
    record={'baseline':checkpoint['pcb_sha256'],'project':str(work),'old_pad1':old_position,'new_pad1':new_position,'promoted':False}
    try:
        anchor=next(pad for pad in board.FindFootprintByReference('L301').Pads() if pad.GetNumber()=='2') if arguments.connect_inductor else None
        endpoint=[pcbnew.ToMM(value) for value in anchor.GetPosition()] if anchor else old_position
        record['route']=route_layer(board,'+5V','F.Cu',arguments.route_width,new_position,endpoint,evidence,search_margin=5,protect_i2s_reference=arguments.protect_reference)
        pcbnew.SaveBoard(str(path),board)
        reports,summary=pipeline.check(work)
        record.update(summary=str(reports/'summary.json'),status=summary['status'],drc=summary['drc'])
    except Exception as error:
        pcbnew.SaveBoard(str(path),board)
        record['error']=str(error)
    pipeline.write_json(evidence/'candidate.json',record)
    print(json.dumps(record,ensure_ascii=False))


if __name__=='__main__':main()
