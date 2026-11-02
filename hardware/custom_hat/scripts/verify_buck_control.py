"""Verify the four-passive relocation, all original connections and the sense branch."""
import json
import math
from pathlib import Path
import uuid

import pcbnew
import pipeline
from verify_release_metadata import snapshot
from add_i2c_pullups import vector
from inspect_buck_control import EVIDENCE
from relayout_buck_control import PLACEMENTS, pad


def protection(board):
    return {via.m_Uuid.AsString():(int(via.GetFillingMode()),int(via.GetCappingMode()))
            for via in board.GetTracks() if via.Type()==pcbnew.PCB_VIA_T and via.GetFillingMode()==pcbnew.FILLING_MODE_FILLED}


def main():
    candidate_path=EVIDENCE/"candidate.json"
    candidate=json.loads(candidate_path.read_text(encoding="utf-8"))
    work=pipeline.managed(Path(candidate["project"]))
    before=pipeline.prepare(pipeline.PRIMARY)
    runs={}
    for label,project in (("before",before),("after",work)):
        board_path=project/(pipeline.STEM+".kicad_pcb")
        output=project.parent/("control-filled-"+label+"-"+uuid.uuid4().hex[:8]+".json")
        commands=[]
        pipeline.run_command([pipeline.find_cli(),"pcb","drc","--format","json","--severity-all","--schematic-parity",
                              "--refill-zones","--save-board","--output",output,board_path],EVIDENCE,"filled-"+label,commands,output)
        report=json.loads(output.read_text(encoding="utf-8"))
        runs[label]={"project":str(project),"pcb_sha256":pipeline.digest(board_path),"commands":commands,
                     "violations":len(report["violations"]),"unconnected":len(report["unconnected_items"]),"parity":len(report["schematic_parity"])}
    old_board=pcbnew.LoadBoard(str(before/(pipeline.STEM+".kicad_pcb")))
    new_board=pcbnew.LoadBoard(str(work/(pipeline.STEM+".kicad_pcb")))
    original=snapshot(before/(pipeline.STEM+".kicad_pcb"))
    repaired=snapshot(work/(pipeline.STEM+".kicad_pcb"))
    unexpected=[]
    moved=[]
    for identifier,entry in original["pads"].items():
        expected=dict(entry)
        reference=entry["reference"]
        if reference in PLACEMENTS:
            old_footprint=old_board.FindFootprintByReference(reference)
            center=old_footprint.GetPosition()
            xpos,ypos,angle=PLACEMENTS[reference]
            delta=math.radians(angle-old_footprint.GetOrientationDegrees())
            offset_x=entry["position"][0]-center.x
            offset_y=entry["position"][1]-center.y
            expected["position"]=[round(pcbnew.FromMM(xpos)+math.cos(delta)*offset_x+math.sin(delta)*offset_y),
                                  round(pcbnew.FromMM(ypos)-math.sin(delta)*offset_x+math.cos(delta)*offset_y)]
            expected["orientation"]=entry["orientation"]+angle-old_footprint.GetOrientationDegrees()
            moved.append([reference,entry["pin"]])
        actual=repaired["pads"].get(identifier)
        if actual is None:
            unexpected.append([identifier,"missing"])
            continue
        compatible=all(expected[key]==actual[key] for key in expected if key not in {"position","orientation"})
        compatible=compatible and expected["orientation"]%360==actual["orientation"]%360
        compatible=compatible and all(abs(expected["position"][index]-actual["position"][index])<=2 for index in (0,1))
        if not compatible:
            unexpected.append({"reference":reference,"pin":entry["pin"],"expected":expected,"actual":actual})
    placement=json.loads((EVIDENCE/"placement-contract.json").read_text(encoding="utf-8"))
    route_data=json.loads((EVIDENCE/"control-route-plan.json").read_text(encoding="utf-8"))
    removed=set(original["tracks"])-set(repaired["tracks"])
    added=set(repaired["tracks"])-set(original["tracks"])
    changed=[identifier for identifier,track in original["tracks"].items() if identifier in repaired["tracks"] and repaired["tracks"][identifier]!=track]
    expected_added={identifier for route in route_data["routes"] for identifier in route["added_tracks"]}
    lost={identifier:sorted(set(group)-set(repaired["connections"].get(identifier,[])))
          for identifier,group in original["connections"].items() if not set(group).issubset(repaired["connections"].get(identifier,[]))}
    branch=next(route for route in route_data["routes"] if route["net"]=="+5V")
    branch_ids=set(branch["added_tracks"])
    branch_items=[item for item in new_board.GetTracks() if item.m_Uuid.AsString() in branch_ids]
    branch_shapes=[item.GetEffectiveShape(pcbnew.F_Cu) for item in branch_items]
    contacts=[item for item in new_board.GetTracks() if item.IsOnLayer(pcbnew.F_Cu) and item.GetNetname()=="+5V" and item.m_Uuid.AsString() not in branch_ids
              and any(shape.Collide(item.GetEffectiveShape(pcbnew.F_Cu),0) for shape in branch_shapes)]
    touched_pads=[footprint.GetReference()+"."+item.GetNumber() for footprint in new_board.GetFootprints() for item in footprint.Pads()
                  if item.IsOnLayer(pcbnew.F_Cu) and item.GetNetname()=="+5V" and any(shape.Collide(item.GetEffectiveShape(pcbnew.F_Cu),0) for shape in branch_shapes)]
    contact_region=pad(new_board,"C305","1").GetBoundingBox()
    contact_region.Inflate(pcbnew.FromMM(0.25))
    outside_contacts=[]
    for start,end in zip(branch["points"],branch["points"][1:]):
        count=max(1,math.ceil(math.dist(start[:2],end[:2])/0.01))
        for index in range(count+1):
            point=vector((start[0]+(end[0]-start[0])*index/count,start[1]+(end[1]-start[1])*index/count))
            if contact_region.Contains(point):
                continue
            shape=pcbnew.SHAPE_CIRCLE(point,pcbnew.FromMM(0.125))
            matches=[item.m_Uuid.AsString() for item in contacts if item.GetEffectiveShape(pcbnew.F_Cu).Collide(shape,0)]
            if matches:
                outside_contacts.append({"position":list(point),"items":matches})
    lengths={}
    for route in route_data["routes"]:
        lengths[route["net"]]=lengths.get(route["net"],0)+sum(math.dist(start[:2],end[:2]) for start,end in zip(route["points"],route["points"][1:]))
    result={"runs":runs,"moved_pad_keys":moved,"unexpected_pad_changes":unexpected,"position_comparison_tolerance_nm":2,
            "pad_keys_unchanged":set(original["pads"])==set(repaired["pads"]),"pad_nets_unchanged":original["nets"]==repaired["nets"],
            "removed_objects":sorted(removed),"expected_removed_objects":placement["removed_original_objects"],"added_objects":sorted(added),
            "expected_added_objects":sorted(expected_added),"changed_other_tracks":changed,"lost_connections":lost,
            "manufacturing_requirements_preserved":protection(old_board)==protection(new_board),"protected_via_count":len(protection(new_board)),
            "new_net_lengths_mm":lengths,"sense_branch_touched_pads":touched_pads,"sense_branch_old_copper_contacts":[item.m_Uuid.AsString() for item in contacts],
            "sense_branch_contacts_outside_output_pad_region":outside_contacts,"sense_contact_sample_step_mm":0.01,
            "project_settings_unchanged":pipeline.digest(work/(pipeline.STEM+".kicad_pro"))==pipeline.digest(pipeline.PRIMARY/(pipeline.STEM+".kicad_pro")),
            "rules_unchanged":pipeline.digest(work/(pipeline.STEM+".kicad_dru"))==pipeline.digest(pipeline.PRIMARY/(pipeline.STEM+".kicad_dru")),
            "production_ready":False}
    result["accepted"]=all((len(moved)==8,not unexpected,result["pad_keys_unchanged"],result["pad_nets_unchanged"],
                            removed==set(placement["removed_original_objects"]),added==expected_added,not changed,not lost,
                            result["manufacturing_requirements_preserved"],len(protection(new_board))==6,
                            set(touched_pads)=={"C305.1","R301.1"},not outside_contacts,
                            result["project_settings_unchanged"],result["rules_unchanged"],
                            all(runs["after"][key]==0 for key in ("violations","unconnected","parity"))))
    pipeline.write_json(EVIDENCE/"geometry-connectivity-check.json",result)
    if not result["accepted"]:
        raise RuntimeError("Control-loop geometry or topology verification failed")
    reports,summary=pipeline.check(work)
    candidate["summary"]=str(reports/"summary.json")
    pipeline.write_json(candidate_path,candidate)
    print(json.dumps({"accepted":result["accepted"],"new_net_lengths_mm":lengths,"lost_connections":len(lost),"protected_vias":len(protection(new_board)),"status":summary["status"]}))


if __name__=="__main__":
    main()
