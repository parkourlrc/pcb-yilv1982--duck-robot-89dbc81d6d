import argparse
import json
from pathlib import Path
import shutil

import pcbnew

from add_i2c_pullups import obstacles, position, vector
import plan_i2s_sdo as planner
from fit_ldo_candidate import remove_objects


parser = argparse.ArgumentParser()
parser.add_argument("directory", type=Path)
arguments = parser.parse_args()
directory = arguments.directory.resolve()
path = directory / "custom_hat_rev_b.kicad_pcb"
shutil.copy2(path, directory / "before-signal-repair.kicad_pcb")
board = pcbnew.LoadBoard(str(path))
targets = [("I2S_LRCK", "U701", "3", "J101", "35"), ("I2S_SDO", "U701", "4", "J101", "40"), ("CODEC_RIGHT_LOP", "U701", "29", "C732", "1")]
target_names = {row[0] for row in targets}
report = json.loads((directory / "drc-complete-project.json").read_text(encoding="utf-8"))
dangling = {item["uuid"] for finding in report["violations"] if finding["type"] == "via_dangling" for item in finding["items"]}
removed = [track.m_Uuid.AsString() for track in board.GetTracks() if track.GetNetname() in target_names or track.m_Uuid.AsString() in dangling]
temporary = directory / "signal-repair-working.kicad_pcb"
shutil.copy2(path, temporary)
remove_objects(temporary, removed)
board = pcbnew.LoadBoard(str(temporary))
planner.EVIDENCE = directory
planner.LAYERS = ["F.Cu", "B.Cu"]
planner.STEP = 0.025
planner.WIDTH = 0.15
planner.VIA_AVOID_RADIUS = 0.3
planner.VIA_PENALTY = 120.0
planner.XMIN, planner.YMIN, planner.XMAX, planner.YMAX = 131.0, 100.6, 163.8, 124.0
planner.COLS = round((planner.XMAX-planner.XMIN)/planner.STEP)+1
planner.ROWS = round((planner.YMAX-planner.YMIN)/planner.STEP)+1
planner.SIZE = planner.COLS*planner.ROWS
plans = []
for net, start_ref, start_pin, end_ref, end_pin in targets:
    start_pad = next(pad for pad in board.FindFootprintByReference(start_ref).Pads() if pad.GetNumber()==start_pin)
    end_pad = next(pad for pad in board.FindFootprintByReference(end_ref).Pads() if pad.GetNumber()==end_pin)
    if start_pad.GetNetname()!=net or end_pad.GetNetname()!=net:
        raise RuntimeError("Endpoint net mismatch for "+net)
    print("Routing "+net, flush=True)
    plan = planner.solve(obstacles(board), net, position(start_pad), position(end_pad), [0,1] if end_ref=="J101" else [0], 0)
    plan["via_diameter"] = 0.6
    for start, end in zip(plan["points"], plan["points"][1:]):
        if start[2] != end[2]:
            track = pcbnew.PCB_VIA(board)
            track.SetPosition(vector(start[:2]))
            track.SetViaType(pcbnew.VIATYPE_THROUGH)
            track.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
            track.SetWidth(pcbnew.FromMM(0.6))
            track.SetDrill(pcbnew.FromMM(0.3))
        else:
            track = pcbnew.PCB_TRACK(board)
            track.SetStart(vector(start[:2]))
            track.SetEnd(vector(end[:2]))
            track.SetLayer(pcbnew.F_Cu if start[2]==0 else pcbnew.B_Cu)
            track.SetWidth(pcbnew.FromMM(0.15))
        track.SetNetCode(board.FindNet(net).GetNetCode())
        board.Add(track)
    plans.append(plan)
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
pcbnew.SaveBoard(str(path), board)
(directory / "signal-repair.json").write_text(json.dumps(plans, indent=2), encoding="utf-8")
print(json.dumps({"routes":len(plans),"status":"needs_native_DRC"}))
