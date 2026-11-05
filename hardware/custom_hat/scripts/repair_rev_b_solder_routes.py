"""Incremental native-DRC guided repair of the solder-access candidate only."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys

import pcbnew

from add_i2c_pullups import obstacles, position, vector
import plan_i2s_sdo as planner


def install_via_terminal_clearance():
    """Allow via copper to join its own net, but keep its drill out of pads.

    Foreign copper retains the planner's original clearance. A 0.3mm drill
    stays 0.05mm outside every same-net pad's bounding box; native DRC and the
    final exposed-pad audit remain mandatory.
    """
    original = planner.occupancy
    def occupancy(items, radius, layers, target_net, forbid_terminal=False):
        if not forbid_terminal:
            return original(items, radius, layers, target_net, False)
        grid = original(items, radius, layers, target_net, False)
        for item in items:
            if item.get('net') != target_net:
                continue
            if item['kind'] == 'pad':
                left, top, right, bottom = item['bounds']
                margin = .20
                planner.mark(grid, (left-margin,top-margin,right+margin,bottom+margin),
                             lambda x,y: math.hypot(max(left-x,0,x-right),max(top-y,0,y-bottom)) <= margin)
            elif item['kind'] == 'via':
                x0,y0 = item['position']
                extent = .15+item.get('drill',.3)/2+.25
                planner.mark(grid,(x0-extent,y0-extent,x0+extent,y0+extent),
                             lambda x,y: math.hypot(x-x0,y-y0) <= extent)
        return grid
    planner.occupancy = occupancy


def native(path, label):
    output = path.parent / (label + '.json')
    cli = Path(sys.executable).parent / 'kicad-cli.exe'
    result = subprocess.run([str(cli), 'pcb', 'drc', '--format', 'json', '--schematic-parity',
                             '-o', str(output), str(path)], capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr.decode('utf8', errors='replace'))
    return json.loads(output.read_text(encoding='utf8'))


def save(board, path):
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(str(path), board)


def add_plan(board, plan):
    for first, last in zip(plan['points'], plan['points'][1:]):
        if first[2] != last[2]:
            track = pcbnew.PCB_VIA(board)
            track.SetPosition(vector(first[:2]))
            track.SetWidth(pcbnew.FromMM(plan['via_diameter']))
            track.SetDrill(pcbnew.FromMM(.3))
            track.SetViaType(pcbnew.VIATYPE_THROUGH)
            track.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
            track.SetFrontTentingMode(pcbnew.TENTING_MODE_TENTED)
            track.SetBackTentingMode(pcbnew.TENTING_MODE_TENTED)
        else:
            track = pcbnew.PCB_TRACK(board)
            track.SetStart(vector(first[:2]))
            track.SetEnd(vector(last[:2]))
            track.SetWidth(pcbnew.FromMM(plan['width']))
            track.SetLayer((pcbnew.F_Cu, pcbnew.B_Cu)[first[2]])
        track.SetNet(board.FindNet(plan['net']))
        board.Add(track)


def finish_power_obstacles(board, directory):
    plans=json.loads((directory/'explicit-servo-buses.json').read_text())['plans']
    plans.append(json.loads((directory/'explicit-5v-trunk.json').read_text())['plan'])
    protected=[]
    for plan in plans:
        for a,b in zip(plan['points'],plan['points'][1:]):
            if a[2]!=b[2]:continue
            matches=[t for t in board.GetTracks() if t.Type()!=pcbnew.PCB_VIA_T and t.GetNetname()==plan['net']
                     and t.GetLayer()==(pcbnew.F_Cu,pcbnew.B_Cu)[a[2]] and pcbnew.ToMM(t.GetWidth())>=plan['width']-.00001
                     and {tuple(pcbnew.ToMM(t.GetStart())),tuple(pcbnew.ToMM(t.GetEnd()))}=={tuple(a[:2]),tuple(b[:2])}]
            if not matches:raise RuntimeError('Specified power segment is missing: '+str((a,b)))
            protected.extend(matches)
    ids={t.m_Uuid.AsString() for t in protected};removed=[]
    for t in list(board.GetTracks()):
        if t.m_Uuid.AsString() in ids:continue
        if any(t.GetNetname()!=p.GetNetname() and t.IsOnLayer(p.GetLayer())
               and t.GetEffectiveShape(p.GetLayer()).Collide(p.GetEffectiveShape(p.GetLayer()),pcbnew.FromMM(.200001)) for p in protected):
            removed.append({'uuid':t.m_Uuid.AsString(),'net':t.GetNetname()})
            board.Remove(t);t.thisown=False
    board.BuildConnectivity();connectivity=board.GetConnectivity()
    visited=set();floating=[]
    for seed in list(board.GetTracks()):
        if seed.GetNetname()=='POWER_GND' or seed.m_Uuid.AsString() in visited:continue
        group=[];stack=[seed];anchored=False
        while stack:
            t=stack.pop();uid=t.m_Uuid.AsString()
            if uid in visited:continue
            visited.add(uid);group.append(t)
            anchored |= bool(connectivity.GetConnectedPads(t))
            stack.extend(q for q in connectivity.GetConnectedTracks(t) if q.GetNetname()==seed.GetNetname() and q.m_Uuid.AsString() not in visited)
        if not anchored:floating.extend(group)
    for t in floating:
        removed.append({'uuid':t.m_Uuid.AsString(),'net':t.GetNetname(),'reason':'native connected component has no pads'})
        board.Remove(t);t.thisown=False
    return removed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', type=Path)
    parser.add_argument('--label', default='local-r1')
    parser.add_argument('--cleanup-only', action='store_true')
    parser.add_argument('--rip-net', action='append', default=[])
    parser.add_argument('--allow-own-net-via', action='store_true')
    parser.add_argument('--finish-power-obstacles', action='store_true')
    args = parser.parse_args()
    path = args.directory.resolve() / 'custom_hat_rev_b.kicad_pcb'
    assert '扩展板乙版降本' in str(path) and 'rev_b' not in path.parent.parts
    backup = path.parent / ('before-' + args.label + '.kicad_pcb')
    if backup.exists():
        raise FileExistsError(backup)
    shutil.copy2(path, backup)
    board = pcbnew.LoadBoard(str(path))
    if args.finish_power_obstacles:
        power_cleanup=finish_power_obstacles(board,path.parent)
        (path.parent/(args.label+'-power-cleanup.json')).write_text(json.dumps(power_cleanup,indent=2)+'\n',encoding='utf8')
    for track in list(board.GetTracks()):
        if track.GetNetname() in args.rip_net:
            board.Remove(track)
            track.thisown = False
    for track in board.GetTracks():
        if track.Type() != pcbnew.PCB_VIA_T and track.GetWidth() < pcbnew.FromMM(.15):
            track.SetWidth(pcbnew.FromMM(.15))
        if track.Type() == pcbnew.PCB_VIA_T:
            track.SetFrontTentingMode(pcbnew.TENTING_MODE_TENTED)
            track.SetBackTentingMode(pcbnew.TENTING_MODE_TENTED)
    # The long value text is retained in the assembly/Fab layer.
    board.FindFootprintByReference('U302').Value().SetLayer(pcbnew.F_Fab)
    save(board, path)
    removed = []
    for iteration in range(16):
        report = native(path, args.label + '-cleanup-' + str(iteration))
        ids = {i['uuid'] for v in report['violations'] if v['type'] in {'track_dangling', 'via_dangling'} for i in v['items']}
        if not ids:
            break
        board = pcbnew.LoadBoard(str(path))
        for track in list(board.GetTracks()):
            if track.m_Uuid.AsString() in ids:
                removed.append({'uuid': track.m_Uuid.AsString(), 'net': track.GetNetname()})
                board.Remove(track)
                track.thisown = False
        save(board, path)
    report = native(path, args.label + '-pre-route')
    print('Cleanup:', Counter(v['type'] for v in report['violations']), 'unconnected:', len(report['unconnected_items']), flush=True)
    plans, failed = [], []
    if not args.cleanup_only:
        if args.allow_own_net_via:
            install_via_terminal_clearance()
        board = pcbnew.LoadBoard(str(path))
        items = {x.m_Uuid.AsString(): x for x in board.GetTracks()}
        items.update({p.m_Uuid.AsString(): p for f in board.GetFootprints() for p in f.Pads()})
        planner.EVIDENCE = path.parent
        planner.LAYERS = ['F.Cu', 'B.Cu']
        planner.STEP = .025
        # Match this project's actual Power netclass; +3V3 is Default/0.15mm.
        planner.POWER = {'POWER_GND', 'VBATT_2S_IN', '+5V', '+5V_PRE_IDEAL'}
        planner.VIA_AVOID_RADIUS = .3
        planner.VIA_PENALTY = 100.
        priority = {'CODEC_LEFT_LOP': 0, 'CODEC_RIGHT_LOP': 1, 'I2S_SDI': 2}
        def order(violation):
            item = items.get(violation['items'][0]['uuid'])
            return priority.get(item.GetNetname(), 10) if item is not None else 20
        for violation in sorted(report['unconnected_items'], key=order):
            endpoints = [items.get(i['uuid']) for i in violation['items']]
            if any(p is None for p in endpoints):
                continue  # Zone islands are connected after routing with ground stitching.
            start, end = endpoints
            net = start.GetNetname()
            if net != end.GetNetname():
                raise RuntimeError('Unconnected report net mismatch')
            startpos, endpos = position(start), position(end)
            planner.WIDTH = .6 if net in planner.POWER else (.25 if net == 'AMP_VDD_FILT' else .15)
            fb = next(p for p in board.FindFootprintByReference('U301').Pads() if p.GetNumber() == '1')
            if net == '+5V_PRE_IDEAL' and fb.m_Uuid.AsString() in {start.m_Uuid.AsString(), end.m_Uuid.AsString()}:
                # AP63205 pin 1 is the high-impedance FB sense connection.
                # This does not replace the wide inductor/output power path.
                planner.WIDTH = .25
            planner.XMIN = max(100.6, min(startpos[0], endpos[0])-7)
            planner.YMIN = max(100.6, min(startpos[1], endpos[1])-7)
            planner.XMAX = min(164.4, max(startpos[0], endpos[0])+7)
            planner.YMAX = min(129.4, max(startpos[1], endpos[1])+7)
            planner.COLS = round((planner.XMAX-planner.XMIN)/planner.STEP)+1
            planner.ROWS = round((planner.YMAX-planner.YMIN)/planner.STEP)+1
            planner.SIZE = planner.COLS*planner.ROWS
            startlayers = [i for i, layer in enumerate((pcbnew.F_Cu, pcbnew.B_Cu)) if start.IsOnLayer(layer)]
            endlayers = [i for i, layer in enumerate((pcbnew.F_Cu, pcbnew.B_Cu)) if end.IsOnLayer(layer)]
            print('Route', net, startpos, '->', endpos, flush=True)
            try:
                plan = planner.solve(obstacles(board), net, startpos, endpos, endlayers, startlayers)
                plan['via_diameter'] = .6
                add_plan(board, plan)
                plans.append(plan)
                save(board, path)
            except RuntimeError as error:
                failed.append({'net': net, 'start': startpos, 'end': endpos, 'error': str(error)})
                print('Needs further repair:', str(error), flush=True)
    final = native(path, args.label + '-final')
    record = {'removed': removed, 'plans': plans, 'failed': failed,
              'violations': dict(Counter(v['type'] for v in final['violations'])),
              'unconnected': len(final['unconnected_items']), 'parity': len(final['schematic_parity'])}
    (path.parent / (args.label + '-repair.json')).write_text(json.dumps(record, indent=2)+'\n', encoding='utf8')
    print(json.dumps({k: v for k, v in record.items() if k not in {'removed', 'plans'}}), flush=True)


if __name__ == '__main__':
    main()
