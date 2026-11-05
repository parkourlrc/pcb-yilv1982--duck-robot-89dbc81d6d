from pathlib import Path
import json
import shutil

import pcbnew


project = Path(__file__).resolve().parents[1]/"rev_b"
path = project/"custom_hat_rev_b.kicad_pcb"
board = pcbnew.LoadBoard(str(path))
if board.GetTracks():
    raise RuntimeError("Only use on the unrouted layout candidate")
codec = board.FindFootprintByReference("U701")
pads = {pad.GetNumber():pad for pad in codec.Pads() if pad.GetNumber()}
plans = []
for pin, via_position in {"1":(135.1,112.65),"2":(135.1,113.45),"3":(135.1,114.25),"4":(135.1,115.05),"5":(135.1,115.85),"8":(135.1,117.45),"29":(138.75,111.65)}.items():
    pad = pads[pin]
    endpoint = pcbnew.VECTOR2I(*(pcbnew.FromMM(value) for value in via_position))
    vertices = [pad.GetPosition()]
    if pin in {"1","2","3","4","5","8"}:
        vertices.append(pcbnew.VECTOR2I(pcbnew.FromMM(135.75),pad.GetPosition().y))
    vertices.append(endpoint)
    for start, end in zip(vertices,vertices[1:]):
        track = pcbnew.PCB_TRACK(board)
        track.SetStart(start)
        track.SetEnd(end)
        track.SetWidth(pcbnew.FromMM(0.15))
        track.SetLayer(pcbnew.F_Cu)
        track.SetNet(pad.GetNet())
        board.Add(track)
    via = pcbnew.PCB_VIA(board)
    via.SetPosition(endpoint)
    via.SetWidth(pcbnew.FromMM(0.6))
    via.SetDrill(pcbnew.FromMM(0.3))
    via.SetViaType(pcbnew.VIATYPE_THROUGH)
    via.SetLayerPair(pcbnew.F_Cu,pcbnew.B_Cu)
    via.SetNet(pad.GetNet())
    board.Add(via)
    plans.append({"pin":pin,"net":pad.GetNetname(),"via":via_position,"diameter":0.6,"drill":0.3})
pcbnew.SaveBoard(str(path),board)
(project/"codec-fanout.json").write_text(json.dumps(plans,indent=2),encoding="utf-8")
print(json.dumps({"fanouts":len(plans),"status":"native_DRC_required"}))
