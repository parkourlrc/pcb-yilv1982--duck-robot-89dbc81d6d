"""Keep the trimmed C309 outline in a matching project footprint and clear labels."""
import json
from pathlib import Path

import pcbnew

import pipeline
from add_i2c_pullups import vector
from enforce_manufacturing_text import EVIDENCE
from repair_release_metadata import properties, replace_children, set_property


NAME = "C_0805_2012Metric_LDO_ClearSilk"


def main():
    candidate_path = EVIDENCE / "candidate.json"
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    work = pipeline.managed(Path(candidate["project"]))
    library = work / "duck.pretty"
    if (EVIDENCE / "library-variant.json").exists():
        raise RuntimeError("Library variant already exists")
    board_path = work / (pipeline.STEM + ".kicad_pcb")
    board = pcbnew.LoadBoard(str(board_path))
    board.FindFootprintByReference("U803").Reference().SetLayer(pcbnew.B_Fab)
    board.FindFootprintByReference("J802").Reference().SetPosition(vector((160.42, 123.4)))
    capacitor = board.FindFootprintByReference("C309")
    capacitor.SetFPID(pcbnew.LIB_ID("duck", NAME))
    temporary = pcbnew.BOARD()
    duplicate = pcbnew.FOOTPRINT(capacitor)
    temporary.Add(duplicate)
    duplicate.SetPosition(vector((0, 0)))
    duplicate.Flip(duplicate.GetPosition(), pcbnew.FLIP_DIRECTION_TOP_BOTTOM)
    duplicate.SetOrientationDegrees(0)
    duplicate.SetReference("REF**")
    pcbnew.FootprintSave(str(library), duplicate)
    if not (library / (NAME + ".kicad_mod")).is_file():
        raise RuntimeError("Cannot save matching project footprint")
    pcbnew.SaveBoard(str(board_path), board)
    changed = []
    def update(node):
        if properties(node).get("Reference") != "C309":
            return False
        set_property(node, "Footprint", "duck:" + NAME)
        return True
    for path in work.glob("*.kicad_sch"):
        original = path.read_text(encoding="utf-8")
        modified = replace_children(original, "symbol", update)
        if modified != original:
            path.write_text(modified, encoding="utf-8")
            changed.append(path.name)
    if len(changed) != 1:
        raise RuntimeError("Expected exactly one C309 schematic instance")
    stock = pipeline.find_cli().parent.parent / "share/kicad/footprints/Capacitor_SMD.pretty/C_0805_2012Metric.kicad_mod"
    pipeline.write_json(EVIDENCE / "library-variant.json", {"reference": "C309", "before": "Capacitor_SMD:C_0805_2012Metric", "after": "duck:" + NAME,
        "source": str(stock), "source_sha256": pipeline.digest(stock), "variant_sha256": pipeline.digest(library / (NAME + ".kicad_mod")),
        "purpose": "One outline segment moved from silkscreen to Fab to clear the neighboring LDO; pads and component position unchanged",
        "schematic_changed": changed, "U803_reference_layer": "B.Fab", "J802_reference_position_mm": [160.42, 123.4]})
    reports, summary = pipeline.check(work)
    candidate["summary"] = str(reports / "summary.json")
    pipeline.write_json(candidate_path, candidate)
    print(json.dumps({"status": summary["status"], "drc": summary["drc"], "netlist": summary["netlist_check"]["mismatches"]}))


if __name__ == "__main__":
    main()
