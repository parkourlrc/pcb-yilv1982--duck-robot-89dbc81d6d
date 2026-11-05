"""Find a physically clear pair of vias for the remaining C704 supply link."""
import argparse
import json
import math
from pathlib import Path
import shutil

import pcbnew

from add_i2c_pullups import obstacles, position, vector
import plan_i2s_sdo as planner
from repair_rev_b_solder_routes import add_plan, save, native, install_via_terminal_clearance


def main():
    ap=argparse.ArgumentParser();ap.add_argument('directory',type=Path)
    ap.add_argument('--reference',default='C704');ap.add_argument('--pin',default='1')
    ap.add_argument('--net',default='+1V8_CODEC');ap.add_argument('--label',default='cap-via-escape')
    args=ap.parse_args()
    path=args.directory.resolve()/'custom_hat_rev_b.kicad_pcb'
    candidate_root=Path(__file__).resolve().parents[3]/'docs/references/扩展板乙版降本'
    if not path.is_relative_to(candidate_root):raise RuntimeError('Only use this mutator on an isolated cost-study candidate')
    backup=path.parent/('before-'+args.label+'.kicad_pcb')
    if backup.exists():raise FileExistsError(backup)
    shutil.copy2(path,backup)
    board=pcbnew.LoadBoard(str(path));net=args.net
    cap=board.FindFootprintByReference(args.reference)
    old={p.GetNumber():p.GetPosition() for p in cap.Pads()}
    if args.reference=='C704':cap.SetPosition(vector((139.3,109.9)))
    new={p.GetNumber():p.GetPosition() for p in cap.Pads()}
    for t in board.GetTracks():
        if t.Type()!=pcbnew.PCB_VIA_T and t.IsOnLayer(pcbnew.F_Cu):
            for pin,pt in old.items():
                if t.GetStart()==pt:t.SetStart(new[pin])
                if t.GetEnd()==pt:t.SetEnd(new[pin])
    pad=next(p for p in cap.Pads() if p.GetNumber()==args.pin);start=position(pad)
    assert pad.GetNetname()==net
    width=.25 if args.reference=='U301' and args.pin=='1' else .15
    layers=(pcbnew.F_Cu,pcbnew.B_Cu)
    foreign={layer:[] for layer in layers};exposed=[];holes=[]
    power={'POWER_GND','VBATT_2S_IN','+5V','+5V_PRE_IDEAL'}
    for fp in board.GetFootprints():
        for p in fp.Pads():
            if p.GetAttribute()==pcbnew.PAD_ATTRIB_SMD:
                exposed.append(p.GetEffectiveShape(pcbnew.F_Cu))
            if p.GetNetname()==net:continue
            gap=.2 if p.GetNetname() in power else .15
            if p.GetAttribute()==pcbnew.PAD_ATTRIB_NPTH:gap=.25
            for layer in layers:
                if p.IsOnLayer(layer):foreign[layer].append((p.GetEffectiveShape(layer),pcbnew.FromMM(gap)))
    for t in board.GetTracks():
        if t.Type()==pcbnew.PCB_VIA_T:holes.append(t.GetEffectiveHoleShape())
        if t.GetNetname()==net:continue
        gap=.2 if t.GetNetname() in power else .15
        for layer in layers:
            if t.IsOnLayer(layer):foreign[layer].append((t.GetEffectiveShape(layer),pcbnew.FromMM(gap)))
    def via_at(xy):
        v=pcbnew.PCB_VIA(board);v.SetPosition(vector(xy));v.SetWidth(pcbnew.FromMM(.6));v.SetDrill(pcbnew.FromMM(.3))
        v.SetViaType(pcbnew.VIATYPE_THROUGH);v.SetLayerPair(*layers);v.SetNet(board.FindNet(net))
        v.SetFrontTentingMode(pcbnew.TENTING_MODE_TENTED);v.SetBackTentingMode(pcbnew.TENTING_MODE_TENTED)
        if any(v.GetEffectiveHoleShape().Collide(s,pcbnew.FromMM(.051)) for s in exposed):return None
        if any(v.GetEffectiveHoleShape().Collide(s,pcbnew.FromMM(.251)) for s in holes):return None
        if any(v.GetEffectiveShape(layer).Collide(s,gap+1000) for layer in layers for s,gap in foreign[layer]):return None
        return v
    def short_at(xy):
        t=pcbnew.PCB_TRACK(board);t.SetStart(pad.GetPosition());t.SetEnd(vector(xy));t.SetWidth(pcbnew.FromMM(width));t.SetLayer(pcbnew.F_Cu);t.SetNet(board.FindNet(net))
        if any(t.GetEffectiveShape(pcbnew.F_Cu).Collide(s,gap+1000) for s,gap in foreign[pcbnew.F_Cu]):return None
        return t
    first=[]
    grid=sorted((dx*dx+dy*dy,dx,dy) for dx in range(-24,25) for dy in range(-24,25))
    for _,dx,dy in grid:
        xy=(round(start[0]+dx*.1,4),round(start[1]+dy*.1,4))
        v=via_at(xy)
        if v is not None:
            short=short_at(xy)
            if short is not None:first.append((xy,v,short))
        if len(first)==12:break
    second=[]
    for t in board.GetTracks():
        if t.GetNetname()!=net or t.Type()==pcbnew.PCB_VIA_T or not t.IsOnLayer(pcbnew.F_Cu):continue
        a,b=position(t),tuple(pcbnew.ToMM(t.GetEnd()))
        for f in (.25,.5,.75):
            xy=tuple(round(a[i]+(b[i]-a[i])*f,4) for i in (0,1));v=via_at(xy)
            if v is not None:second.append((xy,v))
    print('Clear cap escapes:',[p[0] for p in first], 'Existing-net via candidates:',len(second),flush=True)
    if not first or not second:raise RuntimeError('No native-shape-safe via pair')
    planner.EVIDENCE=path.parent;planner.LAYERS=['F.Cu','B.Cu'];planner.POWER=power
    planner.STEP=.025;planner.WIDTH=width;planner.VIA_AVOID_RADIUS=.3;planner.VIA_PENALTY=100
    planner.XMIN,planner.YMIN,planner.XMAX,planner.YMAX=127,105.5,146,120
    if args.reference=='U301':planner.XMIN,planner.YMIN,planner.XMAX,planner.YMAX=100.7,107,133,128.9
    planner.COLS=round((planner.XMAX-planner.XMIN)/planner.STEP)+1;planner.ROWS=round((planner.YMAX-planner.YMIN)/planner.STEP)+1;planner.SIZE=planner.COLS*planner.ROWS
    install_via_terminal_clearance()
    trials=sorted((math.dist(a[0],b[0]),i,j) for i,a in enumerate(first) for j,b in enumerate(second))
    for _,i,j in trials[:16]:
        a,av,short=first[i];b,bv=second[j]
        virtual=[{'kind':'via','net':net,'position':xy,'width':.6,'drill':.3} for xy in (a,b)]
        try:plan=planner.solve(obstacles(board)+virtual,net,a,b,[1],[1])
        except RuntimeError:continue
        plan['via_diameter']=.6
        board.Add(av);board.Add(bv);board.Add(short);add_plan(board,plan);save(board,path)
        record={'reference':args.reference,'pin':args.pin,'component_position':position(cap),'cap_via':a,'existing_net_via':b,'route':plan,
                'clearance_basis':'native copper shapes +1um guard; drill-to-exposed-pad 0.051mm; final DRC required'}
        (path.parent/(args.label+'.json')).write_text(json.dumps(record,indent=2)+'\n',encoding='utf8')
        report=native(path,args.label+'-final');print('Connected; DRC violations:',len(report['violations']),'unconnected:',len(report['unconnected_items']),flush=True)
        return
    raise RuntimeError('Via candidates found but no routed pair in bounded attempts')


if __name__=='__main__':main()
