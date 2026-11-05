"""Screen native round-hole spacing against explicitly sourced fabrication limits."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path

import pcbnew

import pipeline


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    arguments = parser.parse_args()
    project = arguments.project.resolve()
    evidence = arguments.evidence.resolve()
    board_path = project / (pipeline.STEM + ".kicad_pcb")
    board = pcbnew.LoadBoard(str(board_path))
    holes, excluded = [], []
    for footprint in board.GetFootprints():
        for pad in footprint.Pads():
            drill = pad.GetDrillSize()
            if not drill.x:
                continue
            identifier = footprint.GetReference() + "." + pad.GetNumber()
            if drill.x != drill.y:
                excluded.append({"item": identifier, "reason": "Non-round hole requires a slot-specific screen"})
                continue
            holes.append({"id": identifier, "type": "npth" if pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH else "pth",
                          "position_mm": [pcbnew.ToMM(value) for value in pad.GetPosition()], "diameter_mm": pcbnew.ToMM(drill.x)})
    for via in board.GetTracks():
        if via.Type() != pcbnew.PCB_VIA_T:
            continue
        holes.append({"id": via.m_Uuid.AsString(), "type": "blind" if via.GetViaType() == pcbnew.VIATYPE_MICROVIA else "via",
                      "position_mm": [pcbnew.ToMM(value) for value in via.GetPosition()], "diameter_mm": pcbnew.ToMM(via.GetDrill()),
                      "copper_diameter_mm": pcbnew.ToMM(via.GetFrontWidth()), "net": via.GetNetname()})
    limits = {("via", "via"): .254, ("pth", "pth"): .5, ("pth", "via"): .2,
              ("blind", "blind"): .24, ("blind", "via"): .18, ("blind", "pth"): .18,
              ("npth", "pth"): .5}
    minima, violations, uncited_minima = {}, [], {}
    for index, first in enumerate(holes):
        for second in holes[index + 1:]:
            pair = tuple(sorted((first["type"], second["type"])))
            clearance = math.dist(first["position_mm"], second["position_mm"]) - (first["diameter_mm"] + second["diameter_mm"]) / 2
            row = {"items": [first["id"], second["id"]], "types": list(pair), "edge_gap_mm": clearance, "limit_mm": limits.get(pair)}
            target = minima if pair in limits else uncited_minima
            key = ":".join(pair)
            if key not in target or clearance < target[key]["edge_gap_mm"]:
                target[key] = row
            if pair in limits and clearance + 1e-6 < limits[pair]:
                violations.append(row)
    source_root = Path(__file__).resolve().parents[3]
    source_paths = [source_root / "docs/references/扩展板电路仿真工具/manufacturer-rules-20261031/sources" / name
                    for name in ("jlc-capabilities.txt", "jlc-hdi-faq.txt")]
    result = {"pcb_sha256": pipeline.digest(board_path), "hole_counts": dict(Counter(row["type"] for row in holes)),
              "evaluated_pairs": minima, "violations": violations, "excluded_shapes": excluded,
              "pairs_without_a_cited_limit": uncited_minima,
              "source_files": [{"path": path.relative_to(source_root).as_posix(), "sha256": pipeline.digest(path)} for path in source_paths],
              "threshold_attribution": "Conservative project screening thresholds, not all verbatim supplier limits. Archived PCB capability text lists via-to-via 0.2mm and pad-hole spacing 0.45mm; this screen retains 0.254mm/0.5mm margins. Mixed/HDI pairs retain the previously recorded review thresholds.",
              "scope": "CAD nominal round-hole edge distances only; no drill compensation, slot screen, plating/tolerance, mask bridge or supplier acceptance claim",
              "project_spacing_screen_passed": not violations and not excluded, "manufacturing_approved": False, "hardware_tested": False}
    pipeline.write_json(evidence / "hole-spacing-audit.json", result)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
