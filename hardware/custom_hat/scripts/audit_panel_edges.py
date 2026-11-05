"""Check centered mouse-bite groups, copper trimming and retained I2S reference copper."""
from collections import defaultdict
import csv
import math
from pathlib import Path

import pcbnew
import pipeline
from add_i2c_pullups import vector
from build_hat_smt_panel import rectangle
from search_remaining_thermal_pads import covered


def analyze_panel_edges(source_board,panel_board,contract):
    groups=defaultdict(list)
    for footprint in panel_board.GetFootprints():
        if footprint.GetReference().startswith('MB'):
            pad=next(iter(footprint.Pads()))
            point=[pcbnew.ToMM(value) for value in pad.GetPosition()]
            groups[(point[1],0 if point[0]<132.5 else 1)].append((point[0],pad))
    group_checks=[]
    for (ypos,side),items in sorted(groups.items()):
        items.sort(key=lambda item:item[0])
        gaps=[items[index+1][0]-items[index][0]-.6 for index in range(len(items)-1)]
        group_checks.append({'y_mm':ypos,'xs_mm':[item[0] for item in items],
            'centered_on_unit_nominal_outline':ypos in {100,130,132,162},'count':len(items),
            'all_npth_0p6mm':all(pad.GetAttribute()==pcbnew.PAD_ATTRIB_NPTH and list(pad.GetDrillSize())==[600000,600000] for _,pad in items),
            'web_gaps_mm':gaps,'all_web_gaps_0p4mm':all(abs(gap-.4)<1e-6 for gap in gaps)})
    mechanical=pcbnew.SHAPE_POLY_SET()
    valid_outline=panel_board.GetBoardPolygonOutlines(mechanical,False)
    nominal_area=85*82-(4-math.pi)*2*2
    void_area=nominal_area-mechanical.Area()/1e12
    cut_hits=[]
    for (ypos,_),items in groups.items():
        center=(items[0][0]+items[-1][0])/2
        cut=rectangle((center-2.8,ypos-.001,center+2.8,ypos+.001))
        for layer in [pcbnew.F_Cu,pcbnew.In1_Cu,pcbnew.In2_Cu,pcbnew.B_Cu]:
            for footprint in panel_board.GetFootprints():
                for pad in footprint.Pads():
                    if pad.GetAttribute()!=pcbnew.PAD_ATTRIB_NPTH and pad.IsOnLayer(layer) and cut.Collide(pad.GetEffectiveShape(layer),pcbnew.FromMM(.2)):
                        cut_hits.append({'at_y':ypos,'object':footprint.GetReference()+'.'+pad.GetNumber(),'layer':panel_board.GetLayerName(layer)})
            for track in panel_board.GetTracks():
                if track.IsOnLayer(layer) and cut.Collide(track.GetEffectiveShape(layer),pcbnew.FromMM(.2)):
                    cut_hits.append({'at_y':ypos,'object':track.m_Uuid.AsString(),'layer':panel_board.GetLayerName(layer)})
            for zone in panel_board.Zones():
                if zone.IsOnLayer(layer) and zone.GetFilledPolysList(layer).Collide(cut,pcbnew.FromMM(.2)):
                    cut_hits.append({'at_y':ypos,'object':zone.m_Uuid.AsString(),'layer':panel_board.GetLayerName(layer)})
    zone_checks=[]
    zone_map={row['source']:row['panel'] for row in contract['maps']['zones']}
    zones={zone.m_Uuid.AsString():zone for zone in panel_board.Zones()}
    for source_zone in source_board.Zones():
        layer=source_zone.GetLayer()
        for identifier,offset in [(source_zone.m_Uuid.AsString(),0),(zone_map[source_zone.m_Uuid.AsString()],32)]:
            candidate=zones[identifier]
            source_fill=pcbnew.SHAPE_POLY_SET(source_zone.GetFilledPolysList(layer))
            source_fill.Move(vector((0,offset)))
            lost=pcbnew.SHAPE_POLY_SET(source_fill)
            lost.BooleanSubtract(candidate.GetFilledPolysList(layer))
            added=pcbnew.SHAPE_POLY_SET(candidate.GetFilledPolysList(layer))
            added.BooleanSubtract(source_fill)
            gross_lost=lost.Area()/1e12
            gross_added=added.Area()/1e12
            for left,top,right,bottom in contract.get('tab_copper_exclusions_mm',[]):
                region=rectangle((left-.15,top-.25,right+.15,bottom+.25))
                lost.BooleanSubtract(region)
                added.BooleanSubtract(region)
            zone_checks.append({'source_zone':source_zone.m_Uuid.AsString(),'panel_zone':identifier,'offset_y_mm':offset,
                'layer':panel_board.GetLayerName(layer),'lost_area_mm2':gross_lost,'added_area_mm2':gross_added,
                'unexplained_lost_outside_edge_neighborhood_mm2':lost.Area()/1e12,
                'unexplained_added_outside_edge_neighborhood_mm2':added.Area()/1e12})
    sample_path=pipeline.BASE.parents[1]/'docs/references/归档扩展板贴片与层叠复核/relocate-after-plane-samples.csv'
    with sample_path.open(encoding='utf-8',newline='') as stream:
        samples=list(csv.DictReader(stream))
    reference_loss=[]
    for row in samples:
        point=vector((float(row['x_mm']),float(row['y_mm'])))
        for layer_name,net in [('F.Cu','POWER_GND'),('In1.Cu','POWER_GND'),('In2.Cu','+3V3'),('B.Cu','POWER_GND')]:
            if layer_name==row['source_layer']:
                continue
            layer=source_board.GetLayerID(layer_name)
            if not covered(source_board,point,layer,net):
                continue
            for prefix,offset in [('',0),('B2/',32)]:
                if not covered(panel_board,point+vector((0,offset)),layer,prefix+net):
                    reference_loss.append({'unit_y_offset':offset,'signal':row['net'],'plane':layer_name,'point':[row['x_mm'],row['y_mm']]})
    all_groups=bool(len(group_checks)==8 and all(row['centered_on_unit_nominal_outline'] and row['count']==5 and row['all_npth_0p6mm'] and row['all_web_gaps_0p4mm'] for row in group_checks))
    trim_valid=bool(len(zone_checks)==8 and all(row['unexplained_lost_outside_edge_neighborhood_mm2']<1e-6 and row['unexplained_added_outside_edge_neighborhood_mm2']<1e-6 for row in zone_checks))
    result={'centered_hole_groups':group_checks,'centered_group_geometry_pass':all_groups,'closed_outline':valid_outline,
        'solid_outline_count':mechanical.OutlineCount(),'milled_void_area_mm2':void_area,'milled_void_fraction':void_area/nominal_area,
        'cut_line_copper_hits_with_0p2mm_clearance':cut_hits,'zone_trim_checks':zone_checks,'zone_changes_local_to_tab_edges':trim_valid,
        'i2s_samples_per_unit':len(samples),'i2s_actual_reference_copper_loss':reference_loss,
        'limits':['0.15mm lateral/0.25mm normal neighborhood around trim includes native fill corner rounding and local neck cleanup',
                  'Reference-copper sampling is not a field solution or actual EMI measurement',
                  'Centered perforation leaves scalloped edges; mechanical depaneling and burr inspection remain manufacturing-stage work'],
        'manufacturing_released':False}
    result['accepted']=all((all_groups,valid_outline,mechanical.OutlineCount()==1,not cut_hits,trim_valid,not reference_loss,void_area/nominal_area<.5))
    return result
