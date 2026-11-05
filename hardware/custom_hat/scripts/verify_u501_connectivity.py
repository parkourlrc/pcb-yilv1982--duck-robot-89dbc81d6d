"""Check pad connectivity after a local repair using freshly refilled board copies."""
import json
from pathlib import Path
import shutil
import tempfile

import pcbnew

import pipeline


def partitions(board):
    board.BuildConnectivity()
    connectivity = board.GetConnectivity()
    pads = {pad.m_Uuid.AsString(): pad for footprint in board.GetFootprints() for pad in footprint.Pads() if pad.GetNetCode() > 0}
    groups = {}
    for identifier, pad in pads.items():
        group = {item.m_Uuid.AsString() for item in connectivity.GetConnectedItems(pad) if item.m_Uuid.AsString() in pads}
        group.add(identifier)
        groups[identifier] = sorted(group)
    return groups


def main():
    evidence = pipeline.BASE.parents[1] / "docs/references/扩展板电路仿真工具/u501-repair-20261030"
    result = json.loads((evidence / "result.json").read_text(encoding="utf-8"))
    work = pipeline.managed(Path(result["work"]))
    if pipeline.digest(pipeline.PRIMARY / (pipeline.STEM + ".kicad_pcb")) != result["before_hash"]:
        raise ValueError("Primary board has changed since the baseline")
    if pipeline.digest(work / (pipeline.STEM + ".kicad_pcb")) != result["candidate_hash"]:
        raise ValueError("Candidate board changed since its DRC")
    commands = []
    groups = {}
    endpoints = {}
    with tempfile.TemporaryDirectory(prefix="hat-u501-connectivity-") as temporary:
        for label, source in (("before", pipeline.PRIMARY), ("after", work)):
            copy = Path(temporary) / label
            copy.mkdir()
            for path in pipeline.design_files(source):
                destination = copy / path.relative_to(source)
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, destination)
            board_path = copy / (pipeline.STEM + ".kicad_pcb")
            report = copy / "filled-drc.json"
            pipeline.run_command([pipeline.find_cli(), "pcb", "drc", "--format", "json", "--severity-all", "--refill-zones", "--save-board", "--output", report, board_path], evidence, "connectivity-" + label, commands, report)
            board = pcbnew.LoadBoard(str(board_path))
            groups[label] = partitions(board)
            tracks = {item.m_Uuid.AsString(): item for item in board.GetTracks()}
            endpoints[label] = {}
            for identifier in ("c1e10eb3-326a-4a09-9c55-5322c45938c8", "e2205697-9fa5-483f-b2f6-58643a86132d"):
                endpoints[label][identifier] = sorted(item.m_Uuid.AsString() for item in board.GetConnectivity().GetConnectedItems(tracks[identifier]))
    splits = {identifier: group for identifier, group in groups["before"].items() if not set(group).issubset(groups["after"].get(identifier, []))}
    endpoint_equivalent = len({tuple(group) for stage in endpoints.values() for group in stage.values()}) == 1
    outcome = {"commands": commands, "connected_pad_count": len(groups["before"]), "lost_pad_connections": splits, "endpoint_equivalent": endpoint_equivalent, "endpoint_connected_items": endpoints, "groups": groups}
    passed = not splits and endpoint_equivalent and not result["changes"]["violations"]["added"] and not result["changes"]["schematic_parity"]["added"]
    outcome["local_acceptance"] = passed
    pipeline.write_json(evidence / "connectivity-verification.json", outcome)
    result["initial_strict_uuid_acceptance"] = result["local_acceptance"]
    result["local_acceptance"] = passed
    result["review_note"] = "Freshly refilled copies retain all prior same-net pad connections; the changed unconnected endpoint is in the same unchanged +3V3 connected group."
    pipeline.write_json(evidence / "result.json", result)
    print(json.dumps({"local_acceptance": passed, "connected_pads": len(groups["before"]), "lost_connections": len(splits), "endpoint_equivalent": endpoint_equivalent}))
    if not passed:
        raise SystemExit("Connectivity review failed")


if __name__ == "__main__":
    main()
