"""Add evidenced I2C5 pull-ups in a complete workspace, without promoting it."""
import argparse
import json
import math
from pathlib import Path
import shutil
import uuid

import pcbnew

import pipeline
import plan_i2s_sdo as planner
from generate_rev_a import Sheet, children, dump, first, parse, uid
from repair_release_metadata import child_spans, properties, replace_children, set_property
from repair_u501 import geometry


EVIDENCE = pipeline.BASE.parents[1] / "docs/references/扩展板电路仿真工具/i2c-pullups-20261031"
BASELINE = "d4fc46fa5fe08beb8e48d91caef4b23493d8d54641a8e31108c0f968642f61e2"
FOOTPRINT = "Resistor_SMD:R_0402_1005Metric"
ATTRIBUTES = {
    "MPN": "CRCW04024K70FKED",
    "Manufacturer": "Vishay",
    "Datasheet": "https://www.vishay.com/docs/20035/dcrcwe3.pdf",
    "BOM Comments": "4.7kOhm 1% 100ppm/K; design selected; verify parallel external pull-ups",
}
PARTS = [("R501", "I2C5_SCL", 145.5, 110.0, "29"), ("R502", "I2C5_SDA", 147.5, 110.0, "31")]


def vector(position):
    return pcbnew.VECTOR2I(*(pcbnew.FromMM(value) for value in position))


def position(item):
    return tuple(pcbnew.ToMM(value) for value in item.GetPosition())


def append_schematic(project):
    path = project / "imu_tof.kicad_sch"
    original = path.read_text(encoding="utf-8")
    tree = parse(original)
    references = {properties(node).get("Reference") for node in children(tree, "symbol")}
    if references & {part[0] for part in PARTS}:
        raise ValueError("Pull-up references already exist")
    sheet = Sheet("imu_tof", "I2C5 pull-up addition")
    sheet.counter = 1000
    for index, (reference, signal, _, _, _) in enumerate(PARTS):
        sheet.component("Device:R", reference, "4.7k", 241.3 + 30.48 * index, 96.52,
                        {"1": "+3V3", "2": signal}, FOOTPRINT)
    for node in children(sheet.tree, "symbol"):
        for key, value in ATTRIBUTES.items():
            set_property(node, key, value)
    sheet.text("R501/R502: 4.7k to 3V3. Start at 100kHz; total bus C <= 240pF. External parallel pull-ups require recalculation.", 35, 156.21)
    start, end, block = next(child_spans(original, "lib_symbols"))
    library = parse(block)
    if any(node[1] == "Device:R" for node in children(library, "symbol")):
        raise ValueError("Unexpected existing resistor library entry")
    library.extend(sheet.lib[1:])
    original = original[:start] + dump(library, 1) + original[end:]
    additions = [node for node in sheet.tree if isinstance(node, list) and node[0] in {"symbol", "wire", "global_label", "text"}]
    closing = original.rfind(")")
    original = original[:closing] + "\n" + "\n".join(dump(node, 1) for node in additions) + original[closing:]
    path.write_text(original, encoding="utf-8")
    contract_path = project / "net-contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    contract["pins"].extend(sheet.contract)
    contract["i2c5_pullups"] = {"date": "2026-10-31", "references": [part[0] for part in PARTS], "ohms": 4700, "initial_clock_hz": 100000, "bus_capacitance_limit_pf": 240}
    pipeline.write_json(contract_path, contract)


def configure_planner():
    planner.EVIDENCE = EVIDENCE
    planner.LAYERS = ["F.Cu"]
    planner.STEP = 0.025
    planner.WIDTH = 0.15
    planner.XMIN, planner.YMIN, planner.XMAX, planner.YMAX = 140.0, 103.0, 151.0, 112.0
    planner.COLS = round((planner.XMAX - planner.XMIN) / planner.STEP) + 1
    planner.ROWS = round((planner.YMAX - planner.YMIN) / planner.STEP) + 1
    planner.SIZE = planner.COLS * planner.ROWS


def obstacles(board):
    items = geometry(board)
    for item in items:
        if item["kind"] == "pad" and set(item["layers"]) == {"F.Cu", "B.Cu"}:
            item["layers"] = ["F.Cu", "B.Cu", "In1.Cu", "In2.Cu"]
    return items


def add_route(board, net, points):
    for start, end in zip(points, points[1:]):
        if start[:2] == end[:2]:
            continue
        if start[2] != 0 or end[2] != 0:
            raise ValueError("Unexpected layer transition")
        track = pcbnew.PCB_TRACK(board)
        track.SetStart(vector(start[:2]))
        track.SetEnd(vector(end[:2]))
        track.SetWidth(pcbnew.FromMM(planner.WIDTH))
        track.SetLayer(pcbnew.F_Cu)
        track.SetNetCode(board.FindNet(net).GetNetCode())
        board.Add(track)


def build_board(project):
    board_path = project / (pipeline.STEM + ".kicad_pcb")
    source_path = pipeline.PRIMARY / (pipeline.STEM + ".kicad_pcb")
    if pipeline.digest(source_path) != BASELINE:
        raise ValueError("Source changed before layout retry")
    shutil.copy2(board_path, project.parent / ("before-layout-" + uuid.uuid4().hex[:8] + ".kicad_pcb"))
    board = pcbnew.LoadBoard(str(source_path))
    library = pipeline.find_cli().parent.parent / "share/kicad/footprints/Resistor_SMD.pretty"
    for reference, signal, xpos, ypos, _ in PARTS:
        footprint = pcbnew.FootprintLoad(str(library), "R_0402_1005Metric")
        if footprint is None:
            raise FileNotFoundError(library)
        footprint.SetFPID(pcbnew.LIB_ID("Resistor_SMD", "R_0402_1005Metric"))
        footprint.SetReference(reference)
        footprint.SetValue("4.7k")
        footprint.SetPosition(vector((xpos, ypos)))
        footprint.SetOrientationDegrees(90)
        footprint.SetPath(pcbnew.KIID_PATH("/" + str(uid("root")) + "/" + str(uid("sheet:imu_tof")) + "/" + str(uid("imu_tof:" + reference))))
        footprint.Reference().SetTextSize(vector((0.8, 0.8)))
        footprint.Reference().SetTextThickness(pcbnew.FromMM(0.1))
        footprint.Reference().SetTextAngle(pcbnew.EDA_ANGLE(0, pcbnew.DEGREES_T))
        label_x = xpos - 0.7 if reference == "R501" else xpos + 0.7
        footprint.Reference().SetPosition(vector((label_x, ypos + 1.55)))
        if reference == "R501":
            footprint.Reference().SetTextAngle(pcbnew.EDA_ANGLE(90, pcbnew.DEGREES_T))
            footprint.Reference().SetPosition(vector((145.9, 112.4)))
        footprint.Value().SetVisible(False)
        board.Add(footprint)
        for pad in footprint.Pads():
            pad.SetNet(board.FindNet("+3V3" if pad.GetNumber() == "1" else signal))
    configure_planner()
    pcbnew.SaveBoard(str(project.parent / "placement-trial.kicad_pcb"), board)
    pipeline.write_json(project.parent / "placement-geometry.json", obstacles(board))
    plans = []
    for reference, signal, _, _, header_pin in PARTS:
        footprint = board.FindFootprintByReference(reference)
        signal_pad = next(pad for pad in footprint.Pads() if pad.GetNumber() == "2")
        header_pad = next(pad for pad in board.FindFootprintByReference("J101").Pads() if pad.GetNumber() == header_pin)
        print(f"Routing {reference}: {position(signal_pad)} to {position(header_pad)}", flush=True)
        plan = planner.solve(obstacles(board), signal, position(signal_pad), position(header_pad), [0], 0)
        add_route(board, signal, plan["points"])
        plans.append(plan)
    for reference, _, _, _, _ in PARTS:
        footprint = board.FindFootprintByReference(reference)
        power_pad = next(pad for pad in footprint.Pads() if pad.GetNumber() == "1")
        start = position(power_pad)
        items = obstacles(board)
        via_grid = planner.occupancy(items, 0.3, ["F.Cu", "B.Cu", "In1.Cu", "In2.Cu"], "+3V3", True)
        targets = [planner.coordinates(index) for index in range(planner.SIZE) if not via_grid[index]]
        targets.sort(key=lambda point: math.dist(start, point[:2]))
        for target in targets[:250]:
            try:
                plan = planner.solve(items, "+3V3", start, target[:2], [0], 0)
            except RuntimeError:
                continue
            add_route(board, "+3V3", plan["points"])
            via = pcbnew.PCB_VIA(board)
            via.SetPosition(vector(target[:2]))
            via.SetWidth(pcbnew.FromMM(0.6))
            via.SetDrill(pcbnew.FromMM(0.3))
            via.SetViaType(pcbnew.VIATYPE_THROUGH)
            via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
            via.SetNetCode(board.FindNet("+3V3").GetNetCode())
            board.Add(via)
            plan["new_via"] = {"position": target[:2], "diameter": 0.6, "drill": 0.3}
            plans.append(plan)
            break
        else:
            raise RuntimeError("No standard through-via path for " + reference)
    pcbnew.SaveBoard(str(board_path), board)
    text = board_path.read_text(encoding="utf-8")
    def metadata(node):
        if properties(node).get("Reference") not in {part[0] for part in PARTS}:
            return False
        for key, value in ATTRIBUTES.items():
            set_property(node, key, value, board=True)
        return True
    board_path.write_text(replace_children(text, "footprint", metadata), encoding="utf-8")
    return plans


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path)
    arguments = parser.parse_args()
    if arguments.project:
        project = pipeline.managed(arguments.project)
    else:
        if (EVIDENCE / "candidate.json").exists():
            raise FileExistsError("Inspect the existing candidate before another attempt")
        if pipeline.digest(pipeline.PRIMARY / (pipeline.STEM + ".kicad_pcb")) != BASELINE:
            raise ValueError("Source changed since review")
        project = pipeline.prepare(pipeline.PRIMARY)
        pipeline.write_json(EVIDENCE / "candidate.json", {"project": str(project), "source_pcb_sha256": BASELINE, "promoted": False})
        append_schematic(project)
    plans = build_board(project)
    pipeline.write_json(project.parent / "i2c-route-plan.json", plans)
    reports, result = pipeline.check(project)
    pipeline.write_json(EVIDENCE / "candidate.json", {"project": str(project), "source_pcb_sha256": BASELINE, "summary": str(reports / "summary.json"), "promoted": False})
    print(json.dumps({"project": str(project), "reports": str(reports), "drc": result["drc"], "erc": result["erc"], "status": result["status"]}))


if __name__ == "__main__":
    main()
