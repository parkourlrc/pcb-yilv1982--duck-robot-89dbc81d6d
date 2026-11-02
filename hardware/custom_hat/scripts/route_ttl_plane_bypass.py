"""Add nearby TTL capacitors with short VCC tracks and local ground-plane vias."""
import json
import math
from pathlib import Path
import shutil

import pcbnew

import pipeline
import add_ttl_local_bypass as bypass
from add_i2c_pullups import vector
from finish_ttl_local_bypass import route_layer
from repair_release_metadata import properties, replace_children, set_property


def ground_vias(board, reference):
    ground = next(pad for pad in board.FindFootprintByReference(reference).Pads() if pad.GetNumber() == "2")
    center = tuple(pcbnew.ToMM(value) for value in ground.GetPosition())
    layers = (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu)
    shapes = {layer: [pad.GetEffectiveShape(layer) for footprint in board.GetFootprints() for pad in footprint.Pads()
                     if pad.IsOnLayer(layer) and pad.GetNetname() != "POWER_GND"] +
                    [item.GetEffectiveShape(layer) for item in board.GetTracks() if item.IsOnLayer(layer) and item.GetNetname() != "POWER_GND"]
              for layer in layers}
    openings = [pad.GetEffectiveShape(pcbnew.B_Cu) for footprint in board.GetFootprints() for pad in footprint.Pads() if pad.IsOnLayer(pcbnew.B_Cu)]
    plane = [zone.GetFilledPolysList(pcbnew.In1_Cu) for zone in board.Zones() if zone.IsOnLayer(pcbnew.In1_Cu) and zone.GetNetname() == "POWER_GND"]
    probe = pcbnew.PCB_VIA(board)
    probe.SetWidth(pcbnew.FromMM(.6))
    probe.SetDrill(pcbnew.FromMM(.3))
    probe.SetViaType(pcbnew.VIATYPE_THROUGH)
    probe.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    results = []
    for horizontal in range(-25, 26):
        for vertical in range(-25, 26):
            position = (round(center[0] + horizontal / 10, 4), round(center[1] + vertical / 10, 4))
            if math.dist(position, center) > 2.5 or position[1] > 129.2:
                continue
            probe.SetPosition(vector(position))
            if not any(shape.Contains(probe.GetPosition()) for shape in plane):
                continue
            if any(probe.GetEffectiveShape(layer).Collide(shape, pcbnew.FromMM(.205)) for layer, obstacles in shapes.items() for shape in obstacles):
                continue
            if any(probe.GetEffectiveShape(pcbnew.B_Cu).Collide(shape, pcbnew.FromMM(.15)) for shape in openings):
                continue
            results.append(position)
    return sorted(results, key=lambda position: math.dist(position, center))[:16]


def main():
    candidate_path = bypass.EVIDENCE / "candidate.json"
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    work = pipeline.managed(Path(candidate["project"]))
    path = work / (pipeline.STEM + ".kicad_pcb")
    archive = work.parent / "rejected-bottom-bypass.kicad_pcb"
    if archive.exists() and pipeline.digest(path) != pipeline.digest(work.parent / "before-ttl-local-relocation.kicad_pcb"):
        raise FileExistsError("Existing candidate contains changes; inspect before retry")
    if pipeline.digest(pipeline.PRIMARY / path.name) != bypass.BASELINE:
        raise RuntimeError("Primary changed")
    if not archive.exists():
        shutil.copy2(path, archive)
    elif (bypass.EVIDENCE / "plane-placement-failures.json").exists():
        shutil.copy2(bypass.EVIDENCE / "plane-placement-failures.json", bypass.EVIDENCE / "plane-placement-failures-radius1p6.json")
    shutil.copy2(work.parent / "before-ttl-local-relocation.kicad_pcb", path)
    selected, failures = [], []
    for reference, device in bypass.PARTS.items():
        board = pcbnew.LoadBoard(str(path))
        all_positions = bypass.candidates(board, board.FindFootprintByReference(reference), device, limit=None)
        positions, seen = [], set()
        for position in all_positions:
            key = (position["angle"], *(round(value * 2) for value in position["position"]))
            if key not in seen:
                seen.add(key)
                positions.append(position)
        if reference == "C329":
            positions.sort(key=lambda position: (tuple(position["position"]) != (138.0, 126.3) or position["angle"] != 90, position["score"]))
        pipeline.write_json(bypass.EVIDENCE / (reference + "-plane-positions.json"), positions)
        found = False
        for position in positions:
            board = pcbnew.LoadBoard(str(path))
            capacitor = board.FindFootprintByReference(reference)
            capacitor.SetPosition(vector(position["position"]))
            capacitor.SetOrientationDegrees(position["angle"])
            try:
                power = route_layer(board, "+3V3", "B.Cu", .2, bypass.pad_position(board, reference, "1"), bypass.pad_position(board, device, "5"))
            except RuntimeError as error:
                failures.append({"reference": reference, "position": position, "phase": "VCC", "error": str(error)})
                continue
            for via_position in ground_vias(board, reference):
                try:
                    ground = route_layer(board, "POWER_GND", "B.Cu", .2, bypass.pad_position(board, reference, "2"), via_position)
                except RuntimeError:
                    continue
                via = pcbnew.PCB_VIA(board)
                via.SetPosition(vector(via_position))
                via.SetWidth(pcbnew.FromMM(.6))
                via.SetDrill(pcbnew.FromMM(.3))
                via.SetViaType(pcbnew.VIATYPE_THROUGH)
                via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
                via.SetNetCode(board.FindNet("POWER_GND").GetNetCode())
                board.Add(via)
                selected.append({"reference": reference, "device": device, "placement": position, "routes": [power, ground],
                                 "ground_via": {"uuid": via.m_Uuid.AsString(), "position": via_position, "diameter_mm": .6, "drill_mm": .3}})
                pcbnew.SaveBoard(str(path), board)
                pipeline.write_json(bypass.EVIDENCE / "plane-bypasses-selected.json", selected)
                print(reference + " routed " + json.dumps(selected[-1]), flush=True)
                found = True
                break
            if found:
                break
            failures.append({"reference": reference, "position": position, "phase": "GND", "error": "No local plane via route"})
        pipeline.write_json(bypass.EVIDENCE / "plane-placement-failures.json", failures)
        if not found:
            raise RuntimeError("No local plane bypass for " + reference)
    def metadata(node):
        if properties(node).get("Reference") not in bypass.PARTS:
            return False
        for key, value in bypass.FIELDS.items():
            set_property(node, key, value, board=True)
        return True
    path.write_text(replace_children(path.read_text(encoding="utf-8"), "footprint", metadata), encoding="utf-8")
    pipeline.write_json(bypass.EVIDENCE / "ttl-route-contract.json", {"parts": selected, "fields": bypass.FIELDS,
        "removed_original_objects": [], "modified_original_objects": [], "branches": [], "new_vias": len(selected),
        "failed_attempts": failures, "preserved": ["all original footprints", "all original pad geometry", "all original copper geometry", "OE logic", "project settings", "rules"],
        "ground_return": "Local B.Cu pad-to-via tracks into existing In1 ground; plane path must be checked after refill"})
    reports, summary = pipeline.check(work)
    candidate["summary"] = str(reports / "summary.json")
    pipeline.write_json(candidate_path, candidate)
    print(json.dumps({"drc": summary["drc"], "erc": summary["erc"], "status": summary["status"]}))


if __name__ == "__main__":
    main()
