"""Finish the capacitor clearance and simplify the new low-current 5V tap."""
import json
from pathlib import Path

import pcbnew
import pipeline
from add_i2c_pullups import vector
from generate_rev_a import first, parse
from repair_release_metadata import child_spans
from inspect_buck_control import EVIDENCE
from relayout_buck_control import PLACEMENTS, pad, mm_position


def main():
    candidate_path=EVIDENCE/"candidate.json"
    candidate=json.loads(candidate_path.read_text(encoding="utf-8"))
    work=pipeline.managed(Path(candidate["project"]))
    board_path=work/(pipeline.STEM+".kicad_pcb")
    board=pcbnew.LoadBoard(str(board_path))
    capacitor=board.FindFootprintByReference("C301")
    old_pad=list(pad(board,"C301","1").GetPosition())
    capacitor.SetPosition(vector(PLACEMENTS["C301"][:2]))
    new_pad=pad(board,"C301","1").GetPosition()
    plans=json.loads((EVIDENCE/"control-route-plan.json").read_text(encoding="utf-8"))
    for track in board.GetTracks():
        if track.Type()!=pcbnew.PCB_VIA_T and track.GetNetname()=="COMP_RC":
            if list(track.GetStart())==old_pad:
                track.SetStart(new_pad)
            if list(track.GetEnd())==old_pad:
                track.SetEnd(new_pad)
    rc=next(route for route in plans["routes"] if route["net"]=="COMP_RC")
    rc["points"][-1]=[*mm_position(pad(board,"C301","1")),0]
    power=next(route for route in plans["routes"] if route["net"]=="+5V")
    shapes=[item.GetEffectiveShape(pcbnew.F_Cu) for footprint in board.GetFootprints() for item in footprint.Pads()
            if item.IsOnLayer(pcbnew.F_Cu) and item.GetNetname()!="+5V"]
    shapes.extend(item.GetEffectiveShape(pcbnew.F_Cu) for item in board.GetTracks() if item.IsOnLayer(pcbnew.F_Cu) and item.GetNetname()!="+5V")
    probe=pcbnew.PCB_TRACK(board)
    probe.SetLayer(pcbnew.F_Cu)
    probe.SetWidth(pcbnew.FromMM(0.25))
    points=power["points"]
    simplified=[points[0]]
    cursor=0
    while cursor<len(points)-1:
        selected=cursor+1
        for end in range(len(points)-1,cursor+1,-1):
            probe.SetStart(vector(points[cursor][:2]))
            probe.SetEnd(vector(points[end][:2]))
            shape=probe.GetEffectiveShape(pcbnew.F_Cu)
            if not any(obstacle.Collide(shape,pcbnew.FromMM(0.205)) for obstacle in shapes):
                selected=end
                break
        simplified.append(points[selected])
        cursor=selected
    pcbnew.SaveBoard(str(board_path),board)
    text=board_path.read_text(encoding="utf-8")
    previous_ids=set(power["added_tracks"])
    removed=set()
    for start,end,block in reversed(list(child_spans(text,"segment"))):
        node=parse(block)
        identifier=str(first(node,"uuid")[1])
        if identifier in previous_ids:
            removed.add(identifier)
            text=text[:start]+text[end:]
    if removed!=previous_ids:
        raise RuntimeError("The power tap changed unexpectedly")
    board_path.write_text(text,encoding="utf-8")
    board=pcbnew.LoadBoard(str(board_path))
    new_ids=[]
    for start,end in zip(simplified,simplified[1:]):
        track=pcbnew.PCB_TRACK(board)
        track.SetStart(vector(start[:2]))
        track.SetEnd(vector(end[:2]))
        track.SetWidth(pcbnew.FromMM(0.25))
        track.SetLayer(pcbnew.F_Cu)
        track.SetNetCode(board.FindNet("+5V").GetNetCode())
        board.Add(track)
        new_ids.append(track.m_Uuid.AsString())
    power["pre_native_simplification_points"]=points
    power["points"]=simplified
    power["added_tracks"]=new_ids
    pcbnew.SaveBoard(str(board_path),board)
    pipeline.write_json(EVIDENCE/"control-route-plan.json",plans)
    placement=json.loads((EVIDENCE/"placement-contract.json").read_text(encoding="utf-8"))
    placement["positions"]=PLACEMENTS
    pipeline.write_json(EVIDENCE/"placement-contract.json",placement)
    reports,summary=pipeline.check(work)
    candidate["summary"]=str(reports/"summary.json")
    pipeline.write_json(candidate_path,candidate)
    print(json.dumps({"drc":summary["drc"],"status":summary["status"],"power_tap_segments_before":len(previous_ids),"power_tap_segments_after":len(new_ids)}))


if __name__=="__main__":
    main()
