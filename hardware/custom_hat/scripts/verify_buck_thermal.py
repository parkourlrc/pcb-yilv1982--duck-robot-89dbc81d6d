"""Verify relocated C308, preserved connectivity and five filled/capped thermal vias."""
import json
from pathlib import Path
import uuid

import pcbnew
import pipeline
from verify_release_metadata import snapshot
from plan_buck_thermal_vias import EVIDENCE


def main():
    candidate_path=EVIDENCE/"candidate.json"
    candidate=json.loads(candidate_path.read_text(encoding="utf-8"))
    work=pipeline.managed(Path(candidate["project"]))
    before=pipeline.prepare(pipeline.PRIMARY)
    runs={}
    for label,project in (("before",before),("after",work)):
        board_path=project/(pipeline.STEM+".kicad_pcb")
        output=project.parent/("thermal-filled-"+label+"-"+uuid.uuid4().hex[:8]+".json")
        commands=[]
        pipeline.run_command([pipeline.find_cli(),"pcb","drc","--format","json","--severity-all","--schematic-parity",
                              "--refill-zones","--save-board","--output",output,board_path],EVIDENCE,"filled-"+label,commands,output)
        report=json.loads(output.read_text(encoding="utf-8"))
        runs[label]={"project":str(project),"pcb_sha256":pipeline.digest(board_path),"commands":commands,
                     "violations":len(report["violations"]),"unconnected":len(report["unconnected_items"]),"parity":len(report["schematic_parity"])}
    original=snapshot(before/(pipeline.STEM+".kicad_pcb"))
    repaired=snapshot(work/(pipeline.STEM+".kicad_pcb"))
    unexpected=[]
    for identifier,pad in original["pads"].items():
        expected=dict(pad)
        if pad["reference"]=="C308":
            expected["position"]=[123700000,116550000 if pad["pin"]=="1" else 114650000]
            expected["orientation"]=90.0
        if pad["reference"]=="C303":
            expected["position"]=[125365000 if pad["pin"]=="1" else 128315000,108800000]
        if repaired["pads"].get(identifier)!=expected:
            unexpected.append({"reference":pad["reference"],"pin":pad["pin"],"expected":expected,"actual":repaired["pads"].get(identifier)})
    routing=json.loads((EVIDENCE/"ldo-cap-routes.json").read_text(encoding="utf-8"))
    thermal=json.loads((EVIDENCE/"thermal-vias-added.json").read_text(encoding="utf-8"))
    input_cap=json.loads((EVIDENCE/"input-cap-relocation.json").read_text(encoding="utf-8"))
    removed=set(original["tracks"])-set(repaired["tracks"])
    expected_removed=set(routing["removed_original_objects"])
    added=set(repaired["tracks"])-set(original["tracks"])
    expected_added={identifier for route in routing["routes"] for identifier in route["added_tracks"]}|{via["uuid"] for via in thermal["new_vias"]}
    expected_added.update(input_cap["added_tracks"])
    expected_added.add(input_cap["added_ground_via"])
    changed=[identifier for identifier,track in original["tracks"].items() if identifier in repaired["tracks"] and repaired["tracks"][identifier]!=track]
    expected_changed={input_cap["changed_enable_via"],*input_cap["changed_enable_tracks"]}
    lost={identifier:sorted(set(group)-set(repaired["connections"].get(identifier,[])))
          for identifier,group in original["connections"].items() if not set(group).issubset(repaired["connections"].get(identifier,[]))}
    board=pcbnew.LoadBoard(str(work/(pipeline.STEM+".kicad_pcb")))
    board.BuildConnectivity()
    pad=next(pad for pad in board.FindFootprintByReference("U301").Pads() if pad.GetNumber()=="9")
    ids={item["uuid"] for item in thermal["new_vias"]}
    via_checks=[]
    for via in board.GetTracks():
        if via.Type()!=pcbnew.PCB_VIA_T or via.m_Uuid.AsString() not in ids:
            continue
        connected={item.m_Uuid.AsString() for item in board.GetConnectivity().GetConnectedItems(via)}
        plane_contacts={}
        for layer in (pcbnew.F_Cu,pcbnew.In1_Cu,pcbnew.B_Cu):
            matches=[zone for zone in board.Zones() if zone.GetNetname()=="POWER_GND" and zone.GetLayer()==layer]
            plane_contacts[board.GetLayerName(layer)]=any(zone.GetFilledPolysList(layer).Contains(via.GetPosition()) for zone in matches)
        via_checks.append({"uuid":via.m_Uuid.AsString(),"net":via.GetNetname(),"within_ep_bbox":pad.GetBoundingBox().Contains(via.GetPosition()),
                           "connected_to_u301_ep":pad.m_Uuid.AsString() in connected,"ground_plane_centers":plane_contacts,
                           "filled_requirement":via.GetFillingMode()==pcbnew.FILLING_MODE_FILLED,"capped_requirement":via.GetCappingMode()==pcbnew.CAPPING_MODE_CAPPED})
    result={"runs":runs,"unexpected_pad_changes":unexpected,"pad_keys_unchanged":set(original["pads"])==set(repaired["pads"]),
            "pad_nets_unchanged":original["nets"]==repaired["nets"],"removed_original_tracks":sorted(removed),
            "expected_removed_original_tracks":sorted(expected_removed),"changed_original_tracks":changed,"expected_changed_original_tracks":sorted(expected_changed),
            "added_objects":sorted(added),"expected_added_objects":sorted(expected_added),"lost_connections":lost,"thermal_via_checks":via_checks,
            "project_settings_unchanged":pipeline.digest(work/(pipeline.STEM+".kicad_pro"))==pipeline.digest(pipeline.PRIMARY/(pipeline.STEM+".kicad_pro")),
            "rules_unchanged":pipeline.digest(work/(pipeline.STEM+".kicad_dru"))==pipeline.digest(pipeline.PRIMARY/(pipeline.STEM+".kicad_dru")),
            "production_ready":False}
    result["accepted"]=all((not unexpected,result["pad_keys_unchanged"],result["pad_nets_unchanged"],removed==expected_removed,
                            added==expected_added,set(changed)==expected_changed,not lost,len(via_checks)==5,
                            all(item["within_ep_bbox"] and item["connected_to_u301_ep"] and item["filled_requirement"] and item["capped_requirement"]
                                and all(item["ground_plane_centers"].values()) and item["net"]=="POWER_GND" for item in via_checks),
                            result["project_settings_unchanged"],result["rules_unchanged"],
                            all(runs["after"][key]==0 for key in ("violations","unconnected","parity"))))
    pipeline.write_json(EVIDENCE/"geometry-connectivity-check.json",result)
    if not result["accepted"]:
        raise RuntimeError("Thermal geometry or connection check failed")
    reports,summary=pipeline.check(work)
    candidate["summary"]=str(reports/"summary.json")
    pipeline.write_json(candidate_path,candidate)
    print(json.dumps({"accepted":result["accepted"],"thermal_vias":via_checks,"status":summary["status"]}))


if __name__=="__main__":
    main()
