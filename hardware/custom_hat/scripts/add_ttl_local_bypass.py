"""Add two local 100nF VCC bypasses for the TTL buffers in an isolated project."""
import json
import math
from pathlib import Path

import pcbnew

import pipeline
import plan_i2s_sdo as planner
from add_i2c_pullups import obstacles, vector
from generate_rev_a import Sheet, children, dump, first, parse, uid
from repair_release_metadata import properties, replace_children, set_property


EVIDENCE = pipeline.BASE.parents[1] / "docs/references/扩展板电路仿真工具/ttl-bypass-20261031"
BASELINE = "d6c72facdd3b68fda23a7f09b557c01a5e9bf0eb06f7662aa46990d9bd7bb805"
PARTS = {"C329": "U801", "C330": "U802"}
FIELDS = {"MPN": "C0402C104K3RACTU", "Manufacturer": "KEMET", "Voltage Rating": "25V", "Dielectric": "X7R", "Tolerance": "10%",
          "Datasheet": "https://content.kemet.com/datasheets/KEM_C1002_X7R_SMD.pdf",
          "BOM Comments": "Dedicated100nF TTL-buffer VCC bypass;TI SCES224S/SCES223U power-supply recommendations;not hardware verified"}


def pad_position(board, reference, number):
    pad = next(pad for pad in board.FindFootprintByReference(reference).Pads() if pad.GetNumber() == number)
    return tuple(pcbnew.ToMM(value) for value in pad.GetPosition())


def append_schematic(work):
    path = work / "servo_ttl.kicad_sch"
    original = path.read_text(encoding="utf-8")
    existing = {properties(node).get("Reference") for node in children(parse(original), "symbol")}
    if set(PARTS) & existing:
        raise RuntimeError("TTL capacitor reference already exists")
    sheet = Sheet("servo_ttl", "Local TTL bypasses")
    sheet.counter = 4000
    for index, reference in enumerate(PARTS):
        sheet.component("Device:C", reference, "100nF", 203.2 + 40.64 * index, 175.26,
                        {"1": "+3V3", "2": "POWER_GND"}, "Capacitor_SMD:C_0402_1005Metric")
    for symbol in children(sheet.tree, "symbol"):
        for key, value in FIELDS.items():
            set_property(symbol, key, value)
    sheet.text("C329/C330: local100nF bypasses from VCC toGND at U801/U802; existing bus polarity and OE logic unchanged.", 35.56, 198.12)
    library = first(parse(original), "lib_symbols")
    if not any(node[1] == "Device:C" for node in children(library, "symbol")):
        from repair_release_metadata import child_spans
        start, end, block = next(child_spans(original, "lib_symbols"))
        combined = parse(block)
        combined.extend(sheet.lib[1:])
        original = original[:start] + dump(combined, 1) + original[end:]
    additions = [node for node in sheet.tree if isinstance(node, list) and node[0] in {"symbol", "wire", "global_label", "text"}]
    closing = original.rfind(")")
    original = original[:closing] + "\n" + "\n".join(dump(node, 1) for node in additions) + original[closing:]
    path.write_text("\n".join(line.rstrip() for line in original.splitlines()) + "\n", encoding="utf-8")
    contract_path = work / "net-contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    contract["pins"].extend(sheet.contract)
    contract["ttl_local_bypass"] = {"parts": PARTS, "value_f": 1e-7, "mpn": FIELDS["MPN"], "hardware_verified": False}
    pipeline.write_json(contract_path, contract)


def candidates(board, capacitor, device, limit=35):
    fixed = [footprint for footprint in board.GetFootprints() if footprint.GetReference() != capacitor.GetReference()
             and not (footprint.GetReference() in PARTS and footprint.GetPosition().x > pcbnew.FromMM(170))]
    courts = [footprint.GetCourtyard(pcbnew.B_CrtYd) for footprint in fixed if footprint.GetCourtyard(pcbnew.B_CrtYd).OutlineCount()]
    holes = [pad.GetEffectiveShape(pcbnew.B_Cu) for footprint in fixed for pad in footprint.Pads() if pad.GetDrillSize().x]
    copper = [(pad.GetNetname(), pad.GetEffectiveShape(pcbnew.B_Cu)) for footprint in fixed for pad in footprint.Pads() if pad.IsOnLayer(pcbnew.B_Cu)]
    copper.extend((item.GetNetname(), item.GetEffectiveShape(pcbnew.B_Cu)) for item in board.GetTracks() if item.IsOnLayer(pcbnew.B_Cu))
    vias = [item.GetEffectiveShape(pcbnew.B_Cu) for item in board.GetTracks() if item.Type() == pcbnew.PCB_VIA_T and item.IsOnLayer(pcbnew.B_Cu)]
    power, ground = pad_position(board, device, "5"), pad_position(board, device, "3")
    results = []
    for angle in (0, 90, 180, -90):
        capacitor.SetOrientationDegrees(angle)
        for xpos_index in range(round((power[0] - 4) * 10), round((power[0] + 4) * 10) + 1):
            for ypos_index in range(round((power[1] - 4) * 10), min(1286, round((power[1] + 4) * 10)) + 1):
                center = (xpos_index / 10, ypos_index / 10)
                capacitor.SetPosition(vector(center))
                court = capacitor.GetCourtyard(pcbnew.B_CrtYd)
                if any(court.Collide(shape, 0) for shape in courts) or any(court.Collide(shape, 0) for shape in holes):
                    continue
                valid = True
                pads = {}
                for pad in capacitor.Pads():
                    shape = pad.GetEffectiveShape(pcbnew.B_Cu)
                    if any(net != pad.GetNetname() and shape.Collide(obstacle, pcbnew.FromMM(0.205)) for net, obstacle in copper):
                        valid = False
                        break
                    if any(shape.Collide(via, pcbnew.FromMM(0.08)) for via in vias):
                        valid = False
                        break
                    pads[pad.GetNumber()] = tuple(pcbnew.ToMM(value) for value in pad.GetPosition())
                if valid:
                    score = math.dist(pads["1"], power) + 0.4 * math.dist(pads["2"], ground)
                    results.append({"position": center, "angle": angle, "pads": pads, "score": score})
    ordered = sorted(results, key=lambda item: item["score"])
    return ordered[:limit] if limit is not None else ordered


def route(board, net, start, end):
    planner.EVIDENCE = EVIDENCE
    planner.LAYERS = ["B.Cu"]
    planner.STEP, planner.WIDTH = 0.025, 0.2
    planner.XMIN, planner.YMIN = min(start[0], end[0]) - 3, min(start[1], end[1]) - 3
    planner.XMAX, planner.YMAX = max(start[0], end[0]) + 3, min(129.5, max(start[1], end[1]) + 3)
    planner.COLS = round((planner.XMAX - planner.XMIN) / planner.STEP) + 1
    planner.ROWS = round((planner.YMAX - planner.YMIN) / planner.STEP) + 1
    planner.SIZE = planner.COLS * planner.ROWS
    plan = planner.solve(obstacles(board), net, start, end, [0], 0)
    shapes = [pad.GetEffectiveShape(pcbnew.B_Cu) for footprint in board.GetFootprints() for pad in footprint.Pads() if pad.IsOnLayer(pcbnew.B_Cu) and pad.GetNetname() != net]
    shapes.extend(item.GetEffectiveShape(pcbnew.B_Cu) for item in board.GetTracks() if item.IsOnLayer(pcbnew.B_Cu) and item.GetNetname() != net)
    probe = pcbnew.PCB_TRACK(board)
    probe.SetLayer(pcbnew.B_Cu)
    probe.SetWidth(pcbnew.FromMM(0.2))
    points = plan["points"]
    compact, cursor = [points[0][:2]], 0
    while cursor < len(points) - 1:
        chosen = cursor + 1
        for endpoint in range(len(points) - 1, cursor, -1):
            probe.SetStart(vector(points[cursor][:2]))
            probe.SetEnd(vector(points[endpoint][:2]))
            if not any(shape.Collide(probe.GetEffectiveShape(pcbnew.B_Cu), pcbnew.FromMM(0.205)) for shape in shapes):
                chosen = endpoint
                break
        compact.append(points[chosen][:2])
        cursor = chosen
    added = []
    for first_point, last_point in zip(compact, compact[1:]):
        track = pcbnew.PCB_TRACK(board)
        track.SetStart(vector(first_point))
        track.SetEnd(vector(last_point))
        track.SetLayer(pcbnew.B_Cu)
        track.SetWidth(pcbnew.FromMM(0.2))
        track.SetNetCode(board.FindNet(net).GetNetCode())
        board.Add(track)
        added.append(track.m_Uuid.AsString())
    return {"net": net, "points": compact, "added_tracks": added, "width_mm": 0.2, "layer": "B.Cu"}


def main():
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    candidate_path = EVIDENCE / "candidate.json"
    if candidate_path.exists():
        raise FileExistsError("Inspect existing TTL candidate before retry")
    source = pipeline.PRIMARY / (pipeline.STEM + ".kicad_pcb")
    if pipeline.digest(source) != BASELINE:
        raise RuntimeError("Primary baseline changed")
    work = pipeline.prepare(pipeline.PRIMARY)
    candidate = {"project": str(work), "baseline": BASELINE, "promoted": False}
    pipeline.write_json(candidate_path, candidate)
    append_schematic(work)
    path = work / source.name
    board = pcbnew.LoadBoard(str(path))
    library = pipeline.find_cli().parent.parent / "share/kicad/footprints/Capacitor_SMD.pretty"
    for index, reference in enumerate(PARTS):
        capacitor = pcbnew.FootprintLoad(str(library), "C_0402_1005Metric")
        board.Add(capacitor)
        capacitor.SetReference(reference)
        capacitor.SetValue("100nF")
        capacitor.SetFPID(pcbnew.LIB_ID("Capacitor_SMD", "C_0402_1005Metric"))
        capacitor.SetPosition(vector((180 + index * 3, 180)))
        capacitor.Flip(capacitor.GetPosition(), pcbnew.FLIP_DIRECTION_TOP_BOTTOM)
        capacitor.SetPath(pcbnew.KIID_PATH("/" + str(uid("root")) + "/" + str(uid("sheet:servo_ttl")) + "/" + str(uid("servo_ttl:" + reference))))
        capacitor.Reference().SetLayer(pcbnew.B_Fab)
        capacitor.Reference().SetTextSize(vector((0.8, 0.8)))
        capacitor.Reference().SetVisible(False)
        capacitor.Value().SetVisible(False)
        for pad in capacitor.Pads():
            pad.SetNet(board.FindNet("+3V3" if pad.GetNumber() == "1" else "POWER_GND"))
    pcbnew.SaveBoard(str(path), board)
    selected = []
    failures = []
    for reference, device in PARTS.items():
        board = pcbnew.LoadBoard(str(path))
        capacitor = board.FindFootprintByReference(reference)
        positions = candidates(board, capacitor, device)
        pipeline.write_json(EVIDENCE / (reference + "-positions.json"), positions)
        print(reference + " legal placement candidates: " + str(len(positions)), flush=True)
        for position in positions:
            board = pcbnew.LoadBoard(str(path))
            capacitor = board.FindFootprintByReference(reference)
            capacitor.SetPosition(vector(position["position"]))
            capacitor.SetOrientationDegrees(position["angle"])
            try:
                routes = [route(board, "+3V3", pad_position(board, reference, "1"), pad_position(board, device, "5")),
                          route(board, "POWER_GND", pad_position(board, reference, "2"), pad_position(board, device, "3"))]
            except RuntimeError as error:
                failures.append({"reference": reference, "position": position, "error": str(error)})
                pipeline.write_json(EVIDENCE / "placement-failures.json", failures)
                continue
            pcbnew.SaveBoard(str(path), board)
            selected.append({"reference": reference, "device": device, "placement": position, "routes": routes})
            break
        else:
            raise RuntimeError("No complete VCC/ground route found for " + reference)
    def metadata(node):
        if properties(node).get("Reference") not in PARTS:
            return False
        for key, value in FIELDS.items():
            set_property(node, key, value, board=True)
        return True
    path.write_text(replace_children(path.read_text(encoding="utf-8"), "footprint", metadata), encoding="utf-8")
    pipeline.write_json(EVIDENCE / "ttl-route-contract.json", {"parts": selected, "fields": FIELDS, "removed_original_objects": [], "new_vias": 0,
                        "failed_attempts": failures, "preserved": ["all original footprint andcopper geometry", "net assignments", "OE logic", "project settings", "rules"]})
    reports, summary = pipeline.check(work)
    candidate["summary"] = str(reports / "summary.json")
    pipeline.write_json(candidate_path, candidate)
    print(json.dumps({"placements": [{"reference": part["reference"], "placement": part["placement"]} for part in selected],
                      "drc": summary["drc"], "erc": summary["erc"], "status": summary["status"]}))


if __name__ == "__main__":
    main()
