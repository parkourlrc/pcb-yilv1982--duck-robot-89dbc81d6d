"""Simplify only the new output branch using continuous native copper checks."""
import json
from pathlib import Path

import pcbnew
import pipeline
from add_i2c_pullups import vector
from generate_rev_a import first, parse
from repair_release_metadata import child_spans
from upgrade_buck_capacitors import EVIDENCE


def main():
    candidate_path=EVIDENCE/"candidate.json"
    candidate=json.loads(candidate_path.read_text(encoding="utf-8"))
    work=pipeline.managed(Path(candidate["project"]))
    board_path=work/(pipeline.STEM+".kicad_pcb")
    plan=json.loads((EVIDENCE/"output-branch-route.json").read_text(encoding="utf-8"))
    board=pcbnew.LoadBoard(str(board_path))
    shapes=[pad.GetEffectiveShape(pcbnew.F_Cu) for footprint in board.GetFootprints() for pad in footprint.Pads()
            if pad.IsOnLayer(pcbnew.F_Cu) and pad.GetNetname()!="+5V"]
    shapes.extend(item.GetEffectiveShape(pcbnew.F_Cu) for item in board.GetTracks() if item.IsOnLayer(pcbnew.F_Cu) and item.GetNetname()!="+5V")
    probe=pcbnew.PCB_TRACK(board)
    probe.SetLayer(pcbnew.F_Cu)
    probe.SetWidth(pcbnew.FromMM(0.6))
    points=plan["points"]
    simplified=[points[0]]
    cursor=0
    while cursor<len(points)-1:
        selected=cursor+1
        for endpoint in range(len(points)-1,cursor+1,-1):
            probe.SetStart(vector(points[cursor][:2]))
            probe.SetEnd(vector(points[endpoint][:2]))
            shape=probe.GetEffectiveShape(pcbnew.F_Cu)
            if not any(obstacle.Collide(shape,pcbnew.FromMM(0.205)) for obstacle in shapes):
                selected=endpoint
                break
        simplified.append(points[selected])
        cursor=selected
    old_ids=set(plan["added_tracks"])
    text=board_path.read_text(encoding="utf-8")
    removed=set()
    for start,end,block in reversed(list(child_spans(text,"segment"))):
        identifier=str(first(parse(block),"uuid")[1])
        if identifier in old_ids:
            removed.add(identifier)
            text=text[:start]+text[end:]
    if removed!=old_ids:
        raise RuntimeError("New route changed unexpectedly")
    board_path.write_text(text,encoding="utf-8")
    board=pcbnew.LoadBoard(str(board_path))
    added=[]
    for start,end in zip(simplified,simplified[1:]):
        track=pcbnew.PCB_TRACK(board)
        track.SetStart(vector(start[:2]))
        track.SetEnd(vector(end[:2]))
        track.SetLayer(pcbnew.F_Cu)
        track.SetWidth(pcbnew.FromMM(0.6))
        track.SetNetCode(board.FindNet("+5V").GetNetCode())
        board.Add(track)
        added.append(track.m_Uuid.AsString())
    pcbnew.SaveBoard(str(board_path),board)
    plan["points_before_native_simplification"]=points
    plan["points"]=simplified
    plan["added_tracks"]=added
    pipeline.write_json(EVIDENCE/"output-branch-route.json",plan)
    reports,summary=pipeline.check(work)
    candidate["summary"]=str(reports/"summary.json")
    pipeline.write_json(candidate_path,candidate)
    print(json.dumps({"segments_before":len(old_ids),"segments_after":len(added),"drc":summary["drc"],"status":summary["status"]}))


if __name__=="__main__":
    main()
