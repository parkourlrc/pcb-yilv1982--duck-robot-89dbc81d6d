"""Locate filled-ground components and distinguish pad-connected from orphan copper."""
import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path

import pcbnew


def main():
    ap=argparse.ArgumentParser();ap.add_argument('directory',type=Path);args=ap.parse_args()
    path=args.directory.resolve()/'custom_hat_rev_b.kicad_pcb'
    board=pcbnew.LoadBoard(str(path));layers=(pcbnew.F_Cu,pcbnew.B_Cu)
    nodes=[]
    for z in board.Zones():
        if z.GetNetname()!='POWER_GND':continue
        for layer in layers:
            if not z.IsOnLayer(layer):continue
            polygons=z.GetFilledPolysList(layer)
            for i in range(polygons.OutlineCount()):
                box=polygons.COutline(i).BBox()
                nodes.append({'layer':layer,'polygons':polygons,'index':i,
                              'bounds':[pcbnew.ToMM(v) for v in (box.GetLeft(),box.GetTop(),box.GetRight(),box.GetBottom())]})
    parent=list(range(len(nodes)))
    def root(i):
        while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
        return i
    def join(ids):
        if ids:
            r=root(ids[0])
            for i in ids[1:]:parent[root(i)]=r
    def at(points,available):
        hits=set()
        for i,n in enumerate(nodes):
            if n['layer'] not in available:continue
            for point in points:
                if n['polygons'].Contains(point,n['index']):hits.add(i);break
        return sorted(hits)
    pads=[];conductors=[]
    for f in board.GetFootprints():
        for p in f.Pads():
            if p.GetNetname()!='POWER_GND':continue
            center=p.GetPosition();size=p.GetSize();angle=math.radians(p.GetOrientationDegrees())
            points=[center]
            for dx,dy in ((.35,0),(-.35,0),(0,.35),(0,-.35)):
                x,y=size.x*dx,size.y*dy
                points.append(pcbnew.VECTOR2I(round(center.x+x*math.cos(angle)+y*math.sin(angle)),round(center.y-x*math.sin(angle)+y*math.cos(angle))))
            hits=at(points,[layer for layer in layers if p.IsOnLayer(layer)])
            join(hits);pads.append({'pad':f.GetReference()+'.'+p.GetNumber(),'nodes':hits})
    for t in board.GetTracks():
        if t.GetNetname()!='POWER_GND':continue
        if t.Type()==pcbnew.PCB_VIA_T:
            center=t.GetPosition();r=(t.GetFrontWidth()+t.GetDrill())/4
            points=[center]+[pcbnew.VECTOR2I(round(center.x+r*math.cos(a)),round(center.y+r*math.sin(a))) for a in (0,math.pi/2,math.pi,3*math.pi/2)]
            available=layers;kind='via'
        else:
            a,b=t.GetStart(),t.GetEnd();count=max(1,math.ceil(math.hypot(b.x-a.x,b.y-a.y)/pcbnew.FromMM(.1)))
            points=[pcbnew.VECTOR2I(round(a.x+(b.x-a.x)*i/count),round(a.y+(b.y-a.y)*i/count)) for i in range(count+1)]
            available=[t.GetLayer()];kind='track'
        hits=at(points,available);join(hits)
        conductors.append({'uuid':t.m_Uuid.AsString(),'kind':kind,'nodes':hits,'xy':list(pcbnew.ToMM(t.GetPosition()))})
    groups=defaultdict(lambda:{'nodes':[],'pads':[],'conductors':[]})
    for i,n in enumerate(nodes):groups[root(i)]['nodes'].append({'id':i,'layer':board.GetLayerName(n['layer']),'bounds':n['bounds']})
    for p in pads:
        if p['nodes']:groups[root(p['nodes'][0])]['pads'].append(p['pad'])
    for t in conductors:
        if t['nodes']:groups[root(t['nodes'][0])]['conductors'].append(t)
    result={'pcb_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'groups':list(groups.values()),
            'pads_without_polygon_hits':[p for p in pads if not p['nodes']],
            'conductors_without_polygon_hits':[t for t in conductors if not t['nodes']],
            'limits':'Samples native filled polygons and conductor centers; native DRC is the final connectivity authority.'}
    (path.parent/'ground-islands.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'groups':[{'polygons':g['nodes'],'pads':g['pads'],'conductors':len(g['conductors'])} for g in result['groups']],
                      'pads_without_hits':result['pads_without_polygon_hits'],'conductors_without_hits':len(result['conductors_without_polygon_hits'])}))


if __name__=='__main__':main()
