"""Compare the final spacing candidate to its immutable design baseline."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path

import pcbnew

from plan_rev_b_solder_access import ROOT, STEM
from resume_rev_b_solder_access import signature


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def physical(board):
    result = {}
    for f in board.GetFootprints():
        angle = math.radians(f.GetOrientationDegrees())
        pads = []
        for p in f.Pads():
            dx,dy = p.GetPosition().x-f.GetPosition().x,p.GetPosition().y-f.GetPosition().y
            local = [round(pcbnew.ToMM(dx*math.cos(angle)-dy*math.sin(angle)),5),
                     round(pcbnew.ToMM(dx*math.sin(angle)+dy*math.cos(angle)),5)]
            pads.append([p.GetNumber(),p.GetNetname(),local,list(pcbnew.ToMM(p.GetSize())),
                         list(pcbnew.ToMM(p.GetDrillSize())),p.GetAttribute(),p.GetShape(),
                         p.IsOnLayer(pcbnew.F_Mask),p.IsOnLayer(pcbnew.B_Mask)])
        result[f.GetReference()] = sorted(pads)
    return result


def check_power_paths(board, directory):
    plans=json.loads((directory/'explicit-servo-buses.json').read_text())['plans']
    plans.append(json.loads((directory/'explicit-5v-trunk.json').read_text())['plan'])
    results=[]
    for plan in plans:
        good=True
        for a,b in zip(plan['points'],plan['points'][1:]):
            if a[2]!=b[2]:
                good &= any(t.Type()==pcbnew.PCB_VIA_T and t.GetNetname()==plan['net']
                            and math.dist(pcbnew.ToMM(t.GetPosition()),a[:2])<.00001
                            and pcbnew.ToMM(t.GetFrontWidth())>=plan['via_diameter']-.00001 for t in board.GetTracks())
                continue
            dx,dy=b[0]-a[0],b[1]-a[1];length2=dx*dx+dy*dy;intervals=[]
            for t in board.GetTracks():
                if t.Type()==pcbnew.PCB_VIA_T or t.GetNetname()!=plan['net'] or t.GetLayer()!=(pcbnew.F_Cu,pcbnew.B_Cu)[a[2]] or pcbnew.ToMM(t.GetWidth())<plan['width']-.00001:continue
                p,q=pcbnew.ToMM(t.GetStart()),pcbnew.ToMM(t.GetEnd())
                if any(abs((x-a[0])*dy-(y-a[1])*dx)>math.sqrt(length2)*.00001 for x,y in (p,q)):continue
                u,v=sorted(((x-a[0])*dx+(y-a[1])*dy)/length2 for x,y in (p,q))
                intervals.append((max(0,u),min(1,v)))
            covered=0
            for low,high in sorted(intervals):
                if low>covered+.00001:break
                covered=max(covered,high)
            good &= covered>=1-.00001
        results.append({'net':plan['net'],'width_mm':plan['width'],'continuous_specified_path':bool(good)})
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('directory',type=Path)
    args = parser.parse_args()
    directory = args.directory.resolve()
    path = directory/(STEM+'.kicad_pcb')
    base = ROOT/'docs/references/扩展板乙版降本/layout-spacing/baseline-99ecc45d'
    old = pcbnew.LoadBoard(str(base/path.name))
    board = pcbnew.LoadBoard(str(path))
    native = json.loads((directory/'drc-complete-project.json').read_text(encoding='utf8'))
    access = json.loads((directory/'access.json').read_text(encoding='utf8'))
    files = [p.name for p in base.iterdir() if p.suffix in {'.kicad_sch','.kicad_pro','.kicad_dru','.kicad_sym'}]
    unchanged = {name:digest(base/name)==digest(directory/name) for name in files}
    old_phys, new_phys = physical(old), physical(board)
    changed_pads = [r for r in old_phys if old_phys[r] != new_phys[r]]
    fixed = {}
    for ref in ['J101','H1','H2','H3','H4']:
        a,b = old.FindFootprintByReference(ref),board.FindFootprintByReference(ref)
        fixed[ref] = [(p.GetNumber(),tuple(p.GetPosition())) for p in a.Pads()] == [(p.GetNumber(),tuple(p.GetPosition())) for p in b.Pads()]
    def outline(b):
        return sorted((g.GetShape(),tuple(g.GetStart()),tuple(g.GetEnd())) for g in b.GetDrawings() if g.GetLayer()==pcbnew.Edge_Cuts)
    vias = [t for t in board.GetTracks() if t.Type()==pcbnew.PCB_VIA_T]
    exposed = []
    for f in board.GetFootprints():
        for pad in f.Pads():
            if pad.GetAttribute() == pcbnew.PAD_ATTRIB_SMD and pad.IsOnLayer(pcbnew.F_Cu):
                for via in vias:
                    if via.GetEffectiveHoleShape().Collide(pad.GetEffectiveShape(pcbnew.F_Cu),pcbnew.FromMM(.05)):
                        exposed.append({'pad':f.GetReference()+'.'+pad.GetNumber(),'via':via.m_Uuid.AsString()})
    missing_masks = [f.GetReference()+'.'+p.GetNumber() for f in board.GetFootprints() for p in f.Pads()
                     if p.GetAttribute()==pcbnew.PAD_ATTRIB_PTH and not (p.IsOnLayer(pcbnew.F_Mask) and p.IsOnLayer(pcbnew.B_Mask))]
    power_paths=check_power_paths(board,directory)
    checks = {'same_parts_and_nets':signature(board)==signature(old), 'same_local_pad_geometry':not changed_pads,
              'same_schematic_rules_and_symbols':all(unchanged.values()), 'fixed_header_and_holes':all(fixed.values()),
              'same_board_outline':outline(old)==outline(board), 'same_two_layer_stack':board.GetCopperLayerCount()==old.GetCopperLayerCount()==2,
              'native_clean':not any(native[k] for k in ['violations','unconnected_items','schematic_parity']),
              'spacing_hash_matches':access['pcb_sha256']==digest(path),
              'spacing_clear':not any(access[k] for k in ['rule_failures','design_margin_failures','missing_body_envelopes']),
              'no_via_drill_in_exposed_smd':not exposed, 'tht_mask_openings_preserved':not missing_masks,
              'via_drills_at_least_0_3':all(v.GetDrill()>=pcbnew.FromMM(.3) for v in vias)}
    checks['specified_wide_power_paths_intact']=all(p['continuous_specified_path'] for p in power_paths)
    record = {'pcb_sha256':digest(path),'baseline_sha256':digest(base/path.name),'checks':checks,
              'changed_local_pads':changed_pads,'fixed_coordinates':fixed,'unchanged_files':unchanged,
              'via_in_exposed_smd':exposed,'missing_tht_masks':missing_masks,
              'via_sizes':dict(Counter(str((pcbnew.ToMM(v.GetFrontWidth()),pcbnew.ToMM(v.GetDrill()))) for v in vias)),
              'native_violations':dict(Counter(v['type'] for v in native['violations'])),
              'power_paths':power_paths,
              'trust_summary':{'CAD':'native rules, exact geometry and source hashes','physical_test':'not performed','factory_approval':'pending'},
              'confidence':'native CAD and immutable-baseline comparison; not a hardware measurement',
              'production_release':False,'factory_quote_obtained':False}
    (directory/'candidate-audit.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'checks':checks,'changed_pads':changed_pads,'via_in_pad':exposed}))
    if not all(checks.values()):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
