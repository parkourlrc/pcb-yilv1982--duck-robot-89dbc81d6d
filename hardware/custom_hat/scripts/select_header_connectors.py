"""Select Samtec headers and correct J101 body registration in a full copy."""
import json
from pathlib import Path
import uuid

import pcbnew
import pipeline
from generate_rev_a import children, first, parse, q
from repair_release_metadata import properties, replace_children, set_property


EVIDENCE = pipeline.BASE.parents[1] / "docs/references/hat-simulation-tools-20261029/connectors-20261031"
BASELINE = "a101bc83040836d1f130179b636896ece6fca460334afa4b39c861c329c97c93"
PARTS = {
    "J101": {"mpn": "SSW-120-01-G-D", "footprint": "duck:Radxa40P_Samtec_SSW120", "drill": 1.04, "height": "8.51mm body; 2.64mm solder tail",
             "datasheet": "https://suddendocs.samtec.com/catalog_english/ssw_th.pdf"},
    "J301": {"mpn": "TSW-108-07-G-S", "footprint": "duck:Samtec_TSW108_07", "drill": 1.02, "height": "2.54mm body; 5.84mm post; 2.54mm solder tail",
             "datasheet": "https://suddendocs.samtec.com/catalog_english/tsw_th.pdf"},
    "J403": {"mpn": "TSW-103-07-G-S", "footprint": "duck:Samtec_TSW103_07", "drill": 1.02, "height": "2.54mm body; 5.84mm post; 2.54mm solder tail",
             "datasheet": "https://suddendocs.samtec.com/catalog_english/tsw_th.pdf"},
    "J802": {"mpn": "TSW-102-07-G-S", "footprint": "duck:Samtec_TSW102_07", "drill": 1.02, "height": "2.54mm body; 5.84mm post; 2.54mm solder tail",
             "datasheet": "https://suddendocs.samtec.com/catalog_english/tsw_th.pdf"},
}


def line(start, end, layer, width):
    return ["fp_line", ["start", *start], ["end", *end], ["stroke", ["width", width], ["type", "solid"]],
            ["layer", q(layer)], ["uuid", q(uuid.uuid4())]]


def rectangle(bounds, layer, width):
    left, top, right, bottom = bounds
    points = [(left, top), (right, top), (right, bottom), (left, bottom), (left, top)]
    return [line(start, end, layer, width) for start, end in zip(points, points[1:])]


def correct_socket(node):
    drawings = {"fp_line", "fp_rect", "fp_poly", "fp_arc", "fp_circle"}
    node[:] = [entry for entry in node if not (isinstance(entry, list) and entry and entry[0] in drawings)]
    node.extend(rectangle((-1.205, -1.525, 3.745, 49.785), "F.Fab", 0.1))
    node.extend(rectangle((-1.335, -1.655, 3.875, 49.915), "F.SilkS", 0.12))
    node.extend(rectangle((-1.705, -2.025, 4.245, 50.285), "F.CrtYd", 0.05))
    node.extend([line((-1.6, -1.9), (-0.8, -1.9), "F.SilkS", 0.12), line((-1.6, -1.9), (-1.6, -1.1), "F.SilkS", 0.12)])
    for model in children(node, "model"):
        first(first(model, "offset"), "xyz")[1:] = [2.54, 0, 0]
    description = first(node, "descr")
    description[1] = q("Samtec SSW-120-01-G-D envelope; 2x20 2.54mm; logical numbering per Radxa interface; generic 3D model shifted +2.54mm, visual only")


def main():
    if (EVIDENCE / "candidate.json").exists():
        raise FileExistsError("Review existing candidate before rerunning")
    if pipeline.digest(pipeline.PRIMARY / (pipeline.STEM + ".kicad_pcb")) != BASELINE:
        raise RuntimeError("Primary baseline changed")
    work = pipeline.prepare(pipeline.PRIMARY)
    pipeline.write_json(EVIDENCE / "candidate.json", {"project": str(work), "baseline": BASELINE, "promoted": False})
    seen = {"schematic": set(), "pcb": set()}
    def update(node, board=False):
        fields = properties(node)
        reference = fields.get("Reference")
        if reference not in PARTS:
            return False
        part = PARTS[reference]
        if fields.get("MPN"):
            raise RuntimeError("Previously selected connector " + reference)
        if board:
            node[1] = q(part["footprint"])
            for pad in children(node, "pad"):
                first(pad, "drill")[1] = part["drill"]
            if reference == "J101":
                correct_socket(node)
        else:
            set_property(node, "Footprint", part["footprint"])
        for key, value in {
            "MPN": part["mpn"], "Manufacturer": "Samtec", "Datasheet": part["datasheet"],
            "Assembly Height": part["height"],
            "BOM Comments": "Design selection from manufacturer catalog/drawing; final mating/header current and installed height remain to be validated",
        }.items():
            set_property(node, key, value, board=board)
        seen["pcb" if board else "schematic"].add(reference)
        return True
    for path in sorted(work.glob("*.kicad_sch")):
        original = path.read_text(encoding="utf-8")
        updated = replace_children(original, "symbol", update)
        if updated != original:
            path.write_text("\n".join(row.rstrip() for row in updated.splitlines()) + "\n", encoding="utf-8")
    board_path = work / (pipeline.STEM + ".kicad_pcb")
    board_path.write_text(replace_children(board_path.read_text(encoding="utf-8"), "footprint", lambda node: update(node, True)), encoding="utf-8")
    if any(references != set(PARTS) for references in seen.values()):
        raise RuntimeError("Connector reference mismatch")
    board = pcbnew.LoadBoard(str(board_path))
    for reference, part in PARTS.items():
        footprint = board.FindFootprintByReference(reference)
        footprint.SetPosition(pcbnew.VECTOR2I(0, 0))
        footprint.SetOrientationDegrees(0)
        pcbnew.FootprintSave(str(work / "duck.pretty"), footprint)
        expected = work / "duck.pretty" / (part["footprint"].split(":")[1] + ".kicad_mod")
        if not expected.is_file():
            raise RuntimeError("Local footprint not saved")
    pipeline.write_json(EVIDENCE / "selected-parts.json", PARTS)
    reports, result = pipeline.check(work)
    pipeline.write_json(EVIDENCE / "candidate.json", {"project": str(work), "baseline": BASELINE, "summary": str(reports / "summary.json"), "promoted": False})
    print(json.dumps({"project": str(work), "drc": result["drc"], "erc": result["erc"], "status": result["status"]}))


if __name__ == "__main__":
    main()
