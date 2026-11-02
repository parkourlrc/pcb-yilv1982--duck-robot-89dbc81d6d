"""Keep the relocated input capacitor clear of enable routing and inner-layer power."""
import json
from pathlib import Path

import pcbnew
import pipeline
from add_i2c_pullups import vector
from plan_buck_thermal_vias import EVIDENCE


def main():
    candidate_path=EVIDENCE/"candidate.json"
    candidate=json.loads(candidate_path.read_text(encoding="utf-8"))
    work=pipeline.managed(Path(candidate["project"]))
    board_path=work/(pipeline.STEM+".kicad_pcb")
    board=pcbnew.LoadBoard(str(board_path))
    entry=json.loads((EVIDENCE/"input-cap-relocation.json").read_text(encoding="utf-8"))
    ground_via=next(item for item in board.GetTracks() if item.m_Uuid.AsString()==entry["added_ground_via"])
    old_ground=list(ground_via.GetPosition())
    new_ground=vector((129.5,108.2))
    ground_via.SetPosition(new_ground)
    for track in board.GetTracks():
        if track.Type()!=pcbnew.PCB_VIA_T and track.GetNetCode()==ground_via.GetNetCode():
            if list(track.GetStart())==old_ground:
                track.SetStart(new_ground)
            if list(track.GetEnd())==old_ground:
                track.SetEnd(new_ground)
    enable_via=next(item for item in board.GetTracks() if item.m_Uuid.AsString()=="f47fafc7-5fe7-4c36-93b1-acaee80ababf")
    old_enable=list(enable_via.GetPosition())
    new_enable=vector((128.8,110.4))
    changed=[]
    for track in board.GetTracks():
        if track.Type()==pcbnew.PCB_VIA_T or track.GetNetCode()!=enable_via.GetNetCode():
            continue
        modified=False
        if list(track.GetStart())==old_enable:
            track.SetStart(new_enable)
            modified=True
        if list(track.GetEnd())==old_enable:
            track.SetEnd(new_enable)
            modified=True
        if modified:
            changed.append(track.m_Uuid.AsString())
    enable_via.SetPosition(new_enable)
    entry["ground_via_position"]=[129.5,108.2]
    entry["changed_enable_via"]=enable_via.m_Uuid.AsString()
    entry["changed_enable_tracks"]=changed
    entry.setdefault("enable_via_from",[pcbnew.ToMM(value) for value in old_enable])
    entry["enable_via_to"]=[128.8,110.4]
    pcbnew.SaveBoard(str(board_path),board)
    pipeline.write_json(EVIDENCE/"input-cap-relocation.json",entry)
    reports,summary=pipeline.check(work)
    candidate["summary"]=str(reports/"summary.json")
    pipeline.write_json(candidate_path,candidate)
    print(json.dumps({"drc":summary["drc"],"status":summary["status"],"changed_enable_tracks":changed}))


if __name__=="__main__":
    main()
