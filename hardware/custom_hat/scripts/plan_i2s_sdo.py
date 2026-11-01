"""Plan routes on the existing four copper layers against explicit copper geometry."""
import heapq
import argparse
import itertools
import copy
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "docs/references/hat-simulation-tools-20261029/i2s-sdo-repair-20261030"
STEP = 0.05
XMIN, YMIN, XMAX, YMAX = 119.0, 100.5, 164.4, 121.0
COLS = round((XMAX-XMIN)/STEP)+1
ROWS = round((YMAX-YMIN)/STEP)+1
SIZE = COLS*ROWS
WIDTH = 0.15
LAYERS = ['F.Cu','B.Cu','In1.Cu','In2.Cu']
VIA_AVOID_RADIUS = 1.0
POWER = {"POWER_GND", "+5V", "+3V3", "VBATT_2S_IN", "SERVO_VBAT", "BUCK_SW"}


def distance_segment(xpos, ypos, start, end):
    delta_x, delta_y = end[0]-start[0], end[1]-start[1]
    length = delta_x*delta_x+delta_y*delta_y
    fraction = max(0.0, min(1.0, ((xpos-start[0])*delta_x+(ypos-start[1])*delta_y)/length)) if length else 0
    return math.hypot(xpos-start[0]-fraction*delta_x, ypos-start[1]-fraction*delta_y)


def mark(grid, bounds, predicate):
    first_x=max(0,math.floor((bounds[0]-XMIN)/STEP))
    last_x=min(COLS-1,math.ceil((bounds[2]-XMIN)/STEP))
    first_y=max(0,math.floor((bounds[1]-YMIN)/STEP))
    last_y=min(ROWS-1,math.ceil((bounds[3]-YMIN)/STEP))
    for row in range(first_y,last_y+1):
        for column in range(first_x,last_x+1):
            if predicate(XMIN+column*STEP,YMIN+row*STEP):
                grid[row*COLS+column]=1


def occupancy(items, radius, layers, target_net, forbid_terminal=False):
    grid=bytearray(SIZE)
    for item in items:
        if item.get("net")==target_net and not forbid_terminal:
            continue
        clearance=0.2 if item.get("net") in POWER else 0.15
        margin=radius+clearance+0.015
        if item["kind"]=="pad" and (set(item["layers"]) & set(layers)):
            left,top,right,bottom=item["bounds"]
            mark(grid,(left-margin,top-margin,right+margin,bottom+margin),lambda xpos,ypos: math.hypot(max(left-xpos,0,xpos-right),max(top-ypos,0,ypos-bottom))<=margin)
        elif item["kind"]=="track" and item["layer"] in layers:
            start,end=item["start"],item["end"]
            extent=margin+item["width"]/2
            bounds=(min(start[0],end[0])-extent,min(start[1],end[1])-extent,max(start[0],end[0])+extent,max(start[1],end[1])+extent)
            mark(grid,bounds,lambda xpos,ypos:distance_segment(xpos,ypos,start,end)<=extent)
        elif item["kind"]=="via":
            xpos,ypos=item["position"]
            extent=margin+item["width"]/2
            mark(grid,(xpos-extent,ypos-extent,xpos+extent,ypos+extent),lambda probe_x,probe_y:math.hypot(probe_x-xpos,probe_y-ypos)<=extent)
        elif item["kind"]=="keepout" and item["layer"] in layers:
            left=min(point[0] for point in item["points"])-radius
            right=max(point[0] for point in item["points"])+radius
            top=min(point[1] for point in item["points"])-radius
            bottom=max(point[1] for point in item["points"])+radius
            mark(grid,(left,top,right,bottom),lambda xpos,ypos:left<=xpos<=right and top<=ypos<=bottom)
    return grid


def node(xpos,ypos,layer):
    return layer*SIZE+round((ypos-YMIN)/STEP)*COLS+round((xpos-XMIN)/STEP)


def coordinates(identifier):
    layer,offset=divmod(identifier,SIZE)
    row,column=divmod(offset,COLS)
    return round(XMIN+column*STEP,4),round(YMIN+row*STEP,4),layer


def solve(items,target_net,start_position,end_position,end_layers=None,start_layer=1):
    grids=[occupancy(items,WIDTH/2,[layer],target_net) for layer in LAYERS]
    vias=occupancy(items,VIA_AVOID_RADIUS,['F.Cu','B.Cu','In1.Cu','In2.Cu'],target_net,True)
    start=node(*start_position,start_layer)
    goals={node(*end_position,layer) for layer in (range(len(LAYERS)) if end_layers is None else end_layers)}
    if grids[start_layer][start%SIZE]:
        raise RuntimeError('Starting pad blocked by conservative geometry')
    def heuristic(identifier):
        xpos,ypos,_=coordinates(identifier)
        return math.hypot(xpos-end_position[0],ypos-end_position[1])/STEP
    queue=[(heuristic(start),0.0,start)]
    costs={start:0.0}
    parents={}
    goal=None
    while queue:
        _,cost,current=heapq.heappop(queue)
        if cost>costs[current]:continue
        if current in goals:
            goal=current
            break
        layer,offset=divmod(current,SIZE)
        row,column=divmod(offset,COLS)
        neighbors=[]
        for delta_x,delta_y in [(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]:
            next_x,next_y=column+delta_x,row+delta_y
            if not(0<=next_x<COLS and 0<=next_y<ROWS):continue
            next_offset=next_y*COLS+next_x
            if grids[layer][next_offset]:continue
            if delta_x and delta_y and (grids[layer][row*COLS+next_x] or grids[layer][next_y*COLS+column]):continue
            neighbors.append((layer*SIZE+next_offset,math.hypot(delta_x,delta_y)))
        if not vias[offset]:
            for next_layer in range(len(LAYERS)):
                if next_layer!=layer and not grids[next_layer][offset]:neighbors.append((next_layer*SIZE+offset,60.0))
        for neighbor,increment in neighbors:
            next_cost=cost+increment
            if next_cost<costs.get(neighbor,float('inf')):
                costs[neighbor]=next_cost
                parents[neighbor]=current
                heapq.heappush(queue,(next_cost+heuristic(neighbor),next_cost,neighbor))
    if goal is None:
        (EVIDENCE/('search-failure-'+target_net+'.json')).write_text(json.dumps({'width':WIDTH,'step':STEP,'states':len(costs),'reachable':[coordinates(identifier) for identifier in costs]},indent=2),encoding='utf-8')
        raise RuntimeError(f'No path in this conservative search region ({len(costs)} states); not proof of physical impossibility')
    route=[goal]
    while route[-1]!=start:route.append(parents[route[-1]])
    route.reverse()
    points=[coordinates(identifier) for identifier in route]
    compact=[points[0]]
    for index in range(1,len(points)-1):
        previous,current,next_point=points[index-1:index+2]
        vector_before=tuple(round(current[axis]-previous[axis],4) for axis in range(3))
        vector_after=tuple(round(next_point[axis]-current[axis],4) for axis in range(3))
        if vector_before!=vector_after:compact.append(current)
    compact.append(points[-1])
    compact[0]=(*start_position,1)
    compact[-1]=(*end_position,compact[-1][2])
    return {'net':target_net,'width':WIDTH,'via_diameter':0.5,'via_drill':0.3,'points':compact,'states':len(costs),'cost_including_via_penalty':costs[goal]*STEP,'limitations':'Conservative pad bounding boxes; no zone polygons; final KiCad DRC and refill required'}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--group',action='store_true')
    args=parser.parse_args()
    items=json.loads((EVIDENCE/'geometry-before.json').read_text(encoding='utf-8'))
    for item in items:
        if item['kind']=='pad' and set(item['layers'])=={'F.Cu','B.Cu'}:item['layers']=LAYERS[:]
    targets=[('I2S_SDO',(150.3625,113.6),(156.58,102.05))]
    if args.group:
        targets=[('I2S_SDI',(150.3625,113.1),(154.04,102.05)),*targets,('I2S_LRCK',(150.3625,114.1),(151.5,104.59)),('I2S_BCLK',(150.3625,114.6),(121.02,102.05))]
    names={target[0] for target in targets}
    removed=[item for item in items if item['kind'] in {'track','via'} and item.get('net') in names]
    items=[item for item in items if item not in removed]
    attempts=[]
    for order in itertools.permutations(targets):
        candidates=copy.deepcopy(items)
        plans=[]
        try:
            for net,start,end in order:
                plan=solve(candidates,net,start,end)
                plans.append(plan)
                for first,last in zip(plan['points'],plan['points'][1:]):
                    if first[2]!=last[2]:candidates.append({'kind':'via','net':net,'position':first[:2],'width':0.5,'drill':0.3})
                    else:candidates.append({'kind':'track','net':net,'layer':LAYERS[first[2]],'start':first[:2],'end':last[:2],'width':WIDTH})
        except RuntimeError as error:
            attempts.append({'order':[entry[0] for entry in order],'completed':len(plans),'failure':str(error)})
            (EVIDENCE/'search-attempts.json').write_text(json.dumps(attempts,indent=2)+'\n',encoding='utf-8')
            print('Ordering',len(attempts),'completed',len(plans),flush=True)
            continue
        attempts.append({'order':[entry[0] for entry in order],'completed':len(plans)})
        break
    (EVIDENCE/'search-attempts.json').write_text(json.dumps(attempts,indent=2)+'\n',encoding='utf-8')
    if len(plans)!=len(targets):raise RuntimeError('No complete candidate for these bounded routing orders')
    result={'plans':plans,'removed_uuids':[item['uuid'] for item in removed]}
    (EVIDENCE/'route-plan.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))


if __name__=='__main__':main()
