"""Try larger annular rings without moving existing vias or weakening rules."""
import json
import math

import pcbnew
import pipeline


EVIDENCE = pipeline.BASE.parents[1] / "docs/references/扩展板电路仿真工具/annular-rings-20261031"
BASELINE = "3bbf6ca679d413b12d89482cecacd7c7ba7e2b5cf2b146daf43bc1be3a96dc70"


def main():
    EVIDENCE.mkdir(exist_ok=True)
    if (EVIDENCE / "candidate.json").exists():
        raise FileExistsError("Inspect prior candidate")
    source = pipeline.PRIMARY / (pipeline.STEM + ".kicad_pcb")
    if pipeline.digest(source) != BASELINE:
        raise RuntimeError("Baseline changed")
    work = pipeline.prepare(pipeline.PRIMARY)
    pipeline.write_json(EVIDENCE / "candidate.json", {"project": str(work), "baseline": BASELINE, "promoted": False})
    board = pcbnew.LoadBoard(str(source))
    changes = []
    for via in board.GetTracks():
        if via.Type() != pcbnew.PCB_VIA_T or via.GetViaType() != pcbnew.VIATYPE_THROUGH:
            continue
        drill = pcbnew.ToMM(via.GetDrill())
        diameter = pcbnew.ToMM(via.GetFrontWidth())
        if diameter - drill >= 0.25 - 1e-8:
            continue
        target = math.ceil((drill + 0.25 - 1e-8) / 0.05) * 0.05
        changes.append({"uuid": via.m_Uuid.AsString(), "net": via.GetNetname(), "position": [pcbnew.ToMM(value) for value in via.GetPosition()],
                        "old_diameter": diameter, "new_diameter": target, "drill": drill})
        via.SetWidth(pcbnew.FromMM(target))
    pcbnew.SaveBoard(str(work / source.name), board)
    pipeline.write_json(EVIDENCE / "changes.json", changes)
    reports, result = pipeline.check(work)
    pipeline.write_json(EVIDENCE / "candidate.json", {"project": str(work), "baseline": BASELINE, "summary": str(reports / "summary.json"), "promoted": False})
    print(json.dumps({"through_vias_enlarged": len(changes), "drc": result["drc"], "status": result["status"]}))


if __name__ == "__main__":
    main()
