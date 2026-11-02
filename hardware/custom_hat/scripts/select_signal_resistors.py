"""Apply manufacturer-documented resistor choices to a managed workspace."""
import argparse
from pathlib import Path

import pipeline
from repair_release_metadata import properties, replace_children, set_property


PARTS = {
    "R301": ("52.3k", "0805", "CRCW080552K3FKEA"),
    "R302": ("10k", "0805", "CRCW080510K0FKEA"),
    "R303": ("200k", "0805", "CRCW0805200KFKEA"),
    "R304": ("14k", "0805", "CRCW080514K0FKEA"),
    "R305": ("100k", "0805", "CRCW0805100KFKEA"),
    "R308": ("10k", "0402", "CRCW040210K0FKED"),
    "R310": ("100k", "0402", "CRCW0402100KFKED"),
    "R311": ("100k", "0402", "CRCW0402100KFKED"),
    "R312": ("2.2k", "0402", "CRCW04022K20FKED"),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    arguments = parser.parse_args()
    project = pipeline.managed(arguments.project)
    seen = {"schematic": set(), "pcb": set()}
    def update(node, board=False):
        fields = properties(node)
        reference = fields.get("Reference")
        if reference not in PARTS:
            return False
        value, package, mpn = PARTS[reference]
        footprint = str(node[1]) if board else fields.get("Footprint", "")
        if fields.get("Value") != value or ("R_" + package + "_") not in footprint:
            raise ValueError("Unexpected resistor configuration: " + reference)
        existing = fields.get("MPN", "")
        if existing and existing != mpn:
            raise ValueError("Conflicting selected MPN: " + reference)
        for key, choice in {
            "MPN": mpn, "Manufacturer": "Vishay",
            "Datasheet": "https://www.vishay.com/docs/20035/dcrcwe3.pdf",
            "BOM Comments": "1% 100ppm/K; D/CRCW e3 ordering table p2-3; design selected, stock not released",
        }.items():
            set_property(node, key, choice, board=board)
        seen["pcb" if board else "schematic"].add(reference)
        return True
    for path in sorted(project.glob("*.kicad_sch")):
        original = path.read_text(encoding="utf-8")
        modified = replace_children(original, "symbol", update)
        if modified != original:
            path.write_text(modified, encoding="utf-8")
    path = project / (pipeline.STEM + ".kicad_pcb")
    path.write_text(replace_children(path.read_text(encoding="utf-8"), "footprint", lambda node: update(node, True)), encoding="utf-8")
    if any(references != set(PARTS) for references in seen.values()):
        raise RuntimeError("Missing source or PCB resistor")
    pipeline.write_json(project.parent / "resistor-selection.json", {"source": "Vishay document 20035, 14-Apr-2026, p2-3", "parts": PARTS, "geometry_changed": False})
    print("Selected 9 existing resistors; R309 power jumper requires a separate current-rating choice")


if __name__ == "__main__":
    main()
