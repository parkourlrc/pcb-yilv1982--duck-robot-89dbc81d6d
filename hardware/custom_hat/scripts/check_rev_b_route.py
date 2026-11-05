import argparse
from collections import Counter
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pcbnew


parser = argparse.ArgumentParser()
parser.add_argument("directory", type=Path)
parser.add_argument("--fill-ground", action="store_true")
arguments = parser.parse_args()
directory = arguments.directory.resolve()
project = Path(__file__).resolve().parents[1] / "rev_b"
stem = "custom_hat_rev_b"
for source in project.iterdir():
    if source.is_file() and (source.suffix in {".kicad_pro", ".kicad_dru", ".kicad_sch", ".kicad_sym"} or source.name in {"fp-lib-table", "sym-lib-table"}):
        shutil.copy2(source, directory / source.name)
shutil.copytree(project / "duck.pretty", directory / "duck.pretty", dirs_exist_ok=True)
board_path = directory / (stem + ".kicad_pcb")
if arguments.fill_ground:
    shutil.copy2(board_path, directory / "before-ground.kicad_pcb")
    board = pcbnew.LoadBoard(str(board_path))
    ground = board.FindNet("POWER_GND")
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        zone = pcbnew.ZONE(board)
        zone.SetLayer(layer)
        zone.SetNet(ground)
        zone.SetLocalClearance(pcbnew.FromMM(0.2))
        zone.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
        zone.SetMinThickness(pcbnew.FromMM(0.2))
        polygon = zone.Outline()
        polygon.NewOutline()
        for xpos, ypos in ((100.3, 100.3), (164.7, 100.3), (164.7, 129.7), (100.3, 129.7)):
            polygon.Append(pcbnew.FromMM(xpos), pcbnew.FromMM(ypos))
        board.Add(zone)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(str(board_path), board)
cli = Path(sys.executable).parent / "kicad-cli.exe"
report_path = directory / "drc-complete-project.json"
result = subprocess.run([str(cli), "pcb", "drc", "--format", "json", "--schematic-parity", "--exit-code-violations", "-o", str(report_path), str(board_path)], capture_output=True, text=True, encoding="utf-8", errors="replace")
(directory / "drc-complete-project.log").write_text(result.stdout + result.stderr, encoding="utf-8")
report = json.loads(report_path.read_text(encoding="utf-8"))
print(json.dumps({"violations":dict(Counter(item["type"] for item in report["violations"])), "unconnected":len(report["unconnected_items"]), "parity":len(report["schematic_parity"]), "exit_code": result.returncode}, ensure_ascii=False))
