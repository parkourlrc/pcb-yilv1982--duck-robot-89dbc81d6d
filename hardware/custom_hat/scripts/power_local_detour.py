"""Create a ground stitching point by detouring explicitly identified nearby tracks."""
import argparse
import heapq
import json
import math

import pcbnew

import pipeline
import plan_i2s_sdo as planner
import repair_u501
from power_repair_steps import load_state,attempt
from repair_power_connections import EVIDENCE
from simplify_i2s_plan import clear_segment


def route(items,net,layer,start,end,width):
    planner.STEP=.05
    planner.XMIN=max(100.6,round(min(start[0],end[0])-3,2))
    planner.YMIN=max(100.6,round(min(start[1],end[1])-3,2))
    planner.XMAX=min(164.4,round(max(start[0],end[0])+3,2))
    planner.YMAX=min(129.4,round(max(start[1],end[1])+3,2))
    planner.COLS=math.ceil((planner.XMAX-planner.XMIN)/planner.STEP)+1
    planner.ROWS=math.ceil((planner.YMAX-planner.YMIN)/planner.STEP)+1
    planner.SIZE=planner.COLS*planner.ROWS
    grid=planner.occupancy(items,width/2,[layer],net)
    source=planner.node(*start,0)
    goal=planner.node(*end,0)
    if grid[source] or grid[goal]:raise RuntimeError('Detour endpoint blocked by conservative geometry')
    def heuristic(identifier):
        xpos,ypos,_=planner.coordinates(identifier)
        return math.hypot(xpos-end[0],ypos-end[1])/planner.STEP
    queue=[(heuristic(source),0.0,source)]
    costs={source:0.0}
    parents={}
    reached=False
    while queue:
        _,cost,current=heapq.heappop(queue)
        if cost>costs[current]:continue
        if current==goal:
            reached=True
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
                costs[neighbor]=next_cost;parents[neighbor]=current
                heapq.heappush(queue,(next_cost+heuristic(neighbor),next_cost,neighbor))
    if not reached:raise RuntimeError('No local detour found')
    path=[goal]
    while path[-1]!=source:path.append(parents[path[-1]])
    path.reverse()
    points=[planner.coordinates(identifier)[:2] for identifier in path]
    points[0]=tuple(start);points[-1]=tuple(end)
    compact=[points[0]]
    index=0
    while index<len(points)-1:
        found=False
        for candidate in range(len(points)-1,index,-1):
            first,last=points[index],points[candidate]
            delta_x,delta_y=last[0]-first[0],last[1]-first[1]
            diagonal=min(abs(delta_x),abs(delta_y))
            corners=[(first[0]+math.copysign(diagonal,delta_x),first[1]+math.copysign(diagonal,delta_y)),(last[0]-math.copysign(diagonal,delta_x),last[1]-math.copysign(diagonal,delta_y))]
            for corner in corners:
                if clear_segment(grid,first,corner) and clear_segment(grid,corner,last):
                    if corner!=compact[-1]:compact.append(corner)
                    if last!=compact[-1]:compact.append(last)
                    index=candidate;found=True;break
            if found:break
        if not found:index+=1;compact.append(points[index])
    return compact


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--target',choices=['U801','C310'],required=True);args=parser.parse_args()
    state,work=load_state();label='ground-detour-interior-'+args.target
    if any(record['label']==label for record in state['attempts']):return
    configs={
        'U801':([131.2522,123.8032],['d4121fe5-d24a-49c4-84a3-a60acc110f06']),
        'C310':([148.0655,112.6],['2d1d3345-baae-4615-9995-dbc7b16b102c','722d7268-cb45-4556-85c9-09361310296a']),
    }
    location,identifiers=configs[args.target]
    board=pcbnew.LoadBoard(str(work/(pipeline.STEM+'.kicad_pcb')))
    geometry=repair_u501.geometry(board)
    tracks={item.m_Uuid.AsString():item for item in board.GetTracks()}
    originals=[item for item in geometry if item.get('uuid') in identifiers]
    if len(originals)!=len(identifiers):raise ValueError('Detour baseline changed')
    items=[item for item in geometry if item.get('uuid') not in identifiers]
    for item in items:
        if item['kind']=='pad' and set(item['layers'])=={'F.Cu','B.Cu'}:item['layers']=planner.LAYERS[:]
    items.append({'kind':'via','net':'POWER_GND','position':location,'width':.5,'drill':.3})
    plans=[]
    for original in originals:
        points=route(items,original['net'],original['layer'],original['start'],original['end'],original['width'])
        plans.append({**original,'points':points})
        for first,last in zip(points,points[1:]):items.append({'kind':'track','net':original['net'],'layer':original['layer'],'width':original['width'],'start':first,'end':last})
    pipeline.write_json(EVIDENCE/(label+'-plan.json'),{'via':location,'plans':plans})
    def edit(target):
        for identifier in identifiers:target.Remove(tracks[identifier])
        for plan in plans:
            for first,last in zip(plan['points'],plan['points'][1:]):
                segment=pcbnew.PCB_TRACK(target)
                segment.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(first[0]),pcbnew.FromMM(first[1])))
                segment.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(last[0]),pcbnew.FromMM(last[1])))
                segment.SetWidth(pcbnew.FromMM(plan['width']))
                segment.SetLayer(target.GetLayerID(plan['layer']))
                segment.SetNet(target.FindNet(plan['net']))
                target.Add(segment)
        via=pcbnew.PCB_VIA(target)
        via.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(location[0]),pcbnew.FromMM(location[1])))
        via.SetWidth(pcbnew.FromMM(.5));via.SetDrill(pcbnew.FromMM(.3))
        via.SetLayerPair(pcbnew.F_Cu,pcbnew.B_Cu);via.SetNet(target.FindNet('POWER_GND'));target.Add(via)
    attempt(state,work,label,edit,board=board)


if __name__=='__main__':main()
