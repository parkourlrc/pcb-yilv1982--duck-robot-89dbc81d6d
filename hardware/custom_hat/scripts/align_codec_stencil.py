"""Align selected TI exposed-pad and stencil details in an isolated complete project."""
import argparse
import json
from pathlib import Path

import pcbnew
import pipeline
from add_i2c_pullups import vector
from repair_release_metadata import properties, replace_children, set_property


EVIDENCE=pipeline.BASE.parents[1]/'docs/references/归档扩展板钢网与裸露焊盘'
LIBRARY_NAMES={'U701':'TI_RHB0032E_AIC3104_EP345','U702':'TI_NDP0003B_LP38691_PasteGrid'}
DESCRIPTIONS={
    'U701':'TLV320AIC3104 RHB0032E: TI4223442B p101-102 EP3.45mm R0.05 and four1.49mm paste windows at+/-0.845; original0.875x0.25 signal lands retained; generic3D body visual only',
    'U702':'LP38691 NDP0003B: TI4219870A p36 sixteen1.15x1.12 paste windows on1.35x1.32 pitch; center6.665mm from lead axis; no optional-middle-lead paste; original copper and generic3D body retained'
}


def save_library(board, reference, directory):
    footprint=board.FindFootprintByReference(reference)
    temporary=pcbnew.BOARD()
    duplicate=pcbnew.Cast_to_FOOTPRINT(footprint.Duplicate(False))
    temporary.Add(duplicate)
    if duplicate.GetLayer()==pcbnew.B_Cu:
        duplicate.Flip(duplicate.GetPosition(),True)
    duplicate.SetOrientationDegrees(0)
    duplicate.SetPosition(vector((0,0)))
    pcbnew.FootprintSave(str(directory),duplicate)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--attempt',required=True)
    parser.add_argument('--codec-only',action='store_true')
    args=parser.parse_args()
    folder=EVIDENCE/args.attempt
    folder.mkdir(exist_ok=False)
    checkpoint=pipeline.current_checkpoint()
    work=pipeline.prepare(pipeline.PRIMARY)
    path=work/(pipeline.STEM+'.kicad_pcb')
    board=pcbnew.LoadBoard(str(path))
    for zone in board.Zones():
        zone.UnFill()
    codec=board.FindFootprintByReference('U701')
    codec.SetFPID(pcbnew.LIB_ID('duck',LIBRARY_NAMES['U701']))
    codec.SetLibDescription(DESCRIPTIONS['U701'])
    ep=next(pad for pad in codec.Pads() if pad.GetNumber()=='33')
    ep.SetSize(vector((3.45,3.45)))
    ep.SetShape(pcbnew.PAD_SHAPE_ROUNDRECT)
    ep.SetRoundRectRadiusRatio(pcbnew.B_Cu,.05/3.45)
    center=codec.GetPosition()
    paste_pads=[pad for pad in codec.Pads() if not pad.GetNumber() and pad.IsOnLayer(pcbnew.B_Paste)]
    if len(paste_pads)!=4:
        raise RuntimeError('Unexpected codec stencil')
    for pad in paste_pads:
        offset=pad.GetPosition()-center
        pad.SetPosition(center+vector((-.845 if offset.x<0 else .845,-.845 if offset.y<0 else .845)))
        pad.SetSize(vector((1.49,1.49)))
        pad.SetRoundRectCornerRadius(pcbnew.FromMM(.05))
    changed={'U701'}
    if not args.codec_only:
        ldo=board.FindFootprintByReference('U702')
        ldo.SetFPID(pcbnew.LIB_ID('duck',LIBRARY_NAMES['U702']))
        ldo.SetLibDescription(DESCRIPTIONS['U702'])
        lead_one=next(pad for pad in ldo.Pads() if pad.GetNumber()=='1').GetPosition()
        lead_three=next(pad for pad in ldo.Pads() if pad.GetNumber()=='3').GetPosition()
        ldo_center=pcbnew.VECTOR2I(lead_one.x+pcbnew.FromMM(4.38+2.285),(lead_one.y+lead_three.y)//2)
        old_paste=[pad for pad in ldo.Pads() if not pad.GetNumber() and pad.IsOnLayer(pcbnew.B_Paste)]
        if len(old_paste)!=4:
            raise RuntimeError('Unexpected LDO stencil')
        for pad in ldo.Pads():
            if pad.GetNumber()=='2' and pad.GetSize().x<3000000:
                layers=pad.GetLayerSet()
                layers.RemoveLayer(pcbnew.B_Paste)
                pad.SetLayerSet(layers)
        for column in range(4):
            for row in range(4):
                index=column*4+row
                pad=old_paste[index] if index<4 else pcbnew.PAD(ldo)
                pad.SetNumber('')
                pad.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
                pad.SetShape(pcbnew.PAD_SHAPE_ROUNDRECT)
                pad.SetSize(vector((1.15,1.12)))
                pad.SetRoundRectCornerRadius(pcbnew.FromMM(.05))
                layers=pcbnew.LSET()
                layers.AddLayer(pcbnew.B_Paste)
                pad.SetLayerSet(layers)
                pad.SetPosition(ldo_center+vector(((column-1.5)*1.35,(row-1.5)*1.32)))
                if index>=4:
                    ldo.Add(pad)
        changed.add('U702')
    pcbnew.SaveBoard(str(path),board)
    for reference in changed:
        save_library(board,reference,work/'duck.pretty')
    def update_symbol(node):
        reference=properties(node).get('Reference')
        if reference not in changed:
            return False
        set_property(node,'Footprint','duck:'+LIBRARY_NAMES[reference])
        return True
    for schematic in work.glob('*.kicad_sch'):
        content=schematic.read_text(encoding='utf-8')
        updated=replace_children(content,'symbol',update_symbol)
        if updated!=content:
            schematic.write_text(updated,encoding='utf-8')
    reports,summary=pipeline.check(work)
    record={'baseline':checkpoint['pcb_sha256'],'project':str(work),'changed_references':sorted(changed),
        'summary':str(reports/'summary.json'),'native_status':summary['status'],'drc':summary['drc'],'promoted':False}
    pipeline.write_json(folder/'candidate.json',record)
    print(json.dumps(record))


if __name__=='__main__':
    main()
