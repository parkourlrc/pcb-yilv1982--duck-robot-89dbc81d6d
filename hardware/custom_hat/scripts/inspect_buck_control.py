"""Record the existing control routing and the R301 supply terminal branch."""
import json
import math

import pcbnew
import pipeline


EVIDENCE=pipeline.BASE.parents[1]/"docs/references/扩展板电路仿真工具/buck-control-20261031"
BASELINE="6555f994e1ee6b99949df5ee4cfc35ce31169f6b0d01421cdd037f6736ec410d"
CONTROL_NETS={"+5V_FB","BUCK_COMP","COMP_RC"}


def main():
    EVIDENCE.mkdir(parents=True,exist_ok=True)
    path=pipeline.PRIMARY/(pipeline.STEM+".kicad_pcb")
    if pipeline.digest(path)!=BASELINE:
        raise RuntimeError("Source changed")
    board=pcbnew.LoadBoard(str(path))
    tracks=list(board.GetTracks())
    control=[{"uuid":item.m_Uuid.AsString(),"net":item.GetNetname(),"kind":"via" if item.Type()==pcbnew.PCB_VIA_T else "track",
              "layer":board.GetLayerName(item.GetLayer()),"start":[pcbnew.ToMM(value) for value in item.GetStart()],
              "end":[pcbnew.ToMM(value) for value in item.GetEnd()],
              "width":pcbnew.ToMM(item.GetFrontWidth() if item.Type()==pcbnew.PCB_VIA_T else item.GetWidth())}
             for item in tracks if item.GetNetname() in CONTROL_NETS]
    seed=next(pad for pad in board.FindFootprintByReference("R301").Pads() if pad.GetNumber()=="1")
    layer=pcbnew.F_Cu
    current=tuple(seed.GetPosition())
    visited=[]
    steps=[]
    stop=None
    for _ in range(100):
        point=pcbnew.VECTOR2I(*current)
        other_pads=[footprint.GetReference()+"."+pad.GetNumber() for footprint in board.GetFootprints() for pad in footprint.Pads()
                    if pad.m_Uuid.AsString()!=seed.m_Uuid.AsString() and pad.GetNetname()=="+5V" and pad.IsOnLayer(layer)
                    and pad.GetEffectiveShape(layer).Collide(point)]
        vias=[item.m_Uuid.AsString() for item in tracks if item.Type()==pcbnew.PCB_VIA_T and item.GetNetname()=="+5V"
              and item.GetEffectiveShape(layer).Collide(point)]
        if other_pads or vias:
            stop={"point":[pcbnew.ToMM(value) for value in current],"other_pads":other_pads,"vias":vias}
            break
        candidates=[item for item in tracks if item.Type()!=pcbnew.PCB_VIA_T and item.GetNetname()=="+5V" and item.GetLayer()==layer
                    and item.m_Uuid.AsString() not in visited and (tuple(item.GetStart())==current or tuple(item.GetEnd())==current)]
        if len(candidates)!=1:
            stop={"point":[pcbnew.ToMM(value) for value in current],"junction_degree_remaining":len(candidates),"tracks":[item.m_Uuid.AsString() for item in candidates]}
            break
        item=candidates[0]
        visited.append(item.m_Uuid.AsString())
        following=tuple(item.GetEnd()) if tuple(item.GetStart())==current else tuple(item.GetStart())
        steps.append({"uuid":item.m_Uuid.AsString(),"start":[pcbnew.ToMM(value) for value in current],"end":[pcbnew.ToMM(value) for value in following]})
        current=following
    if not stop:
        raise RuntimeError("Could not bound the terminal branch")
    result={"source_pcb_sha256":BASELINE,"control_objects":control,"supply_terminal_branch":steps,"supply_branch_stop":stop,
            "total_track_lengths_mm":{name:sum(math.dist(item["start"],item["end"]) for item in control if item["net"]==name and item["kind"]=="track") for name in CONTROL_NETS},
            "production_ready":False}
    pipeline.write_json(EVIDENCE/"before-control-routing.json",result)
    print(json.dumps({"control_objects":len(control),"lengths":result["total_track_lengths_mm"],"supply_branch":steps,"stop":stop}))


if __name__=="__main__":
    main()
