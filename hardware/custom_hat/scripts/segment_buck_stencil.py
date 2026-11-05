"""Select a four-window U301 exposed-pad stencil without changing copper or nets."""
import json
from pathlib import Path

import pcbnew
import pipeline
from add_i2c_pullups import vector
from align_codec_stencil import save_library
from repair_release_metadata import properties,replace_children,set_property


EVIDENCE=pipeline.BASE.parents[1]/'docs/references/归档扩展板钢网分窗审查'
LIBRARY_NAME='SO8EP_AP64350_Paste4_Project'
DESCRIPTION='AP64350 SO8EP: Diodes copper lands retained; project-selected four1.45x1.10mm R0.05 paste windows at+/-0.825,+/-0.65;69.63pct coverage; not a Diodes-qualified stencil or measured solder result'


def main():
    if (EVIDENCE/'candidate.json').exists():
        raise FileExistsError('Review existing candidate before generating another')
    checkpoint=pipeline.current_checkpoint()
    work=pipeline.prepare(pipeline.PRIMARY)
    path=work/(pipeline.STEM+'.kicad_pcb')
    board=pcbnew.LoadBoard(str(path))
    footprint=board.FindFootprintByReference('U301')
    center=footprint.GetPosition()
    thermal=next(pad for pad in footprint.Pads() if pad.GetNumber()=='9')
    if list(thermal.GetSize())!=[3502000,2613000] or not thermal.IsOnLayer(pcbnew.F_Paste):
        raise RuntimeError('Unexpected original U301 thermal land')
    footprint.SetFPID(pcbnew.LIB_ID('duck',LIBRARY_NAME))
    footprint.SetLibDescription(DESCRIPTION)
    layers=thermal.GetLayerSet()
    layers.RemoveLayer(pcbnew.F_Paste)
    thermal.SetLayerSet(layers)
    windows=[]
    for x_offset in [-.825,.825]:
        for y_offset in [-.65,.65]:
            pad=pcbnew.PAD(footprint)
            pad.SetNumber('')
            pad.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
            pad.SetShape(pcbnew.PAD_SHAPE_ROUNDRECT)
            pad.SetSize(vector((1.45,1.10)))
            pad.SetRoundRectRadiusRatio(pcbnew.F_Cu,.05/1.10)
            paste_layers=pcbnew.LSET()
            paste_layers.AddLayer(pcbnew.F_Paste)
            pad.SetLayerSet(paste_layers)
            pad.SetPosition(center+vector((x_offset,y_offset)))
            footprint.Add(pad)
            windows.append({'uuid':pad.m_Uuid.AsString(),'position_mm':[pcbnew.ToMM(value) for value in pad.GetPosition()],'size_mm':[1.45,1.10],'corner_radius_mm':.05})
    pcbnew.SaveBoard(str(path),board)
    save_library(board,'U301',work/'duck.pretty')
    def update(node):
        if properties(node).get('Reference')!='U301':
            return False
        set_property(node,'Footprint','duck:'+LIBRARY_NAME)
        return True
    changed_schematics=[]
    for schematic in work.glob('*.kicad_sch'):
        content=schematic.read_text(encoding='utf-8')
        updated=replace_children(content,'symbol',update)
        if updated!=content:
            schematic.write_text(updated,encoding='utf-8')
            changed_schematics.append(schematic.name)
    reports,summary=pipeline.check(work)
    result={'baseline':checkpoint['pcb_sha256'],'project':str(work),'windows':windows,'changed_schematics':changed_schematics,
        'summary':str(reports/'summary.json'),'native_status':summary['status'],'drc':summary['drc'],'promoted':False,
        'basis':'Project engineering choice informed by ADI AN6412 leaded-EP guidance; not a Diodes factory stencil',
        'intended_stencil_mm':.125,'hardware_tested':False}
    pipeline.write_json(EVIDENCE/'candidate.json',result)
    print(json.dumps(result))


if __name__=='__main__':
    main()
