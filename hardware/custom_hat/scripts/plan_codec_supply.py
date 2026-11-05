"""Reserve a local codec power via while detouring only the SCL terminal branch."""
import heapq
import json
import math
import copy
import itertools
from pathlib import Path

import plan_i2s_sdo as planner
from power_local_detour import route


EVIDENCE=Path(__file__).resolve().parents[3]/'docs/references/扩展板电路仿真工具/codec-supply-20261030'
REMOVED={'4c3169ee-ed94-45ec-a287-d62c2d71b812','5ad54a15-7efc-4bc8-903e-b68115dd64f0',
         '32bcce4f-0c46-4431-ba9c-597ff40bef9a','a38ba9d2-6fa7-4b1e-ae9e-408a287d1ab0','e0b332c8-0fe0-4b98-ad36-a21defb7767a','e52a2ff9-5693-4118-9e2b-2851c63a964f',
         '10ae63f1-45a3-4521-bfae-6a7c0e1458f3','fff083ab-41be-4a01-a647-23c2126eec58'}


def main():
    geometry=json.loads((EVIDENCE/'geometry-before.json').read_text(encoding='utf-8'))
    REMOVED.update(item['uuid'] for item in geometry if item['kind'] in {'track','via'} and item.get('net') in {'I2S_SDI','I2S_SDO','I2S_LRCK','I2S_BCLK'})
    originals=[item for item in geometry if item.get('uuid') in REMOVED]
    if len(originals)!=len(REMOVED) or any(item['net'] not in {'I2C5_SCL','I2S_SDI','I2S_SDO','I2S_LRCK','I2S_BCLK'} for item in originals):raise ValueError('Signal baseline changed')
    items=[item for item in geometry if item.get('uuid') not in REMOVED]
    for item in items:
        if item['kind']=='pad' and set(item['layers'])=={'F.Cu','B.Cu'}:item['layers']=planner.LAYERS[:]
    planner.POWER.update(item.get('net') for item in items)
    planner.STEP=.025
    planner.XMIN,planner.YMIN,planner.XMAX,planner.YMAX=147.,109.,152.,114.
    planner.COLS=201;planner.ROWS=201;planner.SIZE=201*201
    grid=planner.occupancy(items,.1,['B.Cu'],'+3V3')
    vias=planner.occupancy(items,.25,planner.LAYERS,'+3V3',True)
    source=planner.node(150.3625,112.1,0)
    queue=[(0.,source)];costs={source:0.};parents={};goals=[]
    while queue:
        cost,current=heapq.heappop(queue)
        if cost>costs[current]:continue
        xpos,ypos,_=planner.coordinates(current)
        if not vias[current] and all(math.hypot(xpos-other[0],ypos-other[1])>.5 for other in goals):
            goals.append((xpos,ypos,current))
            if len(goals)>=16:break
        row,column=divmod(current,planner.COLS)
        for delta_x,delta_y in [(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]:
            next_x,next_y=column+delta_x,row+delta_y
            if not(0<=next_x<planner.COLS and 0<=next_y<planner.ROWS):continue
            neighbor=next_y*planner.COLS+next_x
            if grid[neighbor]:continue
            if delta_x and delta_y and (grid[row*planner.COLS+next_x] or grid[next_y*planner.COLS+column]):continue
            next_cost=cost+math.hypot(delta_x,delta_y)
            if next_cost<costs.get(neighbor,float('inf')):
                costs[neighbor]=next_cost;parents[neighbor]=current;heapq.heappush(queue,(next_cost,neighbor))
    print('Reachable bounds',[(min(planner.coordinates(identifier)[axis] for identifier in costs),max(planner.coordinates(identifier)[axis] for identifier in costs)) for axis in [0,1]],flush=True)
    candidates=[]
    for xpos,ypos,identifier in goals:
        path=[identifier]
        while path[-1]!=source:path.append(parents[path[-1]])
        path.reverse()
        points=[planner.coordinates(node)[:2] for node in path]
        compact=[(150.3625,112.1)]
        for index in range(1,len(points)-1):
            first,current,last=points[index-1:index+2]
            if tuple(round(current[axis]-first[axis],4) for axis in (0,1))!=tuple(round(last[axis]-current[axis],4) for axis in (0,1)):compact.append(current)
        compact.append(points[-1])
        candidates.append({'via':[xpos,ypos],'power_points':compact})
    attempts=[]
    planner.EVIDENCE=EVIDENCE
    success=False
    signals=[('I2C5_SCL',(150.3625,111.6),(148.7442,109.5837)),('I2S_SDI',(150.3625,113.1),(154.04,102.05)),('I2S_SDO',(150.3625,113.6),(156.58,102.05)),('I2S_LRCK',(150.3625,114.1),(151.5,104.59)),('I2S_BCLK',(150.3625,114.6),(121.02,102.05))]
    orders=[[signals[index] for index in order] for order in [(0,1,3,2,4),(0,1,2,3,4),(1,0,3,2,4),(1,3,2,0,4),(0,4,3,2,1),(4,3,2,1,0)]]
    for candidate in candidates:
        for order in orders:
            obstacles=copy.deepcopy(items)+[{'kind':'via','net':'+3V3','position':candidate['via'],'width':.5,'drill':.3}]
            for first,last in zip(candidate['power_points'],candidate['power_points'][1:]):obstacles.append({'kind':'track','net':'+3V3','layer':'B.Cu','start':first,'end':last,'width':.2})
            try:
                planner.POWER={'POWER_GND','+5V','+3V3','VBATT_2S_IN','SERVO_VBAT','BUCK_SW'}
                planner.STEP=.05
                planner.WIDTH=.1
                planner.XMIN,planner.YMIN,planner.XMAX,planner.YMAX=119.,100.5,158.,120.
                planner.COLS=round((planner.XMAX-planner.XMIN)/planner.STEP)+1;planner.ROWS=round((planner.YMAX-planner.YMIN)/planner.STEP)+1;planner.SIZE=planner.COLS*planner.ROWS
                plans=[]
                for net,first,last in order:
                    signal=planner.solve(obstacles,net,first,last)
                    plans.append(signal)
                    for start,end in zip(signal['points'],signal['points'][1:]):
                        if start[2]!=end[2]:obstacles.append({'kind':'via','net':net,'position':start[:2],'width':.5,'drill':.3})
                        else:obstacles.append({'kind':'track','net':net,'layer':planner.LAYERS[start[2]],'start':start[:2],'end':end[:2],'width':signal['width']})
                candidate.update(signals=plans,removed=sorted(REMOVED))
                attempts.append({'via':candidate['via'],'order':[entry[0] for entry in order],'success':True})
                (EVIDENCE/'route-plan.json').write_text(json.dumps(candidate,indent=2)+'\n',encoding='utf-8')
                print('Complete candidate',candidate['via'],flush=True)
                success=True;break
            except RuntimeError as error:
                attempts.append({'via':candidate['via'],'order':[entry[0] for entry in order],'success':False,'reason':str(error),'completed_nets':[entry['net'] for entry in plans],'failed_net':net})
                (EVIDENCE/'search-record.json').write_text(json.dumps({'states':len(costs),'via_candidates':len(candidates),'attempts':attempts},indent=2)+'\n',encoding='utf-8')
                print('Attempt',len(attempts),'failed',flush=True)
        if success:break
    (EVIDENCE/'search-record.json').write_text(json.dumps({'states':len(costs),'via_candidates':len(candidates),'attempts':attempts},indent=2)+'\n',encoding='utf-8')
    if not attempts or not attempts[-1]['success']:raise SystemExit('No viable local SCL detour; no PCB changed')


if __name__=='__main__':main()
