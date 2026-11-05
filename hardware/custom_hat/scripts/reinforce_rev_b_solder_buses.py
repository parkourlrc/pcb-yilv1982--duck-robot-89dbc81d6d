"""Restore explicit wide power paths after connector relocation; candidate only."""
import argparse
import json
from pathlib import Path
import shutil

import pcbnew

from add_i2c_pullups import obstacles, position
import plan_i2s_sdo as planner
from repair_rev_b_solder_routes import add_plan, save, native


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', type=Path)
    parser.add_argument('--label', default='power-r1')
    parser.add_argument('--only', choices=['VBATT_2S_IN','POWER_GND','+5V'])
    args = parser.parse_args()
    path = args.directory.resolve() / 'custom_hat_rev_b.kicad_pcb'
    assert '扩展板乙版降本' in str(path)
    backup = path.parent / ('before-'+args.label+'.kicad_pcb')
    if backup.exists():
        raise FileExistsError(backup)
    shutil.copy2(path, backup)
    board = pcbnew.LoadBoard(str(path))
    planner.EVIDENCE = path.parent
    planner.STEP = .05
    planner.POWER = {'POWER_GND', 'VBATT_2S_IN', '+5V', '+5V_PRE_IDEAL'}
    planner.VIA_PENALTY = 160
    planner.XMIN, planner.YMIN, planner.XMAX, planner.YMAX = 100.7, 100.7, 133, 128.9
    planner.COLS = round((planner.XMAX-planner.XMIN)/planner.STEP)+1
    planner.ROWS = round((planner.YMAX-planner.YMIN)/planner.STEP)+1
    planner.SIZE = planner.COLS*planner.ROWS
    plans, failures = [], []
    requests = [('VBATT_2S_IN', 'J401', '2', 'J402', '2', 1.6, ['B.Cu'], .6),
                ('POWER_GND', 'J401', '1', 'J402', '1', 1.6, ['F.Cu'], .6),
                ('+5V', 'Q301', '3', 'J101', '2', 1.0, ['F.Cu', 'B.Cu'], 1.0)]
    for net, ar, ap, br, bp, width, layers, via in requests:
        if args.only and net != args.only:
            continue
        start = next(p for p in board.FindFootprintByReference(ar).Pads() if p.GetNumber() == ap)
        end = next(p for p in board.FindFootprintByReference(br).Pads() if p.GetNumber() == bp)
        assert start.GetNetname() == end.GetNetname() == net
        planner.LAYERS, planner.WIDTH, planner.VIA_AVOID_RADIUS = layers, width, via/2
        print('Wide bus:', net, flush=True)
        try:
            plan = planner.solve(obstacles(board), net, position(start), position(end), [0] if len(layers)==1 else [0,1], 0)
            if layers == ['B.Cu']:
                plan['points'] = [[x,y,1] for x,y,_ in plan['points']]
            plan['via_diameter'] = via
            plan['endpoints'] = [ar+'.'+ap, br+'.'+bp]
            add_plan(board, plan)
            plans.append(plan)
            save(board, path)
        except RuntimeError as error:
            failures.append({'net': net, 'error': str(error)})
            print('Needs repair:', error, flush=True)
    report = native(path, args.label+'-drc')
    record = {'plans': plans, 'failures': failures, 'unconnected': len(report['unconnected_items']),
              'violations': len(report['violations']), 'not_a_current_rating': True}
    (path.parent/(args.label+'.json')).write_text(json.dumps(record,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in record.items() if k != 'plans'}),flush=True)


if __name__ == '__main__':
    main()
