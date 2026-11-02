"""Search local LDO placement against native copper, then route a checked candidate."""
import argparse
import json
import math
from pathlib import Path

import pcbnew

import pipeline
import plan_i2s_sdo as planner
from add_i2c_pullups import obstacles, vector
from generate_rev_a import first, parse
from improve_ldo_capacitors import EVIDENCE, add_track
from repair_release_metadata import child_spans


def remove_objects(path, identifiers):
    text = path.read_text(encoding="utf-8")
    found = set()
    for start, end, block in reversed(list(child_spans(text))):
        node = parse(block)
        if node[0] in {"segment", "via"} and str(first(node, "uuid")[1]) in identifiers:
            found.add(str(first(node, "uuid")[1]))
            text = text[:start] + text[end:]
    if found != set(identifiers):
        raise RuntimeError("Route removal contract mismatch")
    path.write_text(text, encoding="utf-8")


def clear_old_stub(board):
    current = (135921500, 123436300)
    target = (128118700, 123884800)
    removed = ["8c428ffb-1cfc-4493-8dbd-a0189eba285f"]
    tracks = list(board.GetTracks())
    while current != target:
        adjacent = [track for track in tracks if track.Type() != pcbnew.PCB_VIA_T and track.GetLayer() == pcbnew.In2_Cu
                    and track.GetNetname() == "+1V8_CODEC" and track.m_Uuid.AsString() not in removed
                    and current in {tuple(track.GetStart()), tuple(track.GetEnd())}]
        if len(adjacent) != 1:
            raise RuntimeError("Old capacitor branch is not a unique pendant path")
        track = adjacent[0]
        removed.append(track.m_Uuid.AsString())
        current = tuple(track.GetEnd()) if tuple(track.GetStart()) == current else tuple(track.GetStart())
    return removed


def placement_candidates(board, footprint, fixed_references, max_candidates=80):
    fixed = [item for item in board.GetFootprints() if item.GetReference() in fixed_references]
    copper = [(pad.GetNetname(), pad.GetEffectiveShape(pcbnew.B_Cu)) for item in fixed for pad in item.Pads() if pad.IsOnLayer(pcbnew.B_Cu)]
    copper.extend((item.GetNetname(), item.GetEffectiveShape(pcbnew.B_Cu)) for item in board.GetTracks() if item.IsOnLayer(pcbnew.B_Cu))
    courts = [item.GetCourtyard(pcbnew.B_CrtYd) for item in fixed if item.GetCourtyard(pcbnew.B_CrtYd).OutlineCount()]
    through_pads = [pad.GetEffectiveShape(pcbnew.B_Cu) for item in fixed for pad in item.Pads() if pad.GetDrillSize().x]
    vias = [item for item in board.GetTracks() if item.Type() == pcbnew.PCB_VIA_T and item.IsOnLayer(pcbnew.B_Cu)]
    candidates = []
    for angle in (0, 90, 180, -90):
        footprint.SetOrientationDegrees(angle)
        for ypos_index in range(602, 642):
            for xpos_index in range(594, 666):
                center = (xpos_index / 5, ypos_index / 5)
                footprint.SetPosition(vector(center))
                court = footprint.GetCourtyard(pcbnew.B_CrtYd)
                if any(court.Collide(other, 0) for other in courts):
                    continue
                if any(court.Collide(shape, 0) for shape in through_pads):
                    continue
                valid = True
                for pad in footprint.Pads():
                    shape = pad.GetEffectiveShape(pcbnew.B_Cu)
                    if any(net != pad.GetNetname() and shape.Collide(other, pcbnew.FromMM(0.205)) for net, other in copper):
                        valid = False
                        break
                    if any(shape.Collide(via.GetEffectiveShape(pcbnew.B_Cu), pcbnew.FromMM(0.07)) for via in vias):
                        valid = False
                        break
                if valid:
                    pads = {pad.GetNumber(): [pcbnew.ToMM(value) for value in pad.GetPosition()] for pad in footprint.Pads()}
                    score = math.dist(pads["1"], (126.17, 121.98)) + 0.3 * math.dist(pads["2"], (125.25, 120.75))
                    candidates.append({"position": center, "angle": angle, "pads": pads, "score": score})
    return sorted(candidates, key=lambda entry: entry["score"])[:max_candidates]


def simplified_path(board, net, width, points):
    shapes = [pad.GetEffectiveShape(pcbnew.B_Cu) for footprint in board.GetFootprints() for pad in footprint.Pads()
              if pad.IsOnLayer(pcbnew.B_Cu) and pad.GetNetname() != net]
    shapes.extend(item.GetEffectiveShape(pcbnew.B_Cu) for item in board.GetTracks() if item.IsOnLayer(pcbnew.B_Cu) and item.GetNetname() != net)
    probe = pcbnew.PCB_TRACK(board)
    probe.SetWidth(pcbnew.FromMM(width))
    probe.SetLayer(pcbnew.B_Cu)
    simplified = [points[0][:2]]
    cursor = 0
    while cursor < len(points) - 1:
        chosen = cursor + 1
        for endpoint in range(len(points) - 1, cursor, -1):
            probe.SetStart(vector(points[cursor][:2]))
            probe.SetEnd(vector(points[endpoint][:2]))
            if not any(shape.Collide(probe.GetEffectiveShape(pcbnew.B_Cu), pcbnew.FromMM(0.205)) for shape in shapes):
                chosen = endpoint
                break
        simplified.append(points[chosen][:2])
        cursor = chosen
    return simplified


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--retry", action="store_true")
    arguments = parser.parse_args()
    candidate_path = EVIDENCE / "candidate.json"
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    work = pipeline.managed(Path(candidate["project"]))
    path = work / (pipeline.STEM + ".kicad_pcb")
    contract = json.loads((EVIDENCE / "change-contract.json").read_text(encoding="utf-8"))
    previous_path = EVIDENCE / "placement-routes.json"
    original_added = [identifier for route in contract["routes"] for identifier in route["added_tracks"]]
    if previous_path.exists():
        if not arguments.retry:
            raise FileExistsError("Review previous placement attempt before retry")
        previous = json.loads(previous_path.read_text(encoding="utf-8"))
        previous["rejected_summary"] = candidate["summary"]
        pipeline.write_json(EVIDENCE / "placement-rejected-pth.json", previous)
        stub = previous["removed_old_stub"]
        remove_objects(path, original_added)
    else:
        native = pcbnew.LoadBoard(str(path))
        stub = clear_old_stub(native)
        remove_objects(path, stub + original_added)
    board = pcbnew.LoadBoard(str(path))
    capacitor = board.FindFootprintByReference("C309")
    resistor = board.FindFootprintByReference("R703")
    fixed = {footprint.GetReference() for footprint in board.GetFootprints()} - {"C309", "R703"}
    caps = placement_candidates(board, capacitor, fixed, 12)
    pipeline.write_json(EVIDENCE / "capacitor-placement-candidates.json", caps)
    print("Legal capacitor placements: " + str(len(caps)), flush=True)
    planner.EVIDENCE = EVIDENCE
    planner.LAYERS = ["B.Cu"]
    planner.STEP = 0.025
    planner.XMIN, planner.YMIN, planner.XMAX, planner.YMAX = 118, 118, 134, 129.6
    planner.COLS = round((planner.XMAX - planner.XMIN) / planner.STEP) + 1
    planner.ROWS = round((planner.YMAX - planner.YMIN) / planner.STEP) + 1
    planner.SIZE = planner.COLS * planner.ROWS
    attempts = []
    for cap in caps:
        capacitor.SetPosition(vector(cap["position"]))
        capacitor.SetOrientationDegrees(cap["angle"])
        resistors = placement_candidates(board, resistor, fixed | {"C309"}, 20)
        resistors.sort(key=lambda entry: math.dist(entry["pads"]["1"], cap["pads"]["2"]) + math.dist(entry["pads"]["2"], (125.25, 120.75)))
        for res in resistors[:6]:
            resistor.SetPosition(vector(res["position"]))
            resistor.SetOrientationDegrees(res["angle"])
            routes = []
            request = [
                ("LDO_CAP_RETURN", 0.3, cap["pads"]["2"], res["pads"]["1"]),
                ("+1V8_CODEC", 0.3, cap["pads"]["1"], (126.17, 121.98)),
                ("POWER_GND", 0.3, res["pads"]["2"], (125.25, 120.75)),
                ("AUDIO_AMP_EN", 0.25, (123.3713, 121.1586), (130.1677, 127.955)),
            ]
            trial_path = work.parent / "ldo-placement-only.kicad_pcb"
            pcbnew.SaveBoard(str(trial_path), board)
            try:
                for net, width, start, end in request:
                    planner.WIDTH = width
                    plan = planner.solve(obstacles(board), net, start, end, [0], 0)
                    points = simplified_path(board, net, width, plan["points"])
                    added = add_track(board, net, points, width)
                    routes.append({"net": net, "width": width, "points": points, "added_tracks": added})
            except RuntimeError as error:
                attempts.append({"capacitor": cap, "resistor": res, "failure": str(error)})
                pipeline.write_json(EVIDENCE / "placement-attempts.json", attempts)
                board = pcbnew.LoadBoard(str(path))
                capacitor = board.FindFootprintByReference("C309")
                resistor = board.FindFootprintByReference("R703")
                capacitor.SetPosition(vector(cap["position"]))
                capacitor.SetOrientationDegrees(cap["angle"])
                continue
            pcbnew.SaveBoard(str(path), board)
            result = {"capacitor": cap, "resistor": res, "removed_old_stub": stub, "routes": routes, "failed_attempts": attempts}
            pipeline.write_json(EVIDENCE / "placement-routes.json", result)
            contract.setdefault("initial_routes", contract["routes"])
            contract["removed_tracks"] = sorted(set(contract["removed_tracks"]) | set(stub))
            contract["routes"] = routes
            contract["capacitor_position"] = cap["position"]
            contract["capacitor_angle"] = cap["angle"]
            contract["resistor_position"] = res["position"]
            contract["resistor_angle"] = res["angle"]
            pipeline.write_json(EVIDENCE / "change-contract.json", contract)
            reports, summary = pipeline.check(work)
            candidate["summary"] = str(reports / "summary.json")
            pipeline.write_json(candidate_path, candidate)
            print(json.dumps({"cap": cap, "resistor": res, "drc": summary["drc"], "status": summary["status"]}))
            return
    raise RuntimeError("No complete local route in searched placements")


if __name__ == "__main__":
    main()
