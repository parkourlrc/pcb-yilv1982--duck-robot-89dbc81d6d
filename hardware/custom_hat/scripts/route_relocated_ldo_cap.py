"""Connect moved C308 directly to LDO input and detour only amplifier enable."""
import json
from pathlib import Path

import pcbnew
import pipeline
import plan_i2s_sdo as planner
from add_i2c_pullups import obstacles, vector
from generate_rev_a import first, parse
from repair_release_metadata import child_spans
from plan_buck_thermal_vias import EVIDENCE


REMOVE = {
    "3e74bf04-f4e0-4bfa-9e62-b26ff8b4ed4c",
    "bce30e35-3e5a-4e8a-b5bc-e6d6e2860bb4",
    "bc8e53b6-9dee-4df6-ab5f-ff79479a1a27",
    "d2216719-5b4b-4512-93e2-10276adb4610",
    "ba4e1c65-b32b-48c9-babb-5272c28562fa",
    "a8f9c369-051b-4721-ac6f-48429444c23b",
}


def main():
    candidate_path = EVIDENCE/"candidate.json"
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    work = pipeline.managed(Path(candidate["project"]))
    board_path = work/(pipeline.STEM+".kicad_pcb")
    original = board_path.read_text(encoding="utf-8")
    removed = []
    for start, end, block in reversed(list(child_spans(original))):
        node = parse(block)
        if node[0] not in {"segment", "via"}:
            continue
        identifier = first(node, "uuid")[1]
        if identifier in REMOVE:
            removed.append(str(identifier))
            original = original[:start]+original[end:]
    if set(removed)!=REMOVE:
        raise RuntimeError("Candidate baseline changed")
    board_path.write_text(original, encoding="utf-8")
    board = pcbnew.LoadBoard(str(board_path))
    capacitor = board.FindFootprintByReference("C308")
    capacitor.SetPosition(vector((123.7,115.6)))
    capacitor.SetOrientationDegrees(90)
    power_pad = next(pad for pad in capacitor.Pads() if pad.GetNumber()=="1")
    input_pad = next(pad for pad in board.FindFootprintByReference("U702").Pads() if pad.GetNumber()=="3")
    enable_pad = next(pad for pad in board.FindFootprintByReference("R311").Pads() if pad.GetNumber()=="1")
    planner.EVIDENCE = EVIDENCE
    planner.LAYERS = ["B.Cu"]
    planner.STEP = 0.025
    planner.XMIN,planner.YMIN,planner.XMAX,planner.YMAX = 119,112,129,123
    planner.COLS=round((planner.XMAX-planner.XMIN)/planner.STEP)+1
    planner.ROWS=round((planner.YMAX-planner.YMIN)/planner.STEP)+1
    planner.SIZE=planner.COLS*planner.ROWS
    routes=[]
    for net, width, start, end in (
        ("+3V3",0.3,tuple(pcbnew.ToMM(value) for value in power_pad.GetPosition()),tuple(pcbnew.ToMM(value) for value in input_pad.GetPosition())),
        ("AUDIO_AMP_EN",0.25,tuple(pcbnew.ToMM(value) for value in enable_pad.GetPosition()),(123.3713,121.1586)),
    ):
        planner.WIDTH=width
        plan=planner.solve(obstacles(board),net,start,end,[0],0)
        identifiers=[]
        for first_point,last_point in zip(plan["points"],plan["points"][1:]):
            if first_point[:2]==last_point[:2]:
                continue
            track=pcbnew.PCB_TRACK(board)
            track.SetStart(vector(first_point[:2]))
            track.SetEnd(vector(last_point[:2]))
            track.SetWidth(pcbnew.FromMM(width))
            track.SetLayer(pcbnew.B_Cu)
            track.SetNetCode(board.FindNet(net).GetNetCode())
            board.Add(track)
            identifiers.append(track.m_Uuid.AsString())
        plan["added_tracks"]=identifiers
        routes.append(plan)
    pcbnew.SaveBoard(str(board_path),board)
    pipeline.write_json(EVIDENCE/"ldo-cap-routes.json",{"removed_original_objects":sorted(REMOVE),"routes":routes,"capacitor_position":[123.7,115.6,90]})
    reports,summary=pipeline.check(work)
    candidate["summary"]=str(reports/"summary.json")
    pipeline.write_json(candidate_path,candidate)
    print(json.dumps({"drc":summary["drc"],"status":summary["status"]}))


if __name__=="__main__":
    main()
