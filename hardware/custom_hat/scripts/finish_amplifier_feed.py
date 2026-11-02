"""Simplify only the new amplifier input branch using native copper clearance."""
import json
from pathlib import Path

import pcbnew

import pipeline
from add_i2c_pullups import vector
from fit_ldo_candidate import remove_objects
from improve_amplifier_decoupling import EVIDENCE, add_tracks


def main():
    candidate_path = EVIDENCE / "candidate.json"
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    work = pipeline.managed(Path(candidate["project"]))
    path = work / (pipeline.STEM + ".kicad_pcb")
    contract_path = EVIDENCE / "amp-route-contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    route = next(item for item in contract["routes"] if item["layer"] == "In2.Cu")
    if "points_before_simplification" in route or candidate["promoted"]:
        raise RuntimeError("Amplifier feed already simplified/promoted")
    board = pcbnew.LoadBoard(str(path))
    layer = pcbnew.In2_Cu
    shapes = [pad.GetEffectiveShape(layer) for footprint in board.GetFootprints() for pad in footprint.Pads()
              if pad.IsOnLayer(layer) and pad.GetNetname() != "+5V"]
    shapes.extend(item.GetEffectiveShape(layer) for item in board.GetTracks() if item.IsOnLayer(layer) and item.GetNetname() != "+5V")
    probe = pcbnew.PCB_TRACK(board)
    probe.SetLayer(layer)
    probe.SetWidth(pcbnew.FromMM(0.6))
    points = route["points"]
    simplified = [points[0]]
    cursor = 0
    while cursor < len(points) - 1:
        selected = cursor + 1
        for endpoint in range(len(points) - 1, cursor, -1):
            probe.SetStart(vector(points[cursor]))
            probe.SetEnd(vector(points[endpoint]))
            if not any(shape.Collide(probe.GetEffectiveShape(layer), pcbnew.FromMM(0.205)) for shape in shapes):
                selected = endpoint
                break
        simplified.append(points[selected])
        cursor = selected
    removed = route["added_tracks"]
    remove_objects(path, removed)
    board = pcbnew.LoadBoard(str(path))
    route["points_before_simplification"] = points
    route["points"] = simplified
    route["added_tracks"] = add_tracks(board, "+5V", layer, simplified, 0.6)
    pcbnew.SaveBoard(str(path), board)
    pipeline.write_json(contract_path, contract)
    reports, summary = pipeline.check(work)
    candidate["summary"] = str(reports / "summary.json")
    pipeline.write_json(candidate_path, candidate)
    print(json.dumps({"segments_before": len(removed), "segments_after": len(route["added_tracks"]), "drc": summary["drc"], "status": summary["status"]}))


if __name__ == "__main__":
    main()
