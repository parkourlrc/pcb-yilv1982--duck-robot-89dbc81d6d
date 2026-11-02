"""Inspect native connected groups and ground polygon islands after a refill."""
import json
from pathlib import Path
import uuid

import pcbnew
import pipeline
from improve_via_annular_rings import EVIDENCE
from verify_release_metadata import snapshot


def main():
    candidate = json.loads((EVIDENCE / "candidate.json").read_text(encoding="utf-8"))
    work = pipeline.managed(Path(candidate["project"]))
    board_path = work / (pipeline.STEM + ".kicad_pcb")
    report = work.parent / ("saved-annular-" + uuid.uuid4().hex[:8] + ".json")
    pipeline.run_command([pipeline.find_cli(), "pcb", "drc", "--format", "json", "--severity-all", "--refill-zones", "--save-board", "--output", report, board_path],
                         EVIDENCE, "saved-annular", [], report)
    original = snapshot(pipeline.PRIMARY / board_path.name)
    repaired = snapshot(board_path)
    lost = {identifier: sorted(set(group) - set(repaired["connections"].get(identifier, [])))
            for identifier, group in original["connections"].items() if not set(group).issubset(repaired["connections"].get(identifier, []))}
    board = pcbnew.LoadBoard(str(board_path))
    polygons = []
    for zone in board.Zones():
        if zone.GetNetname() != "POWER_GND":
            continue
        layer = zone.GetLayer()
        shape = zone.GetFilledPolysList(layer)
        for index in range(shape.OutlineCount()):
            polygon = shape.Outline(index)
            bounds = polygon.BBox()
            pads = [footprint.GetReference() + "." + pad.GetNumber() for footprint in board.GetFootprints() for pad in footprint.Pads()
                    if pad.GetNetname() == "POWER_GND" and pad.IsOnLayer(layer) and polygon.PointInside(pad.GetPosition())]
            vias = [via.m_Uuid.AsString() for via in board.GetTracks() if via.Type() == pcbnew.PCB_VIA_T and via.GetNetname() == "POWER_GND" and polygon.PointInside(via.GetPosition())]
            polygons.append({"layer": board.GetLayerName(layer), "index": index, "bbox": [pcbnew.ToMM(value) for value in (bounds.GetLeft(), bounds.GetTop(), bounds.GetRight(), bounds.GetBottom())], "pads_inside": pads, "vias_inside": vias})
    result = {"lost_connections": lost, "lost_pad_names": [repaired["pads"].get(identifier) for identifier in lost], "ground_polygons": polygons}
    pipeline.write_json(EVIDENCE / "native-connectivity-diagnostic.json", result)
    print(json.dumps({"lost_pad_count": len(lost), "ground_polygons": polygons}))


if __name__ == "__main__":
    main()
