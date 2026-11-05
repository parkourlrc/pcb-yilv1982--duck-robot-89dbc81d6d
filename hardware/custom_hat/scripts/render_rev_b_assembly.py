from pathlib import Path
import subprocess
import sys

import pcbnew

from repair_release_metadata import child_spans


project=Path(__file__).resolve().parents[1]/"rev_b"
source=project/"custom_hat_rev_b.kicad_pcb"
output=project/"review-output"
text=source.read_text(encoding="utf-8")
for start,end,block in reversed(list(child_spans(text))):
    if block.lstrip().split(maxsplit=1)[0] in {"(segment","(via","(zone"}:
        text=text[:start]+text[end:]
view=output/"assembly-view-only.kicad_pcb"
view.write_text(text,encoding="utf-8")
board=pcbnew.LoadBoard(str(view))
for footprint in board.GetFootprints():
    footprint.Value().SetVisible(False)
    footprint.Value().SetText("")
    for field in footprint.GetFields():
        field.SetVisible(False)
    reference=footprint.Reference()
    reference.SetVisible(True)
    reference.SetLayer(pcbnew.B_Fab if footprint.GetLayer()==pcbnew.B_Cu else pcbnew.F_Fab)
    reference.SetPosition(footprint.GetPosition())
    reference.SetTextAngle(pcbnew.EDA_ANGLE(90 if abs(footprint.GetOrientationDegrees())%180==90 else 0,pcbnew.DEGREES_T))
    reference.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(0.7),pcbnew.FromMM(0.7)))
    reference.SetTextThickness(pcbnew.FromMM(0.1))
    for shape in footprint.GraphicalItems():
        if shape.Type()==pcbnew.PCB_TEXT_T:
            shape.SetVisible(False)
            shape.SetText("")
pcbnew.SaveBoard(str(view),board)
cli=Path(sys.executable).parent/"kicad-cli.exe"
for name,layers,mirror in (("assembly-top","F.Cu,F.Fab,Edge.Cuts",False),("assembly-bottom","B.Cu,B.Fab,Edge.Cuts",True)):
    command=[str(cli),"pcb","export","svg","-l",layers,"--mode-single","--fit-page-to-board","--exclude-drawing-sheet","-o",str(output/(name+".svg")),str(view)]
    if mirror:
        command.insert(-1,"--mirror")
    subprocess.run(command,check=True)
print("Rendered views from a derivative without zones or tracks; source PCB unchanged")
