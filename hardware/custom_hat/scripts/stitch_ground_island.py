"""Connect a known ground copper island using a geometrically valid stitching via."""
import argparse
import json
import math

import pcbnew

import pipeline
import plan_i2s_sdo as planner
import repair_u501
from power_repair_steps import load_state,attempt
from repair_power_connections import EVIDENCE


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--pad',required=True)
    args=parser.parse_args()
    state,work=load_state()
    label='ground-island-all-inner-regions-'+args.pad.replace('.','-')
    if any(record['label']==label for record in state['attempts']):return
    board=pcbnew.LoadBoard(str(work/(pipeline.STEM+'.kicad_pcb')))
    ref,number=args.pad.split('.')
    pad=next(pad for pad in board.FindFootprintByReference(ref).Pads() if pad.GetNumber()==number)
    zone=next(zone for zone in board.Zones() if zone.GetLayer()==pcbnew.B_Cu and zone.GetNetname()=='POWER_GND')
    polys=zone.GetFilledPolysList(pcbnew.B_Cu)
    index=next(index for index in range(polys.OutlineCount()) if polys.Contains(pad.GetPosition(),index))
    box=polys.COutline(index).BBox()
    planner.STEP=.025
    planner.XMIN=pcbnew.ToMM(box.GetLeft())
    planner.YMIN=pcbnew.ToMM(box.GetTop())
    planner.XMAX=pcbnew.ToMM(box.GetRight())
    planner.YMAX=pcbnew.ToMM(box.GetBottom())
    planner.COLS=math.ceil((planner.XMAX-planner.XMIN)/planner.STEP)+1
    planner.ROWS=math.ceil((planner.YMAX-planner.YMIN)/planner.STEP)+1
    planner.SIZE=planner.COLS*planner.ROWS
    items=repair_u501.geometry(board)
    planner.POWER.update(item.get('net') for item in items)
    for item in items:
        if item['kind']=='pad' and set(item['layers'])=={'F.Cu','B.Cu'}:item['layers']=planner.LAYERS[:]
    foreign=[item for item in items if item.get('net')!='POWER_GND']
    grid=planner.occupancy(foreign,.25,planner.LAYERS,'POWER_GND',True)
    for item in items:
        if item.get('net')!='POWER_GND':continue
        if item['kind']=='pad':
            left,top,right,bottom=item['bounds']
            margin=.30
            planner.mark(grid,(left-margin,top-margin,right+margin,bottom+margin),lambda xpos,ypos:math.hypot(max(left-xpos,0,xpos-right),max(top-ypos,0,ypos-bottom))<=margin)
        elif item['kind']=='via':
            xpos,ypos=item['position']
            margin=.5
            planner.mark(grid,(xpos-margin,ypos-margin,xpos+margin,ypos+margin),lambda probe_x,probe_y:math.hypot(probe_x-xpos,probe_y-ypos)<=margin)
    inner=next(zone for zone in board.Zones() if zone.GetLayer()==pcbnew.In1_Cu and zone.GetNetname()=='POWER_GND')
    inner_polys=inner.GetFilledPolysList(pcbnew.In1_Cu)
    source=next(pad for pad in board.FindFootprintByReference('J101').Pads() if pad.GetNumber()=='6')
    inner_index=next(index for index in range(inner_polys.OutlineCount()) if inner_polys.Contains(source.GetPosition(),index))
    candidates=[]
    for identifier in range(planner.SIZE):
        if grid[identifier]:continue
        xpos,ypos,_=planner.coordinates(identifier)
        position=pcbnew.VECTOR2I(pcbnew.FromMM(xpos),pcbnew.FromMM(ypos))
        if polys.Contains(position,index) and inner_polys.Contains(position):
            candidates.append((math.hypot(xpos-pcbnew.ToMM(pad.GetPosition().x),ypos-pcbnew.ToMM(pad.GetPosition().y)),xpos,ypos))
    candidates.sort()
    if not candidates:
        record={'label':label,'accepted':False,'reason':'No conservative stitching position inside the known ground island'}
        state['attempts'].append(record)
        pipeline.write_json(EVIDENCE/'state.json',state)
        print(json.dumps(record),flush=True)
        return
    _,xpos,ypos=candidates[0]
    pipeline.write_json(EVIDENCE/(label+'-plan.json'),{'pad':args.pad,'position':[xpos,ypos],'via_diameter':.5,'drill':.3,'candidate_count':len(candidates)})
    def edit(target):
        via=pcbnew.PCB_VIA(target)
        via.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(xpos),pcbnew.FromMM(ypos)))
        via.SetWidth(pcbnew.FromMM(.5))
        via.SetDrill(pcbnew.FromMM(.3))
        via.SetLayerPair(pcbnew.F_Cu,pcbnew.B_Cu)
        via.SetNet(target.FindNet('POWER_GND'))
        target.Add(via)
    attempt(state,work,label,edit,board=board)


if __name__=='__main__':main()
