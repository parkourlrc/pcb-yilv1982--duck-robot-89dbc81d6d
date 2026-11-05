"""Reserve separate codec escape vias before routing the clock/data trunks."""
import argparse
import json
from pathlib import Path
import shutil

import pcbnew

from add_i2c_pullups import obstacles, position, vector
import plan_i2s_sdo as planner
from repair_rev_b_solder_routes import add_plan, save, native, install_via_terminal_clearance


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', type=Path)
    parser.add_argument('--label',default='clock-fanout')
    parser.add_argument('--back-trunks',action='store_true')
    args = parser.parse_args()
    path = args.directory.resolve()/'custom_hat_rev_b.kicad_pcb'
    candidate_root=Path(__file__).resolve().parents[3]/'docs/references/扩展板乙版降本'
    if not path.is_relative_to(candidate_root):raise RuntimeError('Only use this mutator on an isolated cost-study candidate')
    backup = path.parent/('before-'+args.label+'.kicad_pcb')
    if backup.exists():
        raise FileExistsError(backup)
    shutil.copy2(path, backup)
    board = pcbnew.LoadBoard(str(path))
    requests = [('1','AUDIO_MCLK',(135.1,112.65),'Y701','3'),
                ('2','I2S_BCLK',(135.1,113.45),'J101','12'),
                ('3','I2S_LRCK',(135.1,114.25),'J101','35'),
                ('4','I2S_SDO',(135.1,115.05),'J101','40'),
                ('5','I2S_SDI',(135.1,115.85),'J101','38')]
    names = {row[1] for row in requests}
    for t in list(board.GetTracks()):
        if t.GetNetname() in names:
            board.Remove(t)
            t.thisown = False
    initial_ids = {t.m_Uuid.AsString() for t in board.GetTracks()}
    fanouts = []
    codec = board.FindFootprintByReference('U701')
    for pin,net,via,ref,ep in requests:
        pad = next(p for p in codec.Pads() if p.GetNumber()==pin)
        assert pad.GetNetname()==net
        xy = position(pad)
        points = [[*xy,0],[135.75,xy[1],0],[*via,0],[*via,1]]
        plan = {'net':net,'width':.15,'via_diameter':.6,'points':points}
        add_plan(board,plan)
        fanouts.append(plan)
    save(board,path)
    report = native(path,args.label+'-initial')
    colliding = []
    for v in report['violations']:
        if v['type'] in {'shorting_items','clearance','hole_clearance','hole_to_hole','solder_mask_bridge'}:
            old_ids = {i['uuid'] for i in v['items']} & initial_ids
            if not old_ids:
                raise RuntimeError('Fanout collision without removable prior track: '+str(v))
            colliding.extend(old_ids)
    for t in list(board.GetTracks()):
        if t.m_Uuid.AsString() in colliding:
            board.Remove(t)
            t.thisown = False
    save(board,path)
    planner.EVIDENCE = path.parent
    planner.LAYERS = ['F.Cu','B.Cu']
    planner.POWER = {'POWER_GND','VBATT_2S_IN','+5V','+5V_PRE_IDEAL'}
    planner.STEP,planner.WIDTH,planner.VIA_AVOID_RADIUS,planner.VIA_PENALTY = .025,.15,.3,100.
    planner.XMIN,planner.YMIN,planner.XMAX,planner.YMAX = 119,100.6,163.8,124
    planner.COLS = round((planner.XMAX-planner.XMIN)/planner.STEP)+1
    planner.ROWS = round((planner.YMAX-planner.YMIN)/planner.STEP)+1
    planner.SIZE = planner.COLS*planner.ROWS
    install_via_terminal_clearance()
    routes,failed = [],[]
    for pin,net,via,ref,ep in requests:
        pad = next(p for p in board.FindFootprintByReference(ref).Pads() if p.GetNumber()==ep)
        assert pad.GetNetname()==net
        print('Clock trunk:',net,flush=True)
        try:
            back_only = args.back_trunks and ref=='J101'
            planner.LAYERS = ['B.Cu'] if back_only else ['F.Cu','B.Cu']
            plan = planner.solve(obstacles(board),net,via,position(pad),[0] if back_only or ref!='J101' else [0,1],0 if back_only else 1)
            if back_only:
                plan['points'] = [[x,y,1] for x,y,_ in plan['points']]
            plan['via_diameter']=.6
            add_plan(board,plan)
            routes.append(plan)
            save(board,path)
        except RuntimeError as error:
            failed.append({'net':net,'error':str(error)})
            print('Needs repair:',error,flush=True)
    result = native(path,args.label+'-final')
    record = {'fanouts':fanouts,'routes':routes,'removed_prior_tracks':colliding,'failed':failed,
              'violations':len(result['violations']),'unconnected':len(result['unconnected_items'])}
    (path.parent/(args.label+'.json')).write_text(json.dumps(record,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in record.items() if k not in {'fanouts','routes','removed_prior_tracks'}}),flush=True)


if __name__ == '__main__':
    main()
