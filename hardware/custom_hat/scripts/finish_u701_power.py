"""Connect the final U701.7 +3V3 pad to R308.2 in an isolated full workspace."""
from collections import Counter
import json
from pathlib import Path
import shutil
import tempfile

import pcbnew

import pipeline
import plan_i2s_sdo as planner
import repair_u501
from verify_u501_connectivity import partitions
from power_repair_steps import EVIDENCE


def sig(item):
    return (item["type"], item["severity"], tuple(sorted(entry["uuid"] for entry in item["items"])))


def main():
    evidence = Path(__import__('os').environ.get('U701_EVIDENCE', str(pipeline.BASE.parents[1] / 'docs/references/hat-simulation-tools-20261029/u701-power-20261030')))
    evidence.mkdir(parents=True, exist_ok=True)
    if (evidence / "result.json").exists():
        raise FileExistsError("Existing U701 power record must be reviewed first")
    work = pipeline.prepare(pipeline.PRIMARY)
    before_dir, before = pipeline.check(work)
    board_path = work / (pipeline.STEM + ".kicad_pcb")
    shutil.copy2(board_path, evidence / "before.kicad_pcb")
    for name in ("drc.json", "summary.json", "erc.json"):
        shutil.copy2(before_dir / name, evidence / ("before-" + name))
    board = pcbnew.LoadBoard(str(board_path))
    geometry = repair_u501.geometry(board)
    for item in geometry:
        if item["kind"] == "pad" and set(item["layers"]) == {"F.Cu", "B.Cu"}:
            item["layers"] = planner.LAYERS[:]
    planner.XMIN, planner.YMIN, planner.XMAX, planner.YMAX = 144.0, 108.0, 153.0, 116.0
    planner.STEP = 0.05
    planner.WIDTH = 0.15
    planner.COLS = round((planner.XMAX - planner.XMIN) / planner.STEP) + 1
    planner.ROWS = round((planner.YMAX - planner.YMIN) / planner.STEP) + 1
    planner.SIZE = planner.COLS * planner.ROWS
    plan = planner.solve(geometry, "+3V3", (146.96, 110.81), (150.3625, 112.1))
    pipeline.write_json(evidence / "route-plan.json", plan)
    old_tracks = {item.m_Uuid.AsString(): item for item in board.GetTracks()}

    def add_track(net, layer, start, end, width):
        item = pcbnew.PCB_TRACK(board)
        item.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(start[0]), pcbnew.FromMM(start[1])))
        item.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(end[0]), pcbnew.FromMM(end[1])))
        item.SetWidth(pcbnew.FromMM(width))
        item.SetLayer(board.GetLayerID(layer))
        item.SetNet(board.FindNet(net))
        board.Add(item)

    for start, end in zip(plan["points"], plan["points"][1:]):
        if start[2] != end[2]:
            via = pcbnew.PCB_VIA(board)
            via.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(start[0]), pcbnew.FromMM(start[1])))
            via.SetWidth(pcbnew.FromMM(plan["via_diameter"]))
            via.SetDrill(pcbnew.FromMM(plan["via_drill"]))
            via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
            via.SetNet(board.FindNet("+3V3"))
            board.Add(via)
        else:
            add_track("+3V3", planner.LAYERS[start[2]], start, end, plan["width"])
    board.BuildConnectivity()
    pcbnew.SaveBoard(str(board_path), board)
    after_dir, after = pipeline.check(work)
    shutil.copy2(board_path, evidence / "after.kicad_pcb")
    for name in ("drc.json", "summary.json", "erc.json"):
        shutil.copy2(after_dir / name, evidence / ("after-" + name))
    pipeline.write_json(evidence / "geometry-before.json", geometry)
    pipeline.write_json(evidence / "geometry-after.json", repair_u501.geometry(pcbnew.LoadBoard(str(board_path))))
    reports = {name: json.loads((evidence / (name + "-drc.json")).read_text(encoding="utf-8")) for name in ("before", "after")}
    changes = {}
    for category in ("violations", "unconnected_items", "schematic_parity"):
        old = Counter(sig(item) for item in reports["before"][category])
        new = Counter(sig(item) for item in reports["after"][category])
        changes[category] = {"added": list((new - old).elements()), "removed": list((old - new).elements())}
    groups = {}
    commands = []
    with tempfile.TemporaryDirectory(prefix="hat-u701-connectivity-") as temporary:
        for label, source in (("before", pipeline.PRIMARY), ("after", work)):
            copied = Path(temporary) / label
            copied.mkdir()
            for source_path in pipeline.design_files(source):
                target = copied / source_path.relative_to(source)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_path, target)
            copied_board = copied / board_path.name
            report = copied / "filled-drc.json"
            pipeline.run_command([pipeline.find_cli(), "pcb", "drc", "--format", "json", "--severity-all", "--refill-zones", "--save-board", "--output", report, copied_board], evidence, "connectivity-" + label, commands, report)
            groups[label] = partitions(pcbnew.LoadBoard(str(copied_board)))
    lost = {identifier: connected for identifier, connected in groups["before"].items() if not set(connected).issubset(groups["after"].get(identifier, []))}
    sdo = False
    after_board = pcbnew.LoadBoard(str(board_path))
    after_groups = partitions(after_board)
    all_pads = {pad.m_Uuid.AsString(): footprint.GetReference() + "." + pad.GetNumber() for footprint in after_board.GetFootprints() for pad in footprint.Pads()}
    u701 = next(pad.m_Uuid.AsString() for pad in after_board.FindFootprintByReference("U701").Pads() if pad.GetNumber() == "7")
    r308 = next(pad.m_Uuid.AsString() for pad in after_board.FindFootprintByReference("R308").Pads() if pad.GetNumber() == "2")
    sdo = r308 in after_groups.get(u701, [])
    accepted = not any(changes[category]["added"] for category in changes)
    accepted = accepted and not lost and sdo and after["drc"]["unconnected_items"]["count"] < before["drc"]["unconnected_items"]["count"]
    accepted = accepted and not after["netlist_check"]["mismatches"] and not after["netlist_check"]["contract_differences"]
    pipeline.write_json(evidence / "connectivity-verification.json", {"commands": commands, "lost_connections": lost, "u701_7_to_r308_2": sdo, "groups": groups})
    result = {"work": str(work), "before_hash": pipeline.digest(evidence / "before.kicad_pcb"), "candidate_hash": pipeline.digest(board_path), "route": plan, "changes": changes, "local_acceptance": bool(accepted), "promoted": False, "before": before["drc"], "after": after["drc"]}
    pipeline.write_json(evidence / "result.json", result)
    print(json.dumps({"accepted": bool(accepted), "u701_7_to_r308_2": sdo, "lost_connections": len(lost), "before": before["drc"], "after": after["drc"]}, ensure_ascii=False))
    if not accepted:
        raise SystemExit("U701 power candidate rejected; primary unchanged")


if __name__ == "__main__":
    main()
