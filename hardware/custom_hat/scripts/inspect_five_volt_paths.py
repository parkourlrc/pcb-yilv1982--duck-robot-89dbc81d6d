"""Trace actual 5V copper overlaps and separate main feeds from the feedback leaf."""
import heapq
import json
import math

import pcbnew

import pipeline


EVIDENCE = pipeline.BASE.parents[1] / "docs/references/hat-simulation-tools-20261029/five-volt-paths-20261031"
BASELINE = "af8da97fb052d1f55de10772e62a1a64559df7c82223fcad50c8c0b6d1114562"


def main():
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    path = pipeline.PRIMARY / (pipeline.STEM + ".kicad_pcb")
    if pipeline.digest(path) != BASELINE:
        raise RuntimeError("5V baseline changed")
    board = pcbnew.LoadBoard(str(path))
    layers = (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu)
    native = {}
    records = {}
    for footprint in board.GetFootprints():
        for pad in footprint.Pads():
            if pad.GetNetname() != "+5V":
                continue
            name = "pad:" + footprint.GetReference() + "." + pad.GetNumber()
            native[name] = pad
            records[name] = {"kind": "pad", "reference": footprint.GetReference(), "pin": pad.GetNumber(),
                             "position_mm": [pcbnew.ToMM(value) for value in pad.GetPosition()], "squares": 0}
    for item in board.GetTracks():
        if item.GetNetname() != "+5V":
            continue
        name = item.m_Uuid.AsString()
        native[name] = item
        is_via = item.Type() == pcbnew.PCB_VIA_T
        length = 0 if is_via else math.dist(tuple(item.GetStart()), tuple(item.GetEnd())) / 1e6
        width = pcbnew.ToMM(item.GetFrontWidth() if is_via else item.GetWidth())
        records[name] = {"kind": "via" if is_via else "track", "layer": item.GetLayerName(),
                         "start_mm": [pcbnew.ToMM(value) for value in item.GetStart()], "end_mm": [pcbnew.ToMM(value) for value in item.GetEnd()],
                         "width_mm": width, "drawn_length_mm": length, "squares": length / width if not is_via else 0}
    shapes = {name: {layer: item.GetEffectiveShape(layer) for layer in layers if item.IsOnLayer(layer)} for name, item in native.items()}
    graph = {name: [] for name in native}
    names = list(native)
    for index, name in enumerate(names):
        for other in names[index + 1:]:
            common = set(shapes[name]) & set(shapes[other])
            if any(shapes[name][layer].Collide(shapes[other][layer], 2) for layer in common):
                graph[name].append(other)
                graph[other].append(name)
    source = "pad:L301.2"
    costs = {source: 0.0}
    parents = {}
    queue = [(0.0, source)]
    while queue:
        distance, current = heapq.heappop(queue)
        if distance != costs[current]:
            continue
        for neighbor in graph[current]:
            estimate = distance + records[neighbor]["squares"]
            if estimate < costs.get(neighbor, float("inf")):
                costs[neighbor] = estimate
                parents[neighbor] = current
                heapq.heappush(queue, (estimate, neighbor))
    paths = {}
    for name in records:
        if not name.startswith("pad:") or name == source:
            continue
        if name not in costs:
            raise RuntimeError("Overlap graph failed to reach " + name)
        route = [name]
        while route[-1] != source:
            route.append(parents[route[-1]])
        route.reverse()
        widths = [records[node]["width_mm"] for node in route if records[node]["kind"] == "track"]
        paths[name] = {"objects": route, "minimum_track_width_mm": min(widths),
                       "sum_drawn_segment_lengths_mm": sum(records[node].get("drawn_length_mm", 0) for node in route),
                       "sum_squares": costs[name], "drawing_sum_1oz_25c_ohm": 0.0005 * costs[name],
                       "vias": [node for node in route if records[node]["kind"] == "via"]}
    result = {"pcb_sha256": BASELINE, "nodes": records, "overlap_graph": graph, "paths": paths,
              "model_scope": "Native same-layer copper overlap topology. Path cost sums entire drawn segment L/W and uses TI1oz25C0.5mOhm/square. Entire-segment cost and zero-cost overlap jumps can overestimate or underestimate real resistance; parallel currents are not solved, and via/pad/contact/ground-return resistance is omitted. Use this cost to locate paths, not as a physical equivalent-resistance guarantee or supply-voltage acceptance."}
    pipeline.write_json(EVIDENCE / "five-volt-topology.json", result)
    print(json.dumps({name: {key: value for key, value in data.items() if key != "objects"} for name, data in paths.items()}))


if __name__ == "__main__":
    main()
