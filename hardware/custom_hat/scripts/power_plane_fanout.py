"""Plan short pad-to-plane fanouts with copper obstacles, then accept by native DRC."""
import argparse
import heapq
import json
import math
import subprocess
import sys

import pcbnew

import pipeline
import plan_i2s_sdo as planner
import repair_u501
from power_repair_steps import load_state,attempt
from repair_power_connections import EVIDENCE


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--pad')
    parser.add_argument('--variant',type=int,default=0)
    parser.add_argument('--existing',action='store_true')
    args=parser.parse_args()
    state,work=load_state()
    if not args.pad:
        targets=['C308.1','R311.2','U702.3','TP803.1','U801.5','U802.5','R308.2','C319.1','C312.1','C313.1','C315.1','C320.1','J502.1','U701.7','U701.18','U701.24','U701.25','U501.3','U501.7','U501.11','U501.14','U501.15']
        for target in targets:
            subprocess.run([sys.executable,__file__,'--pad',target],check=True)
        return
    label='fanout-layer-fixed-'+args.pad.replace('.','-')+('-v'+str(args.variant) if args.variant else '')+('-existing' if args.existing else '')
    if any(record['label']==label for record in state['attempts']):
        print('Already attempted',args.pad,flush=True)
        return
    board=pcbnew.LoadBoard(str(work/(pipeline.STEM+'.kicad_pcb')))
    board.BuildConnectivity()
    ref,number=args.pad.split('.')
    footprint=board.FindFootprintByReference(ref)
    pad=next(pad for pad in footprint.Pads() if pad.GetNumber()==number)
    target_net=pad.GetNetname()
    if target_net not in {'+3V3','POWER_GND'}:raise ValueError('Unexpected target net')
    source_pin='1' if target_net=='+3V3' else '6'
    source=next(pad for pad in board.FindFootprintByReference('J101').Pads() if pad.GetNumber()==source_pin)
    if source.m_Uuid.AsString() in {item.m_Uuid.AsString() for item in board.GetConnectivity().GetConnectedItems(pad)}:
        print('Already on source group',args.pad,flush=True)
        return
    plane_layer=pcbnew.In2_Cu if target_net=='+3V3' else pcbnew.In1_Cu
    zone=next(zone for zone in board.Zones() if zone.GetLayer()==plane_layer and zone.GetNetname()==target_net)
    polygons=zone.GetFilledPolysList(plane_layer)
    source_polygons=[index for index in range(polygons.OutlineCount()) if polygons.Contains(source.GetPosition(),index)]
    if not source_polygons:raise ValueError('Source pad not in filled source polygon')
    items=repair_u501.geometry(board)
    for item in items:
        if item['kind']=='pad' and set(item['layers'])=={'F.Cu','B.Cu'}:item['layers']=planner.LAYERS[:]
    planner.POWER.update(item.get('net') for item in items)
    xpos,ypos=pcbnew.ToMM(pad.GetPosition().x),pcbnew.ToMM(pad.GetPosition().y)
    planner.STEP=0.05
    radius=8.0 if args.variant else 4.0
    planner.XMIN=round(max(100.6,xpos-radius),2)
    planner.YMIN=round(max(100.6,ypos-radius),2)
    planner.XMAX=round(min(164.4,xpos+radius),2)
    planner.YMAX=round(min(129.4,ypos+radius),2)
    planner.COLS=round((planner.XMAX-planner.XMIN)/planner.STEP)+1
    planner.ROWS=round((planner.YMAX-planner.YMIN)/planner.STEP)+1
    planner.SIZE=planner.COLS*planner.ROWS
    layer_id=footprint.GetLayer()
    if not pad.IsOnLayer(layer_id):raise ValueError('Pad is not on its footprint copper layer')
    layer=board.GetLayerName(layer_id)
    width=0.2
    grid=planner.occupancy(items,width/2,[layer],target_net)
    vias=planner.occupancy(items,0.25,planner.LAYERS,target_net,True)
    existing_goals=set()
    if args.existing:
        for item in board.GetConnectivity().GetConnectedItems(source):
            if item.Type()==pcbnew.PCB_VIA_T or item.IsOnLayer(layer_id):
                positions=[item.GetPosition()]
                if item.Type()==pcbnew.PCB_TRACE_T:positions.extend([item.GetStart(),item.GetEnd()])
                for position in positions:
                    goal_x,goal_y=pcbnew.ToMM(position.x),pcbnew.ToMM(position.y)
                    if planner.XMIN<=goal_x<=planner.XMAX and planner.YMIN<=goal_y<=planner.YMAX:
                        existing_goals.add(planner.node(goal_x,goal_y,0))
    if args.variant:
        for previous in EVIDENCE.glob('fanout*'+args.pad.replace('.','-')+'*-plan.json'):
            old_plan=json.loads(previous.read_text(encoding='utf-8'))
            old_x,old_y=old_plan['points'][-1]
            planner.mark(vias,(old_x-.65,old_y-.65,old_x+.65,old_y+.65),lambda probe_x,probe_y:math.hypot(probe_x-old_x,probe_y-old_y)<.65)
    start=planner.node(xpos,ypos,0)
    if grid[start]:
        print('Conservative start blocked',args.pad,flush=True)
        return
    queue=[(0.0,start)]
    costs={start:0.0}
    parents={}
    goal=None
    while queue:
        cost,current=heapq.heappop(queue)
        if cost>costs[current]:continue
        probe_x,probe_y,_=planner.coordinates(current)
        location=pcbnew.VECTOR2I(pcbnew.FromMM(probe_x),pcbnew.FromMM(probe_y))
        reaches_goal=current in existing_goals if args.existing else not vias[current] and any(polygons.Contains(location,index) for index in source_polygons)
        if cost>0 and reaches_goal:
            goal=current
            break
        row,column=divmod(current,planner.COLS)
        for delta_x,delta_y in [(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]:
            next_x,next_y=column+delta_x,row+delta_y
            if not(0<=next_x<planner.COLS and 0<=next_y<planner.ROWS):continue
            neighbor=next_y*planner.COLS+next_x
            if grid[neighbor]:continue
            if delta_x and delta_y and (grid[row*planner.COLS+next_x] or grid[next_y*planner.COLS+column]):continue
            next_cost=cost+math.hypot(delta_x,delta_y)
            if next_cost<costs.get(neighbor,float('inf')):
                costs[neighbor]=next_cost
                parents[neighbor]=current
                heapq.heappush(queue,(next_cost,neighbor))
    if goal is None:
        record={'label':label,'accepted':False,'reason':'No conservative fanout to source polygon within local region','states':len(costs)}
        state['attempts'].append(record)
        pipeline.write_json(EVIDENCE/'state.json',state)
        print(json.dumps(record),flush=True)
        return
    path=[goal]
    while path[-1]!=start:path.append(parents[path[-1]])
    path.reverse()
    points=[planner.coordinates(identifier)[:2] for identifier in path]
    compact=[points[0]]
    for index in range(1,len(points)-1):
        previous,current,next_point=points[index-1:index+2]
        if tuple(round(current[axis]-previous[axis],4) for axis in (0,1))!=tuple(round(next_point[axis]-current[axis],4) for axis in (0,1)):compact.append(current)
    compact.append(points[-1])
    compact[0]=(xpos,ypos)
    plan={'target':args.pad,'net':target_net,'layer':layer,'width':width,'via_diameter':0.5,'via_drill':0.3,'points':compact,'source_polygons':source_polygons,'existing_goal':args.existing}
    pipeline.write_json(EVIDENCE/(label+'-plan.json'),plan)
    def edit(target_board):
        net=target_board.FindNet(target_net)
        for first,last in zip(compact,compact[1:]):
            if first==last:continue
            track=pcbnew.PCB_TRACK(target_board)
            track.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(first[0]),pcbnew.FromMM(first[1])))
            track.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(last[0]),pcbnew.FromMM(last[1])))
            track.SetLayer(layer_id)
            track.SetNet(net)
            track.SetWidth(pcbnew.FromMM(width))
            target_board.Add(track)
        if not args.existing:
            via=pcbnew.PCB_VIA(target_board)
            via.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(compact[-1][0]),pcbnew.FromMM(compact[-1][1])))
            via.SetWidth(pcbnew.FromMM(.5))
            via.SetDrill(pcbnew.FromMM(.3))
            via.SetLayerPair(pcbnew.F_Cu,pcbnew.B_Cu)
            via.SetNet(net)
            target_board.Add(via)
    attempt(state,work,label,edit,board=board)


if __name__=='__main__':main()
