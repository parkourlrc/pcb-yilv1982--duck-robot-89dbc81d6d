"""Measure native round-hole clearance to foreign copper on all four layers."""
import argparse
import json
from pathlib import Path

import pcbnew

import pipeline


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    arguments = parser.parse_args()
    board_path = arguments.project.resolve() / (pipeline.STEM + ".kicad_pcb")
    board = pcbnew.LoadBoard(str(board_path))
    layers = (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu)
    holes, unhandled = [], []
    copper = {layer: [] for layer in layers}
    for footprint in board.GetFootprints():
        for pad in footprint.Pads():
            identifier = pad.m_Uuid.AsString()
            drill = pad.GetDrillSize()
            nonplated = pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH
            if drill.x:
                if drill.x != drill.y:
                    unhandled.append({"id": identifier, "reason": "non-round drill"})
                else:
                    holes.append({"id": identifier, "label": footprint.GetReference() + "." + pad.GetNumber(), "type": "npth" if nonplated else "pth_pad",
                                  "net": pad.GetNetname(), "diameter": drill.x, "position": pad.GetPosition()})
            if not nonplated:
                for layer in layers:
                    if pad.IsOnLayer(layer):
                        copper[layer].append((identifier, pad.GetNetname(), pad.GetEffectiveShape(layer)))
        for item in [*footprint.GraphicalItems(), *footprint.GetFields()]:
            if item.GetLayer() in layers:
                unhandled.append({"id": item.m_Uuid.AsString(), "reason": "footprint copper graphic requires separate treatment"})
    for item in board.GetTracks():
        identifier = item.m_Uuid.AsString()
        if item.Type() == pcbnew.PCB_VIA_T:
            if item.GetViaType() != pcbnew.VIATYPE_THROUGH:
                unhandled.append({"id": identifier, "reason": "non-through via in an all-through audit"})
            holes.append({"id": identifier, "label": identifier, "type": "via", "net": item.GetNetname(), "diameter": item.GetDrill(), "position": item.GetPosition()})
        for layer in layers:
            if item.IsOnLayer(layer):
                copper[layer].append((identifier, item.GetNetname(), item.GetEffectiveShape(layer)))
    for zone in board.Zones():
        for layer in layers:
            if zone.IsOnLayer(layer):
                copper[layer].append((zone.m_Uuid.AsString(), zone.GetNetname(), zone.GetFilledPolysList(layer)))
    for item in board.GetDrawings():
        if item.GetLayer() in layers:
            unhandled.append({"id": item.m_Uuid.AsString(), "reason": "board copper graphic requires separate treatment"})
    probe = pcbnew.PCB_VIA(board)
    probe.SetViaType(pcbnew.VIATYPE_THROUGH)
    probe.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    limits = {"via": .2, "npth": .25, "pth_pad": .3}
    rows, violations = [], []
    search_limit = pcbnew.FromMM(.75)
    for hole in holes:
        probe.SetPosition(hole["position"])
        probe.SetWidth(hole["diameter"])
        for layer in layers:
            shape = probe.GetEffectiveShape(layer)
            neighbors = [(identifier, other) for identifier, net, other in copper[layer] if identifier != hole["id"]
                         and (hole["type"] == "npth" or not hole["net"] or net != hole["net"])
                         and other.Collide(shape, search_limit)]
            gap = None
            if neighbors:
                low, high = 0, search_limit
                while low < high:
                    middle = (low + high) // 2
                    if any(other.Collide(shape, middle) for _, other in neighbors):
                        high = middle
                    else:
                        low = middle + 1
                gap = pcbnew.ToMM(high)
            required = limits[hole["type"]]
            row = {"item": hole["label"], "type": hole["type"], "layer": board.GetLayerName(layer),
                   "minimum_foreign_copper_gap_mm": gap, "search_radius_clearance_mm": .75, "project_limit_mm": required}
            rows.append(row)
            offending = [identifier for identifier, other in neighbors if other.Collide(shape, pcbnew.FromMM(required) - 1)]
            if offending:
                violations.append({**row, "foreign_copper_items": offending})
    result = {"pcb_sha256": pipeline.digest(board_path), "round_holes": len(holes), "layer_evaluations": len(rows),
              "minimum_by_type_mm": {kind: min((row["minimum_foreign_copper_gap_mm"] for row in rows if row["type"] == kind and row["minimum_foreign_copper_gap_mm"] is not None), default=None) for kind in limits},
              "violations": violations, "unhandled": unhandled, "rows": rows,
              "scope": "Native copper pads/tracks/vias and saved filled zones; same-net copper contacts and own plated lands are intentional. Nominal geometry only, no drilling/plating tolerance guarantee.",
              "accepted": not violations and not unhandled, "manufacturing_approved": False}
    pipeline.write_json(arguments.evidence.resolve() / "hole-copper-clearance-audit.json", result)
    print(json.dumps({key: value for key, value in result.items() if key != "rows"}))
    if not result["accepted"]:
        raise RuntimeError("Hole-to-copper screen failed")


if __name__ == "__main__":
    main()
