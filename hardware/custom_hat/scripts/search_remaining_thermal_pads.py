"""Check manufacturable relief gaps and orientations against actual I2S reference copper."""
import csv
import json
from pathlib import Path
import subprocess

import pcbnew
import pipeline
from add_i2c_pullups import vector


EVIDENCE=pipeline.BASE.parents[1]/'docs/references/归档扩展板贴片与层叠复核'


def covered(board,point,layer,net):
    if any(zone.IsOnLayer(layer) and zone.GetNetname()==net and zone.GetFilledPolysList(layer).Contains(point) for zone in board.Zones()):
        return True
    if any(pad.IsOnLayer(layer) and pad.GetNetname()==net and pad.GetEffectiveShape(layer).Collide(point,0)
           for footprint in board.GetFootprints() for pad in footprint.Pads()):
        return True
    return any(track.IsOnLayer(layer) and track.GetNetname()==net and track.GetEffectiveShape(layer).Collide(point,0) for track in board.GetTracks())


def main():
    EVIDENCE.mkdir(exist_ok=True)
    output=EVIDENCE/'thermal-search.json'
    if output.exists():
        raise FileExistsError('Inspect earlier results instead of replacing them')
    checkpoint=pipeline.current_checkpoint()
    source=pipeline.PRIMARY/(pipeline.STEM+'.kicad_pcb')
    baseline=pcbnew.LoadBoard(str(source))
    sample_path=pipeline.BASE.parents[1]/'docs/references/归档扩展板音频芯片焊盘/padstack-after-plane-samples.csv'
    with sample_path.open(encoding='utf-8',newline='') as stream:
        rows=list(csv.DictReader(stream))
    outcomes=[]
    for reference,layer_name in (('C310','B.Cu'),('C305','F.Cu')):
        target=next(pad for pad in baseline.FindFootprintByReference(reference).Pads() if pad.GetNumber()=='2')
        bounds=target.GetBoundingBox()
        points=[]
        for row in rows:
            if row['source_layer']==layer_name:
                continue
            point=vector((float(row['x_mm']),float(row['y_mm'])))
            if not (bounds.GetLeft()-500000<=point.x<=bounds.GetRight()+500000 and bounds.GetTop()-500000<=point.y<=bounds.GetBottom()+500000):
                continue
            if covered(baseline,point,baseline.GetLayerID(layer_name),'POWER_GND'):
                points.append((row,point))
        for gap in (.1,.15,.2):
            for angle in (0,45,90,135):
                work=pipeline.prepare(pipeline.PRIMARY)
                path=work/(pipeline.STEM+'.kicad_pcb')
                board=pcbnew.LoadBoard(str(path))
                pad=next(pad for pad in board.FindFootprintByReference(reference).Pads() if pad.GetNumber()=='2')
                pad.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_THERMAL)
                pad.SetLocalThermalSpokeWidthOverride(pcbnew.FromMM(.25))
                pad.SetThermalGap(pcbnew.FromMM(gap))
                pad.SetThermalSpokeAngle(pcbnew.EDA_ANGLE(angle,pcbnew.DEGREES_T))
                pcbnew.SaveBoard(str(path),board)
                report=work.parent/'thermal-search-drc.json'
                command=[pipeline.find_cli(),'pcb','drc','--format','json','--severity-all','--schematic-parity','--refill-zones','--save-board','--output',report,path]
                result=subprocess.run(list(map(str,command)),capture_output=True,encoding='utf-8',errors='replace',timeout=180)
                (work.parent/'thermal-search.log').write_text(result.stdout+result.stderr,encoding='utf-8');result.check_returncode()
                drc=json.loads(report.read_text(encoding='utf-8'))
                board=pcbnew.LoadBoard(str(path))
                missing=[row for row,point in points if not covered(board,point,board.GetLayerID(layer_name),'POWER_GND')]
                row={'reference':reference,'gap_mm':gap,'spoke_mm':.25,'angle':angle,'project':str(work),'pcb_sha256':pipeline.digest(path),
                     'violations':len(drc['violations']),'unconnected':len(drc['unconnected_items']),'parity':len(drc['schematic_parity']),
                     'baseline_points':len(points),'actual_copper_lost_samples':len(missing),'actual_lost_represented_mm':sum(float(item['represented_mm']) for item in missing)}
                row['passes_local_screen']=not any(row[key] for key in ('violations','unconnected','parity','actual_copper_lost_samples'))
                outcomes.append(row)
                pipeline.write_json(output,{'source_pcb_sha256':checkpoint['pcb_sha256'],'sample_file':str(sample_path),'outcomes':outcomes,
                    'limits':'Local reference coverage uses pads/tracks/filled zones union at existing I2S samples; no HF impedance or actual solder-temperature claim','promoted':False})
                print(json.dumps(row),flush=True)
        print(reference+' search complete',flush=True)
    if pipeline.fingerprints(pipeline.PRIMARY)!=checkpoint['design_hashes']:
        raise RuntimeError('Source changed')


if __name__=='__main__':main()
