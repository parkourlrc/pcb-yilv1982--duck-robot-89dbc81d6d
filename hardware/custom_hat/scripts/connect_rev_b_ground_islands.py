"""Join identified F.Cu ground islands to the main back ground, using native shapes."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil

import pcbnew
from add_i2c_pullups import vector
from repair_rev_b_solder_routes import save,native


def main():
    ap=argparse.ArgumentParser();ap.add_argument('directory',type=Path)
    ap.add_argument('--label',default='island-ground-links');ap.add_argument('--allow-back-track-ripup',action='store_true')
    ap.add_argument('--allow-thin-track-ripup',action='store_true');ap.add_argument('--bridge-front',action='store_true');args=ap.parse_args()
    path=args.directory.resolve()/'custom_hat_rev_b.kicad_pcb'
    candidate_root=Path(__file__).resolve().parents[3]/'docs/references/扩展板乙版降本'
    if not path.is_relative_to(candidate_root):raise RuntimeError('Only use this mutator on an isolated cost-study candidate')
    data=json.loads((path.parent/'ground-islands.json').read_text())
    assert data['pcb_sha256']==hashlib.sha256(path.read_bytes()).hexdigest()
    backup=path.parent/('before-'+args.label+'.kicad_pcb')
    if backup.exists():raise FileExistsError(backup)
    shutil.copy2(path,backup);board=pcbnew.LoadBoard(str(path))
    front=next(z.GetFilledPolysList(pcbnew.F_Cu) for z in board.Zones() if z.IsOnLayer(pcbnew.F_Cu))
    back=next(z.GetFilledPolysList(pcbnew.B_Cu) for z in board.Zones() if z.IsOnLayer(pcbnew.B_Cu))
    layers=(pcbnew.F_Cu,pcbnew.B_Cu);foreign={layer:[] for layer in layers};smd=[];holes=[];padpos={}
    for fp in board.GetFootprints():
        for p in fp.Pads():
            padpos[fp.GetReference()+'.'+p.GetNumber()]=tuple(pcbnew.ToMM(p.GetPosition()))
            if p.GetAttribute()==pcbnew.PAD_ATTRIB_SMD:smd.append(p.GetEffectiveShape(pcbnew.F_Cu))
            if p.GetDrillSize().x:holes.append(p.GetEffectiveShape(pcbnew.F_Cu))
            if p.GetNetname()=='POWER_GND':continue
            gap=.25 if p.GetAttribute()==pcbnew.PAD_ATTRIB_NPTH else .2
            for layer in layers:
                if p.IsOnLayer(layer):foreign[layer].append((p.GetEffectiveShape(layer),pcbnew.FromMM(gap),p))
    for t in board.GetTracks():
        if t.Type()==pcbnew.PCB_VIA_T:holes.append(t.GetEffectiveHoleShape())
        if t.GetNetname()=='POWER_GND':continue
        for layer in layers:
            if t.IsOnLayer(layer):foreign[layer].append((t.GetEffectiveShape(layer),pcbnew.FromMM(.2),t))
    main=max(data['groups'],key=lambda g:len(g['pads']))
    assert all(n['layer']=='F.Cu' for g in data['groups'] if g is not main for n in g['nodes'])
    # The audit found every B.Cu ground polygon in the main connected group.
    assert len([n for n in main['nodes'] if n['layer']=='B.Cu'])==back.OutlineCount()
    placed=[];missing=[];removed=[];removed_ids=set()
    for group in data['groups']:
        if group is main:continue
        boxes=[n['bounds'] for n in group['nodes']]
        bounds=[min(b[0] for b in boxes),min(b[1] for b in boxes),max(b[2] for b in boxes),max(b[3] for b in boxes)]
        if args.bridge_front:
            points=[padpos[p] for p in group['pads']]
            bounds=[min(p[0] for p in points)-2.5,min(p[1] for p in points)-2.5,max(p[0] for p in points)+2.5,max(p[1] for p in points)+2.5]
        indices=[n['id'] for n in group['nodes']]
        # Ground audit enumerates all F polygons first, so F node IDs equal indices.
        options=[]
        for ix in range(math.floor(bounds[0]*20),math.ceil(bounds[2]*20)+1):
            for iy in range(math.floor(bounds[1]*20),math.ceil(bounds[3]*20)+1):
                xy=(ix*.05,iy*.05);point=vector(xy)
                if (not args.bridge_front and not any(front.Contains(point,i) for i in indices)) or not back.Contains(point):continue
                if not(100.6<xy[0]<164.4 and 100.6<xy[1]<129.4):continue
                score=min(math.dist(xy,padpos[p]) for p in group['pads'])
                options.append((score,xy))
        viable=[]
        for score,xy in sorted(options):
            via=pcbnew.PCB_VIA(board);via.SetPosition(vector(xy));via.SetWidth(pcbnew.FromMM(.6));via.SetDrill(pcbnew.FromMM(.3))
            via.SetViaType(pcbnew.VIATYPE_THROUGH);via.SetLayerPair(*layers);via.SetNet(board.FindNet('POWER_GND'))
            hole=via.GetEffectiveHoleShape()
            if any(hole.Collide(s,pcbnew.FromMM(.051)) for s in smd):continue
            if any(hole.Collide(s,pcbnew.FromMM(.251)) for s in holes):continue
            short=None
            if args.bridge_front:
                anchor=min(group['pads'],key=lambda p:math.dist(xy,padpos[p]))
                short=pcbnew.PCB_TRACK(board);short.SetStart(vector(padpos[anchor]));short.SetEnd(vector(xy));short.SetWidth(pcbnew.FromMM(.25));short.SetLayer(pcbnew.F_Cu);short.SetNet(board.FindNet('POWER_GND'))
            collisions=[];blocked=False
            for layer in layers:
                for s,gap,obj in foreign[layer]:
                    if obj.m_Uuid.AsString() in removed_ids:continue
                    hit=via.GetEffectiveShape(layer).Collide(s,gap+1000)
                    if short is not None and layer==pcbnew.F_Cu:hit |= short.GetEffectiveShape(layer).Collide(s,gap+1000)
                    if not hit:continue
                    if (args.allow_thin_track_ripup or (args.allow_back_track_ripup and layer==pcbnew.B_Cu)) and obj.Type()==pcbnew.PCB_TRACE_T and pcbnew.ToMM(obj.GetWidth())<.6:
                        collisions.append(obj)
                    else:blocked=True;break
                if blocked:break
            if blocked:continue
            viable.append((len(collisions),score,xy,via,collisions,short))
            if not collisions:break
        if viable:
            _,_,xy,via,collisions,short=min(viable,key=lambda c:(c[0],c[1]))
            for track in collisions:
                uid=track.m_Uuid.AsString()
                if uid not in removed_ids:
                    removed_ids.add(uid);removed.append({'uuid':uid,'net':track.GetNetname()})
                    board.Remove(track);track.thisown=False
            via.SetFrontTentingMode(pcbnew.TENTING_MODE_TENTED);via.SetBackTentingMode(pcbnew.TENTING_MODE_TENTED)
            board.Add(via);holes.append(via.GetEffectiveHoleShape())
            if short is not None:board.Add(short)
            placed.append({'pads':group['pads'],'via':xy,'uuid':via.m_Uuid.AsString(),'front_bridge':short is not None})
        else:missing.append(group['pads'])
    save(board,path);report=native(path,args.label+'-final')
    result={'placed':placed,'missing':missing,'removed_back_tracks':removed,'violations':len(report['violations']),'unconnected':len(report['unconnected_items'])}
    (path.parent/(args.label+'.json')).write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps(result))


if __name__=='__main__':main()
