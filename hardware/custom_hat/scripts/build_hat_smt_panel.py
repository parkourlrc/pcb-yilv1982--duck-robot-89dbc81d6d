"""Build a two-unit manufacturing panel without changing the source HAT."""
from collections import Counter
import csv
import argparse
import json
from pathlib import Path
import shutil
import subprocess

import pcbnew
import pipeline
from add_i2c_pullups import vector


ROOT = pipeline.BASE.parents[1]
EVIDENCE = ROOT / "docs/references/归档扩展板贴片规范复查"
OUTPUT = pipeline.BASE / "panels/a1-smt-2up-20261102"


def rectangle(bounds):
    shape = pcbnew.SHAPE_POLY_SET()
    shape.NewOutline()
    left, top, right, bottom = bounds
    for point in ((left, top), (right, top), (right, bottom), (left, bottom)):
        shape.Append(*[pcbnew.FromMM(value) for value in point])
    return shape


def segment(board, start, end, layer=pcbnew.Edge_Cuts):
    item = pcbnew.PCB_SHAPE(board)
    item.SetShape(pcbnew.SHAPE_T_SEGMENT)
    item.SetStart(vector(start))
    item.SetEnd(vector(end))
    item.SetWidth(pcbnew.FromMM(.05))
    item.SetLayer(layer)
    board.Add(item)


def hole(board, reference, point, diameter):
    footprint = pcbnew.FOOTPRINT(board)
    footprint.SetReference(reference)
    footprint.SetValue("Panel NPTH")
    footprint.SetAttributes(pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_EXCLUDE_FROM_POS_FILES | pcbnew.FP_BOARD_ONLY)
    footprint.SetPosition(vector(point))
    footprint.Reference().SetVisible(False)
    footprint.Value().SetVisible(False)
    pad = pcbnew.PAD(footprint)
    pad.SetAttribute(pcbnew.PAD_ATTRIB_NPTH)
    pad.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
    pad.SetDrillSize(vector((diameter, diameter)))
    pad.SetSize(vector((diameter, diameter)))
    pad.SetLayerSet(pcbnew.LSET.AllCuMask())
    pad.SetPosition(vector(point))
    footprint.Add(pad)
    board.Add(footprint)


def fiducial(board, reference, point, side):
    footprint = pcbnew.FOOTPRINT(board)
    footprint.SetReference(reference)
    footprint.SetValue("Panel fiducial 1mm/2mm")
    footprint.SetAttributes(pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_EXCLUDE_FROM_POS_FILES | pcbnew.FP_BOARD_ONLY)
    footprint.SetLayer(side)
    footprint.SetPosition(vector(point))
    footprint.Reference().SetVisible(False)
    footprint.Value().SetVisible(False)
    pad = pcbnew.PAD(footprint)
    pad.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
    pad.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
    pad.SetSize(vector((1, 1)))
    layers = pcbnew.LSET()
    layers.AddLayer(side)
    layers.AddLayer(pcbnew.F_Mask if side == pcbnew.F_Cu else pcbnew.B_Mask)
    pad.SetLayerSet(layers)
    pad.SetLocalSolderMaskMargin(pcbnew.FromMM(.5))
    pad.SetPosition(vector(point))
    footprint.Add(pad)
    board.Add(footprint)


def main():
    global OUTPUT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suffix", default="")
    parser.add_argument("--center-mouse-bites", action="store_true",default=True)
    parser.add_argument("--legacy-offset-mouse-bites",dest='center_mouse_bites',action='store_false')
    parser.add_argument("--tab-centers",type=float,nargs=2,default=(108,160))
    arguments = parser.parse_args()
    if arguments.suffix:
        OUTPUT = OUTPUT.with_name(OUTPUT.name + "-" + arguments.suffix)
    checkpoint = pipeline.current_checkpoint()
    OUTPUT.mkdir(parents=True, exist_ok=False)
    EVIDENCE.mkdir(exist_ok=True)
    source_path = pipeline.PRIMARY / (pipeline.STEM + ".kicad_pcb")
    panel_path = OUTPUT / "hat_a1_smt_2up.kicad_pcb"
    shutil.copy2(source_path, panel_path)
    shutil.copy2(pipeline.PRIMARY / (pipeline.STEM + ".kicad_pro"), panel_path.with_suffix(".kicad_pro"))
    project_path=panel_path.with_suffix('.kicad_pro')
    project=json.loads(project_path.read_text(encoding='utf-8'))
    settings=project['net_settings']
    settings['netclass_patterns']=[*settings.get('netclass_patterns',[]),
        *({**entry,'pattern':'B2/'+entry['pattern']} for entry in settings.get('netclass_patterns',[]))]
    for field in ['netclass_assignments','net_colors']:
        original=dict(settings.get(field,{}))
        settings[field]={**original,**{'B2/'+name:value for name,value in original.items()}}
    pipeline.write_json(project_path,project)
    shutil.copy2(pipeline.PRIMARY / (pipeline.STEM + ".kicad_dru"), panel_path.with_suffix(".kicad_dru"))
    shutil.copy2(pipeline.PRIMARY / "fp-lib-table", OUTPUT / "fp-lib-table")
    shutil.copytree(pipeline.PRIMARY / "duck.pretty", OUTPUT / "duck.pretty")
    rules_path = panel_path.with_suffix(".kicad_dru")
    rules_path.write_text(rules_path.read_text(encoding="utf-8") + '''
(rule "Second unit codec small mechanical via"
  (condition "A.Type == 'Via' && A.Via_Type == 'Through' && A.NetName == 'B2/+3V3' && A.insideCourtyard('B2_U701') && A.Diameter == 0.35mm && A.Hole == 0.15mm")
  (constraint annular_width (min 0.10mm))
  (constraint via_diameter (min 0.35mm))
  (constraint hole_size (min 0.15mm)))
(rule "Second unit codec solder-side filled via land"
  (layer B.Cu)
  (condition "A.Type == 'Via' && A.Via_Type == 'Through' && A.NetName == 'B2/+3V3' && A.insideCourtyard('B2_U701') && A.Hole == 0.15mm")
  (constraint annular_width (min 0.05mm))
  (constraint via_diameter (min 0.25mm))
  (constraint hole_size (min 0.15mm)))
''', encoding="utf-8")
    board = pcbnew.LoadBoard(str(panel_path))
    source_footprints, source_tracks, source_zones = list(board.GetFootprints()), list(board.GetTracks()), list(board.Zones())
    source_drawings = list(board.GetDrawings())
    source_nets = {code: net.GetNetname() for code, net in board.GetNetsByNetcode().items() if code}
    second_nets = {}
    for code, name in source_nets.items():
        entry = pcbnew.NETINFO_ITEM(board, "B2/" + name)
        board.Add(entry)
        second_nets[code] = entry
    offset = vector((0, 32))
    maps = {"footprints": [], "tracks": [], "zones": []}
    for source in source_footprints:
        original_reference = source.GetReference()
        duplicate = pcbnew.Cast_to_FOOTPRINT(source.Duplicate(False))
        duplicate.SetReference("B2_" + original_reference)
        duplicate.Move(offset)
        duplicate.Reference().SetVisible(False)
        board.Add(duplicate)
        if source.Reference().IsVisible():
            label = pcbnew.PCB_TEXT(board)
            label.SetText(original_reference)
            label.SetPosition(source.Reference().GetPosition() + offset)
            label.SetLayer(source.Reference().GetLayer())
            label.SetTextSize(source.Reference().GetTextSize())
            label.SetTextThickness(source.Reference().GetTextThickness())
            label.SetTextAngle(source.Reference().GetDrawRotation())
            label.SetMirrored(source.Reference().IsMirrored())
            label.SetHorizJustify(source.Reference().GetHorizJustify())
            label.SetVertJustify(source.Reference().GetVertJustify())
            label.SetBold(source.Reference().IsBold())
            label.SetItalic(source.Reference().IsItalic())
            board.Add(label)
        for pad in duplicate.Pads():
            if pad.GetNetCode():
                pad.SetNet(second_nets[pad.GetNetCode()])
        maps["footprints"].append({"source": original_reference, "panel": duplicate.GetReference(), "uuid": duplicate.m_Uuid.AsString()})
    for source in source_tracks:
        duplicate = pcbnew.Cast_to_PCB_VIA(source.Duplicate()) if source.Type() == pcbnew.PCB_VIA_T else pcbnew.Cast_to_PCB_TRACK(source.Duplicate())
        code = source.GetNetCode()
        duplicate.Move(offset)
        board.Add(duplicate)
        duplicate.SetNet(second_nets[code])
        maps["tracks"].append({"source": source.m_Uuid.AsString(), "panel": duplicate.m_Uuid.AsString(), "net": duplicate.GetNetname()})
    for source in source_zones:
        duplicate = pcbnew.Cast_to_ZONE(source.Duplicate(False))
        code = source.GetNetCode()
        duplicate.Move(offset)
        board.Add(duplicate)
        if code:
            duplicate.SetNet(second_nets[code])
        maps["zones"].append({"source": source.m_Uuid.AsString(), "panel": duplicate.m_Uuid.AsString()})
    for source in source_drawings:
        if source.GetLayer() == pcbnew.Edge_Cuts:
            board.Remove(source)
        else:
            duplicate = pcbnew.Cast_to_PCB_TEXT(source.Duplicate()) if source.Type() == pcbnew.PCB_TEXT_T else pcbnew.Cast_to_PCB_SHAPE(source.Duplicate())
            duplicate.Move(offset)
            board.Add(duplicate)
    for start, end in (((92,90),(173,90)),((175,92),(175,170)),((173,172),(92,172)),((90,170),(90,92))):
        segment(board, start, end)
    for start, middle, end in (((173,90),(174.414214,90.585786),(175,92)),((175,170),(174.414214,171.414214),(173,172)),
                               ((92,172),(90.585786,171.414214),(90,170)),((90,92),(90.585786,90.585786),(92,90))):
        arc = pcbnew.PCB_SHAPE(board)
        arc.SetShape(pcbnew.SHAPE_T_ARC)
        arc.SetArcGeometry(vector(start),vector(middle),vector(end))
        arc.SetWidth(pcbnew.FromMM(.05))
        arc.SetLayer(pcbnew.Edge_Cuts)
        board.Add(arc)
    slots = rectangle((98,98,167,164))
    for bounds in ((100,100,165,130),(100,132,165,162)):
        slots.BooleanSubtract(rectangle(bounds))
    tabs = []
    for center in arguments.tab_centers:
        for top, bottom in ((98,100),(130,132),(162,164)):
            bounds = (center-2.8,top,center+2.8,bottom)
            slots.BooleanSubtract(rectangle(bounds))
            tabs.append(bounds)
    for index in range(slots.OutlineCount()):
        outline = slots.Outline(index)
        points = [(pcbnew.ToMM(outline.CPoint(point).x),pcbnew.ToMM(outline.CPoint(point).y)) for point in range(outline.PointCount())]
        for start,end in zip(points,points[1:]+points[:1]):
            segment(board,start,end)
    mouse_bites = []
    mouse_rows = (100,130,132,162) if arguments.center_mouse_bites else (99.75,130.25,131.75,162.25)
    for center in arguments.tab_centers:
        for ypos in mouse_rows:
            for difference in (-2,-1,0,1,2):
                point = (center+difference,ypos)
                reference = "MB"+str(len(mouse_bites)+1)
                hole(board,reference,point,.6)
                mouse_bites.append(point)
    tab_copper_exclusions=[]
    if arguments.center_mouse_bites:
        for center in arguments.tab_centers:
            for ypos in mouse_rows:
                bounds=(center-2.8,ypos-.6,center+2.8,ypos+.6)
                tab_copper_exclusions.append(bounds)
                for zone in board.Zones():
                    outline=zone.Outline()
                    outline.BooleanSubtract(rectangle(bounds))
                    zone.UnFill()
    tooling = [(94,110),(94,154),(171,110),(171,154)]
    for index, point in enumerate(tooling):
        hole(board,"PH"+str(index+1),point,2)
    fiducials = {"F.Cu": [(94,94),(171,94),(94,168)], "B.Cu": [(94,94),(171,99),(171,168)]}
    for side, points in fiducials.items():
        for index,point in enumerate(points):
            fiducial(board,"PFID_"+side[0]+str(index+1),point,board.GetLayerID(side))
    pcbnew.SaveBoard(str(panel_path),board)
    mapping = {"source_pcb_sha256":checkpoint["pcb_sha256"],"panel":str(panel_path),"panel_size_mm":[85,82],"board_offsets_mm":[[0,0],[0,32]],
               "unit_count":2,"rail_width_mm":8,"routed_gap_mm":2,"outer_corner_radius_mm":2,"tabs":tabs,"mouse_bite_holes_mm":mouse_bites,
               "mouse_bite_diameter_mm":.6,"mouse_bite_pitch_mm":1,"tooling_holes_mm":tooling,"tooling_diameter_mm":2,
               "mouse_bites_centered_on_unit_outline":arguments.center_mouse_bites,"tab_copper_exclusions_mm":tab_copper_exclusions,
               "fiducials":fiducials,"maps":maps,"primary_unchanged":pipeline.fingerprints(pipeline.PRIMARY)==checkpoint["design_hashes"],
               "manufacturing_released":False,"status":"candidate_requires_panel_DRC_and_copper_validation"}
    pipeline.write_json(EVIDENCE/"panel-candidate.json",mapping)
    print(json.dumps({key:value for key,value in mapping.items() if key not in {"maps","mouse_bite_holes_mm"}}))


if __name__ == "__main__":
    main()
