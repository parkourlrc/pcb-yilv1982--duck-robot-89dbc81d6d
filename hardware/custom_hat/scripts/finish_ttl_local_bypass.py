"""Resume the isolated TTL candidate with one explicit 5V branch relocation."""
import json
import math
from pathlib import Path
import shutil

import pcbnew

import pipeline
import plan_i2s_sdo as planner
import add_ttl_local_bypass as bypass
from add_i2c_pullups import obstacles, vector
from fit_ldo_candidate import remove_objects
from improve_amplifier_decoupling import add_tracks
from repair_release_metadata import properties, replace_children, set_property


VIA = "1b2f976b-25fe-4183-85a7-09eafc0b8f86"
VERTICAL = "271660fd-a107-4dbc-94f2-0ccac1c2c228"
REMOVED = {"8d444267-70f8-44a7-ab52-81fe5caf93cb"}
POSITION = (135.8, 126.0)


def route_layer(board, net, layer_name, width, start, end, evidence=None, search_margin=3, protect_i2s_reference=False):
    planner.EVIDENCE = evidence or bypass.EVIDENCE
    planner.LAYERS = [layer_name]
    planner.STEP, planner.WIDTH = 0.025, width
    edge_inset = .31 + width / 2
    planner.XMIN, planner.YMIN = max(100 + edge_inset, min(start[0], end[0]) - search_margin), max(100 + edge_inset, min(start[1], end[1]) - search_margin)
    planner.XMAX, planner.YMAX = min(165 - edge_inset, max(start[0], end[0]) + search_margin), min(130 - edge_inset, max(start[1], end[1]) + search_margin)
    planner.COLS = round((planner.XMAX - planner.XMIN) / planner.STEP) + 1
    planner.ROWS = round((planner.YMAX - planner.YMIN) / planner.STEP) + 1
    planner.SIZE = planner.COLS * planner.ROWS
    items = obstacles(board)
    if protect_i2s_reference:
        shadows = [{**item, "layer": layer_name, "net": "POWER_GND"} for item in items
                   if item["kind"] == "track" and item.get("net", "").startswith("I2S_") and item["layer"] != layer_name]
        items.extend(shadows)
    plan = planner.solve(items, net, start, end, [0], 0)
    layer = board.GetLayerID(layer_name)
    shapes = [(pad.GetNetname(), pad.GetEffectiveShape(layer)) for footprint in board.GetFootprints() for pad in footprint.Pads()
              if pad.IsOnLayer(layer) and pad.GetNetname() != net]
    shapes.extend((item.GetNetname(), item.GetEffectiveShape(layer)) for item in board.GetTracks() if item.IsOnLayer(layer) and item.GetNetname() != net)
    virtual_tracks = []
    if protect_i2s_reference:
        for item in board.GetTracks():
            if item.Type() != pcbnew.PCB_VIA_T and item.GetNetname().startswith("I2S_") and not item.IsOnLayer(layer):
                shadow = pcbnew.PCB_TRACK(board)
                shadow.SetStart(item.GetStart())
                shadow.SetEnd(item.GetEnd())
                shadow.SetWidth(item.GetWidth())
                shadow.SetLayer(layer)
                virtual_tracks.append(shadow)
                shapes.append(("POWER_GND", shadow.GetEffectiveShape(layer)))
    probe = pcbnew.PCB_TRACK(board)
    probe.SetLayer(layer)
    probe.SetWidth(pcbnew.FromMM(width))
    points = plan["points"]
    compact, cursor = [points[0][:2]], 0
    while cursor < len(points) - 1:
        chosen = None
        for endpoint in range(len(points) - 1, cursor, -1):
            probe.SetStart(vector(points[cursor][:2]))
            probe.SetEnd(vector(points[endpoint][:2]))
            if not any(shape.Collide(probe.GetEffectiveShape(layer), pcbnew.FromMM(.205 if net in planner.POWER or other_net in planner.POWER else .155)) for other_net, shape in shapes):
                chosen = endpoint
                break
        if chosen is None:
            raise RuntimeError("Native clearance rejects planner route")
        compact.append(points[chosen][:2])
        cursor = chosen
    return {"net": net, "layer": layer_name, "width_mm": width, "points": compact,
            "length_mm": sum(math.dist(first, last) for first, last in zip(compact, compact[1:])),
            "added_tracks": add_tracks(board, net, layer, compact, width)}


def main():
    candidate_path = bypass.EVIDENCE / "candidate.json"
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    work = pipeline.managed(Path(candidate["project"]))
    path = work / (pipeline.STEM + ".kicad_pcb")
    backup = work.parent / "before-ttl-local-relocation.kicad_pcb"
    if backup.exists() or (bypass.EVIDENCE / "ttl-route-contract.json").exists():
        raise FileExistsError("Inspect the prior relocation attempt before retry")
    if pipeline.digest(pipeline.PRIMARY / path.name) != bypass.BASELINE:
        raise RuntimeError("Primary board changed")
    shutil.copy2(path, backup)
    remove_objects(path, REMOVED)
    board = pcbnew.LoadBoard(str(path))
    tracks = {item.m_Uuid.AsString(): item for item in board.GetTracks()}
    tracks[VIA].SetPosition(vector(POSITION))
    branches = []
    try:
        for layer, endpoint in (("In1.Cu", (133.605, 124.9345)), ("In2.Cu", (134.6936, 126.0231))):
            branches.append(route_layer(board, "+5V", layer, 0.6, POSITION, endpoint))
        pcbnew.SaveBoard(str(path), board)
    except Exception:
        shutil.copy2(backup, path)
        raise
    pipeline.write_json(bypass.EVIDENCE / "five-volt-relocation.json", {"via": VIA, "via_after": POSITION,
                        "vertical": VERTICAL, "removed": sorted(REMOVED), "routes": branches})
    selected, failures = [], []
    for reference, device in bypass.PARTS.items():
        board = pcbnew.LoadBoard(str(path))
        capacitor = board.FindFootprintByReference(reference)
        positions = bypass.candidates(board, capacitor, device)
        pipeline.write_json(bypass.EVIDENCE / (reference + "-relocated-positions.json"), positions)
        print(reference + " candidates after relocation: " + str(len(positions)), flush=True)
        for position in positions:
            board = pcbnew.LoadBoard(str(path))
            capacitor = board.FindFootprintByReference(reference)
            capacitor.SetPosition(vector(position["position"]))
            capacitor.SetOrientationDegrees(position["angle"])
            try:
                routes = [route_layer(board, "+3V3", "B.Cu", 0.2, bypass.pad_position(board, reference, "1"), bypass.pad_position(board, device, "5")),
                          route_layer(board, "POWER_GND", "B.Cu", 0.2, bypass.pad_position(board, reference, "2"), bypass.pad_position(board, device, "3"))]
            except RuntimeError as error:
                failures.append({"reference": reference, "position": position, "error": str(error)})
                pipeline.write_json(bypass.EVIDENCE / "relocated-placement-failures.json", failures)
                continue
            pcbnew.SaveBoard(str(path), board)
            selected.append({"reference": reference, "device": device, "placement": position, "routes": routes})
            pipeline.write_json(bypass.EVIDENCE / "selected-bypasses.json", selected)
            print(reference + " routed: " + json.dumps(position) + " lengths " + str([route["length_mm"] for route in routes]), flush=True)
            break
        else:
            raise RuntimeError("No complete local bypass route for " + reference)
    def metadata(node):
        if properties(node).get("Reference") not in bypass.PARTS:
            return False
        for key, value in bypass.FIELDS.items():
            set_property(node, key, value, board=True)
        return True
    path.write_text(replace_children(path.read_text(encoding="utf-8"), "footprint", metadata), encoding="utf-8")
    pipeline.write_json(bypass.EVIDENCE / "ttl-route-contract.json", {"parts": selected, "fields": bypass.FIELDS,
        "removed_original_objects": sorted(REMOVED), "modified_original_objects": [VIA],
        "via_after": POSITION, "branches": branches, "new_vias": 0, "failed_attempts": failures,
        "preserved": ["all original footprints and pad geometry", "all original pad connections", "net assignments", "OE logic", "project settings", "rules"]})
    reports, summary = pipeline.check(work)
    candidate["summary"] = str(reports / "summary.json")
    pipeline.write_json(candidate_path, candidate)
    print(json.dumps({"drc": summary["drc"], "erc": summary["erc"], "status": summary["status"]}))


if __name__ == "__main__":
    main()
