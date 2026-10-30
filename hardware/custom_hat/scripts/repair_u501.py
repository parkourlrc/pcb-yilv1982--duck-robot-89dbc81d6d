"""Remove three verified erroneous copper items in an isolated U501 candidate."""
from collections import Counter
from pathlib import Path
import shutil

import pcbnew

import pipeline


TARGETS = {
    "ebdf4b90-3164-4fa7-8ca2-9c2850c48825": ("POWER_GND", "F.Cu", "track"),
    "9b58a3e5-36c2-440f-a1fb-3ec48dd252e1": ("POWER_GND", "F.Cu", "via"),
    "e97b81a0-7baf-4cb1-bec1-2dbb08172812": ("+1V8_CODEC", "F.Cu", "track"),
}


def geometry(board):
    items = []
    for footprint in board.GetFootprints():
        for pad in footprint.Pads():
            bounds = pad.GetBoundingBox()
            items.append({
                "kind": "pad", "reference": footprint.GetReference(), "number": pad.GetNumber(),
                "net": pad.GetNetname(), "layers": [board.GetLayerName(layer) for layer in (pcbnew.F_Cu, pcbnew.B_Cu) if pad.IsOnLayer(layer)],
                "bounds": [pcbnew.ToMM(value) for value in (bounds.GetLeft(), bounds.GetTop(), bounds.GetRight(), bounds.GetBottom())],
            })
        if footprint.GetReference() == "U501":
            for zone in footprint.Zones():
                outline = zone.Outline().Outline(0)
                items.append({"kind": "keepout", "layer": board.GetLayerName(zone.GetLayer()), "points": [
                    [pcbnew.ToMM(outline.CPoint(index).x), pcbnew.ToMM(outline.CPoint(index).y)]
                    for index in range(outline.PointCount())]})
    for item in board.GetTracks():
        width = item.GetFrontWidth() if item.Type() == pcbnew.PCB_VIA_T else item.GetWidth()
        common = {"uuid": item.m_Uuid.AsString(), "net": item.GetNetname(), "layer": item.GetLayerName(), "width": pcbnew.ToMM(width)}
        if item.Type() == pcbnew.PCB_VIA_T:
            common.update(kind="via", position=[pcbnew.ToMM(item.GetPosition().x), pcbnew.ToMM(item.GetPosition().y)], drill=pcbnew.ToMM(item.GetDrill()))
        else:
            common.update(kind="track", start=[pcbnew.ToMM(item.GetStart().x), pcbnew.ToMM(item.GetStart().y)], end=[pcbnew.ToMM(item.GetEnd().x), pcbnew.ToMM(item.GetEnd().y)])
        items.append(common)
    return items


def signature(violation):
    return (violation["type"], violation["severity"], tuple(sorted(item["uuid"] for item in violation["items"])))


def main():
    import json
    root = pipeline.BASE.parents[1]
    evidence = root / "docs/references/hat-simulation-tools-20261029/u501-repair-20261030"
    evidence.mkdir(parents=True, exist_ok=True)
    if (evidence / "result.json").exists():
        raise FileExistsError("Repair already recorded; inspect the existing checkpoint before rerunning")
    work = pipeline.prepare(pipeline.PRIMARY)
    before_dir, before = pipeline.check(work)
    path = work / (pipeline.STEM + ".kicad_pcb")
    shutil.copy2(path, evidence / "before.kicad_pcb")
    board = pcbnew.LoadBoard(str(path))
    pipeline.write_json(evidence / "geometry-before.json", geometry(board))
    matched = {item.m_Uuid.AsString(): item for item in board.GetTracks() if item.m_Uuid.AsString() in TARGETS}
    if set(matched) != set(TARGETS):
        raise ValueError("The source no longer matches the verified U501 baseline")
    removed = []
    for identifier, item in matched.items():
        kind = "via" if item.Type() == pcbnew.PCB_VIA_T else "track"
        if (item.GetNetname(), item.GetLayerName(), kind) != TARGETS[identifier]:
            raise ValueError(f"Copper signature changed: {identifier}")
        position = item.GetPosition()
        if not (159 < pcbnew.ToMM(position.x) < 164 and 108 < pcbnew.ToMM(position.y) < 111):
            raise ValueError(f"Copper moved outside the approved region: {identifier}")
        removed.append(identifier)
        board.Remove(item)
    board.BuildConnectivity()
    pcbnew.SaveBoard(str(path), board)
    after_dir, after = pipeline.check(work)
    after_board = pcbnew.LoadBoard(str(path))
    pipeline.write_json(evidence / "geometry-after.json", geometry(after_board))
    reports = {}
    for label, directory in (("before", before_dir), ("after", after_dir)):
        reports[label] = json.loads((directory / "drc.json").read_text(encoding="utf-8"))
        for name in ("drc.json", "summary.json", "erc.json"):
            shutil.copy2(directory / name, evidence / (label + "-" + name))
    changes = {}
    for category in ("violations", "unconnected_items", "schematic_parity"):
        old = Counter(signature(item) for item in reports["before"][category])
        new = Counter(signature(item) for item in reports["after"][category])
        changes[category] = {"added": list((new - old).elements()), "removed": list((old - new).elements())}
    accepted = not any(changes[category]["added"] for category in changes)
    accepted = accepted and after["netlist_check"]["mismatches"] == before["netlist_check"]["mismatches"]
    accepted = accepted and not after["drc"]["violations"]["types"].get("items_not_allowed", 0)
    accepted = accepted and not after["drc"]["violations"]["types"].get("shorting_items", 0)
    result = {"work": str(work), "removed_uuids": removed, "changes": changes, "local_acceptance": accepted,
              "before_hash": pipeline.digest(evidence / "before.kicad_pcb"), "candidate_hash": pipeline.digest(path),
              "primary_unchanged": before["source_unchanged"] and after["source_unchanged"], "promoted": False}
    shutil.copy2(path, evidence / "after.kicad_pcb")
    pipeline.write_json(evidence / "result.json", result)
    print(json.dumps({"local_acceptance": accepted, "work": str(work), "before": before["drc"], "after": after["drc"]}, ensure_ascii=False))
    if not accepted:
        raise SystemExit("Candidate did not meet local acceptance; main board unchanged")


if __name__ == "__main__":
    main()
