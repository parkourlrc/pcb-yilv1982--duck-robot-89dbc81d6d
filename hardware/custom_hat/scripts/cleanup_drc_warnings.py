"""Remove verified dangling vias and move U301 silkscreen out of fabrication silk."""
import json
import shutil

import pcbnew

import pipeline


TARGET_VIAS = {
    "ee78dcee-878c-4afc-8028-e77cc9fc0fac": "AUDIO_L",
    "f09e92f2-c04a-4859-9ba2-5efa8700e229": "AUDIO_AMP_EN",
}


def signature(item):
    return (item["type"], item["severity"], tuple(sorted(entry["uuid"] for entry in item["items"])))


def main():
    evidence = pipeline.BASE.parents[1] / "docs/references/扩展板电路仿真工具/warning-cleanup-20261030"
    evidence.mkdir(parents=True, exist_ok=True)
    if (evidence / "result.json").exists():
        raise FileExistsError("Existing cleanup record")
    work = pipeline.prepare(pipeline.PRIMARY)
    before_dir, before = pipeline.check(work)
    board_path = work / (pipeline.STEM + ".kicad_pcb")
    shutil.copy2(board_path, evidence / "before.kicad_pcb")
    for name in ("drc.json", "summary.json", "erc.json"):
        shutil.copy2(before_dir / name, evidence / ("before-" + name))
    board = pcbnew.LoadBoard(str(board_path))
    u301 = board.FindFootprintByReference("U301")
    if u301 is None:
        raise ValueError("U301 missing")
    drawings = u301.GraphicalItems()
    for index in range(drawings.size()):
        graphic = drawings[index]
        if graphic.GetLayer() == pcbnew.F_SilkS:
            graphic.SetLayer(pcbnew.F_Fab)
    u301.Reference().SetVisible(False)
    found = {}
    for item in list(board.GetTracks()):
        if item.Type() == pcbnew.PCB_VIA_T and item.m_Uuid.AsString() in TARGET_VIAS:
            if item.GetNetname() != TARGET_VIAS[item.m_Uuid.AsString()]:
                raise ValueError("Dangling via net changed")
            found[item.m_Uuid.AsString()] = item.GetNetname()
            board.Remove(item)
    if set(found) != set(TARGET_VIAS):
        raise ValueError("Dangling via baseline changed")
    board.BuildConnectivity()
    pcbnew.SaveBoard(str(board_path), board)
    after_dir, after = pipeline.check(work)
    shutil.copy2(board_path, evidence / "after.kicad_pcb")
    for name in ("drc.json", "summary.json", "erc.json"):
        shutil.copy2(after_dir / name, evidence / ("after-" + name))
    changes = {}
    before_report = json.loads((before_dir / "drc.json").read_text(encoding="utf-8"))
    after_report = json.loads((after_dir / "drc.json").read_text(encoding="utf-8"))
    for category in ("violations", "unconnected_items", "schematic_parity"):
        old = {signature(item) for item in before_report[category]}
        new = {signature(item) for item in after_report[category]}
        changes[category] = {"added": list(new - old), "removed": list(old - new)}
    accepted = not changes["violations"]["added"] and after["drc"]["unconnected_items"]["count"] <= before["drc"]["unconnected_items"]["count"]
    accepted = accepted and not after["netlist_check"]["mismatches"] and not after["netlist_check"]["contract_differences"]
    result = {"removed_vias": found, "moved_u301_silk_to_fab": True, "work": str(work), "before_hash": pipeline.digest(evidence / "before.kicad_pcb"), "candidate_hash": pipeline.digest(board_path), "before": before["drc"], "after": after["drc"], "changes": changes, "local_acceptance": bool(accepted), "promoted": False}
    pipeline.write_json(evidence / "result.json", result)
    print(json.dumps({"accepted": bool(accepted), "before": before["drc"], "after": after["drc"]}, ensure_ascii=False))
    if not accepted:
        raise SystemExit("Warning cleanup rejected; primary unchanged")


if __name__ == "__main__":
    main()
