"""Move C310 away from the MCLK reference corridor and give its ground pad thermal relief."""
import argparse
import json
from pathlib import Path

import pcbnew
import pipeline
from add_i2c_pullups import vector


EVIDENCE=pipeline.BASE.parents[1]/'docs/references/归档扩展板贴片与层叠复核'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--attempt',required=True)
    parser.add_argument('--x',type=float,default=147.32)
    parser.add_argument('--y',type=float,default=112.65)
    args=parser.parse_args();folder=EVIDENCE/args.attempt;folder.mkdir(exist_ok=False)
    checkpoint=pipeline.current_checkpoint();work=pipeline.prepare(pipeline.PRIMARY)
    path=work/(pipeline.STEM+'.kicad_pcb');board=pcbnew.LoadBoard(str(path))
    footprint=board.FindFootprintByReference('C310')
    signal=next(pad for pad in footprint.Pads() if pad.GetNumber()=='1');old=signal.GetPosition()
    old_footprint=[pcbnew.ToMM(value) for value in footprint.GetPosition()]
    footprint.SetPosition(vector((args.x,args.y)));new=signal.GetPosition()
    ground=next(pad for pad in footprint.Pads() if pad.GetNumber()=='2')
    ground.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    ground.SetThermalGap(pcbnew.FromMM(.2));ground.SetLocalThermalSpokeWidthOverride(pcbnew.FromMM(.25))
    changed=[]
    for track in board.GetTracks():
        if track.Type()==pcbnew.PCB_VIA_T or track.GetNetname()!='CODEC_RST':continue
        original=[list(track.GetStart()),list(track.GetEnd())]
        if track.GetStart()==old:track.SetStart(new)
        if track.GetEnd()==old:track.SetEnd(new)
        current=[list(track.GetStart()),list(track.GetEnd())]
        if current!=original:changed.append({'uuid':track.m_Uuid.AsString(),'before':original,'after':current})
    if len(changed)!=2:raise RuntimeError('Expected exactly two RESET segment endpoint changes')
    pcbnew.SaveBoard(str(path),board)
    reports,summary=pipeline.check(work)
    record={'baseline':checkpoint['pcb_sha256'],'project':str(work),'old_position_mm':old_footprint,'new_position_mm':[args.x,args.y],
        'changed_tracks':changed,'summary':str(reports/'summary.json'),'drc':summary['drc'],'status':summary['status'],'promoted':False}
    pipeline.write_json(folder/'candidate.json',record);print(json.dumps(record))


if __name__=='__main__':main()
