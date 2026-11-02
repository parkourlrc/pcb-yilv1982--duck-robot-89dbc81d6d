"""Route the TTL bypasses after a local AUDIO_AMP_EN detour in the existing candidate."""
import json
from pathlib import Path
import shutil

import pcbnew

import pipeline
import add_ttl_local_bypass as bypass
from add_i2c_pullups import vector
from fit_ldo_candidate import remove_objects
from finish_ttl_local_bypass import route_layer
from repair_release_metadata import properties, replace_children, set_property


AUDIO = "3a864dc5-2d7b-4abf-8269-3cd64192037c"


def main():
    candidate_path = bypass.EVIDENCE / "candidate.json"
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    work = pipeline.managed(Path(candidate["project"]))
    path = work / (pipeline.STEM + ".kicad_pcb")
    rejected = work.parent / "rejected-five-volt-relocation.kicad_pcb"
    if rejected.exists():
        raise FileExistsError("Inspect prior bottom bypass attempt")
    if pipeline.digest(pipeline.PRIMARY / path.name) != bypass.BASELINE:
        raise RuntimeError("Primary changed")
    shutil.copy2(path, rejected)
    shutil.copy2(work.parent / "before-ttl-local-relocation.kicad_pcb", path)
    remove_objects(path, {AUDIO})
    board = pcbnew.LoadBoard(str(path))
    capacitor = board.FindFootprintByReference("C329")
    capacitor.SetPosition(vector((134.2, 128.6)))
    capacitor.SetOrientationDegrees(180)
    selected = [{"reference": "C329", "device": "U801", "placement": {"position": [134.2, 128.6], "angle": 180}, "routes": []}]
    for net, cap_pin, device_pin in (("+3V3", "1", "5"), ("POWER_GND", "2", "3")):
        selected[0]["routes"].append(route_layer(board, net, "B.Cu", .2, bypass.pad_position(board, "C329", cap_pin), bypass.pad_position(board, "U801", device_pin)))
    branches = [route_layer(board, "AUDIO_AMP_EN", "B.Cu", .25, (130.1677, 127.955), (145.245, 127.955))]
    pcbnew.SaveBoard(str(path), board)
    pipeline.write_json(bypass.EVIDENCE / "bottom-bypass-stage.json", {"parts": selected, "branches": branches, "removed": [AUDIO]})
    print("C329 routed with AUDIO_AMP_EN detour", flush=True)
    positions = bypass.candidates(board, board.FindFootprintByReference("C330"), "U802")
    pipeline.write_json(bypass.EVIDENCE / "C330-bottom-stage-positions.json", positions)
    failures = []
    for position in positions:
        board = pcbnew.LoadBoard(str(path))
        capacitor = board.FindFootprintByReference("C330")
        capacitor.SetPosition(vector(position["position"]))
        capacitor.SetOrientationDegrees(position["angle"])
        try:
            routes = [route_layer(board, net, "B.Cu", .2, bypass.pad_position(board, "C330", cap_pin), bypass.pad_position(board, "U802", device_pin))
                      for net, cap_pin, device_pin in (("+3V3", "1", "5"), ("POWER_GND", "2", "3"))]
        except RuntimeError as error:
            failures.append({"position": position, "error": str(error)})
            pipeline.write_json(bypass.EVIDENCE / "C330-bottom-stage-failures.json", failures)
            continue
        pcbnew.SaveBoard(str(path), board)
        selected.append({"reference": "C330", "device": "U802", "placement": position, "routes": routes})
        print("C330 routed " + json.dumps(position), flush=True)
        break
    else:
        raise RuntimeError("No C330 same-side route")
    def metadata(node):
        if properties(node).get("Reference") not in bypass.PARTS:
            return False
        for key, value in bypass.FIELDS.items():
            set_property(node, key, value, board=True)
        return True
    path.write_text(replace_children(path.read_text(encoding="utf-8"), "footprint", metadata), encoding="utf-8")
    pipeline.write_json(bypass.EVIDENCE / "ttl-route-contract.json", {"parts": selected, "fields": bypass.FIELDS,
        "removed_original_objects": [AUDIO], "modified_original_objects": [], "branches": branches, "new_vias": 0,
        "failed_attempts": failures, "preserved": ["original footprints and pad geometry", "original pad connections", "all 5V copper", "OE logic", "project settings", "rules"]})
    reports, summary = pipeline.check(work)
    candidate["summary"] = str(reports / "summary.json")
    pipeline.write_json(candidate_path, candidate)
    print(json.dumps({"drc": summary["drc"], "erc": summary["erc"], "status": summary["status"]}))


if __name__ == "__main__":
    main()
