"""Place explicit pin-one and cathode marks outside component bodies and solder lands."""
import json
import math

import pcbnew
import pipeline
from add_i2c_pullups import vector


EVIDENCE = pipeline.BASE.parents[1] / 'docs/references/归档扩展板极性与装配资料'


def bounds_mm(box):
    return [pcbnew.ToMM(value) for value in (box.GetLeft(), box.GetTop(), box.GetRight(), box.GetBottom())]


def rectangle(bounds):
    left, top, right, bottom = [pcbnew.FromMM(value) for value in bounds]
    return pcbnew.SHAPE_RECT(left, top, right-left, bottom-top)


def main():
    checkpoint = pipeline.current_checkpoint()
    work = pipeline.prepare(pipeline.PRIMARY)
    path = work / (pipeline.STEM + '.kicad_pcb')
    board = pcbnew.LoadBoard(str(path))
    bodies, pads, existing_silk = [], [], []
    changed_texts = []
    for footprint in board.GetFootprints():
        side = footprint.GetLayer()
        fab = pcbnew.F_Fab if side == pcbnew.F_Cu else pcbnew.B_Fab
        outlines = [item.GetBoundingBox() for item in footprint.GraphicalItems() if item.GetLayer() == fab and item.Type() == pcbnew.PCB_SHAPE_T]
        if outlines:
            bounds = [min(box.GetLeft() for box in outlines),min(box.GetTop() for box in outlines),
                      max(box.GetRight() for box in outlines),max(box.GetBottom() for box in outlines)]
            bodies.append((footprint.GetReference(),side,rectangle([pcbnew.ToMM(value) for value in bounds])))
        for pad in footprint.Pads():
            for copper, silk in ((pcbnew.F_Cu,pcbnew.F_SilkS),(pcbnew.B_Cu,pcbnew.B_SilkS)):
                if pad.IsOnLayer(copper):
                    pads.append((footprint.GetReference(),pad.GetNumber(),silk,pad.GetEffectiveShape(copper)))
        for item in [*footprint.GraphicalItems(),footprint.Reference(),footprint.Value()]:
            if item.GetLayer() not in (pcbnew.F_SilkS,pcbnew.B_SilkS):
                continue
            if hasattr(item,'IsVisible') and not item.IsVisible():
                continue
            existing_silk.append(item)
    for item in board.GetDrawings():
        if item.GetLayer() in (pcbnew.F_SilkS,pcbnew.B_SilkS):
            existing_silk.append(item)
    diode = next(item for item in board.GetDrawings() if item.m_Uuid.AsString() == '5f5103a9-38f9-4bb7-8e3f-9856e70ea2f2')
    diode.SetTextSize(vector((1.27,1.27)))
    changed_texts.append({'action':'enlarge_D301_K','uuid':diode.m_Uuid.AsString(),'size_mm':1.27,'stroke_mm':.15})
    targets = ['D301','U301','U501','U701','U702','U801','U802','U803',
               'J101','J301','J401','J402','J403','J502','J504','J505','J506','J802']
    marks = []
    for reference in targets:
        print('Placing '+reference,flush=True)
        footprint = board.FindFootprintByReference(reference)
        pad_one = next(pad for pad in footprint.Pads() if pad.GetNumber() == '1')
        side = footprint.GetLayer()
        silk = pcbnew.F_SilkS if side == pcbnew.F_Cu else pcbnew.B_SilkS
        diameter = .8 if reference in {'U801','U802'} else 1.0
        if reference == 'D301':
            item = diode
        elif reference.startswith('U'):
            item = pcbnew.PCB_SHAPE(board)
            item.SetShape(pcbnew.SHAPE_T_CIRCLE)
            item.SetFilled(True)
            item.SetWidth(0)
            item.SetLayer(silk)
        else:
            item = pcbnew.PCB_TEXT(board)
            item.SetText('1')
            item.SetTextSize(vector((1,1)))
            item.SetTextThickness(pcbnew.FromMM(.15))
            item.SetLayer(silk)
            item.SetMirrored(side == pcbnew.B_Cu)
        anchor = [pcbnew.ToMM(value) for value in pad_one.GetPosition()]
        candidates = [(round(anchor[0]+horizontal*.1,4),round(anchor[1]+vertical*.1,4))
                      for horizontal in range(-36,37) for vertical in range(-36,37)]
        candidates.sort(key=lambda point:(math.dist(point,anchor),point))
        if reference == 'U301':
            candidates.insert(0,(122.7,110.85))
        if reference == 'D301':
            candidates = [tuple(pcbnew.ToMM(value) for value in item.GetPosition())]
        rejection_counts = {'edge':0,'body':0,'pad':0,'silk':0,'ambiguous':0}
        accepted = None
        for center in candidates:
            if reference.startswith('U'):
                item.SetStart(vector(center))
                item.SetEnd(vector((center[0]+diameter/2,center[1])))
            else:
                item.SetPosition(vector(center))
            bounds = bounds_mm(item.GetBoundingBox())
            if bounds[0]<100.3 or bounds[1]<100.3 or bounds[2]>164.7 or bounds[3]>129.7:
                rejection_counts['edge'] += 1
                continue
            shape = item.GetEffectiveShape()
            if any(body_side == side and body.Collide(shape,pcbnew.FromMM(.05)) for _,body_side,body in bodies):
                rejection_counts['body'] += 1
                continue
            if any(pad_side == silk and pad_shape.Collide(shape,pcbnew.FromMM(.3)) for _,_,pad_side,pad_shape in pads):
                rejection_counts['pad'] += 1
                continue
            if any(other.m_Uuid.AsString()!=item.m_Uuid.AsString() and other.GetLayer()==silk and other.GetEffectiveShape().Collide(shape,pcbnew.FromMM(.15)) for other in existing_silk):
                rejection_counts['silk'] += 1
                continue
            nearest = sorted((math.dist(center,[pcbnew.ToMM(value) for value in pad.GetPosition()]),pad.GetNumber())
                             for pad in footprint.Pads() if pad.GetNumber() and pad.GetNumber().isdigit())
            if nearest[0][1] != '1':
                rejection_counts['ambiguous'] += 1
                continue
            accepted = {'reference':reference,'uuid':item.m_Uuid.AsString(),'layer':board.GetLayerName(silk),
                        'center_mm':center,'bbox_mm':bounds,'anchor_pad':'1','nearest_numbered_pad':'1',
                        'body_clearance_screen_mm':.05,'all_solder_lands_clearance_screen_mm':.3,
                        'diameter_mm':diameter if reference.startswith('U') else None,
                        'text':item.GetText() if hasattr(item,'GetText') else None,
                        'rejection_counts':rejection_counts}
            break
        if not accepted:
            pipeline.write_json(EVIDENCE/'marker-placement-failure.json',{'reference':reference,'rejects':rejection_counts,'project':str(work),'placed':marks})
            raise RuntimeError('No clear polarity mark location: '+reference)
        if reference != 'D301':
            board.Add(item)
        existing_silk.append(item)
        marks.append(accepted)
    pcbnew.SaveBoard(str(path),board)
    reports,summary = pipeline.check(work)
    result = {'source_pcb_sha256':checkpoint['pcb_sha256'],'project':str(work),'marks':marks,'changed_texts':changed_texts,
              'summary':str(reports/'summary.json'),'status':summary['status'],'drc':summary['drc'],'promoted':False,
              'source_unchanged':pipeline.fingerprints(pipeline.PRIMARY)==checkpoint['design_hashes']}
    pipeline.write_json(EVIDENCE/'candidate.json',result)
    print(json.dumps(result,ensure_ascii=False))


if __name__ == '__main__':
    main()
