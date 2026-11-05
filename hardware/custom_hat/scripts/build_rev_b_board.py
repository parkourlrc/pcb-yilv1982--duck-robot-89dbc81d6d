import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

import pcbnew

import generate_rev_a as schematic


base = Path(__file__).resolve().parents[1]
project = base / "rev_b"
repository = base.parents[1]
evidence = repository / "docs/references/扩展板乙版降本"
parts = json.loads((project / "design-components.json").read_text(encoding="utf-8"))
placement_plan = json.loads((project / "placement-plan.json").read_text(encoding="utf-8"))
for component in parts:
    if component["ref"] in placement_plan:
        component["position"] = placement_plan[component["ref"]]
library_root = Path("C:/Users/yilv/AppData/Local/Programs/KiCad/10.0/share/kicad/footprints")
board_file = project / "custom_hat_rev_b.kicad_pcb"
if board_file.exists() and len(pcbnew.LoadBoard(str(board_file)).GetTracks())>25:
    raise RuntimeError("Routed Rev B board exists; do not regenerate over reviewed copper")
source = pcbnew.LoadBoard(str(base / "rev_a/custom_hat_rev_a.kicad_pcb"))
board = pcbnew.BOARD()
board.SetFileName(str(board_file))
board.SetCopperLayerCount(2)


def vector(xpos, ypos):
    return pcbnew.VECTOR2I(pcbnew.FromMM(xpos), pcbnew.FromMM(ypos))


def layers(*identifiers):
    result=pcbnew.LSET()
    for identifier in identifiers:
        result.AddLayer(identifier)
    return result


def rect(footprint, bounds, layer, width=0.05):
    left, top, right, bottom = bounds
    for start, end in (((left,top),(right,top)),((right,top),(right,bottom)),((right,bottom),(left,bottom)),((left,bottom),(left,top))):
        shape=pcbnew.PCB_SHAPE(footprint)
        shape.SetShape(pcbnew.SHAPE_T_SEGMENT)
        shape.SetLayer(layer)
        shape.SetWidth(pcbnew.FromMM(width))
        shape.SetStart(vector(*start))
        shape.SetEnd(vector(*end))
        footprint.Add(shape)


def new_footprint(name, pads, bounds, tht=False, backside=False):
    footprint=pcbnew.FOOTPRINT(board)
    footprint.SetFPID(pcbnew.LIB_ID("duck",name))
    footprint.SetReference("REF**")
    footprint.SetValue(name)
    footprint.SetAttributes(pcbnew.FP_THROUGH_HOLE if tht else pcbnew.FP_SMD)
    layer=pcbnew.B_Cu if backside else pcbnew.F_Cu
    footprint.SetLayer(layer)
    for number,xpos,ypos,width,height,drill in pads:
        pad=pcbnew.PAD(footprint)
        pad.SetNumber(str(number))
        pad.SetPosition(vector(xpos,ypos))
        pad.SetSize(vector(width,height))
        pad.SetShape(pcbnew.PAD_SHAPE_RECT if str(number)=="1" else pcbnew.PAD_SHAPE_OVAL if drill else pcbnew.PAD_SHAPE_ROUNDRECT)
        if drill:
            pad.SetAttribute(pcbnew.PAD_ATTRIB_PTH)
            pad.SetDrillSize(vector(drill,drill))
            pad.SetLayerSet(pcbnew.PAD.PTHMask())
        else:
            pad.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
            pad.SetLayerSet(layers(pcbnew.F_Cu,pcbnew.F_Paste,pcbnew.F_Mask))
            pad.SetRoundRectRadiusRatio(0.15)
        footprint.Add(pad)
    courtyard_layer=pcbnew.B_CrtYd if backside else pcbnew.F_CrtYd
    fab_layer=pcbnew.B_Fab if backside else pcbnew.F_Fab
    silk_layer=pcbnew.B_SilkS if backside else pcbnew.F_SilkS
    rect(footprint,bounds,courtyard_layer)
    rect(footprint,(bounds[0]+0.25,bounds[1]+0.25,bounds[2]-0.25,bounds[3]-0.25),fab_layer,0.1)
    footprint.Reference().SetLayer(silk_layer)
    footprint.Value().SetLayer(fab_layer)
    footprint.Reference().SetPosition(vector(0,bounds[1]-0.9))
    footprint.Value().SetVisible(False)
    pcbnew.FootprintSave(str(project/"duck.pretty"),footprint)
    return footprint


header_pads=[]
for index in range(20):
    header_pads.extend([(2*index+1,index*2.54,0,1.8,1.8,1.02),(2*index+2,index*2.54,-2.54,1.8,1.8,1.02)])
custom={
    "Radxa40P_Zhouri_B":new_footprint("Radxa40P_Zhouri_B",header_pads,(-1.65,-4.06,49.91,1.52),True,True),
    "AMP2007_3P_B":new_footprint("AMP2007_3P_B",[(1,-2,0,1.8,1.8,1.0),(2,0,0,1.8,1.8,1.0),(3,2,0,1.8,1.8,1.0)],(-4.4,-2.25,4.4,2.25),True),
    "A1251_2P_B":new_footprint("A1251_2P_B",[(1,-0.625,0,1.05,1.6,0.7),(2,0.625,0,1.05,1.6,0.7)],(-2.6,-1.6,2.6,1.6),True),
    "LMA2718_B":new_footprint("LMA2718_B",[(1,-0.505,-0.965,0.56,0.54,0),(2,-0.505,0.965,0.56,0.54,0),(3,0.505,0.965,0.56,0.54,0),(4,0.505,-0.965,0.56,0.54,0)],(-1.175,-1.625,1.175,1.625)),
}
ldo_footprint=pcbnew.FootprintLoad(str(library_root/"Package_TO_SOT_SMD.pretty"),"SOT-23")
ldo_footprint.SetFPID(pcbnew.LIB_ID("duck","UMW_XC6206_SOT23_B"))
for pad in ldo_footprint.Pads():
    if pad.GetNumber()=="2":
        pad.SetNumber("3")
    elif pad.GetNumber()=="3":
        pad.SetNumber("2")
pcbnew.FootprintSave(str(project/"duck.pretty"),ldo_footprint)

for drawing in source.GetDrawings():
    if drawing.GetLayer()==pcbnew.Edge_Cuts:
        board.Add(drawing.Duplicate())
for footprint in source.GetFootprints():
    if footprint.GetReference().startswith("H"):
        identifier = footprint.GetFPID()
        if ":" in footprint.GetFPIDAsString():
            nickname, item_name = footprint.GetFPIDAsString().split(":", 1)
            library = project/"duck.pretty" if nickname=="duck" else library_root/(nickname+".pretty")
            duplicate=pcbnew.FootprintLoad(str(library),item_name)
        else:
            duplicate=pcbnew.Cast_to_FOOTPRINT(footprint.Duplicate(False))
        duplicate.SetFPID(identifier)
        duplicate.SetReference(footprint.GetReference())
        duplicate.SetValue(footprint.GetValue())
        duplicate.SetPosition(footprint.GetPosition())
        duplicate.SetOrientation(footprint.GetOrientation())
        duplicate.SetPath(pcbnew.KIID_PATH())
        if ":" in footprint.GetFPIDAsString():
            pcbnew.FootprintSave(str(library),duplicate)
        board.Add(duplicate)

document=ET.parse(evidence/"netlist-candidate.xml").getroot()
pins={}
networks={}
for net in document.findall("nets/net"):
    name=net.get("name")
    item=pcbnew.NETINFO_ITEM(board,name)
    board.Add(item)
    networks[name]=item
    for node in net.findall("node"):
        pins[(node.get("ref"),node.get("pin"))]=name
root_uuid=str(schematic.parse((project/"custom_hat_rev_b.kicad_sch").read_text(encoding="utf-8"))[3][1])
root_tree=schematic.parse((project/"custom_hat_rev_b.kicad_sch").read_text(encoding="utf-8"))
root_uuid=str(schematic.first(root_tree,"uuid")[1])
footprints={}
for component in parts:
    library,name=component["footprint"].split(":",1)
    path=project/(library+".pretty") if library=="duck" else library_root/(library+".pretty")
    footprint=pcbnew.FootprintLoad(str(path),name)
    if footprint is None:
        raise FileNotFoundError(component["footprint"])
    footprint.SetFPID(pcbnew.LIB_ID(library,name))
    footprint.SetReference(component["ref"])
    footprint.SetValue(component["value"])
    board.Add(footprint)
    footprint.SetPath(pcbnew.KIID_PATH(f"/{root_uuid}/{component['sheet_uuid']}/{component['uuid']}"))
    footprint.SetPosition(vector(*component["position"][:2]))
    footprint.SetOrientationDegrees(component["position"][2])
    if component["side"]=="B":
        footprint.Flip(footprint.GetPosition(),True)
    for name,value in (("MPN",component["mpn"]),("LCSC",component["code"]),("Manufacturer",component["manufacturer"]),("Datasheet",component["datasheet"]),("Description",component["description"])):
        footprint.SetField(name,value)
        footprint.GetField(name).SetVisible(False)
    footprint.Reference().SetTextSize(vector(1,1))
    footprint.Reference().SetTextThickness(pcbnew.FromMM(0.15))
    footprint.Reference().SetVisible(False)
    footprint.Value().SetVisible(False)
    for pad in footprint.Pads():
        key=(component["ref"],pad.GetNumber())
        if key in pins:
            pad.SetNet(networks[pins[key]])
        elif pad.GetNumber() in {"MP","0"}:
            pad.SetNet(networks["POWER_GND"])
        elif not pad.IsOnLayer(pcbnew.F_Cu) and not pad.IsOnLayer(pcbnew.B_Cu):
            pad.SetNetCode(0)
        else:
            raise RuntimeError(f"Missing exported net for {key}")
    footprints[component["ref"]]=footprint


def courtyard(footprint):
    layer=pcbnew.B_CrtYd if footprint.GetLayer()==pcbnew.B_Cu else pcbnew.F_CrtYd
    box=footprint.GetCourtyard(layer).BBox()
    if box.GetWidth()==0:
        box=footprint.GetBoundingBox(False,False)
    return tuple(pcbnew.ToMM(value) for value in (box.GetLeft(),box.GetTop(),box.GetRight(),box.GetBottom()))


def intersects(first_box,second_box,gap=0.15):
    return first_box[0]<second_box[2]+gap and second_box[0]<first_box[2]+gap and first_box[1]<second_box[3]+gap and second_box[1]<first_box[3]+gap


holes=[(pcbnew.ToMM(footprint.GetPosition().x),pcbnew.ToMM(footprint.GetPosition().y)) for footprint in board.GetFootprints() if footprint.GetReference().startswith("H")]
occupied=[]
header_boxes=[]
for pad in footprints["J101"].Pads():
    xpos,ypos=pcbnew.ToMM(pad.GetPosition().x),pcbnew.ToMM(pad.GetPosition().y)
    header_boxes.append((xpos-1.08,ypos-1.08,xpos+1.08,ypos+1.08))
placement=[]
priority=lambda part: 0 if part["ref"].startswith("J") else 1 if part["ref"].startswith(("U","L","Q","D","MK","Y")) else 2
for component in sorted(parts,key=lambda part:(priority(part),-((courtyard(footprints[part["ref"]])[2]-courtyard(footprints[part["ref"]])[0])*(courtyard(footprints[part["ref"]])[3]-courtyard(footprints[part["ref"]])[1])))):
    footprint=footprints[component["ref"]]
    if component["ref"]=="J101":
        continue
    anchor=component["position"]
    candidates=[]
    radius_x=(24 if priority(component)==2 else 4) if component["ref"] in placement_plan else 32
    radius_y=(24 if priority(component)==2 else 4) if component["ref"] in placement_plan else 24
    for step_x in range(-radius_x,radius_x+1):
        for step_y in range(-radius_y,radius_y+1):
            delta_x,delta_y=step_x*0.25,step_y*0.25
            candidates.append((delta_x*delta_x+delta_y*delta_y,delta_x,delta_y))
    success=False
    for _,delta_x,delta_y in sorted(candidates):
        footprint.SetPosition(vector(anchor[0]+delta_x,anchor[1]+delta_y))
        box=courtyard(footprint)
        if box[0]<100.55 or box[1]<100.55 or box[2]>164.45 or box[3]>129.45:
            continue
        if any(intersects(box,other) for other in occupied+header_boxes):
            continue
        if any(intersects(box,(xpos-3.0,ypos-3.0,xpos+3.0,ypos+3.0)) for xpos,ypos in holes):
            continue
        success=True
        occupied.append(box)
        placement.append({"ref":component["ref"],"x_mm":anchor[0]+delta_x,"y_mm":anchor[1]+delta_y,"angle":anchor[2],"courtyard":box})
        break
    if not success:
        footprint.SetPosition(vector(anchor[0],anchor[1]))
        box=courtyard(footprint)
        raise RuntimeError("No placement found for "+component["ref"]+" "+json.dumps({"courtyard":box,"collisions":[other for other in occupied+header_boxes if intersects(box,other)]}))

settings=board.GetDesignSettings()
settings.SetBoardThickness(pcbnew.FromMM(1.6))
settings.m_MinClearance=pcbnew.FromMM(0.15)
settings.m_TrackMinWidth=pcbnew.FromMM(0.15)
settings.m_ViasMinSize=pcbnew.FromMM(0.6)
settings.m_MinThroughDrill=pcbnew.FromMM(0.3)
settings.m_CopperEdgeClearance=pcbnew.FromMM(0.3)
settings.m_HoleClearance=pcbnew.FromMM(0.25)
pcbnew.SaveBoard(str(board_file),board)
project_file=project/"custom_hat_rev_b.kicad_pro"
configuration=json.loads(project_file.read_text(encoding="utf-8"))
configuration["meta"]["filename"]="custom_hat_rev_b.kicad_pro"
configuration["board"]["design_settings"]["drc_exclusions"]=[]
configuration["board"]["design_settings"]["rules"].update(min_clearance=0.15,min_track_width=0.15,min_via_diameter=0.6,min_through_hole_diameter=0.3,min_via_annular_width=0.125,min_text_height=1.0,min_text_thickness=0.15)
configuration["net_settings"]["classes"]= [{"name":"Default","clearance":0.15,"track_width":0.25,"via_diameter":0.6,"via_drill":0.3,"microvia_diameter":0.3,"microvia_drill":0.1,"bus_width":12,"wire_width":6,"line_style":0,"schematic_color":"rgba(0, 0, 0, 0)","pcb_color":"rgba(0, 0, 0, 0)"},{"name":"Power","clearance":0.2,"track_width":0.6,"via_diameter":0.6,"via_drill":0.3,"microvia_diameter":0.3,"microvia_drill":0.1,"bus_width":12,"wire_width":6,"line_style":0,"schematic_color":"rgba(0, 0, 0, 0)","pcb_color":"rgba(0, 0, 0, 0)"}]
configuration["net_settings"]["netclass_assignments"]={}
configuration["net_settings"]["netclass_patterns"]=[{"netclass":"Power","pattern":name} for name in ("VBATT_2S_IN","+5V_PRE_IDEAL","+5V","POWER_GND")]
project_file.write_text(json.dumps(configuration,ensure_ascii=False,indent=2),encoding="utf-8")
(project/"custom_hat_rev_b.kicad_dru").write_text('(version 1)\n(rule "Through via annular ring" (condition "A.Type == \'Via\'") (constraint annular_width (min 0.15mm)) (constraint hole_size (min 0.3mm)) (constraint via_diameter (min 0.6mm)))\n(rule "Via copper clearance" (condition "A.Type == \'Via\'") (constraint hole_clearance (min 0.2mm)))\n(rule "PTH copper clearance" (condition "A.Type == \'Pad\' && A.isPlated() && A.Hole_Size_X > 0mm") (constraint hole_clearance (min 0.3mm)))\n(rule "NPTH copper clearance" (condition "A.Type == \'Pad\' && !A.isPlated() && A.Hole_Size_X > 0mm") (constraint hole_clearance (min 0.25mm)))\n',encoding="utf-8")
(evidence/"placement-initial.json").write_text(json.dumps(placement,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps({"footprints":len(footprints),"placed":len(placement),"layer_count":board.GetCopperLayerCount(),"routed":False},ensure_ascii=False))
