"""Detour one audio segment to connect the LRCK reference-copper pocket."""
import json
import uuid

import pcbnew

import pipeline
import plan_i2s_sdo as planner
from add_i2c_pullups import obstacles, vector
from fit_ldo_candidate import remove_objects
from stitch_i2s_reference_pocket import EVIDENCE, BASELINE, coverage


def main():
    candidate_path = EVIDENCE / "candidate.json"
    if candidate_path.exists():
        raise FileExistsError("Inspect existing coupled stitch candidate before retry")
    source = pipeline.PRIMARY / (pipeline.STEM + ".kicad_pcb")
    if pipeline.digest(source) != BASELINE:
        raise RuntimeError("Primary baseline changed")
    choices = json.loads((EVIDENCE / "movable-obstacles.json").read_text(encoding="utf-8"))["choices"]
    choice = choices[0]
    if choice["blocker_count"] != 1 or choice["distinct_nets"] != ["AUDIO_HP_L"]:
        raise RuntimeError("Expected one evidenced audio segment obstruction")
    blocked = choice["blockers"][0]
    original = pcbnew.LoadBoard(str(source))
    work = pipeline.prepare(pipeline.PRIMARY)
    path = work / source.name
    candidate = {"project": str(work), "baseline": BASELINE, "promoted": False}
    pipeline.write_json(candidate_path, candidate)
    remove_objects(path, [blocked["id"]])
    board = pcbnew.LoadBoard(str(path))
    via = pcbnew.PCB_VIA(board)
    via.SetPosition(vector(choice["position_mm"]))
    via.SetWidth(pcbnew.FromMM(0.6))
    via.SetDrill(pcbnew.FromMM(0.3))
    via.SetViaType(pcbnew.VIATYPE_THROUGH)
    via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    via.SetNetCode(board.FindNet("POWER_GND").GetNetCode())
    board.Add(via)
    planner.EVIDENCE = EVIDENCE
    planner.LAYERS = ["In2.Cu"]
    planner.WIDTH, planner.STEP = blocked["width_mm"], 0.025
    planner.XMIN, planner.YMIN, planner.XMAX, planner.YMAX = 148, 108, 153, 113
    planner.COLS = round((planner.XMAX - planner.XMIN) / planner.STEP) + 1
    planner.ROWS = round((planner.YMAX - planner.YMIN) / planner.STEP) + 1
    planner.SIZE = planner.COLS * planner.ROWS
    plan = planner.solve(obstacles(board), "AUDIO_HP_L", blocked["start"], blocked["end"], [0], 0)
    layer = pcbnew.In2_Cu
    shapes = [pad.GetEffectiveShape(layer) for footprint in board.GetFootprints() for pad in footprint.Pads()
              if pad.IsOnLayer(layer) and pad.GetNetname() != "AUDIO_HP_L"]
    shapes.extend(item.GetEffectiveShape(layer) for item in board.GetTracks() if item.IsOnLayer(layer) and item.GetNetname() != "AUDIO_HP_L")
    probe = pcbnew.PCB_TRACK(board)
    probe.SetWidth(pcbnew.FromMM(blocked["width_mm"]))
    probe.SetLayer(layer)
    points = plan["points"]
    simplified = [points[0]]
    cursor = 0
    while cursor < len(points) - 1:
        chosen = cursor + 1
        for endpoint in range(len(points) - 1, cursor, -1):
            probe.SetStart(vector(points[cursor][:2]))
            probe.SetEnd(vector(points[endpoint][:2]))
            if not any(shape.Collide(probe.GetEffectiveShape(layer), pcbnew.FromMM(0.205)) for shape in shapes):
                chosen = endpoint
                break
        simplified.append(points[chosen])
        cursor = chosen
    added = [via.m_Uuid.AsString()]
    for start, end in zip(simplified, simplified[1:]):
        track = pcbnew.PCB_TRACK(board)
        track.SetStart(vector(start[:2]))
        track.SetEnd(vector(end[:2]))
        track.SetWidth(pcbnew.FromMM(blocked["width_mm"]))
        track.SetLayer(layer)
        track.SetNetCode(board.FindNet("AUDIO_HP_L").GetNetCode())
        board.Add(track)
        added.append(track.m_Uuid.AsString())
    pcbnew.SaveBoard(str(path), board)
    report = work.parent / ("coupled-stitch-refill-" + uuid.uuid4().hex[:8] + ".json")
    pipeline.run_command([pipeline.find_cli(), "pcb", "drc", "--format", "json", "--severity-all", "--schematic-parity", "--refill-zones", "--save-board", "--output", report, path],
                         EVIDENCE, "coupled-stitch-refill", [], report)
    updated = pcbnew.LoadBoard(str(path))
    pipeline.write_json(EVIDENCE / "stitch-contract.json", {"new_via": via.m_Uuid.AsString(), "position_mm": choice["position_mm"], "diameter_mm": 0.6, "drill_mm": 0.3,
                        "removed_tracks": [blocked["id"]], "added_tracks": added, "audio_route_points": simplified,
                        "audio_original": blocked, "before": coverage(original), "after": coverage(updated), "source_before": BASELINE,
                        "reference_scope": "Native F.Cu ground-zone coverage under the unchanged In1 LRCK centerline; no EMI/impedance claim"})
    reports, summary = pipeline.check(work)
    candidate["summary"] = str(reports / "summary.json")
    pipeline.write_json(candidate_path, candidate)
    print(json.dumps({"before": coverage(original), "after": coverage(updated), "via": choice["position_mm"], "audio_segments": len(added) - 1,
                      "drc": summary["drc"], "status": summary["status"]}))


if __name__ == "__main__":
    main()
