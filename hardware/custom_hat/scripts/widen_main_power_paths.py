"""Widen the shared battery feed and servo paths without changing electrical interfaces."""
import json
from pathlib import Path

import pcbnew

import pipeline
from add_i2c_pullups import vector


EVIDENCE = pipeline.BASE.parents[1] / "docs/references/hat-simulation-tools-20261029/power-paths-20261031"
BASELINE = "70d00bf6b116b58cafe25cc86a31a63badb70d9f6436431ad7ae98fdb1d5d633"
BATTERY_TRACKS = {"93a89441-6459-41d7-956e-b7dfaa02fade", "e1c190b7-cc1b-41a3-b0ce-d0889a72426a",
                  "e223a735-1756-4d40-87cd-cf00410a7e6e", "5c639288-cbd2-443d-a2d3-c5712368da77", "99f29545-b6d2-4e73-804b-8dfdb1bfa242"}
BOTTOM_PATH = {
    "9096a290-f2f0-49eb-85d9-fa6b1c9c1197": ((110.89, 127.32), (112.72, 129.15)),
    "b4abce8d-34f5-4500-9d72-f1f97b33218f": ((112.72, 129.15), (142.04, 129.15)),
    "bb1bedbb-ebc8-4fd4-85eb-f92f522f78fe": ((142.04, 129.15), (151.49, 119.7)),
}


def main():
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    if (EVIDENCE / "candidate.json").exists():
        raise FileExistsError("Review existing power-path candidate before retry")
    source = pipeline.PRIMARY / (pipeline.STEM + ".kicad_pcb")
    if pipeline.digest(source) != BASELINE:
        raise RuntimeError("Primary power baseline changed")
    work = pipeline.prepare(pipeline.PRIMARY)
    path = work / source.name
    candidate = {"project": str(work), "baseline": BASELINE, "promoted": False}
    pipeline.write_json(EVIDENCE / "candidate.json", candidate)
    board = pcbnew.LoadBoard(str(path))
    changes = []
    for track in board.GetTracks():
        if track.Type() == pcbnew.PCB_VIA_T:
            continue
        identifier = track.m_Uuid.AsString()
        if identifier not in BATTERY_TRACKS and track.GetNetname() != "SERVO_VBAT":
            continue
        if track.GetWidth() != pcbnew.FromMM(0.6):
            raise RuntimeError("Power trace baseline width changed")
        before = {"start": [pcbnew.ToMM(value) for value in track.GetStart()], "end": [pcbnew.ToMM(value) for value in track.GetEnd()], "width_mm": 0.6}
        track.SetWidth(pcbnew.FromMM(1.2))
        if identifier in BOTTOM_PATH:
            start, end = BOTTOM_PATH[identifier]
            track.SetStart(vector(start))
            track.SetEnd(vector(end))
        changes.append({"id": identifier, "net": track.GetNetname(), "layer": track.GetLayerName(), "before": before,
                        "after": {"start": [pcbnew.ToMM(value) for value in track.GetStart()], "end": [pcbnew.ToMM(value) for value in track.GetEnd()], "width_mm": 1.2}})
    if len(changes) != 12 or not BATTERY_TRACKS.issubset({entry["id"] for entry in changes}):
        raise RuntimeError("Expected five battery and seven servo segments")
    pcbnew.SaveBoard(str(path), board)
    pipeline.write_json(EVIDENCE / "power-route-contract.json", {"baseline": BASELINE, "changes": changes,
                        "purpose": "Reduce positive-conductor resistance in shared input and servo paths; not a board current-rating claim",
                        "fixed": ["footprints", "net assignments", "other routing", "project settings", "design rules", "board outline"]})
    reports, summary = pipeline.check(work)
    candidate["summary"] = str(reports / "summary.json")
    pipeline.write_json(EVIDENCE / "candidate.json", candidate)
    print(json.dumps({"work": str(work), "drc": summary["drc"], "erc": summary["erc"], "status": summary["status"]}))


if __name__ == "__main__":
    main()
