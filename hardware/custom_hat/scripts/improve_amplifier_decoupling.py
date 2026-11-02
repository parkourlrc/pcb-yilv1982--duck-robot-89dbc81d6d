"""Place evidenced local bypass/bulk capacitors at PAM8302A in a complete candidate."""
import copy
import json
import uuid

import pcbnew

import pipeline
import plan_i2s_sdo as planner
from add_i2c_pullups import obstacles, vector
from fit_ldo_candidate import remove_objects
from generate_rev_a import Sheet, children, dump, first, parse, q, uid
from repair_release_metadata import properties, replace_children, set_property


EVIDENCE = pipeline.BASE.parents[1] / "docs/references/hat-simulation-tools-20261029/amp-decoupling-20261031"
BASELINE = "0fd6c68918039867ef0d55a028844bbba7efaec68fe107d4a4b0a021ce7169c0"
BULK_POSITION = (148.1, 125.8)
BYPASS_POSITION = (150.8, 126.05)
POWER_VIA = "d90d9315-7dfc-4e87-9112-0b48f92747f3"
POWER_POSITION = (151.95, 125.415)
GROUND_POSITION = (151.95, 126.685)
REMOVE = {"762fa157-7624-4e11-9a6b-7be0a81ccee7", "7d9c6593-cf0e-49a9-a3ea-3500ddc47735",
          "0517fd7c-a4c8-421d-adc0-bfd7f112be4e", "3c897dbe-7abb-47fc-b409-276420d29475",
          "4294b220-cebb-4265-b857-b8b2e64e21e3", "d9547f97-7070-4105-a338-3266e01084b4",
          "88ef0d8e-c128-44b1-ad9d-8bd89b203de9"}
BULK_FIELDS = {"Value": "22uF", "Footprint": "Capacitor_SMD:C_1210_3225Metric", "MPN": "C1210C226K3RACTU",
               "Manufacturer": "KEMET", "Voltage Rating": "25V", "Dielectric": "X7R", "Tolerance": "10%",
               "Datasheet": "https://search.kemet.com/component-documentation/download/specsheet/C1210C226K3RACTU",
               "Assembly Height": "2.5mm nominal; 2.8mm maximum",
               "BOM Comments": "PAM8302A local bulk capacitor; archived typical bias model,not a guaranteed minimum or hardware pass"}
BYPASS_FIELDS = {"Value": "2.2uF", "Footprint": "Capacitor_SMD:C_0805_2012Metric", "MPN": "C0805C225K5RACTU",
                 "Manufacturer": "KEMET", "Voltage Rating": "50V", "Dielectric": "X7R", "Tolerance": "10%",
                 "Datasheet": "https://search.kemet.com/component-documentation/download/specsheet/C0805C225K5RACTU",
                 "Assembly Height": "1.25mm nominal; 1.45mm maximum",
                 "BOM Comments": "PAM8302A local ceramic bypass;2.2uF nominal selected for bias margin;device recommends typical1uF close toVDD"}


def schematic(work):
    path = work / "audio.kicad_sch"
    text = path.read_text(encoding="utf-8")
    references = {properties(node).get("Reference") for node in children(parse(text), "symbol")}
    if "C328" in references:
        raise RuntimeError("C328 already exists")
    changed = []
    def bulk(node):
        if properties(node).get("Reference") != "C323":
            return False
        if properties(node).get("MPN") != "C0805C106K3PACTU":
            raise RuntimeError("Bulk capacitor baseline changed")
        for key, value in BULK_FIELDS.items():
            set_property(node, key, value)
        changed.append("C323")
        return True
    text = replace_children(text, "symbol", bulk)
    if changed != ["C323"]:
        raise RuntimeError("Expected one C323 symbol")
    sheet = Sheet("audio", "Amplifier local bypass addition")
    sheet.counter = 3000
    sheet.component("Device:C", "C328", "2.2uF", 355.6, 175.26,
                    {"1": "+5V", "2": "POWER_GND"}, BYPASS_FIELDS["Footprint"])
    for symbol in children(sheet.tree, "symbol"):
        for key, value in BYPASS_FIELDS.items():
            set_property(symbol, key, value)
    if not any(node[1] == "Device:C" for node in children(first(parse(text), "lib_symbols"), "symbol")):
        raise RuntimeError("Audio sheet lacks cached capacitor symbol")
    sheet.text("C323=22uF bulk and C328=2.2uF ceramic bypass are local to U803 VDD/GND; nominal values are not guaranteed effective capacitance.", 35.56, 191.77)
    additions = [node for node in sheet.tree if isinstance(node, list) and node[0] in {"symbol", "wire", "global_label", "text"}]
    closing = text.rfind(")")
    text = text[:closing] + "\n" + "\n".join(dump(node, 1) for node in additions) + text[closing:]
    path.write_text("\n".join(line.rstrip() for line in text.splitlines()) + "\n", encoding="utf-8")
    contract_path = work / "net-contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    contract["pins"].extend(sheet.contract)
    contract["amp_local_decoupling"] = {"bulk": "C323", "bypass": "C328", "device": "U803", "hardware_verified": False}
    pipeline.write_json(contract_path, contract)


def replace_bulk_geometry(path):
    template_path = pipeline.find_cli().parent.parent / "share/kicad/footprints/Capacitor_SMD.pretty/C_1210_3225Metric.kicad_mod"
    template = parse(template_path.read_text(encoding="utf-8"))
    def replace(node):
        if properties(node).get("Reference") != "C323":
            return False
        node[1] = q(BULK_FIELDS["Footprint"])
        for key, value in BULK_FIELDS.items():
            if key != "Footprint":
                set_property(node, key, value, board=True)
        for key in ("descr", "tags"):
            old, replacement = first(node, key), copy.deepcopy(first(template, key))
            if old:
                node[node.index(old)] = replacement
            elif replacement:
                node.append(replacement)
        geometry_keys = {"fp_line", "fp_rect", "fp_circle", "fp_arc", "fp_poly", "fp_text", "model"}
        node[:] = [entry for entry in node if not (isinstance(entry, list) and entry and entry[0] in geometry_keys)]
        for entry in template:
            if isinstance(entry, list) and entry and entry[0] in geometry_keys:
                addition = copy.deepcopy(entry)
                if entry[0] != "model":
                    addition.append(["uuid", q(uuid.uuid4())])
                node.append(addition)
        for pad in children(node, "pad"):
            expected = next(item for item in children(template, "pad") if item[1] == pad[1])
            pad[3] = expected[3]
            for key in ("at", "size", "roundrect_rratio"):
                old, replacement = first(pad, key), copy.deepcopy(first(expected, key))
                if old:
                    pad[pad.index(old)] = replacement
                elif replacement:
                    pad.append(replacement)
        return True
    path.write_text(replace_children(path.read_text(encoding="utf-8"), "footprint", replace), encoding="utf-8")
    return {"path": str(template_path), "sha256": pipeline.digest(template_path)}


def add_tracks(board, net, layer, points, width):
    result = []
    for start, end in zip(points, points[1:]):
        if start[:2] == end[:2]:
            continue
        track = pcbnew.PCB_TRACK(board)
        track.SetStart(vector(start[:2]))
        track.SetEnd(vector(end[:2]))
        track.SetLayer(layer)
        track.SetWidth(pcbnew.FromMM(width))
        track.SetNetCode(board.FindNet(net).GetNetCode())
        board.Add(track)
        result.append(track.m_Uuid.AsString())
    return result


def main():
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    candidate_path = EVIDENCE / "candidate.json"
    if candidate_path.exists():
        raise FileExistsError("Review existing amplifier candidate before retry")
    source = pipeline.PRIMARY / (pipeline.STEM + ".kicad_pcb")
    if pipeline.digest(source) != BASELINE:
        raise RuntimeError("Primary baseline changed")
    work = pipeline.prepare(pipeline.PRIMARY)
    candidate = {"project": str(work), "baseline": BASELINE, "promoted": False}
    pipeline.write_json(candidate_path, candidate)
    schematic(work)
    path = work / source.name
    remove_objects(path, REMOVE)
    board = pcbnew.LoadBoard(str(path))
    bulk = board.FindFootprintByReference("C323")
    bulk.Flip(bulk.GetPosition(), pcbnew.FLIP_DIRECTION_TOP_BOTTOM)
    bulk.SetPosition(vector(BULK_POSITION))
    bulk.SetOrientationDegrees(0)
    bulk.Reference().SetLayer(pcbnew.F_Fab)
    pcbnew.SaveBoard(str(path), board)
    template = replace_bulk_geometry(path)
    board = pcbnew.LoadBoard(str(path))
    bulk = board.FindFootprintByReference("C323")
    bulk.SetOrientationDegrees(-90)
    bulk.Reference().SetPosition(vector((146.1, 125.8)))
    library = pipeline.find_cli().parent.parent / "share/kicad/footprints/Capacitor_SMD.pretty"
    bypass = pcbnew.FootprintLoad(str(library), "C_0805_2012Metric")
    board.Add(bypass)
    bypass.SetFPID(pcbnew.LIB_ID("Capacitor_SMD", "C_0805_2012Metric"))
    bypass.SetReference("C328")
    bypass.SetValue("2.2uF")
    bypass.SetPosition(vector(BYPASS_POSITION))
    bypass.SetOrientationDegrees(-90)
    bypass.SetPath(pcbnew.KIID_PATH("/" + str(uid("root")) + "/" + str(uid("sheet:audio")) + "/" + str(uid("audio:C328"))))
    bypass.Reference().SetLayer(pcbnew.F_Fab)
    bypass.Reference().SetTextSize(vector((0.8, 0.8)))
    bypass.Reference().SetPosition(vector((152.7, 127.4)))
    bypass.Value().SetVisible(False)
    for pad in bypass.Pads():
        pad.SetNet(board.FindNet("+5V" if pad.GetNumber() == "1" else "POWER_GND"))
    power_via = next(item for item in board.GetTracks() if item.m_Uuid.AsString() == POWER_VIA)
    power_via.SetPosition(vector(POWER_POSITION))
    ground_via = pcbnew.PCB_VIA(board)
    ground_via.SetPosition(vector(GROUND_POSITION))
    ground_via.SetWidth(pcbnew.FromMM(0.6))
    ground_via.SetDrill(pcbnew.FromMM(0.3))
    ground_via.SetViaType(pcbnew.VIATYPE_THROUGH)
    ground_via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    ground_via.SetNetCode(board.FindNet("POWER_GND").GetNetCode())
    board.Add(ground_via)
    def pad_position(reference, number):
        pad = next(pad for pad in board.FindFootprintByReference(reference).Pads() if pad.GetNumber() == number)
        return tuple(pcbnew.ToMM(value) for value in pad.GetPosition())
    routes = [
        {"net": "+5V", "layer": "B.Cu", "points": [pad_position("U803", "6"), POWER_POSITION], "width": 0.6},
        {"net": "POWER_GND", "layer": "B.Cu", "points": [pad_position("U803", "7"), GROUND_POSITION], "width": 0.6},
        {"net": "+5V", "layer": "F.Cu", "points": [POWER_POSITION, pad_position("C328", "1"), pad_position("C323", "1")], "width": 0.6},
        {"net": "POWER_GND", "layer": "F.Cu", "points": [GROUND_POSITION, pad_position("C328", "2"), pad_position("C323", "2")], "width": 0.6},
    ]
    for route in routes:
        layer = pcbnew.B_Cu if route["layer"] == "B.Cu" else pcbnew.F_Cu
        route["added_tracks"] = add_tracks(board, route["net"], layer, route["points"], route["width"])
    planner.EVIDENCE = EVIDENCE
    planner.LAYERS = ["In2.Cu"]
    planner.STEP, planner.WIDTH = 0.025, 0.6
    planner.XMIN, planner.YMIN, planner.XMAX, planner.YMAX = 149, 123, 155, 129.1
    planner.COLS = round((planner.XMAX - planner.XMIN) / planner.STEP) + 1
    planner.ROWS = round((planner.YMAX - planner.YMIN) / planner.STEP) + 1
    planner.SIZE = planner.COLS * planner.ROWS
    plan = planner.solve(obstacles(board), "+5V", (151.0016, 127.3402), POWER_POSITION, [0], 0)
    route = {"net": "+5V", "layer": "In2.Cu", "points": [point[:2] for point in plan["points"]], "width": 0.6}
    route["added_tracks"] = add_tracks(board, route["net"], pcbnew.In2_Cu, route["points"], route["width"])
    routes.append(route)
    pcbnew.SaveBoard(str(path), board)
    def metadata(node):
        if properties(node).get("Reference") != "C328":
            return False
        for key, value in BYPASS_FIELDS.items():
            if key != "Footprint":
                set_property(node, key, value, board=True)
        return True
    path.write_text(replace_children(path.read_text(encoding="utf-8"), "footprint", metadata), encoding="utf-8")
    pipeline.write_json(EVIDENCE / "amp-route-contract.json", {"baseline": BASELINE, "removed_objects": sorted(REMOVE),
                        "bulk_position": BULK_POSITION, "bypass_position": BYPASS_POSITION, "cap_angle": -90,
                        "bulk_fields": BULK_FIELDS, "bypass_fields": BYPASS_FIELDS, "bulk_library_template": template,
                        "moved_power_via": POWER_VIA, "power_via_before": [152.2586, 128.5972], "power_via_after": POWER_POSITION,
                        "new_ground_via": ground_via.m_Uuid.AsString(), "ground_position": GROUND_POSITION, "routes": routes})
    reports, summary = pipeline.check(work)
    candidate["summary"] = str(reports / "summary.json")
    pipeline.write_json(candidate_path, candidate)
    print(json.dumps({"drc": summary["drc"], "erc": summary["erc"], "status": summary["status"]}))


if __name__ == "__main__":
    main()
