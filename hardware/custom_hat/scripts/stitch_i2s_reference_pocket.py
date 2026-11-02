"""Test a ground stitch in the copper pocket under the existing LRCK route."""
import json
import math
from pathlib import Path
import uuid

import pcbnew

import pipeline
from add_i2c_pullups import vector


EVIDENCE = pipeline.BASE.parents[1] / "docs/references/hat-simulation-tools-20261029/i2s-reference-stitch-20261031"
BASELINE = "fda50c8019c3ab68c7c54228fc09fb36dd028e35b43afe26a7dc0f6c090b0771"


def coverage(board):
    plane = next(zone.GetFilledPolysList(pcbnew.F_Cu) for zone in board.Zones() if zone.IsOnLayer(pcbnew.F_Cu) and zone.GetNetname() == "POWER_GND")
    covered = 0.0
    total = 0.0
    for track in board.GetTracks():
        if track.Type() == pcbnew.PCB_VIA_T or track.GetNetname() != "I2S_LRCK" or track.GetLayer() != pcbnew.In1_Cu:
            continue
        start, end = track.GetStart(), track.GetEnd()
        delta = (end.x - start.x, end.y - start.y)
        length = math.hypot(*delta) / 1e6
        count = max(1, math.ceil(length / 0.025))
        total += length
        for index in range(count):
            fraction = (index + 0.5) / count
            point = pcbnew.VECTOR2I(round(start.x + delta[0] * fraction), round(start.y + delta[1] * fraction))
            if plane.Contains(point):
                covered += length / count
    return {"trace_mm": total, "ground_covered_mm": covered, "coverage_pct": 100 * covered / total, "ground_polygons": plane.OutlineCount()}


def main():
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    if (EVIDENCE / "candidate.json").exists():
        raise FileExistsError("Review existing stitch candidate before retry")
    path = pipeline.PRIMARY / (pipeline.STEM + ".kicad_pcb")
    if pipeline.digest(path) != BASELINE:
        raise RuntimeError("Source changed")
    original = pcbnew.LoadBoard(str(path))
    copper_layers = (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu)
    hard = []
    mask_shapes = []
    holes = []
    for footprint in original.GetFootprints():
        for pad in footprint.Pads():
            if pad.GetDrillSize().x:
                holes.append((pad.GetPosition(), max(pad.GetDrillSize().x, pad.GetDrillSize().y) / 2))
            for layer in copper_layers:
                if pad.IsOnLayer(layer):
                    if pad.GetNetname() != "POWER_GND":
                        hard.append(pad.GetEffectiveShape(layer))
                    if layer in (pcbnew.F_Cu, pcbnew.B_Cu):
                        mask_shapes.append(pad.GetEffectiveShape(layer))
    for item in original.GetTracks():
        if item.Type() == pcbnew.PCB_VIA_T:
            holes.append((item.GetPosition(), item.GetDrill() / 2))
        if item.GetNetname() != "POWER_GND":
            for layer in copper_layers:
                if item.IsOnLayer(layer):
                    hard.append(item.GetEffectiveShape(layer))
    front = next(zone.GetFilledPolysList(pcbnew.F_Cu) for zone in original.Zones() if zone.IsOnLayer(pcbnew.F_Cu) and zone.GetNetname() == "POWER_GND")
    inner = next(zone.GetFilledPolysList(pcbnew.In1_Cu) for zone in original.Zones() if zone.IsOnLayer(pcbnew.In1_Cu) and zone.GetNetname() == "POWER_GND")
    attempts = []
    sites = []
    diameter, drill = 0.6, 0.3
    for diameter, drill in ((0.6, 0.3), (0.5, 0.25), (0.45, 0.2)):
        for xpos_index in range(3000, 3061):
            for ypos_index in range(2140, 2201):
                point_mm = (xpos_index / 20, ypos_index / 20)
                point = vector(point_mm)
                if front.Contains(point) or not inner.Contains(point):
                    continue
                if any(shape.Collide(point, pcbnew.FromMM(diameter / 2 + 0.205)) for shape in hard):
                    continue
                if any(shape.Collide(point, pcbnew.FromMM(diameter / 2 + 0.08)) for shape in mask_shapes):
                    continue
                if any(math.dist(tuple(point), tuple(center)) < radius + pcbnew.FromMM(drill / 2 + 0.25) for center, radius in holes):
                    continue
                sites.append(point_mm)
        attempts.append({"diameter_mm": diameter, "drill_mm": drill, "legal_sites": len(sites)})
        if sites:
            break
    sites.sort(key=lambda point: math.dist(point, (151.7, 108.8)))
    pipeline.write_json(EVIDENCE / "candidate-sites.json", {"sites": sites, "diameter_mm": diameter, "drill_mm": drill, "attempts": attempts,
                        "criterion": "Currently empty F ground, present In1 ground, native copper clearance>=0.205mm, avoid all pad-mask regions and holes"})
    if not sites:
        raise RuntimeError("No safe stitch site inside searched pocket")
    work = pipeline.prepare(pipeline.PRIMARY)
    target = work / path.name
    candidate = {"project": str(work), "baseline": BASELINE, "promoted": False}
    pipeline.write_json(EVIDENCE / "candidate.json", candidate)
    board = pcbnew.LoadBoard(str(target))
    via = pcbnew.PCB_VIA(board)
    via.SetPosition(vector(sites[0]))
    via.SetWidth(pcbnew.FromMM(diameter))
    via.SetDrill(pcbnew.FromMM(drill))
    via.SetViaType(pcbnew.VIATYPE_THROUGH)
    via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    via.SetNetCode(board.FindNet("POWER_GND").GetNetCode())
    board.Add(via)
    pcbnew.SaveBoard(str(target), board)
    report = work.parent / ("stitch-filled-" + uuid.uuid4().hex[:8] + ".json")
    pipeline.run_command([pipeline.find_cli(), "pcb", "drc", "--format", "json", "--severity-all", "--schematic-parity", "--refill-zones", "--save-board", "--output", report, target],
                         EVIDENCE, "stitch-refill", [], report)
    updated = pcbnew.LoadBoard(str(target))
    pipeline.write_json(EVIDENCE / "stitch-contract.json", {"new_via": via.m_Uuid.AsString(), "position_mm": sites[0], "diameter_mm": diameter, "drill_mm": drill,
                        "before": coverage(original), "after": coverage(updated), "source_before": BASELINE,
                        "reference_scope": "F.Cu ground zone directly under In1 LRCK centerline; not EMI/impedance verification"})
    reports, summary = pipeline.check(work)
    candidate["summary"] = str(reports / "summary.json")
    pipeline.write_json(EVIDENCE / "candidate.json", candidate)
    print(json.dumps({"site": sites[0], "legal_sites": len(sites), "before": coverage(original), "after": coverage(updated), "drc": summary["drc"], "status": summary["status"]}))


if __name__ == "__main__":
    main()
