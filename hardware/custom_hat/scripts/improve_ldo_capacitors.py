"""Build a complete LDO capacitor and local damping candidate, without promotion."""
import json
from pathlib import Path

import pcbnew

import pipeline
from add_i2c_pullups import vector
from generate_rev_a import Sheet, children, dump, first, parse, q, uid
from repair_release_metadata import child_spans, properties, replace_children, set_property


EVIDENCE = pipeline.BASE.parents[1] / "docs/references/扩展板电路仿真工具/ldo-capacitors-20261031"
BASELINE = "818becfdb21d35b6ceacbe00b6e7837465292d696b56cc7991d4e7494704831f"
CAP_FIELDS = {"Value": "2.2uF", "MPN": "C0805C225K5RACTU", "Manufacturer": "KEMET",
              "Datasheet": "https://search.kemet.com/component-documentation/download/specsheet/C0805C225K5RACTU",
              "Voltage Rating": "50V", "Dielectric": "X7R", "Tolerance": "10%",
              "Assembly Height": "1.25mm nominal; 1.45mm maximum",
              "BOM Comments": "Typical biased model reviewed; capacitance and ESR with C311 require joint loop validation; not a hardware pass"}
RES_FIELDS = {"Value": "0.047", "MPN": "WSLP0603R0470FEA", "Manufacturer": "Vishay",
              "Datasheet": "https://www.vishay.com/docs/30122/wslp.pdf", "Tolerance": "1%",
              "Power Rating": "0.4W at70C; derate above70C", "TCR": "110ppm/C",
              "BOM Comments": "47mOhm capacitor-branch damping only; not in load ground; Vishay30122 p1-2 pad1.02x1.02mm gap0.50mm"}
REMOVE = {"6305b861-749b-44c3-9827-b715077de931", "a61faace-07fa-4a54-8624-c8ba3df79dd8",
          "c92fa2ca-57d5-470d-a1a3-4ca61e63c221", "53f06b25-d441-491b-8a33-ecefc2680121"}
CAP_POSITION = (129.9, 124.9)
RES_POSITION = (129.9, 126.9)


def configure_schematic(work):
    path = work / "power.kicad_sch"
    original = path.read_text(encoding="utf-8")
    changed = []
    def capacitor(node):
        reference = properties(node).get("Reference")
        if reference not in {"C308", "C309"}:
            return False
        if properties(node).get("MPN") != "C0805C105K5RACTU":
            raise RuntimeError("LDO capacitor baseline changed")
        for key, value in CAP_FIELDS.items():
            set_property(node, key, value)
        changed.append(reference)
        return True
    original = replace_children(original, "symbol", capacitor)
    if set(changed) != {"C308", "C309"}:
        raise RuntimeError("Expected two LDO capacitors")
    labels = []
    def label(node):
        if str(first(node, "uuid")[1]) != "5ce0b473-3d22-5b6f-86fd-e6e80a9279dc":
            return False
        if node[1] != "POWER_GND":
            raise RuntimeError("C309 return label baseline changed")
        node[1] = q("LDO_CAP_RETURN")
        labels.append(node)
        return True
    original = replace_children(original, "global_label", label)
    if len(labels) != 1:
        raise RuntimeError("Expected one C309 return label")
    sheet = Sheet("power", "Local LDO capacitor damping")
    sheet.counter = 2000
    sheet.component("Device:R", "R703", "0.047", 285.75, 106.68,
                    {"1": "LDO_CAP_RETURN", "2": "POWER_GND"}, "duck:Vishay_WSLP0603_Damping")
    for symbol in children(sheet.tree, "symbol"):
        for key, value in RES_FIELDS.items():
            set_property(symbol, key, value)
    if not any(node[1] == "Device:R" for node in children(first(parse(original), "lib_symbols"), "symbol")):
        raise RuntimeError("Power sheet has no cached Device:R")
    additions = [node for node in sheet.tree if isinstance(node, list) and node[0] in {"symbol", "wire", "global_label"}]
    closing = original.rfind(")")
    original = original[:closing] + "\n" + "\n".join(dump(node, 1) for node in additions) + original[closing:]
    def note(node):
        if str(first(node, "uuid")[1]) != "4974c7a0-7dd8-59f1-885d-600f6f01526a":
            return False
        node[1] = q("U702 LP38691DT-1.8:3V3 to1V8. C308/C309:2.2uF/50V X7R. R703=47mOhm only in C309 return, never load ground. Include C311 in ESR/loop review.")
        return True
    original = replace_children(original, "text", note)
    path.write_text("\n".join(line.rstrip() for line in original.splitlines()) + "\n", encoding="utf-8")
    contract_path = work / "net-contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    matching = [pin for pin in contract["pins"] if pin["reference"] == "C309" and pin["pin"] == "2"]
    if len(matching) != 1 or matching[0]["net"] != "POWER_GND":
        raise RuntimeError("C309 pin contract changed")
    matching[0]["net"] = "LDO_CAP_RETURN"
    contract["pins"].extend(sheet.contract)
    contract["ldo_damping"] = {"reference": "R703", "ohms": 0.047, "capacitor_branch_only": True,
                               "output_branch": ["U702.1", "C309.1", "C309.2", "R703.1", "R703.2", "POWER_GND"],
                               "hardware_verified": False}
    pipeline.write_json(contract_path, contract)


def create_resistor_library(work):
    library = pipeline.find_cli().parent.parent / "share/kicad/footprints/Resistor_SMD.pretty/R_0603_1608Metric.kicad_mod"
    tree = parse(library.read_text(encoding="utf-8"))
    tree[1] = q("Vishay_WSLP0603_Damping")
    first(tree, "descr")[1] = q("Vishay WSLP0603; doc30122 p2 recommended pads1.02x1.02mm gap0.50mm; 47mOhm damping")
    tree[:] = [entry for entry in tree if not (isinstance(entry, list) and entry and entry[0] in {"fp_line", "fp_rect", "model"})]
    for pad in children(tree, "pad"):
        first(pad, "at")[1:3] = [-0.76 if pad[1] == "1" else 0.76, 0]
        first(pad, "size")[1:3] = [1.02, 1.02]
    for layer, xmin, ymin, xmax, ymax, width in (
        ("F.Fab", -0.762, -0.381, 0.762, 0.381, 0.1),
        ("F.CrtYd", -1.52, -0.76, 1.52, 0.76, 0.05),
    ):
        tree.append(["fp_rect", ["start", xmin, ymin], ["end", xmax, ymax],
                     ["stroke", ["width", width], ["type", "default"]], ["fill", "none"], ["layer", q(layer)]])
    path = work / "duck.pretty/Vishay_WSLP0603_Damping.kicad_mod"
    path.write_text(dump(tree) + "\n", encoding="utf-8")
    return path


def add_track(board, net, points, width):
    identifiers = []
    for start, end in zip(points, points[1:]):
        track = pcbnew.PCB_TRACK(board)
        track.SetStart(vector(start))
        track.SetEnd(vector(end))
        track.SetLayer(pcbnew.B_Cu)
        track.SetWidth(pcbnew.FromMM(width))
        track.SetNetCode(board.FindNet(net).GetNetCode())
        board.Add(track)
        identifiers.append(track.m_Uuid.AsString())
    return identifiers


def create_board(work):
    path = work / (pipeline.STEM + ".kicad_pcb")
    original = path.read_text(encoding="utf-8")
    removed = set()
    for start, end, block in reversed(list(child_spans(original, "segment"))):
        if str(first(parse(block), "uuid")[1]) in REMOVE:
            removed.add(str(first(parse(block), "uuid")[1]))
            original = original[:start] + original[end:]
    if removed != REMOVE:
        raise RuntimeError("LDO route baseline changed")
    path.write_text(original, encoding="utf-8")
    print("Loading complete LDO candidate", flush=True)
    board = pcbnew.LoadBoard(str(path))
    return_net = pcbnew.NETINFO_ITEM(board, "LDO_CAP_RETURN")
    board.Add(return_net)
    print("Configuring capacitor and resistor geometry", flush=True)
    capacitor = board.FindFootprintByReference("C309")
    capacitor.SetPosition(vector(CAP_POSITION))
    capacitor.SetOrientationDegrees(0)
    capacitor.Reference().SetLayer(pcbnew.B_Fab)
    capacitor.Reference().SetPosition(vector((129.9, 123.6)))
    for pad in capacitor.Pads():
        if pad.GetNumber() == "2":
            pad.SetNet(board.FindNet("LDO_CAP_RETURN"))
    print("Loading damping resistor footprint", flush=True)
    resistor = pcbnew.FootprintLoad(str(work / "duck.pretty"), "Vishay_WSLP0603_Damping")
    if resistor is None:
        raise RuntimeError("Damping footprint could not be loaded")
    board.Add(resistor)
    resistor.SetFPID(pcbnew.LIB_ID("duck", "Vishay_WSLP0603_Damping"))
    resistor.SetReference("R703")
    resistor.SetValue("0.047")
    resistor.SetPosition(vector(RES_POSITION))
    resistor.Flip(vector(RES_POSITION), pcbnew.FLIP_DIRECTION_TOP_BOTTOM)
    resistor.SetOrientationDegrees(0)
    resistor.SetPath(pcbnew.KIID_PATH("/" + str(uid("root")) + "/" + str(uid("sheet:power")) + "/" + str(uid("power:R703"))))
    resistor.Reference().SetLayer(pcbnew.B_Fab)
    resistor.Reference().SetTextSize(vector((0.8, 0.8)))
    resistor.Reference().SetPosition(vector((129.9, 128.2)))
    resistor.Value().SetVisible(False)
    for pad in resistor.Pads():
        pad.SetNet(board.FindNet("LDO_CAP_RETURN" if pad.GetNumber() == "1" else "POWER_GND"))
    def pad_position(reference, pin):
        pad = next(pad for pad in board.FindFootprintByReference(reference).Pads() if pad.GetNumber() == pin)
        return tuple(pcbnew.ToMM(value) for value in pad.GetPosition())
    routes = [
        {"net": "+1V8_CODEC", "width": 0.3, "points": [pad_position("U702", "1"), (126.17, 122.32), (128.75, 124.9), pad_position("C309", "1")]},
        {"net": "LDO_CAP_RETURN", "width": 0.3, "points": [pad_position("C309", "2"), (130.85, 125.5), (129.14, 125.5), pad_position("R703", "1")]},
        {"net": "POWER_GND", "width": 0.3, "points": [pad_position("R703", "2"), (131.7, 126.9), (131.7, 123.8282), (131.252198, 123.8282)]},
        {"net": "AUDIO_AMP_EN", "width": 0.25, "points": [(123.3713, 121.1586), (127.3, 125.0873), (127.3, 127.955), (130.1677, 127.955)]},
    ]
    print("Adding four local branches", flush=True)
    for route in routes:
        route["added_tracks"] = add_track(board, route["net"], route["points"], route["width"])
    print("Saving routed LDO candidate", flush=True)
    pcbnew.SaveBoard(str(path), board)
    def metadata(node):
        reference = properties(node).get("Reference")
        fields = CAP_FIELDS if reference in {"C308", "C309"} else RES_FIELDS if reference == "R703" else None
        if fields is None:
            return False
        for key, value in fields.items():
            set_property(node, key, value, board=True)
        return True
    path.write_text(replace_children(path.read_text(encoding="utf-8"), "footprint", metadata), encoding="utf-8")
    pipeline.write_json(EVIDENCE / "change-contract.json", {"base": BASELINE, "removed_tracks": sorted(REMOVE),
                        "capacitor_position": CAP_POSITION, "resistor_position": RES_POSITION,
                        "cap_fields": CAP_FIELDS, "res_fields": RES_FIELDS, "routes": routes,
                        "original_net_change": {"C309.2": ["POWER_GND", "LDO_CAP_RETURN"]},
                        "added_pins": {"R703.1": "LDO_CAP_RETURN", "R703.2": "POWER_GND"}})


def main():
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    if (EVIDENCE / "candidate.json").exists():
        raise FileExistsError("Existing candidate must be reviewed before retry")
    if pipeline.digest(pipeline.PRIMARY / (pipeline.STEM + ".kicad_pcb")) != BASELINE:
        raise RuntimeError("Primary baseline changed")
    work = pipeline.prepare(pipeline.PRIMARY)
    candidate = {"project": str(work), "baseline": BASELINE, "promoted": False}
    pipeline.write_json(EVIDENCE / "candidate.json", candidate)
    configure_schematic(work)
    create_resistor_library(work)
    create_board(work)
    reports, summary = pipeline.check(work)
    candidate["summary"] = str(reports / "summary.json")
    pipeline.write_json(EVIDENCE / "candidate.json", candidate)
    print(json.dumps({"work": str(work), "drc": summary["drc"], "erc": summary["erc"], "status": summary["status"]}))


if __name__ == "__main__":
    main()
