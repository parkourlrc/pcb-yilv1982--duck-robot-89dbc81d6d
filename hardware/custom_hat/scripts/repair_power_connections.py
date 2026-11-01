"""Inspect and repair power connectivity in a complete isolated HAT workspace."""
from collections import Counter
import json
from pathlib import Path
import shutil

import pcbnew

import pipeline
import repair_u501
from verify_u501_connectivity import partitions


EVIDENCE = pipeline.BASE.parents[1] / "docs/references/hat-simulation-tools-20261029/power-repair-20261030"


def main():
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    if (EVIDENCE / "state.json").exists():
        raise FileExistsError("Inspect existing workspace before resuming")
    work = pipeline.prepare(pipeline.PRIMARY)
    reports, summary = pipeline.check(work)
    path = work / (pipeline.STEM + ".kicad_pcb")
    shutil.copy2(path, EVIDENCE / "before.kicad_pcb")
    for name in ("drc.json", "summary.json", "erc.json"):
        shutil.copy2(reports / name, EVIDENCE / ("before-" + name))
    board = pcbnew.LoadBoard(str(path))
    pipeline.write_json(EVIDENCE / "geometry-before.json", repair_u501.geometry(board))
    groups = partitions(board)
    identifiers = {}
    power_pads = []
    for footprint in board.GetFootprints():
        for pad in footprint.Pads():
            identifiers[pad.m_Uuid.AsString()] = footprint.GetReference() + "." + pad.GetNumber()
            if pad.GetNetname() in {"+3V3", "POWER_GND"}:
                power_pads.append({"id": pad.m_Uuid.AsString(), "reference": footprint.GetReference(), "pin": pad.GetNumber(), "net": pad.GetNetname(), "layer": pad.GetLayerName(), "position": [pcbnew.ToMM(pad.GetPosition().x), pcbnew.ToMM(pad.GetPosition().y)]})
    inventory = {}
    for pad in power_pads:
        inventory.setdefault(pad["net"], {})[pad["reference"] + "." + pad["pin"]] = {**pad, "connected_pads": [identifiers[identifier] for identifier in groups[pad["id"]]]}
    pipeline.write_json(EVIDENCE / "power-inventory.json", inventory)
    state = {"work": str(work), "before_hash": pipeline.digest(path), "accepted": [], "attempts": [], "latest_reports": str(reports), "promoted": False}
    pipeline.write_json(EVIDENCE / "state.json", state)
    print(json.dumps({"work": str(work), "power_pads": len(power_pads), "baseline": summary["drc"]}))


if __name__ == "__main__":
    main()
