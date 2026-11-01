"""Replace grid stair steps with clear 45/90 degree segments before KiCad validation."""
import json
import math

import plan_i2s_sdo as planner


def clear_segment(grid, start, end):
    distance=math.hypot(end[0]-start[0],end[1]-start[1])
    count=max(1,math.ceil(distance/(planner.STEP/4)))
    for index in range(count+1):
        xpos=start[0]+(end[0]-start[0])*index/count
        ypos=start[1]+(end[1]-start[1])*index/count
        identifier=planner.node(xpos,ypos,0)
        if identifier<0 or identifier>=planner.SIZE or grid[identifier]:return False
    return True


def main():
    path=planner.EVIDENCE/'route-plan.json'
    result=json.loads(path.read_text(encoding='utf-8'))
    (planner.EVIDENCE/'grid-route-plan.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    original=json.loads((planner.EVIDENCE/'geometry-before.json').read_text(encoding='utf-8'))
    items=[item for item in original if item.get('uuid') not in result['removed_uuids']]
    for item in items:
        if item['kind']=='pad' and set(item['layers'])=={'F.Cu','B.Cu'}:item['layers']=planner.LAYERS[:]
    for plan in result['plans']:
        for first,last in zip(plan['points'],plan['points'][1:]):
            if first[2]!=last[2]:items.append({'kind':'via','net':plan['net'],'position':first[:2],'width':plan['via_diameter'],'drill':plan['via_drill']})
            else:items.append({'kind':'track','net':plan['net'],'layer':planner.LAYERS[first[2]],'start':first[:2],'end':last[:2],'width':plan['width']})
    for plan in result['plans']:
        grids=[planner.occupancy(items,plan['width']/2,[layer],plan['net']) for layer in planner.LAYERS]
        points=plan['points']
        output=[points[0]]
        index=0
        while index<len(points)-1:
            layer=points[index][2]
            maximum=index+1
            while maximum<len(points) and points[maximum][2]==layer:maximum+=1
            if maximum==index+1:
                index+=1
                output.append(points[index])
                continue
            found=False
            for candidate in range(maximum-1,index,-1):
                start,end=points[index],points[candidate]
                delta_x,delta_y=end[0]-start[0],end[1]-start[1]
                diagonal=min(abs(delta_x),abs(delta_y))
                corner_first=[round(start[0]+math.copysign(diagonal,delta_x),4),round(start[1]+math.copysign(diagonal,delta_y),4),layer]
                corner_last=[round(end[0]-math.copysign(diagonal,delta_x),4),round(end[1]-math.copysign(diagonal,delta_y),4),layer]
                for corner in [corner_first,corner_last]:
                    if clear_segment(grids[layer],start,corner) and clear_segment(grids[layer],corner,end):
                        if corner!=output[-1]:output.append(corner)
                        if end!=output[-1]:output.append(end)
                        index=candidate
                        found=True
                        break
                if found:break
            if not found:
                index+=1
                output.append(points[index])
        plan['points']=output
        print(plan['net'],len(points),'->',len(output))
        items=[item for item in items if not(item['kind'] in {'track','via'} and item.get('net')==plan['net'])]
        for first,last in zip(output,output[1:]):
            if first[2]!=last[2]:items.append({'kind':'via','net':plan['net'],'position':first[:2],'width':plan['via_diameter'],'drill':plan['via_drill']})
            else:items.append({'kind':'track','net':plan['net'],'layer':planner.LAYERS[first[2]],'start':first[:2],'end':last[:2],'width':plan['width']})
    path.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
