"""Create a separate, source-bound placement candidate for THT solder access.

No source promotion, manufacturing release, or quote claim is performed.
"""
import argparse
import hashlib
import json
import math
import shutil
from pathlib import Path

import pcbnew


ROOT = Path(__file__).resolve().parents[3]
PROJECT = ROOT / 'hardware/custom_hat/rev_b'
EVIDENCE = ROOT / 'docs/references/扩展板乙版降本/layout-spacing'
STEM = 'custom_hat_rev_b'
BASELINE = '99ecc45dc5ac4f582c1ed5a1d24f732a8f4a1be8a2bd49e81f36294826f167da'


def vector(x, y):
    return pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))


def box(item):
    b = item.GetBoundingBox()
    return [pcbnew.ToMM(v) for v in (b.GetLeft(), b.GetTop(), b.GetRight(), b.GetBottom())]


def graphic_box(f, layer):
    boxes = [box(g) for g in f.GraphicalItems() if g.GetLayer() == layer and g.Type() == pcbnew.PCB_SHAPE_T]
    if not boxes:
        return None
    return [min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)]


def gap(a, b):
    return math.hypot(max(a[0]-b[2], b[0]-a[2], 0), max(a[1]-b[3], b[1]-a[3], 0))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', default='placement-r1')
    args = parser.parse_args()
    source = PROJECT / (STEM+'.kicad_pcb')
    assert hashlib.sha256(source.read_bytes()).hexdigest() == BASELINE
    EVIDENCE.mkdir(exist_ok=True)
    baseline = EVIDENCE/'baseline-99ecc45d'
    if not baseline.exists():
        baseline.mkdir()
        for p in PROJECT.iterdir():
            if p.is_file() and (p.suffix in {'.kicad_pcb','.kicad_pro','.kicad_dru','.kicad_sch','.kicad_sym','.json'} or p.name in {'fp-lib-table','sym-lib-table'}):
                shutil.copy2(p, baseline/p.name)
        shutil.copytree(PROJECT/'duck.pretty', baseline/'duck.pretty')
    target = EVIDENCE/args.name
    target.mkdir(exist_ok=False)
    for p in baseline.iterdir():
        if p.is_dir():
            shutil.copytree(p,target/p.name)
        else:
            shutil.copy2(p,target/p.name)
    b = pcbnew.LoadBoard(str(source))
    fps = {f.GetReference():f for f in b.GetFootprints()}
    original = {r:[*pcbnew.ToMM(f.GetPosition()),f.GetOrientationDegrees()] for r,f in fps.items()}
    # Tall 3P connectors retain their own local pad numbering; rotation is real
    # geometry, not a CPL layer or numbering edit.
    fixed_moves = {'J401':(105.5,113.0,0),'J402':(115.0,113.0,0)}
    desired = {
        'U801':(122.0,111.0,0), 'U802':(127.0,110.7,0),
        'U702':(132.0,110.6,0), 'Y701':(137.0,110.15,0),
        'D401':(119.0,115.7,0),
        'C702':(133.8,109.35,180), 'C703':(134.2,112.0,0),
        'C713':(140.25,109.35,0), 'C704':(139.5,110.4,-90),
        'C711':(141.25,110.4,-90), 'R701':(145.3,109.4,0),
        'R501':(149.0,109.4,0), 'R502':(149.0,111.0,0),
        'FB701':(154.0,109.5,0), 'R402':(115.8,109.4,0),
        'R404':(119.8,111.5,90), 'C401':(121.7,113.8,180),
        'C402':(128.8,109.7,90), 'R401':(123.0,114.4,0),
        'R403':(123.0,116.0,0),
        'C712':(143.7,109.5,0), 'R301':(127.0,113.0,0),
        'C305':(130.0,112.7,0), 'TP803':(124.0,113.8,0),
    }
    for ref,(x,y,a) in fixed_moves.items():
        fps[ref].SetOrientationDegrees(a)
        fps[ref].SetPosition(vector(x,y))
    # Fab envelopes are conservative, with a 0.2mm design margin beyond the
    # platform's nominal 3/5mm rule. Heights of all near-header low parts are
    # below 4mm; the exact source table is recorded with the resulting audit.
    header = fps['J101']
    header_pads = [box(p) for p in header.Pads()]
    fixed = [f for r,f in fps.items() if r not in desired]
    def valid(f):
        court = f.GetCourtyard(pcbnew.F_CrtYd)
        if not court.OutlineCount():
            return False
        bounds = graphic_box(f,pcbnew.F_CrtYd)
        if bounds is None:
            return False
        if bounds[0]<100.25 or bounds[1]<100.25 or bounds[2]>164.75 or bounds[3]>129.75:
            return False
        body = graphic_box(f,pcbnew.F_Fab)
        if body and min(gap(body,p) for p in header_pads)<3.2:
            return False
        for other in fixed:
            if other.GetLayer()!=pcbnew.F_Cu:
                continue
            obstacle = other.GetCourtyard(pcbnew.F_CrtYd)
            if obstacle.OutlineCount() and court.Collide(obstacle,pcbnew.FromMM(.05)):
                return False
        return True
    failed=[]
    for ref,(x0,y0,a0) in desired.items():
        f=fps[ref]
        options=[]
        for dx in range(-24,25):
            for dy in range(-12,21):
                x,y=x0+dx*.25,y0+dy*.25
                for angle in (a0,(a0+90)%360,(a0+180)%360,(a0+270)%360):
                    score=dx*dx+dy*dy+(0 if angle==a0 else 1.5)
                    options.append((score,x,y,angle))
        for _,x,y,a in sorted(options):
            f.SetOrientationDegrees(a)
            f.SetPosition(vector(x,y))
            if valid(f):
                fixed.append(f)
                break
        else:
            failed.append(ref)
            f.SetOrientationDegrees(a0)
            f.SetPosition(vector(x0,y0))
            fixed.append(f)
    moves={r:{'before':original[r],'after':[*pcbnew.ToMM(fps[r].GetPosition()),fps[r].GetOrientationDegrees()]} for r in [*fixed_moves,*desired]}
    pcbnew.SaveBoard(str(target/(STEM+'.kicad_pcb')),b)
    report={'source_sha256':BASELINE,'candidate':str(target.relative_to(ROOT)),'failed_placements':failed,'moves':moves,'routing':'old copper is intentionally not yet modified; candidate is not electrically valid or released'}
    report['footprints']=[{'ref':r,'side':b.GetLayerName(f.GetLayer()),'fab':graphic_box(f,pcbnew.F_Fab if f.GetLayer()==pcbnew.F_Cu else pcbnew.B_Fab),'courtyard':graphic_box(f,pcbnew.F_CrtYd if f.GetLayer()==pcbnew.F_Cu else pcbnew.B_CrtYd),'xy':list(pcbnew.ToMM(f.GetPosition()))} for r,f in fps.items()]
    (target/'placement.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='footprints'},ensure_ascii=False))


if __name__=='__main__':
    main()
