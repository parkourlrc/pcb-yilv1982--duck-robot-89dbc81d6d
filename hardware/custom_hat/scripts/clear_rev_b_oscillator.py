from pathlib import Path
import json

import pcbnew


project=Path(__file__).resolve().parents[1]/"rev_b"
path=project/"custom_hat_rev_b.kicad_pcb"
board=pcbnew.LoadBoard(str(path))
targets={"AUDIO_MCLK":((137.025,106.55),(137.05,106.6))}
changes=[]
for net,(before,after) in targets.items():
    source=pcbnew.VECTOR2I(*(pcbnew.FromMM(value) for value in before))
    target=pcbnew.VECTOR2I(*(pcbnew.FromMM(value) for value in after))
    for track in board.GetTracks():
        if track.GetNetname()!=net:
            continue
        if track.Type()==pcbnew.PCB_VIA_T:
            if track.GetPosition()==source:
                track.SetPosition(target)
                changes.append({"net":net,"before":before,"after":after})
        else:
            if track.GetStart()==source:
                track.SetStart(target)
            if track.GetEnd()==source:
                track.SetEnd(target)
oscillator=board.FindFootprintByReference("Y701")
for track in board.GetTracks():
    if track.m_Uuid.AsString()=="4d1d89c8-5a3c-4370-8f0d-ca0e1b4c5430":
        track.SetWidth(pcbnew.FromMM(0.2))
for shape in oscillator.GraphicalItems():
    if shape.GetLayer()==pcbnew.F_SilkS:
        shape.SetLayer(pcbnew.F_Fab)
pcbnew.FootprintSave(str(project/"duck.pretty"),oscillator)
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
pcbnew.SaveBoard(str(path),board)
print(json.dumps(changes))
