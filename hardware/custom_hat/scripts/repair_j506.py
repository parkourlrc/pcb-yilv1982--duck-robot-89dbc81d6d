"""Move the vertical speaker socket into the inspected local gap in a full copy."""
import json
import shutil

import pcbnew

import pipeline
import repair_u501


def point(xpos, ypos):
    return pcbnew.VECTOR2I(pcbnew.FromMM(xpos), pcbnew.FromMM(ypos))


def main():
    evidence = pipeline.BASE.parents[1] / "docs/references/hat-simulation-tools-20261029/j506-repair-20261030"
    evidence.mkdir(exist_ok=True)
    if (evidence / "result.json").exists():
        raise FileExistsError("Existing repair record must be inspected first")
    work = pipeline.prepare(pipeline.PRIMARY)
    before_dir, before = pipeline.check(work)
    path = work / (pipeline.STEM + ".kicad_pcb")
    shutil.copy2(path, evidence / "before.kicad_pcb")
    board = pcbnew.LoadBoard(str(path))
    original = repair_u501.geometry(board)
    socket = board.FindFootprintByReference("J506")
    old_positions = {pad.GetNetname(): pad.GetPosition() for pad in socket.Pads() if pad.GetNumber() in {"1", "2"}}
    if socket.GetPosition() != point(113.43, 126.05) or socket.GetOrientationDegrees() != 0:
        raise ValueError("J506 no longer matches the inspected placement")
    socket.SetPosition(point(113.0, 122.3))
    new_positions = {pad.GetNetname(): pad.GetPosition() for pad in socket.Pads() if pad.GetNumber() in {"1", "2"}}
    changed = []
    for track in board.GetTracks():
        net = track.GetNetname()
        if net not in old_positions or track.Type() == pcbnew.PCB_VIA_T or track.GetLayer() != pcbnew.B_Cu:
            continue
        if track.GetStart() == old_positions[net]:
            track.SetStart(new_positions[net])
            changed.append(track.m_Uuid.AsString())
        elif track.GetEnd() == old_positions[net]:
            track.SetEnd(new_positions[net])
            changed.append(track.m_Uuid.AsString())
    if len(changed) != 2:
        raise ValueError(f"Expected two terminal tracks, got {len(changed)}")
    board.BuildConnectivity()
    pcbnew.SaveBoard(str(path), board)
    after_dir, after = pipeline.check(work)
    pipeline.write_json(evidence / "geometry-before.json", original)
    pipeline.write_json(evidence / "geometry-after.json", repair_u501.geometry(pcbnew.LoadBoard(str(path))))
    shutil.copy2(path, evidence / "after.kicad_pcb")
    for label, directory in (("before", before_dir), ("after", after_dir)):
        for name in ("drc.json", "summary.json", "erc.json"):
            shutil.copy2(directory / name, evidence / (label + "-" + name))
    result = {"work": str(work), "changed_tracks": changed, "before_hash": pipeline.digest(evidence / "before.kicad_pcb"), "candidate_hash": pipeline.digest(path), "promoted": False}
    pipeline.write_json(evidence / "result.json", result)
    print(json.dumps({"work": str(work), "before": before["drc"], "after": after["drc"]}))


if __name__ == "__main__":
    main()
