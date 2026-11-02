"""Widen the traced main 5V header feed while preserving its feedback branch."""
import json

import pcbnew

import pipeline
from add_i2c_pullups import vector
from inspect_five_volt_paths import EVIDENCE, BASELINE


HEADER_PATH = {
    "907da572-226d-4ecb-b0f0-02e0822f4440": ((108.32, 102.05), (106.25, 102.05)),
    "fb4c44bb-8a49-41e6-b3b9-e206c3c71fad": ((106.25, 102.05), (106.25, 106.4)),
    "f333f4b2-5629-4629-9bb5-ea077b856a8d": ((106.25, 106.4), (121.69, 106.4)),
    "f9dc6536-6fcb-49c2-b0d4-6c11388f9dea": ((121.69, 106.4), (122.1278, 106.838)),
}


def main():
    candidate_path = EVIDENCE / "candidate.json"
    if candidate_path.exists():
        raise FileExistsError("Review existing 5V candidate before retry")
    source = pipeline.PRIMARY / (pipeline.STEM + ".kicad_pcb")
    if pipeline.digest(source) != BASELINE:
        raise RuntimeError("Primary baseline changed")
    work = pipeline.prepare(pipeline.PRIMARY)
    path = work / source.name
    candidate = {"project": str(work), "baseline": BASELINE, "promoted": False}
    pipeline.write_json(candidate_path, candidate)
    board = pcbnew.LoadBoard(str(path))
    changes = []
    for item in board.GetTracks():
        if item.Type() == pcbnew.PCB_VIA_T or item.GetNetname() != "+5V":
            continue
        identifier = item.m_Uuid.AsString()
        start = [pcbnew.ToMM(value) for value in item.GetStart()]
        end = [pcbnew.ToMM(value) for value in item.GetEnd()]
        inner_trunk = item.GetLayer() == pcbnew.In1_Cu and max(start[1], end[1]) <= 115.02
        header_bridge = identifier == "281bcde8-5d04-4765-a26d-002d523b7e94"
        if not inner_trunk and identifier not in HEADER_PATH and not header_bridge:
            continue
        before = {"start": start, "end": end, "width_mm": pcbnew.ToMM(item.GetWidth())}
        item.SetWidth(pcbnew.FromMM(1.2))
        if identifier in HEADER_PATH:
            new_start, new_end = HEADER_PATH[identifier]
            item.SetStart(vector(new_start))
            item.SetEnd(vector(new_end))
        changes.append({"id": identifier, "layer": item.GetLayerName(), "net": item.GetNetname(), "before": before,
                        "after": {"start": [pcbnew.ToMM(value) for value in item.GetStart()], "end": [pcbnew.ToMM(value) for value in item.GetEnd()], "width_mm": 1.2}})
    if not set(HEADER_PATH).issubset({entry["id"] for entry in changes}):
        raise RuntimeError("Header-feed source objects missing")
    pcbnew.SaveBoard(str(path), board)
    pipeline.write_json(EVIDENCE / "header-route-contract.json", {"baseline": BASELINE, "changes": changes,
                        "preserved": ["all footprints", "net assignments", "feedback sense branch", "other routing", "rules", "project settings"],
                        "whole_board_current_rating_approved": False})
    reports, summary = pipeline.check(work)
    candidate["summary"] = str(reports / "summary.json")
    pipeline.write_json(candidate_path, candidate)
    print(json.dumps({"changed_segments": len(changes), "drc": summary["drc"], "erc": summary["erc"], "status": summary["status"]}))


if __name__ == "__main__":
    main()
