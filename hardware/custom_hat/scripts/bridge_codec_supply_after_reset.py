"""Restore the isolated codec 3V3 island using existing plated vias."""
import json
import argparse
from pathlib import Path
import shutil
import uuid

import pcbnew

import pipeline
from connect_codec_hardware_reset import EVIDENCE
from finish_ttl_local_bypass import route_layer


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repair-project-context", action="store_true")
    arguments = parser.parse_args()
    candidate_path = EVIDENCE / "candidate.json"
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    work = pipeline.managed(Path(candidate["project"]))
    path = work / (pipeline.STEM + ".kicad_pcb")
    contract_path = EVIDENCE / "change-contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    if candidate.get("promoted") or any(route["net"] != "CODEC_RST" for route in contract["routes"]):
        raise RuntimeError("Inspect the existing supply bridge before retry")
    backup = work.parent / "before-codec-supply-bridge.kicad_pcb"
    project = work / (pipeline.STEM + ".kicad_pro")
    original_project = pipeline.PRIMARY / project.name
    if arguments.repair_project_context:
        manifest = json.loads((work.parent / "manifest.json").read_text(encoding="utf-8"))
        if pipeline.fingerprints(pipeline.PRIMARY) != manifest["source_hashes"] or pipeline.digest(path) != pipeline.digest(backup):
            raise RuntimeError("Context recovery requires unchanged primary and restored candidate")
        shutil.copy2(project, EVIDENCE / "rejected-project-context.json")
        shutil.copy2(EVIDENCE / "supply-bridge-attempts.json", EVIDENCE / "rejected-project-context-attempts.json")
        shutil.copy2(original_project, project)
    else:
        if backup.exists():
            raise FileExistsError(backup)
        shutil.copy2(path, backup)
    project_digest = pipeline.digest(project)
    attempts = []
    for layer in ("F.Cu", "B.Cu", "In1.Cu"):
        for endpoint in ((158.94, 112.75), (156.04, 110.9), (156.13, 124.06)):
            shutil.copy2(backup, path)
            board = pcbnew.LoadBoard(str(path))
            try:
                route = route_layer(board, "+3V3", layer, .2, (155.79, 115.85), endpoint,
                                    EVIDENCE, search_margin=3, protect_i2s_reference=True)
            except RuntimeError as error:
                attempts.append({"layer": layer, "endpoint": endpoint, "error": str(error)})
                pipeline.write_json(EVIDENCE / "supply-bridge-attempts.json", attempts)
                continue
            pcbnew.SaveBoard(str(path), board)
            if pipeline.digest(project) != project_digest:
                raise RuntimeError("Saving candidate altered its project settings")
            report_path = work.parent / ("supply-bridge-" + uuid.uuid4().hex[:8] + ".json")
            pipeline.run_command([pipeline.find_cli(), "pcb", "drc", "--format", "json", "--severity-all", "--schematic-parity",
                                  "--refill-zones", "--save-board", "--output", report_path, path],
                                 EVIDENCE, "bridge-refill", [], report_path)
            drc = json.loads(report_path.read_text(encoding="utf-8"))
            counts = {key: len(drc[key]) for key in ("violations", "unconnected_items", "schematic_parity")}
            attempts.append({"layer": layer, "endpoint": endpoint, "route": route, "drc": counts, "report": str(report_path)})
            pipeline.write_json(EVIDENCE / "supply-bridge-attempts.json", attempts)
            if any(counts.values()):
                shutil.copy2(backup, path)
                continue
            contract["routes"].append(route)
            contract["supply_bridge"] = {"restore": ["U701.24", "U701.25"], "existing_vias_only": True,
                                         "source": [155.79, 115.85], "destination": endpoint}
            pipeline.write_json(contract_path, contract)
            print(json.dumps({"selected": route, "drc": counts}))
            return
    shutil.copy2(backup, path)
    raise RuntimeError("No accepted supply bridge; original candidate restored")


if __name__ == "__main__":
    main()
