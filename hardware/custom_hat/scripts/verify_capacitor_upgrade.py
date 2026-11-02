"""Verify the four capacitor replacements, preserved connectivity and process flags."""
import json
from pathlib import Path
import uuid

import pcbnew
import pipeline
from generate_rev_a import children, first, parse
from repair_release_metadata import properties
from verify_release_metadata import snapshot
from verify_buck_control import protection
from upgrade_buck_capacitors import EVIDENCE, POSITIONS, MPN


def main():
    candidate_path=EVIDENCE/"candidate.json"
    candidate=json.loads(candidate_path.read_text(encoding="utf-8"))
    work=pipeline.managed(Path(candidate["project"]))
    before=pipeline.prepare(pipeline.PRIMARY)
    runs={}
    for label,project in (("before",before),("after",work)):
        board_path=project/(pipeline.STEM+".kicad_pcb")
        output=project.parent/("capacitor-filled-"+label+"-"+uuid.uuid4().hex[:8]+".json")
        commands=[]
        pipeline.run_command([pipeline.find_cli(),"pcb","drc","--format","json","--severity-all","--schematic-parity",
                              "--refill-zones","--save-board","--output",output,board_path],EVIDENCE,"filled-"+label,commands,output)
        report=json.loads(output.read_text(encoding="utf-8"))
        runs[label]={"project":str(project),"pcb_sha256":pipeline.digest(board_path),"commands":commands,
                     "violations":len(report["violations"]),"unconnected":len(report["unconnected_items"]),"parity":len(report["schematic_parity"])}
    original=snapshot(before/(pipeline.STEM+".kicad_pcb"))
    repaired=snapshot(work/(pipeline.STEM+".kicad_pcb"))
    changed_pads=[]
    unexpected=[]
    for identifier,pad in original["pads"].items():
        expected=dict(pad)
        if pad["reference"] in POSITIONS:
            center=POSITIONS[pad["reference"]]
            expected["position"]=[round((center[0]+(-1.475 if pad["pin"]=="1" else 1.475))*1000000),round(center[1]*1000000)]
            expected["size"]=[1150000,2700000]
            changed_pads.append([pad["reference"],pad["pin"]])
        actual=repaired["pads"].get(identifier)
        compatible=actual is not None and all(expected[key]==actual[key] for key in expected if key!="position")
        compatible=compatible and all(abs(expected["position"][index]-actual["position"][index])<=2 for index in (0,1))
        if not compatible:
            unexpected.append({"pad":identifier,"expected":expected,"actual":actual})
    route=json.loads((EVIDENCE/"output-branch-route.json").read_text(encoding="utf-8"))
    removed=set(original["tracks"])-set(repaired["tracks"])
    added=set(repaired["tracks"])-set(original["tracks"])
    changed=[identifier for identifier,track in original["tracks"].items() if identifier in repaired["tracks"] and repaired["tracks"][identifier]!=track]
    lost={identifier:sorted(set(group)-set(repaired["connections"].get(identifier,[])))
          for identifier,group in original["connections"].items() if not set(group).issubset(repaired["connections"].get(identifier,[]))}
    old_board=pcbnew.LoadBoard(str(before/(pipeline.STEM+".kicad_pcb")))
    board=pcbnew.LoadBoard(str(work/(pipeline.STEM+".kicad_pcb")))
    via_gaps={}
    cap_fields={}
    vias=[item for item in board.GetTracks() if item.Type()==pcbnew.PCB_VIA_T and item.IsOnLayer(pcbnew.F_Cu)]
    for reference in POSITIONS:
        footprint=board.FindFootprintByReference(reference)
        cap_fields[reference]={"value":footprint.GetValue(),"mpn":footprint.GetFieldText("MPN"),"footprint":str(footprint.GetFPID().GetLibItemName())}
        gaps=[]
        for pad in footprint.Pads():
            bounds=pad.GetBoundingBox()
            for via in vias:
                point=via.GetPosition()
                distance=(max(bounds.GetLeft()-point.x,0,point.x-bounds.GetRight())**2+max(bounds.GetTop()-point.y,0,point.y-bounds.GetBottom())**2)**0.5
                gap=pcbnew.ToMM(distance-via.GetFrontWidth()/2-pad.GetSolderMaskExpansion(pcbnew.F_Mask))
                gaps.append((gap,pad.GetNumber(),via.m_Uuid.AsString()))
        via_gaps[reference]=min(gaps)
    tree=parse((work/(pipeline.STEM+".kicad_pcb")).read_text(encoding="utf-8"))
    reserve=next(footprint for footprint in children(tree,"footprint") if properties(footprint).get("Reference")=="C307")
    result={"runs":runs,"changed_pad_keys":changed_pads,"unexpected_pad_changes":unexpected,"position_tolerance_nm":2,
            "pad_keys_unchanged":set(original["pads"])==set(repaired["pads"]),"pad_nets_unchanged":original["nets"]==repaired["nets"],
            "removed_original_tracks":sorted(removed),"expected_removed_tracks":route["removed_original_tracks"],
            "added_tracks":sorted(added),"expected_added_tracks":route["added_tracks"],"changed_other_tracks":changed,"lost_connections":lost,
            "cap_fields":cap_fields,"via_to_cap_mask_bbox_gaps_mm":via_gaps,"c307_dnp_preserved":"dnp" in first(reserve,"attr"),
            "via_process_requirements_preserved":protection(old_board)==protection(board),"protected_via_count":len(protection(board)),
            "project_settings_unchanged":pipeline.digest(work/(pipeline.STEM+".kicad_pro"))==pipeline.digest(pipeline.PRIMARY/(pipeline.STEM+".kicad_pro")),
            "rules_unchanged":pipeline.digest(work/(pipeline.STEM+".kicad_dru"))==pipeline.digest(pipeline.PRIMARY/(pipeline.STEM+".kicad_dru")),
            "production_ready":False}
    result["accepted"]=all((len(changed_pads)==8,not unexpected,result["pad_keys_unchanged"],result["pad_nets_unchanged"],
                            removed==set(route["removed_original_tracks"]),added==set(route["added_tracks"]),not changed,not lost,
                            all(fields=={"value":"22uF","mpn":MPN,"footprint":"C_1210_3225Metric"} for fields in cap_fields.values()),
                            all(gap[0]>0.05 for gap in via_gaps.values()),result["c307_dnp_preserved"],result["via_process_requirements_preserved"],
                            result["protected_via_count"]==6,result["project_settings_unchanged"],result["rules_unchanged"],
                            all(runs["after"][key]==0 for key in ("violations","unconnected","parity"))))
    pipeline.write_json(EVIDENCE/"geometry-connectivity-check.json",result)
    if not result["accepted"]:
        raise RuntimeError("Capacitor upgrade verification failed")
    reports,summary=pipeline.check(work)
    candidate["summary"]=str(reports/"summary.json")
    pipeline.write_json(candidate_path,candidate)
    print(json.dumps({"accepted":result["accepted"],"via_gaps":via_gaps,"lost_connections":len(lost),"status":summary["status"]}))


if __name__=="__main__":
    main()
