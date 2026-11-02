"""Add a second standard stitch only if it restores additional LRCK reference copper."""
import json
import math
from pathlib import Path
import shutil
import uuid

import pcbnew

import pipeline
from add_i2c_pullups import vector
from stitch_i2s_reference_pocket import EVIDENCE, BASELINE, coverage


def main():
    candidate_path = EVIDENCE / "candidate.json"
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    work = pipeline.managed(Path(candidate["project"]))
    path = work / (pipeline.STEM + ".kicad_pcb")
    contract_path = EVIDENCE / "stitch-contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    if "new_vias" in contract or candidate["promoted"] or pipeline.digest(pipeline.PRIMARY / path.name) != BASELINE:
        raise RuntimeError("Candidate is not the reviewed one-stitch baseline")
    board = pcbnew.LoadBoard(str(path))
    before = coverage(board)
    fixed = []
    for footprint in board.GetFootprints():
        for pad in footprint.Pads():
            for layer in (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu):
                if pad.IsOnLayer(layer):
                    fixed.append((pad.GetEffectiveShape(layer), 0.38 if pad.GetNetname() == "POWER_GND" else 0.505))
    for item in board.GetTracks():
        if item.GetNetname() == "POWER_GND" and item.Type() != pcbnew.PCB_VIA_T:
            continue
        for layer in (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu):
            if item.IsOnLayer(layer):
                fixed.append((item.GetEffectiveShape(layer), 0.505))
    front = next(zone.GetFilledPolysList(pcbnew.F_Cu) for zone in board.Zones() if zone.IsOnLayer(pcbnew.F_Cu) and zone.GetNetname() == "POWER_GND")
    inner = next(zone.GetFilledPolysList(pcbnew.In1_Cu) for zone in board.Zones() if zone.IsOnLayer(pcbnew.In1_Cu) and zone.GetNetname() == "POWER_GND")
    sites = []
    for xpos_index in range(3030, 3111):
        for ypos_index in range(2116, 2171):
            coords = (xpos_index / 20, ypos_index / 20)
            point = vector(coords)
            if front.Contains(point) or not inner.Contains(point) or any(shape.Collide(point, pcbnew.FromMM(margin)) for shape, margin in fixed):
                continue
            sites.append(coords)
    sites.sort(key=lambda point: math.dist(point, (151.8, 107.4)))
    pipeline.write_json(EVIDENCE / "upper-pocket-sites.json", {"sites": sites, "before": before, "candidate_sha256": pipeline.digest(path)})
    if not sites:
        raise RuntimeError("No safe standard via site in upper pocket")
    backup = work.parent / "before-upper-stitch.kicad_pcb"
    if backup.exists():
        raise FileExistsError("Review prior upper-stitch attempt")
    shutil.copy2(path, backup)
    via = pcbnew.PCB_VIA(board)
    via.SetPosition(vector(sites[0]))
    via.SetWidth(pcbnew.FromMM(0.6))
    via.SetDrill(pcbnew.FromMM(0.3))
    via.SetViaType(pcbnew.VIATYPE_THROUGH)
    via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    via.SetNetCode(board.FindNet("POWER_GND").GetNetCode())
    board.Add(via)
    pcbnew.SaveBoard(str(path), board)
    report = work.parent / ("upper-stitch-" + uuid.uuid4().hex[:8] + ".json")
    pipeline.run_command([pipeline.find_cli(), "pcb", "drc", "--format", "json", "--severity-all", "--schematic-parity", "--refill-zones", "--save-board", "--output", report, path],
                         EVIDENCE, "upper-stitch-refill", [], report)
    drc = json.loads(report.read_text(encoding="utf-8"))
    after = coverage(pcbnew.LoadBoard(str(path)))
    accepted = not any(drc[key] for key in ("violations", "unconnected_items", "schematic_parity")) and after["ground_covered_mm"] > before["ground_covered_mm"] + 0.2
    result = {"position_mm": sites[0], "new_via": via.m_Uuid.AsString(), "before": before, "after": after, "accepted": accepted,
              "drc": {key: len(drc[key]) for key in ("violations", "unconnected_items", "schematic_parity")}}
    pipeline.write_json(EVIDENCE / "upper-stitch-result.json", result)
    if not accepted:
        shutil.copy2(backup, path)
        raise RuntimeError("Upper stitch rejected and previous candidate restored")
    contract["new_vias"] = [contract["new_via"], via.m_Uuid.AsString()]
    contract["positions_mm"] = [contract["position_mm"], sites[0]]
    contract["added_tracks"].append(via.m_Uuid.AsString())
    contract["after"] = after
    pipeline.write_json(contract_path, contract)
    reports, summary = pipeline.check(work)
    candidate["summary"] = str(reports / "summary.json")
    pipeline.write_json(candidate_path, candidate)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
