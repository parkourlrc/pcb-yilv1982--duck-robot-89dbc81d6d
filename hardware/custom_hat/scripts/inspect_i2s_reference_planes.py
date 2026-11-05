"""Audit I2S reference copper and analyzer islands against native KiCad geometry."""
from collections import defaultdict
import argparse
import csv
import json
import math
from pathlib import Path

import pcbnew

import pipeline
from generate_rev_a import first, parse
from verify_release_metadata import snapshot


EVIDENCE = pipeline.BASE.parents[1] / "docs/references/扩展板电路仿真工具/i2s-reference-20261031"
PREVIOUS = EVIDENCE.parent / "ldo-capacitors-20261031"
PLANES = [(pcbnew.F_Cu, "POWER_GND"), (pcbnew.In1_Cu, "POWER_GND"), (pcbnew.In2_Cu, "+3V3"), (pcbnew.B_Cu, "POWER_GND")]
STEP_MM = 0.025


def main():
    global EVIDENCE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path)
    parser.add_argument("--prefix", default="native")
    parser.add_argument("--evidence", type=Path)
    arguments = parser.parse_args()
    EVIDENCE = arguments.evidence.resolve() if arguments.evidence else EVIDENCE
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    project = pipeline.managed(arguments.project) if arguments.project else pipeline.PRIMARY
    path = project / (pipeline.STEM + ".kicad_pcb")
    digest = pipeline.digest(path)
    checkpoint = json.loads((PREVIOUS / "checkpoint.json").read_text(encoding="utf-8"))
    if not arguments.project and digest != checkpoint["pcb_sha256"]:
        raise RuntimeError("Source changed since native refill/check")
    board = pcbnew.LoadBoard(str(path))
    actual = snapshot(path)
    summary = {}
    for net in ("+3V3", "POWER_GND"):
        identifiers = {identifier for identifier, name in actual["nets"].items() if name == net}
        groups = {tuple(sorted(set(actual["connections"].get(identifier, [])) & identifiers)) for identifier in identifiers}
        summary[net] = {"pad_count": len(identifiers), "native_pad_groups": len(groups),
                        "groups": [[actual["pads"][identifier]["reference"] + "." + actual["pads"][identifier]["pin"] for identifier in group] for group in groups]}
    polygons = []
    zone_shapes = {}
    for layer, net in PLANES:
        key = board.GetLayerName(layer) + ":" + net
        shapes = [zone.GetFilledPolysList(layer) for zone in board.Zones() if zone.IsOnLayer(layer) and zone.GetNetname() == net]
        zone_shapes[key] = shapes
        regions = []
        for shape in shapes:
            for index in range(shape.OutlineCount()):
                outline = shape.Outline(index)
                bounds = outline.BBox()
                regions.append({"index": index, "outer_area_mm2": outline.Area() / 1e12,
                                "bbox_mm": [pcbnew.ToMM(value) for value in (bounds.GetLeft(), bounds.GetTop(), bounds.GetRight(), bounds.GetBottom())],
                                "same_net_vias": [[pcbnew.ToMM(value) for value in via.GetPosition()] for via in board.GetTracks()
                                                  if via.Type() == pcbnew.PCB_VIA_T and via.GetNetname() == net and via.IsOnLayer(layer) and shape.Contains(via.GetPosition(), index)]})
        polygons.append({"layer": board.GetLayerName(layer), "net": net, "outline_count": sum(shape.OutlineCount() for shape in shapes),
                         "area_mm2": sum(shape.Area() for shape in shapes) / 1e12, "regions": regions})
    rows = []
    stats = defaultdict(lambda: {"total_mm": 0.0, "covered_mm": 0.0})
    for track in board.GetTracks():
        if track.Type() == pcbnew.PCB_VIA_T or not track.GetNetname().startswith("I2S_"):
            continue
        start, end = track.GetStart(), track.GetEnd()
        delta = (end.x - start.x, end.y - start.y)
        length = math.hypot(*delta) / 1e6
        subdivisions = max(1, math.ceil(length / STEP_MM))
        row_length = length / subdivisions
        for index in range(subdivisions):
            fraction = (index + 0.5) / subdivisions
            point = pcbnew.VECTOR2I(round(start.x + delta[0] * fraction), round(start.y + delta[1] * fraction))
            row = {"net": track.GetNetname(), "source_layer": track.GetLayerName(), "segment": track.m_Uuid.AsString(),
                   "x_mm": pcbnew.ToMM(point.x), "y_mm": pcbnew.ToMM(point.y), "represented_mm": row_length}
            for key, shapes in zone_shapes.items():
                covered = any(shape.Contains(point) for shape in shapes)
                row[key] = covered
                if key.split(":")[0] == track.GetLayerName():
                    continue
                record = stats[(track.GetNetname(), track.GetLayerName(), key)]
                record["total_mm"] += row_length
                record["covered_mm"] += row_length if covered else 0
            rows.append(row)
    coverage = [{"net": net, "source_layer": layer, "reference_copper": ref, **value,
                 "centerline_coverage_pct": 100 * value["covered_mm"] / value["total_mm"]}
                for (net, layer, ref), value in sorted(stats.items())]
    with (EVIDENCE / (arguments.prefix + "-plane-samples.csv")).open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    microvias = [{"id": via.m_Uuid.AsString(), "net": via.GetNetname(), "position_mm": [pcbnew.ToMM(value) for value in via.GetPosition()],
                  "layers": [board.GetLayerName(via.TopLayer()), board.GetLayerName(via.BottomLayer())]}
                 for via in board.GetTracks() if via.Type() == pcbnew.PCB_VIA_T and via.GetViaType() == pcbnew.VIATYPE_MICROVIA]
    analyzer = json.loads((PREVIOUS / "pcb.json").read_text(encoding="utf-8"))
    setup = first(parse(path.read_text(encoding="utf-8")), "setup")
    result = {"pcb_sha256": digest, "source_checkpoint": str(project.parent / "manifest.json") if arguments.project else str(PREVIOUS / "checkpoint.json"),
              "native_connectivity": summary, "native_zone_polygons": polygons, "microvias": microvias,
              "analyzer_3v3_graph": analyzer["connectivity_graph"]["+3V3"], "analyzer_graph_source": str(PREVIOUS / "pcb.json"),
              "analyzer_graph_source_pcb_sha256": checkpoint["pcb_sha256"], "explicit_stackup_present": first(setup, "stackup") is not None,
              "sample_spacing_upper_bound_mm": STEP_MM, "length_weighted_centerline_samples": True,
              "sample_scope": "Filled zones only, exact native polygons including holes; does not count other pads/tracks or give automatic via-antipad credit. Not field/impedance/EMI simulation. Reference-layer dominance cannot be assigned without layer distances.",
              "coverage": coverage, "hardware_verified": False, "production_ready": False}
    if pipeline.digest(path) != digest:
        raise RuntimeError("Board changed during inspection")
    pipeline.write_json(EVIDENCE / (arguments.prefix + "-reference-check.json"), result)
    print(json.dumps({"native_groups": {net: info["native_pad_groups"] for net, info in summary.items()},
                      "zones": [{key: value for key, value in zone.items() if key != "regions"} for zone in polygons], "microvias": microvias,
                      "lrck_coverage": [record for record in coverage if record["net"] == "I2S_LRCK"]}))


if __name__ == "__main__":
    main()
