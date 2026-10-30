"""Try moving the existing I2S_SDO via to free the U701.7 power corridor."""
import json
from pathlib import Path
import shutil
import subprocess

import pcbnew

import pipeline
import plan_i2s_sdo as planner
import repair_u501
from finish_u701_power import sig


EVIDENCE = pipeline.BASE.parents[1] / "docs/references/hat-simulation-tools-20261029/u701-power-shift-20261030"
OLD_VIA = (149.1, 111.95)
F_SEG = "c5d4af8b-f46e-441b-a03e-d844543e0c80"
B_SEG = "2a881d9d-5f8c-48c5-a258-c55298ef4351"


def main():
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    if (EVIDENCE / "result.json").exists():
        raise FileExistsError("Existing result")
    source = pipeline.PRIMARY
    before_workspace = pipeline.prepare(source)
    before_dir, before = pipeline.check(before_workspace)
    source_board = before_workspace / (pipeline.STEM + ".kicad_pcb")
    geometry = repair_u501.geometry(pcbnew.LoadBoard(str(source_board)))
    for item in geometry:
        if item["kind"] == "pad" and set(item["layers"]) == {"F.Cu", "B.Cu"}:
            item["layers"] = planner.LAYERS[:]
    planner.XMIN, planner.YMIN, planner.XMAX, planner.YMAX = 144.0, 108.0, 153.0, 116.0
    planner.STEP, planner.WIDTH = 0.05, 0.15
    planner.COLS = round((planner.XMAX - planner.XMIN) / planner.STEP) + 1
    planner.ROWS = round((planner.YMAX - planner.YMIN) / planner.STEP) + 1
    planner.SIZE = planner.COLS * planner.ROWS
    planner.VIA_AVOID_RADIUS = 0.25
    route = planner.solve(geometry, "+3V3", (146.96, 110.81), (150.3625, 112.1))
    attempts = []
    candidates = [(148.1, 111.0), (148.2, 111.2), (148.3, 111.4), (148.4, 111.6), (148.5, 111.8), (148.6, 112.0), (148.7, 111.2), (148.8, 111.4)]
    for index, new_position in enumerate(candidates):
        work = pipeline.prepare(source)
        board_path = work / (pipeline.STEM + ".kicad_pcb")
        board = pcbnew.LoadBoard(str(board_path))
        via = next(item for item in board.GetTracks() if item.Type() == pcbnew.PCB_VIA_T and item.GetNetname() == "I2S_SDO" and abs(pcbnew.ToMM(item.GetPosition().x)-OLD_VIA[0]) < .01 and abs(pcbnew.ToMM(item.GetPosition().y)-OLD_VIA[1]) < .01)
        fseg = next(item for item in board.GetTracks() if item.m_Uuid.AsString() == F_SEG)
        bseg = next(item for item in board.GetTracks() if item.m_Uuid.AsString() == B_SEG)
        via.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(new_position[0]), pcbnew.FromMM(new_position[1])))
        fseg.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(new_position[0]), pcbnew.FromMM(new_position[1])))
        bseg.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(new_position[0]), pcbnew.FromMM(new_position[1])))
        net = board.FindNet("+3V3")
        for first, last in zip(route["points"], route["points"][1:]):
            if first[2] != last[2]:
                item = pcbnew.PCB_VIA(board)
                item.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(first[0]), pcbnew.FromMM(first[1])))
                item.SetWidth(pcbnew.FromMM(route["via_diameter"]))
                item.SetDrill(pcbnew.FromMM(route["via_drill"]))
                item.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
            else:
                item = pcbnew.PCB_TRACK(board)
                item.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(first[0]), pcbnew.FromMM(first[1])))
                item.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(last[0]), pcbnew.FromMM(last[1])))
                item.SetWidth(pcbnew.FromMM(route["width"]))
                item.SetLayer(board.GetLayerID(planner.LAYERS[first[2]]))
            item.SetNet(net)
            board.Add(item)
        board.BuildConnectivity()
        pcbnew.SaveBoard(str(board_path), board)
        report_dir, checked = pipeline.check(work)
        record = {"position": new_position, "work": str(work), "drc": checked["drc"], "netlist": checked["netlist_check"], "report": str(report_dir)}
        accepted = checked["drc"]["unconnected_items"]["count"] < before["drc"]["unconnected_items"]["count"]
        accepted = accepted and not checked["drc"]["violations"]["severities"].get("error") and checked["netlist_check"]["mismatches"] == [] and checked["netlist_check"]["contract_differences"] == []
        record["accepted"] = accepted
        attempts.append(record)
        print(json.dumps(record, ensure_ascii=False), flush=True)
        if accepted:
            shutil.copy2(board_path, EVIDENCE / "after.kicad_pcb")
            pipeline.write_json(EVIDENCE / "result.json", {"before_hash": pipeline.digest(source_board), "candidate_hash": pipeline.digest(board_path), "position": new_position, "route": route, "attempts": attempts, "local_acceptance": True, "promoted": False, "before": before["drc"], "after": checked["drc"]})
            return
    pipeline.write_json(EVIDENCE / "search-record.json", {"attempts": attempts, "local_acceptance": False})
    raise SystemExit("No accepted SDO-shift candidate")


if __name__ == "__main__":
    main()
