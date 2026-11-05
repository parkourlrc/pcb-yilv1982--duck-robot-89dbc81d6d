"""Audit THT tail clearances and derive conditional Radxa/HAT spacing ranges."""
import csv
import json
import math
from pathlib import Path

import pcbnew
import pipeline


EVIDENCE=pipeline.BASE.parents[1]/'docs/references/归档扩展板机械适配复核'


def main():
    checkpoint=pipeline.current_checkpoint()
    board=pcbnew.LoadBoard(str(pipeline.PRIMARY/(pipeline.STEM+'.kicad_pcb')))
    package=pipeline.BASE.parents[1]/checkpoint['review_binding']['production_package']
    with (package/'assembly-plan.csv').open(encoding='utf-8-sig',newline='') as stream:
        fitted={row['Reference']:row for row in csv.DictReader(stream) if not row['Assembly'].startswith('DNP')}
    bodies=[]
    tht_pads=[]
    smt_through_pads=[]
    for footprint in board.GetFootprints():
        reference=footprint.GetReference()
        if reference not in fitted:
            continue
        side=footprint.GetLayer()
        fab=pcbnew.F_Fab if side==pcbnew.F_Cu else pcbnew.B_Fab
        boxes=[item.GetBoundingBox() for item in footprint.GraphicalItems() if item.GetLayer()==fab and item.Type()==pcbnew.PCB_SHAPE_T]
        if boxes:
            bodies.append({'reference':reference,'side':side,'box':[min(box.GetLeft() for box in boxes),min(box.GetTop() for box in boxes),max(box.GetRight() for box in boxes),max(box.GetBottom() for box in boxes)]})
        for pad in footprint.Pads():
            if pad.GetDrillSize().x:
                entry={'reference':reference,'pin':pad.GetNumber(),'side':side,'xy':list(pad.GetPosition()),'drill_radius':pad.GetDrillSize().x/2}
                tht_pads.append(entry)
                if fitted[reference]['Assembly'].startswith('SMT'):
                    smt_through_pads.append(entry)
    clearances=[]
    for pad in tht_pads:
        distances=[]
        for body in bodies:
            if body['side']==pad['side']:
                continue
            left,top,right,bottom=body['box']
            xpos,ypos=pad['xy']
            distance=math.hypot(max(left-xpos,xpos-right,0),max(top-ypos,ypos-bottom,0))-pad['drill_radius']
            distances.append((distance,body['reference']))
        distance,reference=min(distances)
        clearances.append({'pad':pad['reference']+'.'+pad['pin'],'nearest_opposite_fab_body':reference,'gap_to_drilled_hole_circle_mm':distance/1e6})
    tail_rows=[]
    thickness_range=[1.57*.9,1.57*1.1]
    for reference,nominal_tail in [('J101',2.64),('J301',2.54),('J403',2.54),('J802',2.54),('J401',3.2),('J402',3.2)]:
        tail_rows.append({'reference':reference,'component_side':board.GetLayerName(board.FindFootprintByReference(reference).GetLayer()),
            'nominal_tail_mm':nominal_tail,'nominal_protrusion_at_1p57_mm':nominal_tail-1.57,
            'protrusion_with_board_thickness_range_mm':[nominal_tail-thickness_range[1],nominal_tail-thickness_range[0]],
            'limitation':'Only PCB thickness spread included; component lead tolerance and solder meniscus excluded'})
    surface=json.loads((EVIDENCE/'radxa-surface-envelope.json').read_text(encoding='utf-8'))
    rows=[]
    for row in surface['front_component_envelopes']:
        reference=row['reference']
        if board.FindFootprintByReference(reference).GetLayer()==pcbnew.F_Cu:
            rows.append({'reference':reference,'reference_host_height_mm':row['radxa_surface_max_z_mm'],'hat_intrusion_mm':row['height_mm'],
                         'required_gap_zero_margin_mm':row['zero_margin_required_gap_mm'],'basis':row['basis']})
    maximum=max(row['required_gap_zero_margin_mm'] for row in rows)
    scenarios=[]
    for gap in [11.01,11.1,11.6,12,12.5,13,13.33]:
        insertion=8.5+8.51-gap
        scenarios.append({'board_front_face_gap_mm':gap,'nominal_ssw_insertion_mm':insertion,
            'within_catalog_insertion_range':3.68-1e-6<=insertion<=6.35+1e-6,'minimum_selected_rigid_clearance_mm':gap-maximum,
            'clearance_by_component_mm':{row['reference']:gap-row['required_gap_zero_margin_mm'] for row in rows},
            'hat_outward_j301_tip_above_radxa_top_mm':gap+1.57+8.38})
    pins=[]
    for pad in board.FindFootprintByReference('J301').Pads():
        pins.append({'pin':int(pad.GetNumber()),'net':pad.GetNetname(),'pcb_xy_mm':[pcbnew.ToMM(value) for value in pad.GetPosition()]})
    result={'date':'2026-11-02','pcb_sha256':checkpoint['pcb_sha256'],'user_height_constraint':'Not fixed; user asked for a feasible range on2026-11-02',
        'tht_pin_count':len(tht_pads),'fitted_body_count':len(bodies),'smt_through_fixed_pins':smt_through_pads,
        'tail_to_opposite_body_clearances':clearances,'minimum_tail_to_opposite_body_gap_mm':min(row['gap_to_drilled_hole_circle_mm'] for row in clearances),
        'tail_protrusions':tail_rows,'tht_after_both_smt_reflows':True,
        'remaining_host_facing_rigid_envelopes':rows,'zero_margin_minimum_gap_mm':maximum,
        'chosen_screening_clearance_mm':.5,'nominal_screening_interval_mm':[maximum+.5,13.33],
        'screening_margin_is_design_assumption_not_factory_spec':True,'scenarios':scenarios,'j301_pins':sorted(pins,key=lambda row:row['pin']),
        'limits':['Range is for the official reference CAD and selected rigid envelopes only',
                  'Host physical revision, male header and all height tolerances unknown',
                  'EH8.1mm includes the mating housing but not wires or bend radius',
                  'Any radiator, camera cable, chassis and external J301 mating housing must be added',
                  'No standoff length or screw purchase is released by this nominal calculation',
                  'Opposite-side clearance uses full drilled-hole circles and Fab body envelopes, not physical lead and solder measurements'],
        'hardware_tested':False,'overall_mechanical_fit_approved':False}
    pipeline.write_json(EVIDENCE/'mechanical-range.json',result)
    print(json.dumps({key:value for key,value in result.items() if key not in {'tail_to_opposite_body_clearances','scenarios','j301_pins'}}))


if __name__=='__main__':
    main()
