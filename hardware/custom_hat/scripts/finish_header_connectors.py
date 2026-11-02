"""Define the top-side screw-head envelope and finish connector silkscreen."""
import json
from pathlib import Path

import pcbnew
import pipeline
from generate_rev_a import children, first, q
from repair_release_metadata import properties, replace_children, set_property
from select_header_connectors import EVIDENCE


def main():
    candidate_path = EVIDENCE / "candidate.json"
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    work = pipeline.managed(Path(candidate["project"]))
    path = work / (pipeline.STEM + ".kicad_pcb")
    def update(node):
        if properties(node).get("Reference") not in {"H1", "H2"}:
            return False
        node[1] = q("duck:MountingHole_2.7_M2.5_Head4.5")
        for circle in children(node, "fp_circle"):
            layer = first(circle, "layer")[1]
            radius = 2.5 if layer in {"F.CrtYd", "F.Courtyard"} else 2.25
            first(circle, "center")[1:3] = [0, 0]
            first(circle, "end")[1:3] = [radius, 0]
        set_property(node, "Assembly Constraint", "Header-facing side: M2.5 socket head diameter <=4.5mm; no washer or hex spacer on this side; screw length set from final stack", board=True)
        first(node, "descr")[1] = q("2.7mm NPTH, top-side M2.5 socket head <=4.5mm plus 0.25mm radial assembly allowance")
        return True
    updated = replace_children(path.read_text(encoding="utf-8"), "footprint", update)
    def move_pin1(node):
        if len(node) > 1 and node[1] == "1":
            identifier = first(node, "uuid")
            if identifier and identifier[1] == "5947e2a9-a198-487b-9586-981b9efe27b4":
                first(node, "at")[1:3] = [108.32, 107.1]
                return True
        return False
    updated = replace_children(updated, "gr_text", move_pin1)
    path.write_text(updated, encoding="utf-8")
    board = pcbnew.LoadBoard(str(path))
    footprint = board.FindFootprintByReference("H1")
    footprint.SetPosition(pcbnew.VECTOR2I(0, 0))
    footprint.SetOrientationDegrees(0)
    pcbnew.FootprintSave(str(work / "duck.pretty"), footprint)
    reports, result = pipeline.check(work)
    candidate["summary"] = str(reports / "summary.json")
    pipeline.write_json(candidate_path, candidate)
    print(json.dumps({"drc": result["drc"], "status": result["status"]}))


if __name__ == "__main__":
    main()
