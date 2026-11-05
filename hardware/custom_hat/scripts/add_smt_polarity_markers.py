"""Add unambiguous visible assembly polarity labels to a guarded candidate."""
import argparse
import json
from pathlib import Path

import pcbnew
import pipeline
from add_i2c_pullups import vector


EVIDENCE=pipeline.BASE.parents[1]/'docs/references/归档扩展板贴片与层叠复核'


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--attempt',required=True)
    parser.add_argument('--u301-x',type=float,default=122.7);parser.add_argument('--u301-y',type=float,default=110.85)
    parser.add_argument('--diode-x',type=float,default=110.5);parser.add_argument('--diode-y',type=float,default=111.5)
    args=parser.parse_args();folder=EVIDENCE/args.attempt;folder.mkdir(exist_ok=False)
    candidate=json.loads((EVIDENCE/'candidate.json').read_text(encoding='utf-8'));source=pipeline.managed(Path(candidate['project']))
    work=pipeline.prepare(source);path=work/(pipeline.STEM+'.kicad_pcb');board=pcbnew.LoadBoard(str(path));marks=[]
    for reference,text,point in [('U301','1',(args.u301_x,args.u301_y)),('D301','K',(args.diode_x,args.diode_y))]:
        item=pcbnew.PCB_TEXT(board);item.SetText(text);item.SetPosition(vector(point));item.SetTextSize(vector((1,1)));item.SetTextThickness(pcbnew.FromMM(.15));item.SetLayer(pcbnew.F_SilkS);board.Add(item)
        marks.append({'reference':reference,'text':text,'position_mm':point,'uuid':item.m_Uuid.AsString(),'height_mm':1,'stroke_mm':.15})
    pcbnew.SaveBoard(str(path),board);reports,summary=pipeline.check(work)
    result={'project':str(work),'source':str(source),'marks':marks,'summary':str(reports/'summary.json'),'drc':summary['drc'],'status':summary['status'],'promoted':False}
    pipeline.write_json(folder/'candidate.json',result);print(json.dumps(result))


if __name__=='__main__':main()
