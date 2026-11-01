"""Route SPK_N through the socket pad corridor and validate the complete candidate."""
from collections import Counter
import json
from pathlib import Path
import shutil
import tempfile

import pcbnew

import pipeline
import repair_u501
from repair_j506 import point
from verify_u501_connectivity import partitions


def main():
    evidence = pipeline.BASE.parents[1] / "docs/references/hat-simulation-tools-20261029/j506-repair-20261030"
    result = json.loads((evidence / "result.json").read_text(encoding="utf-8"))
    work = pipeline.managed(Path(result["work"]))
    board_path = work / (pipeline.STEM + ".kicad_pcb")
    if pipeline.digest(board_path) != result["candidate_hash"]:
        raise ValueError("Candidate changed")
    if pipeline.digest(pipeline.PRIMARY / board_path.name) != result["before_hash"]:
        raise ValueError("Primary changed")
    for name in ("drc.json", "summary.json", "erc.json", "geometry-after.json", "result.json"):
        original = evidence / ("after-" + name if name in {"drc.json", "summary.json", "erc.json"} else name)
        shutil.copy2(original, evidence / ("attempt1-" + original.name))
    board = pcbnew.LoadBoard(str(board_path))
    track = next(item for item in board.GetTracks() if item.m_Uuid.AsString() == "b36a5d11-96fe-41bf-a286-55caf085c336")
    if track.GetNetname() != "SPK_N" or track.GetLayer() != pcbnew.B_Cu:
        raise ValueError("Terminal track signature changed")
    track.SetStart(point(117.0853, 124.725))
    track.SetEnd(point(113.725, 124.725))
    created = []
    for start, end in [((113.725, 124.725), (113.5, 124.5)), ((113.5, 124.5), (113.5, 120.975))]:
        segment = pcbnew.PCB_TRACK(board)
        segment.SetStart(point(*start))
        segment.SetEnd(point(*end))
        segment.SetWidth(track.GetWidth())
        segment.SetLayer(pcbnew.B_Cu)
        segment.SetNet(track.GetNet())
        board.Add(segment)
        created.append(segment.m_Uuid.AsString())
    board.BuildConnectivity()
    pcbnew.SaveBoard(str(board_path), board)
    after_dir, after = pipeline.check(work)
    for name in ("drc.json", "summary.json", "erc.json"):
        shutil.copy2(after_dir / name, evidence / ("after-" + name))
    shutil.copy2(board_path, evidence / "after.kicad_pcb")
    pipeline.write_json(evidence / "geometry-after.json", repair_u501.geometry(pcbnew.LoadBoard(str(board_path))))
    reports = {label: json.loads((evidence / (label + "-drc.json")).read_text(encoding="utf-8")) for label in ("before", "after")}
    changes = {}
    for category in ("violations", "unconnected_items", "schematic_parity"):
        old = Counter(repair_u501.signature(item) for item in reports["before"][category])
        new = Counter(repair_u501.signature(item) for item in reports["after"][category])
        changes[category] = {"added": list((new-old).elements()), "removed": list((old-new).elements())}
    groups = {}
    commands = []
    with tempfile.TemporaryDirectory(prefix="hat-j506-connectivity-") as temporary:
        for label, source in (("before", pipeline.PRIMARY), ("after", work)):
            copy = Path(temporary) / label
            copy.mkdir()
            for path in pipeline.design_files(source):
                destination = copy / path.relative_to(source)
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, destination)
            path = copy / board_path.name
            report = copy / "filled-drc.json"
            pipeline.run_command([pipeline.find_cli(), "pcb", "drc", "--format", "json", "--severity-all", "--refill-zones", "--save-board", "--output", report, path], evidence, "connectivity-" + label, commands, report)
            groups[label] = partitions(pcbnew.LoadBoard(str(path)))
    splits = {identifier: connected for identifier, connected in groups["before"].items() if not set(connected).issubset(groups["after"].get(identifier, []))}
    accepted = not changes["violations"]["added"] and not changes["schematic_parity"]["added"] and not splits
    accepted = accepted and len(reports["after"]["unconnected_items"]) <= len(reports["before"]["unconnected_items"])
    accepted = accepted and not after["netlist_check"]["mismatches"] and not after["netlist_check"]["contract_differences"]
    pipeline.write_json(evidence / "connectivity-verification.json", {"commands": commands, "groups": groups, "lost_pad_connections": splits})
    result.update(changes=changes, added_tracks=created, candidate_hash=pipeline.digest(board_path), local_acceptance=bool(accepted), promoted=False)
    pipeline.write_json(evidence / "result.json", result)
    print(json.dumps({"local_acceptance": bool(accepted), "lost_pad_connections": len(splits), "drc": after["drc"]}))
    if not accepted:
        raise SystemExit("Candidate rejected; primary unchanged")


if __name__ == "__main__":
    main()
