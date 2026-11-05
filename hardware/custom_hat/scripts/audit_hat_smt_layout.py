"""Inventory source-board SMT risks without upgrading guidance to hard failures."""
import csv
import json
import math
from pathlib import Path

import pcbnew
import pipeline


EVIDENCE = pipeline.BASE.parents[1] / "docs/references/归档扩展板贴片规范复查"


def bbox(item):
    bounds = item.GetBoundingBox()
    return [pcbnew.ToMM(value) for value in (bounds.GetLeft(),bounds.GetTop(),bounds.GetRight(),bounds.GetBottom())]


def gap(first, second):
    return math.hypot(max(first[0]-second[2],second[0]-first[2],0),max(first[1]-second[3],second[1]-first[3],0))


def main():
    checkpoint = pipeline.current_checkpoint()
    root = pipeline.BASE.parents[1]
    package = root / checkpoint["review_binding"]["production_package"]
    with (package/"assembly-plan.csv").open(encoding="utf-8-sig",newline="") as stream:
        parts = {row["Reference"]:row for row in csv.DictReader(stream) if not row["Assembly"].startswith("DNP")}
    board = pcbnew.LoadBoard(str(pipeline.PRIMARY/(pipeline.STEM+".kicad_pcb")))
    components, omitted, zones = [], [], []
    for zone in board.Zones():
        zones.append({"layer":board.GetLayerName(zone.GetLayer()),"net":zone.GetNetname(),"pad_connection":int(zone.GetPadConnection()),
                      "thermal_spoke_width_mm":pcbnew.ToMM(zone.GetThermalReliefSpokeWidth()),"thermal_gap_mm":pcbnew.ToMM(zone.GetThermalReliefGap())})
    pads = []
    for footprint in board.GetFootprints():
        reference = footprint.GetReference()
        if reference not in parts:
            continue
        side = footprint.GetLayer()
        fab_layer = pcbnew.F_Fab if side==pcbnew.F_Cu else pcbnew.B_Fab
        outlines = [bbox(item) for item in footprint.GraphicalItems() if item.GetLayer()==fab_layer and item.Type()==pcbnew.PCB_SHAPE_T]
        if outlines:
            bounds = [min(row[0] for row in outlines),min(row[1] for row in outlines),max(row[2] for row in outlines),max(row[3] for row in outlines)]
            components.append({"reference":reference,"side":board.GetLayerName(side),"bbox_mm":bounds,
                               "assembly":parts[reference]["Assembly"],"mpn":parts[reference]["MPN"],"basis":"Fabrication-graphic bounding box; may include leads/chamfers; not a 3D body measurement"})
        else:
            omitted.append(reference)
        for pad in footprint.Pads():
            if pad.GetAttribute()!=pcbnew.PAD_ATTRIB_SMD or not pad.IsOnLayer(side) or not pad.GetNumber():
                continue
            pads.append((reference,pad,side))
    pairs=[]
    for index,first in enumerate(components):
        for second in components[index+1:]:
            if first["side"]!=second["side"] or not first["assembly"].startswith("SMT") or not second["assembly"].startswith("SMT"):
                continue
            distance=gap(first["bbox_mm"],second["bbox_mm"])
            guidance=3 if first["reference"].startswith('U') or second["reference"].startswith('U') else 1
            if distance<guidance:
                pairs.append({"references":[first["reference"],second["reference"]],"side":first["side"],"bbox_gap_mm":distance,
                              "guidance_mm":guidance,"requires_real_body_review":distance<.3,"grade":"P1 reference guidance, not P0 admission failure"})
    exposed_gaps=[]
    for index,(reference,pad,side) in enumerate(pads):
        shape=pad.GetEffectiveShape(side)
        for other_reference,other_pad,other_side in pads[index+1:]:
            if other_side!=side or pad.GetNetname()==other_pad.GetNetname():
                continue
            other=other_pad.GetEffectiveShape(side)
            if not shape.Collide(other,pcbnew.FromMM(.2)):
                continue
            low,high=0,pcbnew.FromMM(.2)
            while low<high:
                middle=(low+high)//2
                if shape.Collide(other,middle):high=middle
                else:low=middle+1
            exposed_gaps.append({"pads":[reference+'.'+pad.GetNumber(),other_reference+'.'+other_pad.GetNumber()],"nominal_copper_gap_mm":pcbnew.ToMM(high),"side":board.GetLayerName(side)})
    thermal=[]
    for reference,pad,side in pads:
        if not reference.startswith(('C','R')):
            continue
        if any(zone.IsOnLayer(side) and zone.GetNetname()==pad.GetNetname() and zone.GetFilledPolysList(side).Contains(pad.GetPosition()) for zone in board.Zones()):
            thermal.append({"pad":reference+'.'+pad.GetNumber(),"net":pad.GetNetname(),"side":board.GetLayerName(side),
                            "pad_connection_override":int(pad.GetLocalZoneConnection()),"pad_center_in_same_net_fill":True})
    result={"pcb_sha256":checkpoint["pcb_sha256"],"components":components,"omitted_fab_outlines":omitted,
            "p1_spacing_guidance_pairs":sorted(pairs,key=lambda row:row['bbox_gap_mm']),"exposed_copper_gap_below_0_2mm":exposed_gaps,
            "zones":zones,"chip_pad_center_in_same_net_fill":thermal,
            "limitations":"Fab bboxes screen guidance; no component mass, nozzle, exact reflow profile, stock or batch condition claim. Pad clearances are copper not soldermask union.",
            "manufacturing_released":False}
    pipeline.write_json(EVIDENCE/'smt-layout-audit.json',result)
    print(json.dumps({"p1_bbox_pairs":len(pairs),"below_0_3mm":[row for row in pairs if row['requires_real_body_review']],"below_0_2mm_pads":exposed_gaps,"zones":zones,"chip_pads_in_fill":len(thermal),"omitted":omitted},ensure_ascii=False))


if __name__=='__main__':
    main()
