"""Search nearby C310 positions with native DRC and explicit solder-pad/via separation."""
import argparse
import csv
import json
import math
from pathlib import Path
import subprocess

import pcbnew
import pipeline
from add_i2c_pullups import vector
from search_remaining_thermal_pads import covered


EVIDENCE = pipeline.BASE.parents[1] / 'docs/references/归档扩展板贴片与层叠复核'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--south', action='store_true')
    arguments = parser.parse_args()
    checkpoint = pipeline.current_checkpoint()
    original = pcbnew.LoadBoard(str(pipeline.PRIMARY / (pipeline.STEM + '.kicad_pcb')))
    with (EVIDENCE / 'relocate-after-plane-samples.csv').open(encoding='utf-8', newline='') as stream:
        sample_rows = list(csv.DictReader(stream))
    samples = []
    for row in sample_rows:
        if row['source_layer'] == 'B.Cu':
            continue
        x_mm, y_mm = float(row['x_mm']), float(row['y_mm'])
        if 145 < x_mm < 150 and 110 < y_mm < 114:
            point = vector((x_mm, y_mm))
            if covered(original, point, pcbnew.B_Cu, 'POWER_GND'):
                samples.append((row, point))
    results = []
    candidates = [(147.32,111.8),(147.32,111.95),(147.12,111.85),(147.5,111.8),
                  (146.85,111.8),(147.65,111.8),(147.0,113.35),(147.0,113.6),
                  (148.5,113.5),(148.6,111.7),(147.72,113.8),(146.65,113.3)]
    if arguments.south:
        candidates = [(147.72,114.1),(147.72,114.25),(147.85,114.1),(147.9,114.3),
                      (147.5,114.1),(147.6,114.4),(147.3,114.5),(148,114.6)]
    output = EVIDENCE / ('c310-clearance-search-south.json' if arguments.south else 'c310-clearance-search.json')
    if output.exists():
        raise FileExistsError(output)
    for point_mm in candidates:
        work = pipeline.prepare(pipeline.PRIMARY)
        path = work / (pipeline.STEM + '.kicad_pcb')
        board = pcbnew.LoadBoard(str(path))
        footprint = board.FindFootprintByReference('C310')
        signal = next(pad_item for pad_item in footprint.Pads() if pad_item.GetNumber() == '1')
        old = signal.GetPosition()
        footprint.SetPosition(vector(point_mm))
        new = signal.GetPosition()
        for item in board.GetTracks():
            if item.Type() == pcbnew.PCB_VIA_T or item.GetNetname() != 'CODEC_RST':
                continue
            if item.GetStart() == old:
                item.SetStart(new)
            if item.GetEnd() == old:
                item.SetEnd(new)
        clearances = []
        for pad in footprint.Pads():
            box = pad.GetBoundingBox()
            for via in board.GetTracks():
                if via.Type() != pcbnew.PCB_VIA_T:
                    continue
                position = via.GetPosition()
                dx = max(box.GetLeft()-position.x, position.x-box.GetRight(), 0)
                dy = max(box.GetTop()-position.y, position.y-box.GetBottom(), 0)
                clearance = (math.hypot(dx,dy) - via.GetWidth(pcbnew.B_Cu)/2)/1e6
                if clearance < 1:
                    clearances.append({'pad':pad.GetNumber(),'via':via.m_Uuid.AsString(),'copper_gap_lower_bound_mm':clearance})
        minimum = min(row['copper_gap_lower_bound_mm'] for row in clearances)
        record = {'position_mm':point_mm,'project':str(work),'minimum_via_copper_gap_mm':minimum,'near_vias':clearances}
        if minimum < .15:
            record.update(accepted=False,reason='Less than0.15mm solder-land/via-copper gap')
        else:
            pcbnew.SaveBoard(str(path),board)
            report = work.parent/'c310-search-drc.json'
            run = subprocess.run(list(map(str,[pipeline.find_cli(),'pcb','drc','--severity-all','--format','json','--schematic-parity','--refill-zones','--save-board','--output',report,path])),capture_output=True,timeout=180)
            (work.parent/'c310-search.log').write_bytes(run.stdout+run.stderr)
            run.check_returncode()
            drc = json.loads(report.read_text(encoding='utf-8'))
            board = pcbnew.LoadBoard(str(path))
            loss = [row for row,point in samples if not covered(board,point,pcbnew.B_Cu,'POWER_GND')]
            record.update(violations=len(drc['violations']),unconnected=len(drc['unconnected_items']),parity=len(drc['schematic_parity']),
                          lost_reference_samples=len(loss),lost_represented_mm=sum(float(row['represented_mm']) for row in loss))
            record['accepted'] = not any(record[key] for key in ('violations','unconnected','parity','lost_reference_samples'))
        results.append(record)
        pipeline.write_json(output,{'baseline':checkpoint['pcb_sha256'],'samples':len(samples),'candidates':results})
        print(json.dumps({key:value for key,value in record.items() if key != 'near_vias'}),flush=True)
        if record['accepted']:
            break


if __name__ == '__main__':
    main()
