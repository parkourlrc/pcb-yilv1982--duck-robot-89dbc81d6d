"""Connect the selected header pin using its plated barrel as a layer choice."""
import json
import argparse
import math
from pathlib import Path

import pcbnew

import pipeline
import plan_i2s_sdo as planner
from add_i2c_pullups import obstacles, vector
from connect_codec_hardware_reset import EVIDENCE
from improve_amplifier_decoupling import add_tracks
from fit_ldo_candidate import remove_objects


def reference_guards(board):
    guards = []
    for track in board.GetTracks():
        if track.Type() == pcbnew.PCB_VIA_T or not track.GetNetname().startswith("I2S_"):
            continue
        start, end = track.GetStart(), track.GetEnd()
        delta = (end.x - start.x, end.y - start.y)
        divisions = max(1, math.ceil(math.hypot(*delta) / 25000))
        for layer_name in ("F.Cu", "In1.Cu", "In2.Cu", "B.Cu"):
            layer = board.GetLayerID(layer_name)
            if track.IsOnLayer(layer):
                continue
            reference_net = "+3V3" if layer_name == "In2.Cu" else "POWER_GND"
            polygons = [zone.GetFilledPolysList(layer) for zone in board.Zones()
                        if zone.IsOnLayer(layer) and zone.GetNetname() == reference_net]
            run = []
            for index in range(divisions + 1):
                point = None
                if index < divisions:
                    fraction = (index + .5) / divisions
                    point = pcbnew.VECTOR2I(round(start.x + delta[0] * fraction), round(start.y + delta[1] * fraction))
                covered = point is not None and any(polygon.Contains(point) for polygon in polygons)
                if covered:
                    run.append(tuple(pcbnew.ToMM(value) for value in point))
                if run and not covered:
                    guards.append({"kind": "track", "net": "POWER_GND", "layer": layer_name,
                                   "start": run[0], "end": run[-1], "width": .01,
                                   "protected_net": track.GetNetname(), "protected_track": track.m_Uuid.AsString()})
                    run = []
    return guards


def compact_run(board, layer, points, guards):
    shapes = [(pad.GetNetname(), pad.GetEffectiveShape(layer)) for footprint in board.GetFootprints() for pad in footprint.Pads()
              if pad.IsOnLayer(layer) and pad.GetNetname() != "CODEC_RST"]
    shapes.extend((item.GetNetname(), item.GetEffectiveShape(layer)) for item in board.GetTracks() if item.IsOnLayer(layer) and item.GetNetname() != "CODEC_RST")
    virtual_tracks = []
    for item in guards:
        if board.GetLayerID(item["layer"]) != layer:
            continue
        shadow = pcbnew.PCB_TRACK(board)
        shadow.SetStart(vector(item["start"]))
        shadow.SetEnd(vector(item["end"]))
        shadow.SetWidth(pcbnew.FromMM(item["width"]))
        shadow.SetLayer(layer)
        virtual_tracks.append(shadow)
        shapes.append(("POWER_GND", shadow.GetEffectiveShape(layer)))
    keepouts = [zone.Outline() for zone in board.Zones() if zone.IsOnLayer(layer) and zone.GetIsRuleArea() and zone.GetDoNotAllowTracks()]
    probe = pcbnew.PCB_TRACK(board)
    probe.SetLayer(layer)
    probe.SetWidth(pcbnew.FromMM(.15))
    compact, cursor = [points[0]], 0
    while cursor < len(points) - 1:
        chosen = None
        for endpoint in range(len(points) - 1, cursor, -1):
            probe.SetStart(vector(points[cursor]))
            probe.SetEnd(vector(points[endpoint]))
            if not any(shape.Collide(probe.GetEffectiveShape(layer), pcbnew.FromMM(.205 if net in planner.POWER else .155)) for net, shape in shapes) and not any(shape.Collide(probe.GetEffectiveShape(layer), 0) for shape in keepouts):
                chosen = endpoint
                break
        if chosen is None:
            raise RuntimeError("Native clearance rejects a reset segment")
        compact.append(points[chosen])
        cursor = chosen
    return compact


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--retry-outer-only", action="store_true")
    parser.add_argument("--outer-only", action="store_true")
    parser.add_argument("--protect-i2s-reference", action="store_true")
    parser.add_argument("--endpoint", choices=("codec-via", "pullup"), default="pullup")
    arguments = parser.parse_args()
    candidate_path = EVIDENCE / "candidate.json"
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    work = pipeline.managed(Path(candidate["project"]))
    path = work / (pipeline.STEM + ".kicad_pcb")
    contract_path = EVIDENCE / "change-contract.json"
    if contract_path.exists():
        if not arguments.retry_outer_only or candidate.get("promoted"):
            raise RuntimeError("A reset route is already recorded")
        previous = json.loads(contract_path.read_text(encoding="utf-8"))
        previous["rejected_summary"] = candidate.get("summary")
        previous["rejected_pcb_sha256"] = pipeline.digest(path)
        pipeline.write_json(EVIDENCE / "rejected-in2-route.json", previous)
        identifiers = [identifier for route in previous["routes"] for identifier in route["added_tracks"]]
        identifiers.extend(via["uuid"] for via in previous["new_vias"])
        remove_objects(path, identifiers)
        contract_path.unlink()
    board = pcbnew.LoadBoard(str(path))
    header_pin = str(candidate["header_pin"])
    header = next(pad for pad in board.FindFootprintByReference("J101").Pads() if pad.GetNumber() == header_pin)
    if header.GetNetname() != "CODEC_RST":
        raise RuntimeError("Selected header pin must already be assigned to CODEC_RST")
    start = tuple(pcbnew.ToMM(value) for value in header.GetPosition())
    planner.EVIDENCE = EVIDENCE
    outer_only = arguments.retry_outer_only or arguments.outer_only
    planner.LAYERS = ["F.Cu", "B.Cu"] if outer_only else ["F.Cu", "B.Cu", "In1.Cu", "In2.Cu"]
    planner.STEP, planner.WIDTH = .05, .15
    planner.XMIN, planner.YMIN, planner.XMAX, planner.YMAX = 100.4, 100.4, 164.6, 129.6
    planner.COLS = round((planner.XMAX - planner.XMIN) / planner.STEP) + 1
    planner.ROWS = round((planner.YMAX - planner.YMIN) / planner.STEP) + 1
    planner.SIZE = planner.COLS * planner.ROWS
    planner.VIA_AVOID_RADIUS, planner.VIA_PENALTY = .275, 200 if outer_only else 400
    planner.VIA_BOUNDS = (100.6, 100.6, 164.4, 129.4)
    available_layers = list(range(len(planner.LAYERS)))
    if arguments.endpoint == "pullup":
        endpoint = next(pad for pad in board.FindFootprintByReference("R308").Pads() if pad.GetNumber() == "1")
        end_position = tuple(pcbnew.ToMM(value) for value in endpoint.GetPosition())
        end_layers = [index for index, name in enumerate(planner.LAYERS) if endpoint.IsOnLayer(board.GetLayerID(name))]
    else:
        end_position, end_layers = (146.3246, 114.0141), available_layers
    items = obstacles(board)
    guards = reference_guards(board) if arguments.protect_i2s_reference else []
    items.extend(guards)
    pipeline.write_json(EVIDENCE / "reset-reference-guards.json", guards)
    plan = planner.solve(items, "CODEC_RST", start, end_position, end_layers, available_layers)
    pipeline.write_json(EVIDENCE / ("outer-layer-plan.json" if arguments.retry_outer_only else "multilayer-plan.json"), plan)
    points = plan["points"]
    transitions = sorted({tuple(first_point[:2]) for first_point, last_point in zip(points, points[1:]) if first_point[2] != last_point[2]})
    if len(transitions) > 2:
        raise RuntimeError("Reset route uses too many new vias; inspect before continuing")
    added_vias = []
    for position in transitions:
        via = pcbnew.PCB_VIA(board)
        via.SetPosition(vector(position))
        via.SetViaType(pcbnew.VIATYPE_THROUGH)
        via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        via.SetWidth(pcbnew.FromMM(.55))
        via.SetDrill(pcbnew.FromMM(.3))
        via.SetNetCode(board.FindNet("CODEC_RST").GetNetCode())
        board.Add(via)
        added_vias.append({"uuid": via.m_Uuid.AsString(), "position": position, "diameter_mm": .55, "drill_mm": .3})
    runs = []
    layer_index, run = points[0][2], [points[0][:2]]
    for point in points[1:]:
        if point[2] != layer_index:
            runs.append((layer_index, run))
            layer_index, run = point[2], [point[:2]]
        else:
            run.append(point[:2])
    runs.append((layer_index, run))
    routes = []
    for layer_index, run in runs:
        if len(run) < 2:
            continue
        layer_name = planner.LAYERS[layer_index]
        layer = board.GetLayerID(layer_name)
        compact = compact_run(board, layer, run, guards)
        routes.append({"net": "CODEC_RST", "layer": layer_name, "width_mm": .15, "points": compact,
                       "length_mm": sum(math.dist(first_point, last_point) for first_point, last_point in zip(compact, compact[1:])),
                       "added_tracks": add_tracks(board, "CODEC_RST", layer, compact, .15)})
    pcbnew.SaveBoard(str(path), board)
    pipeline.write_json(EVIDENCE / "change-contract.json", {"schematic": candidate["schematic_change"], "header_pin": int(header_pin),
        "header_pad_uuid": header.m_Uuid.AsString(), "header_old_net": f"unconnected-(J101-Pin_{header_pin}-Pad{header_pin})", "header_new_net": "CODEC_RST", "header_new_pin_type": "passive",
        "routes": routes, "new_vias": added_vias, "removed_original_copper": [], "changed_existing_copper": [],
        "gpio_source": f"Radxa ZERO3 physical{header_pin} {candidate['gpio_name']},3.3V", "hardware_tested": False,
        "i2s_filled_reference_protected": arguments.protect_i2s_reference,
        "reference_sampling_mm": .025})
    reports, summary = pipeline.check(work)
    candidate["summary"] = str(reports / "summary.json")
    pipeline.write_json(candidate_path, candidate)
    print(json.dumps({"new_vias": added_vias, "route_lengths": [row["length_mm"] for row in routes], "status": summary["status"], "drc": summary["drc"], "erc": summary["erc"]}))


if __name__ == "__main__":
    main()
