"""Finish fiducial placement and project-local footprint associations."""
import argparse
from pathlib import Path

import pipeline
from generate_rev_a import children, first, parse, q
from repair_release_metadata import properties, replace_children, set_property


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, type=Path)
    arguments = parser.parse_args()
    project = pipeline.managed(arguments.project)
    header_id = "duck:Radxa40P_ReversedRows_2x20"
    schematic_path = project / "radxa_40p.kicad_sch"
    text = schematic_path.read_text(encoding="utf-8")

    def header_symbol(node):
        if properties(node).get("Reference") == "J101":
            set_property(node, "Footprint", header_id)
            return True
        return False

    schematic_path.write_text(replace_children(text, "symbol", header_symbol), encoding="utf-8")
    pcb_path = project / (pipeline.STEM + ".kicad_pcb")
    text = pcb_path.read_text(encoding="utf-8")
    fiducial_positions = [(101.5, 110), (163.5, 116), (139, 128.5)]

    def update(node):
        reference = properties(node)["Reference"]
        if reference == "J101":
            node[1] = q(header_id)
        if reference == "C307":
            attributes = first(node, "attr")
            if "dnp" not in attributes:
                attributes.append("dnp")
        if reference.startswith("FID"):
            node[1] = q("duck:Fiducial_1mm_Mask2mm")
            first(node, "at")[1:3] = list(fiducial_positions[(int(reference[3:]) - 1) % 3])
            if reference == "FID6":
                first(node, "at")[1:3] = [101.5, 122]
        for pad in children(node, "pad"):
            net = first(pad, "net")
            if net and str(net[1]).startswith("unconnected-"):
                net[1] = q(str(net[1]).replace("/", "{slash}"))
        return True

    pcb_path.write_text(replace_children(text, "footprint", update), encoding="utf-8")
    import pcbnew
    board = pcbnew.LoadBoard(str(pcb_path))
    for reference in ("U301", "J101", "FID1"):
        footprint = board.FindFootprintByReference(reference)
        footprint.SetPosition(pcbnew.VECTOR2I(0, 0))
        footprint.SetOrientationDegrees(0)
        pcbnew.FootprintSave(str(project / "duck.pretty"), footprint)
        output = project / "duck.pretty" / (str(footprint.GetFPID().GetLibItemName()) + ".kicad_mod")
        if not output.is_file():
            raise RuntimeError("Missing local footprint " + reference)
        parse(output.read_text(encoding="utf-8"))
    print("Updated fiducial placement, DNP, NC escaping, and local footprint libraries")


if __name__ == "__main__":
    main()
