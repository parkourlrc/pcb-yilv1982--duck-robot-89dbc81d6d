"""Try outward-facing THT connectors while preserving every drilled pin coordinate."""
import argparse
import json
import math
from pathlib import Path

import pcbnew
import pipeline
from verify_release_metadata import snapshot
from complete_polarity_markers import rectangle
from add_i2c_pullups import vector


EVIDENCE = pipeline.BASE.parents[1]/'docs/references/归档扩展板机械适配复核'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--only-j301',action='store_true')
    arguments=parser.parse_args()
    checkpoint=pipeline.current_checkpoint()
    work=pipeline.prepare(pipeline.PRIMARY)
    path=work/(pipeline.STEM+'.kicad_pcb')
    before=snapshot(path)
    board=pcbnew.LoadBoard(str(path))
    changes=[]
    for reference in (['J301'] if arguments.only_j301 else ['J301','J401','J402','J403','J802']):
        footprint=board.FindFootprintByReference(reference)
        original={pad.GetNumber():list(pad.GetPosition()) for pad in footprint.Pads()}
        spread_x=max(point[0] for point in original.values())-min(point[0] for point in original.values())
        spread_y=max(point[1] for point in original.values())-min(point[1] for point in original.values())
        flip_left_right=spread_x>spread_y
        footprint.Flip(footprint.GetPosition(),flip_left_right)
        final={pad.GetNumber():list(pad.GetPosition()) for pad in footprint.Pads()}
        if original!=final or footprint.GetLayer()!=pcbnew.B_Cu:
            raise RuntimeError('Pin positions changed: '+reference)
        changes.append({'reference':reference,'to':'B.Cu','flip_left_right':flip_left_right,'pin_positions_unchanged':True})
    if arguments.only_j301:
        body_shapes=[]
        pad_shapes=[]
        silk_items=[]
        for footprint in board.GetFootprints():
            if footprint.GetLayer()==pcbnew.B_Cu:
                bounds=[item.GetBoundingBox() for item in footprint.GraphicalItems() if item.GetLayer()==pcbnew.B_Fab and item.Type()==pcbnew.PCB_SHAPE_T]
                if bounds:
                    box=[min(item.GetLeft() for item in bounds),min(item.GetTop() for item in bounds),max(item.GetRight() for item in bounds),max(item.GetBottom() for item in bounds)]
                    body_shapes.append(rectangle([pcbnew.ToMM(value) for value in box]))
            pad_shapes.extend(pad.GetEffectiveShape(pcbnew.B_Cu) for pad in footprint.Pads() if pad.IsOnLayer(pcbnew.B_Cu))
            silk_items.extend(item for item in [*footprint.GraphicalItems(),footprint.Reference(),footprint.Value()] if item.GetLayer()==pcbnew.B_SilkS and (not hasattr(item,'IsVisible') or item.IsVisible()))
        labels=[]
        for drawing in board.GetDrawings():
            if drawing.m_Uuid.AsString() in {'c9072b7c-569b-444e-a0ef-b58dfda363f1','2646fb3c-762d-4950-8661-bf6aa4b43575','c77d9b57-9a2b-4d2a-9220-f2f2c5d8023f'}:
                drawing.SetLayer(pcbnew.B_SilkS)
                drawing.SetMirrored(True)
                if drawing.GetText() in {'GND','2S+'}:
                    drawing.SetText('2:GND' if drawing.GetText()=='GND' else '1:2S+')
                    labels.append(drawing)
        silk_items.extend(item for item in board.GetDrawings() if item.GetLayer()==pcbnew.B_SilkS)
        for label in labels:
            anchor=[pcbnew.ToMM(value) for value in label.GetPosition()]
            points=[(anchor[0]+offset_x*.1,anchor[1]+offset_y*.1) for offset_x in range(-50,71) for offset_y in range(-30,41)]
            points.sort(key=lambda point:math.dist(point,anchor))
            placed=False
            for point in points:
                label.SetPosition(vector(point))
                box=label.GetBoundingBox()
                if box.GetLeft()<100300000 or box.GetRight()>164700000 or box.GetTop()<100300000 or box.GetBottom()>129700000:
                    continue
                shape=label.GetEffectiveShape()
                if any(body.Collide(shape,50000) for body in body_shapes) or any(pad.Collide(shape,300000) for pad in pad_shapes):
                    continue
                if any(item.m_Uuid!=label.m_Uuid and item.GetEffectiveShape().Collide(shape,150000) for item in silk_items):
                    continue
                placed=True
                break
            if not placed:
                raise RuntimeError('No clear numbered power label location')
    pcbnew.SaveBoard(str(path),board)
    after=snapshot(path)
    if before['nets']!=after['nets'] or before['tracks']!=after['tracks']:
        raise RuntimeError('Nets or tracks changed')
    reports,summary=pipeline.check(work)
    result={'source_pcb_sha256':checkpoint['pcb_sha256'],'project':str(work),'changes':changes,
        'native_status':summary['status'],'summary':str(reports/'summary.json'),'drc':summary['drc'],'promoted':False,
        'limits':(['Only J301 moved, numbered power labels also moved toB; other connectors retain their assembly side',
                   'Reference host spacing, wiring and full assembly remain subject to the mechanical study'] if arguments.only_j301 else
                  ['Initial all-header candidate: board-level direction labels have not yet been moved',
                   'Courtyard and opposite-side bodies must pass before adoption'])}
    pipeline.write_json(EVIDENCE/('outward-power-candidate.json' if arguments.only_j301 else 'outward-headers-candidate.json'),result)
    print(json.dumps(result))


if __name__=='__main__':
    main()
