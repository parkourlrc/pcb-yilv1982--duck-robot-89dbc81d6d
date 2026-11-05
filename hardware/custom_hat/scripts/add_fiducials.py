"""Add three top and three bottom SMT fiducials in an isolated full workspace."""
import json
from pathlib import Path
import shutil

import pcbnew

import pipeline


def main():
    evidence = pipeline.BASE.parents[1] / "docs/references/扩展板电路仿真工具/fiducials-20261030"
    evidence.mkdir(parents=True, exist_ok=True)
    if (evidence / "result.json").exists():
        raise FileExistsError("Existing fiducial record")
    work = pipeline.prepare(pipeline.PRIMARY)
    before_dir, before = pipeline.check(work)
    board_path = work / (pipeline.STEM + ".kicad_pcb")
    shutil.copy2(board_path, evidence / "before.kicad_pcb")
    board = pcbnew.LoadBoard(str(board_path))
    footprint_path = Path(__import__('os').environ['KICAD_FOOTPRINT_ROOT']) / "Fiducial.pretty" / "Fiducial_1mm_Mask2mm.kicad_mod"
    positions = [("FID1", pcbnew.F_Cu, (101.5, 101.5)), ("FID2", pcbnew.F_Cu, (163.5, 101.5)), ("FID3", pcbnew.F_Cu, (101.5, 128.5)), ("FID4", pcbnew.B_Cu, (101.5, 101.5)), ("FID5", pcbnew.B_Cu, (163.5, 101.5)), ("FID6", pcbnew.B_Cu, (101.5, 128.5))]
    for reference, layer, position in positions:
        footprint = pcbnew.FootprintLoad(str(footprint_path.parent), footprint_path.stem)
        if footprint is None:
            raise RuntimeError("Could not load fiducial footprint")
        footprint.SetReference(reference)
        footprint.SetValue("Fiducial")
        footprint.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(position[0]), pcbnew.FromMM(position[1])))
        footprint.SetLayerAndFlip(layer)
        footprint.SetExcludedFromBOM(True)
        board.Add(footprint)
    board.BuildConnectivity()
    pcbnew.SaveBoard(str(board_path), board)
    after_dir, after = pipeline.check(work)
    shutil.copy2(board_path, evidence / "after.kicad_pcb")
    for name in ("drc.json", "summary.json", "erc.json"):
        shutil.copy2(after_dir / name, evidence / ("after-" + name))
    accepted = after["drc"]["violations"]["severities"].get("error", 0) == 0 and after["drc"]["unconnected_items"]["count"] <= before["drc"]["unconnected_items"]["count"] and not after["netlist_check"]["mismatches"]
    result = {"positions": positions, "work": str(work), "before": before["drc"], "after": after["drc"], "candidate_hash": pipeline.digest(board_path), "local_acceptance": bool(accepted), "promoted": False}
    pipeline.write_json(evidence / "result.json", result)
    print(json.dumps({"accepted": bool(accepted), "before": before["drc"], "after": after["drc"]}, ensure_ascii=False))
    if not accepted:
        raise SystemExit("Fiducial candidate rejected; primary unchanged")


if __name__ == "__main__":
    main()
