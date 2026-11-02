"""Explore removing the codec HDI via with an explicit local SDI/SDO reroute."""
import json
import argparse
import math
from pathlib import Path

import pcbnew

import pipeline
from add_i2c_pullups import vector
from fit_ldo_candidate import remove_objects
from finish_ttl_local_bypass import route_layer


EVIDENCE = pipeline.BASE.parents[1] / "docs/references/hat-simulation-tools-20261029/u701-through-via-20261031"
BASELINE = "b06b1051d84509c7434347d5889afb7908dffe1af99b67eea67eb4c3e33a9849"
POWER_VIA = "c6ad78c2-361f-4c03-a650-a32f6c415d72"
SDO_VIA = "f1d6fcd1-f8d6-4abc-870e-838590222a6e"
REMOVED = {"32bcce4f-0c46-4431-ba9c-597ff40bef9a", "a38ba9d2-6fa7-4b1e-ae9e-408a287d1ab0", "e0b332c8-0fe0-4b98-ad36-a21defb7767a", "e52a2ff9-5693-4118-9e2b-2851c63a964f",
           "0576fed2-2183-4678-a0b1-7d1c01dc1524", "2a881d9d-5f8c-48c5-a258-c55298ef4351", "67dc2bda-3626-4533-a4c4-6b3aff806a81", "d475c2ea-a754-43da-a500-0efe14644317",
           "bc4a4abb-3a0b-4955-bfec-fd1ec20e7243", "c5d4af8b-f46e-441b-a03e-d844543e0c80"}
POWER_POSITION = (149.45, 112.1)


def via_positions(board, via, target=(148.3, 112.9)):
    layers = (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu)
    shapes = {layer: [(pad.GetNetname(), pad.GetEffectiveShape(layer)) for footprint in board.GetFootprints() for pad in footprint.Pads()
                     if pad.IsOnLayer(layer) and pad.GetNetname() != via.GetNetname()] +
                    [(item.GetNetname(), item.GetEffectiveShape(layer)) for item in board.GetTracks() if item.IsOnLayer(layer) and item.GetNetname() != via.GetNetname()]
              for layer in layers}
    results = []
    for horizontal in range(1460, 1493):
        for vertical in range(1095, 1140):
            position = (horizontal / 10, vertical / 10)
            via.SetPosition(vector(position))
            if any(shape.Collide(via.GetEffectiveShape(layer), pcbnew.FromMM(.205 if net in {"POWER_GND", "+3V3", "+5V", "BUCK_SW", "VBATT_2S_IN", "SERVO_VBAT"} else .155))
                   for layer, items in shapes.items() for net, shape in items):
                continue
            results.append(position)
    return sorted(results, key=lambda point: math.dist(point, target))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--retry-smaller-sdo", action="store_true")
    parser.add_argument("--retry-clock-route", action="store_true")
    parser.add_argument("--compact-power-via", action="store_true")
    arguments = parser.parse_args()
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    candidate_path = EVIDENCE / "candidate.json"
    if candidate_path.exists() and not arguments.retry_smaller_sdo:
        raise FileExistsError("Inspect the existing through-via candidate")
    if arguments.retry_smaller_sdo:
        previous = json.loads(candidate_path.read_text(encoding="utf-8"))
        if previous.get("promoted") or (EVIDENCE / "route-contract.json").exists():
            raise RuntimeError("Cannot replace an accepted candidate")
        pipeline.write_json(EVIDENCE / ("candidate-rejected-before-compact.json" if arguments.compact_power_via else "candidate-rejected-before-clock.json" if arguments.retry_clock_route else "candidate-rejected-0p55.json"), previous)
    if pipeline.digest(pipeline.PRIMARY / (pipeline.STEM + ".kicad_pcb")) != BASELINE:
        raise RuntimeError("Source changed")
    work = pipeline.prepare(pipeline.PRIMARY)
    path = work / (pipeline.STEM + ".kicad_pcb")
    candidate = {"project": str(work), "baseline": BASELINE, "promoted": False}
    pipeline.write_json(candidate_path, candidate)
    removed = set(REMOVED)
    if arguments.retry_clock_route:
        original = pcbnew.LoadBoard(str(path))
        removed.update(item.m_Uuid.AsString() for item in original.GetTracks() if item.Type() != pcbnew.PCB_VIA_T
                       and item.GetNetname() == "I2S_BCLK" and item.GetLayer() == pcbnew.B_Cu
                       and min(item.GetStart().x, item.GetEnd().x) >= pcbnew.FromMM(147.5))
    remove_objects(path, removed)
    board = pcbnew.LoadBoard(str(path))
    tracks = {item.m_Uuid.AsString(): item for item in board.GetTracks()}
    power = tracks[POWER_VIA]
    power.SetViaType(pcbnew.VIATYPE_THROUGH)
    power.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    power_diameter, power_drill = (.45, .2) if arguments.compact_power_via else (.55, .3)
    power_position = (149.7, 112.1) if arguments.compact_power_via else POWER_POSITION
    power.SetWidth(pcbnew.FromMM(power_diameter))
    power.SetDrill(pcbnew.FromMM(power_drill))
    power.SetPosition(vector(power_position))
    tracks[SDO_VIA].SetPosition(vector((180, 180)))
    if arguments.retry_smaller_sdo:
        tracks[SDO_VIA].SetWidth(pcbnew.FromMM(.45))
        tracks[SDO_VIA].SetDrill(pcbnew.FromMM(.2))
    power_route = route_layer(board, "+3V3", "B.Cu", .2, (150.3625, 112.1), power_position, EVIDENCE)
    pcbnew.SaveBoard(str(path), board)
    positions = via_positions(board, tracks[SDO_VIA], (149.0, 111.95) if arguments.compact_power_via else (148.3, 112.9))
    pipeline.write_json(EVIDENCE / ("sdo-via-compact-positions.json" if arguments.compact_power_via else "sdo-via-clock-positions.json" if arguments.retry_clock_route else "sdo-via-smaller-positions.json" if arguments.retry_smaller_sdo else "sdo-via-positions.json"), positions)
    print("Native-clear SDO via options: " + str(len(positions)), flush=True)
    failures, selected = [], None
    for position in positions[:50]:
        board = pcbnew.LoadBoard(str(path))
        via = next(item for item in board.GetTracks() if item.m_Uuid.AsString() == SDO_VIA)
        via.SetPosition(vector(position))
        try:
            routes = [route_layer(board, "I2S_SDI", "B.Cu", .15, (150.3625, 113.1), (149.55, 111.25), EVIDENCE),
                      route_layer(board, "I2S_SDO", "B.Cu", .15, (150.3625, 113.6), position, EVIDENCE),
                      route_layer(board, "I2S_SDO", "F.Cu", .15, position, (152.6, 108.95), EVIDENCE)]
            if arguments.retry_clock_route:
                routes.append(route_layer(board, "I2S_BCLK", "B.Cu", .15, (150.3625, 114.6), (147.55, 110.35), EVIDENCE))
        except RuntimeError as error:
            failures.append({"position": position, "error": str(error)})
            pipeline.write_json(EVIDENCE / ("failed-compact-routes.json" if arguments.compact_power_via else "failed-clock-routes.json" if arguments.retry_clock_route else "failed-routes.json"), failures)
            continue
        selected = {"position": position, "routes": routes}
        pcbnew.SaveBoard(str(path), board)
        break
    if not selected:
        raise RuntimeError("No full local route; the primary HDI design is unchanged")
    pipeline.write_json(EVIDENCE / "route-contract.json", {"removed_original_objects": sorted(removed), "modified_original_objects": [POWER_VIA, SDO_VIA],
        "power_via": {"uuid": POWER_VIA, "position": power_position, "diameter_mm": power_diameter, "drill_mm": power_drill, "type": "through"},
        "sdo_via": {"uuid": SDO_VIA, "position": selected["position"], "diameter_mm": .45 if arguments.retry_smaller_sdo else .55, "drill_mm": .2 if arguments.retry_smaller_sdo else .3}, "routes": [power_route, *selected["routes"]],
        "all_original_pad_geometry_and_nets_must_be_preserved": True, "all_original_connections_must_be_preserved": True, "failures": failures})
    reports, summary = pipeline.check(work)
    candidate["summary"] = str(reports / "summary.json")
    pipeline.write_json(candidate_path, candidate)
    print(json.dumps({"selected": selected["position"], "status": summary["status"], "drc": summary["drc"]}), flush=True)


if __name__ == "__main__":
    main()
