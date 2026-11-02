"""Reroute the existing 0.6mm C306-C307 branch around the larger ground pad."""
import json
from pathlib import Path

import pcbnew
import pipeline
import plan_i2s_sdo as planner
from add_i2c_pullups import obstacles, vector
from generate_rev_a import first, parse
from repair_release_metadata import child_spans
from upgrade_buck_capacitors import EVIDENCE


def main():
    candidate_path=EVIDENCE/"candidate.json"
    candidate=json.loads(candidate_path.read_text(encoding="utf-8"))
    work=pipeline.managed(Path(candidate["project"]))
    board_path=work/(pipeline.STEM+".kicad_pcb")
    board=pcbnew.LoadBoard(str(board_path))
    start_pad=next(pad for pad in board.FindFootprintByReference("C307").Pads() if pad.GetNumber()=="1")
    target_pad=next(pad for pad in board.FindFootprintByReference("C306").Pads() if pad.GetNumber()=="1")
    tracks=list(board.GetTracks())
    current=tuple(start_pad.GetPosition())
    removed=[]
    terminal=None
    for _ in range(500):
        point=pcbnew.VECTOR2I(*current)
        if target_pad.GetEffectiveShape(pcbnew.F_Cu).Collide(point):
            terminal=current
            break
        adjacent=[track for track in tracks if track.Type()!=pcbnew.PCB_VIA_T and track.GetNetname()=="+5V" and track.GetLayer()==pcbnew.F_Cu
                  and track.m_Uuid.AsString() not in removed and (tuple(track.GetStart())==current or tuple(track.GetEnd())==current)]
        if len(adjacent)!=1:
            raise RuntimeError("Unexpected branch junction; inspect before modifying")
        track=adjacent[0]
        removed.append(track.m_Uuid.AsString())
        current=tuple(track.GetEnd()) if tuple(track.GetStart())==current else tuple(track.GetStart())
    if terminal is None:
        raise RuntimeError("Did not reach C306")
    text=board_path.read_text(encoding="utf-8")
    found=set()
    for start,end,block in reversed(list(child_spans(text,"segment"))):
        identifier=str(first(parse(block),"uuid")[1])
        if identifier in removed:
            found.add(identifier)
            text=text[:start]+text[end:]
    if found!=set(removed):
        raise RuntimeError("Branch source changed")
    board_path.write_text(text,encoding="utf-8")
    board=pcbnew.LoadBoard(str(board_path))
    planner.EVIDENCE=EVIDENCE
    planner.LAYERS=["F.Cu"]
    planner.STEP=0.025
    planner.WIDTH=0.6
    planner.XMIN,planner.YMIN,planner.XMAX,planner.YMAX=150.5,109.5,161.0,118.0
    planner.COLS=round((planner.XMAX-planner.XMIN)/planner.STEP)+1
    planner.ROWS=round((planner.YMAX-planner.YMIN)/planner.STEP)+1
    planner.SIZE=planner.COLS*planner.ROWS
    start=tuple(pcbnew.ToMM(value) for value in terminal)
    end=tuple(pcbnew.ToMM(value) for value in start_pad.GetPosition())
    plan=planner.solve(obstacles(board),"+5V",start,end,[0],0)
    new_ids=[]
    for first_point,last_point in zip(plan["points"],plan["points"][1:]):
        if first_point[:2]==last_point[:2]:
            continue
        track=pcbnew.PCB_TRACK(board)
        track.SetStart(vector(first_point[:2]))
        track.SetEnd(vector(last_point[:2]))
        track.SetLayer(pcbnew.F_Cu)
        track.SetWidth(pcbnew.FromMM(0.6))
        track.SetNetCode(board.FindNet("+5V").GetNetCode())
        board.Add(track)
        new_ids.append(track.m_Uuid.AsString())
    plan["removed_original_tracks"]=removed
    plan["added_tracks"]=new_ids
    plan["from"]="existing C306 positive-pad branch"
    plan["to"]="C307.1"
    pcbnew.SaveBoard(str(board_path),board)
    pipeline.write_json(EVIDENCE/"output-branch-route.json",plan)
    reports,summary=pipeline.check(work)
    candidate["summary"]=str(reports/"summary.json")
    pipeline.write_json(candidate_path,candidate)
    print(json.dumps({"removed_segments":len(removed),"added_segments":len(new_ids),"drc":summary["drc"],"status":summary["status"]}))


if __name__=="__main__":
    main()
